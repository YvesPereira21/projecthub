import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter

from schemas.command import Command

load_dotenv()

folder_path = os.getenv('FOLDER_PATH')
if not folder_path:
    raise ValueError(
        'A variável FOLDER_PATH não foi encontrada no arquivo .env!'
    )

MONITORED_FOLDER = Path(folder_path)

command_router = APIRouter()


def _get_subprocess_env() -> dict:
    """Prepare environment variables with GUI support for subprocesses."""
    env = dict(os.environ)
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


@command_router.post('')
async def run_command(command: Command):
    target = command.cwd if command.cwd else MONITORED_FOLDER
    target_path = Path(target)
    cmd_str = command.command

    if cmd_str.startswith('code'):
        if not command.cwd:
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': (
                    'O caminho do código (project_code_path) não foi '
                    'configurado no sobre.md deste projeto.'
                ),
            }
        if not target_path.exists() or not target_path.is_dir():
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': (
                    f'O diretório do projeto não foi encontrado: {target}. '
                    'Verifique o project_code_path no sobre.md.'
                ),
            }
        cmd_str = f'code "{target_path.resolve()}"'

    elif cmd_str == 'docker_run':
        compose_files = (
            'docker-compose.yml',
            'docker-compose.yaml',
            'compose.yml',
            'compose.yaml',
        )
        has_compose = (
            bool(command.cwd)
            and target_path.is_dir()
            and any((target_path / f).exists() for f in compose_files)
        )

        if has_compose:
            cmd_str = 'docker compose up -d --build'
        else:
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': (
                    'Por favor, coloque o projeto no docker. '
                    'É necessário um docker-compose.yml '
                    'na raiz do projeto.'
                ),
            }

    try:
        process = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=target,
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
