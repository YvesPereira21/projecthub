import asyncio
import codecs
import contextlib
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.command import Command

load_dotenv()

folder_path = os.getenv('FOLDER_PATH')
if not folder_path:
    raise ValueError(
        'A variável FOLDER_PATH não foi encontrada no arquivo .env!'
    )

MONITORED_FOLDER = Path(folder_path)
COMPOSE_FILES = (
    'docker-compose.yml',
    'docker-compose.yaml',
    'compose.yml',
    'compose.yaml',
)
HEARTBEAT_INTERVAL_SECONDS = 10.0

command_router = APIRouter()


def _get_subprocess_env() -> dict:
    """Prepare environment variables with GUI support for subprocesses."""
    env = dict(os.environ)
    env['BUILDKIT_PROGRESS'] = 'plain'
    display_env = os.getenv('DISPLAY_ENV') or env.get('DISPLAY') or ':0'
    env['DISPLAY'] = display_env
    if 'XAUTHORITY' not in env:
        xauth = Path.home() / '.Xauthority'
        if xauth.exists():
            env['XAUTHORITY'] = str(xauth)
    if 'XDG_RUNTIME_DIR' not in env:
        runtime_dir = Path(f'/run/user/{os.getuid()}')
        if runtime_dir.exists():
            env['XDG_RUNTIME_DIR'] = str(runtime_dir)
    return env


def _resolve_command(
    command: Command,
) -> tuple[str | None, Path, str | None]:
    """Resolve and validate the shell command and working directory."""
    target = command.cwd if command.cwd else MONITORED_FOLDER
    target_path = Path(target)
    cmd_str = command.command

    if cmd_str.startswith('code'):
        if not command.cwd:
            return (
                None,
                MONITORED_FOLDER,
                (
                    'O caminho do código (project_code_path) não foi '
                    'configurado no sobre.md deste projeto.'
                ),
            )
        if not target_path.exists() or not target_path.is_dir():
            return (
                None,
                target_path,
                (
                    f'O diretório do projeto não foi encontrado: {target}. '
                    'Verifique o project_code_path no sobre.md.'
                ),
            )
        return f'code "{target_path.resolve()}"', target_path, None

    if cmd_str == 'docker_run':
        has_compose = (
            bool(command.cwd)
            and target_path.is_dir()
            and any((target_path / f).exists() for f in COMPOSE_FILES)
        )
        if not has_compose:
            return (
                None,
                target_path,
                (
                    'Por favor, coloque o projeto no docker. '
                    'É necessário um docker-compose.yml '
                    'na raiz do projeto.'
                ),
            )
        return 'docker compose up -d --build', target_path, None

    return cmd_str, target_path, None


def _ndjson_line(payload: dict) -> bytes:
    """Serialize an event payload as a newline-delimited JSON line."""
    return (json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8')


async def _read_stream(
    stream: asyncio.StreamReader | None,
    kind: str,
    queue: asyncio.Queue[tuple[str, str]],
) -> None:
    """Read decoded text chunks incrementally and push them onto queue."""
    if stream is None:
        await queue.put((f'{kind}_eof', ''))
        return

    decoder = codecs.getincrementaldecoder('utf-8')('replace')
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        text = decoder.decode(chunk, final=False)
        if text:
            await queue.put((kind, text))

    tail = decoder.decode(b'', final=True)
    if tail:
        await queue.put((kind, tail))
    await queue.put((f'{kind}_eof', ''))


@command_router.post('')
async def run_command(command: Command):
    cmd_str, target_path, error_msg = _resolve_command(command)
    if error_msg or cmd_str is None:
        return {'exit_code': 1, 'stdout': '', 'stderr': error_msg or ''}

    try:
        process = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=target_path,
            env=_get_subprocess_env(),
        )

        stdout, stderr = await process.communicate()

        return {
            'exit_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace').strip(),
            'stderr': stderr.decode('utf-8', errors='replace').strip(),
        }

    except Exception as e:
        return {'exit_code': 1, 'stdout': '', 'stderr': str(e)}


async def _consume_process_queue(
    process: asyncio.subprocess.Process,
    queue: asyncio.Queue[tuple[str, str]],
) -> AsyncIterator[bytes]:
    """Yield stdout, stderr, heartbeat, and exit NDJSON events from queue."""
    open_streams = 2
    while open_streams > 0:
        try:
            kind, text = await asyncio.wait_for(
                queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS
            )
        except TimeoutError:
            yield _ndjson_line({'type': 'heartbeat'})
            continue

        if kind.endswith('_eof'):
            open_streams -= 1
        else:
            yield _ndjson_line({'type': kind, 'text': text})

    exit_code = await process.wait()
    yield _ndjson_line({'type': 'exit', 'exit_code': exit_code})


async def _stream_process_events(
    process: asyncio.subprocess.Process,
) -> AsyncIterator[bytes]:
    """Stream stdout/stderr NDJSON events and cancel readers on teardown."""
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
    readers = [
        asyncio.create_task(_read_stream(process.stdout, 'stdout', queue)),
        asyncio.create_task(_read_stream(process.stderr, 'stderr', queue)),
    ]
    try:
        async for payload in _consume_process_queue(process, queue):
            yield payload
    finally:
        for task in readers:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


@command_router.post('/stream')
async def stream_command(command: Command):
    """Execute a validated command and stream output events as NDJSON."""

    async def event_stream() -> AsyncIterator[bytes]:
        yield _ndjson_line({'type': 'start'})

        cmd_str, target_path, error_msg = _resolve_command(command)
        if error_msg or cmd_str is None:
            yield _ndjson_line({'type': 'stderr', 'text': error_msg or ''})
            yield _ndjson_line({'type': 'exit', 'exit_code': 1})
            return

        try:
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=target_path,
                env=_get_subprocess_env(),
            )
            async for payload in _stream_process_events(process):
                yield payload
        except Exception as e:
            yield _ndjson_line({'type': 'stderr', 'text': str(e)})
            yield _ndjson_line({'type': 'exit', 'exit_code': 1})

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return StreamingResponse(
        event_stream(), media_type='application/x-ndjson', headers=headers
    )
