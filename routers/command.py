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


@command_router.post('/commands')
async def run_command(command: Command):
    target = command.cwd if command.cwd else MONITORED_FOLDER

    try:
        process = await asyncio.create_subprocess_shell(
            command.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=target,
        )

        stdout, stderr = await process.communicate()

        return {
            'exit_code': process.returncode,
            'stdout': stdout.decode('utf-8').strip(),
            'stderr': stderr.decode('utf-8').strip(),
        }

    except Exception as e:
        return {'exit_code': 1, 'stdout': '', 'stderr': str(e)}
