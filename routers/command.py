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


@command_router.post('')
async def run_command(command: Command):
    target = command.cwd if command.cwd else MONITORED_FOLDER
    cmd_str = command.command

    if cmd_str == 'docker_run':
        target_path = Path(target)
        has_dockerfile = (target_path / 'Dockerfile').exists()
        has_compose = (target_path / 'docker-compose.yml').exists() or (target_path / 'docker-compose.yaml').exists()
        
        if has_dockerfile and has_compose:
            cmd_str = 'docker compose up -d --build'
        else:
            return {
                'exit_code': 1,
                'stdout': '',
                'stderr': 'Por favor, coloque o projeto no docker. É necessário um Dockerfile e um docker-compose.yml na raiz do projeto.'
            }

    try:
        process = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=target,
        )

        stdout, stderr = await process.communicate()

        return {
            'exit_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace').strip(),
            'stderr': stderr.decode('utf-8', errors='replace').strip(),
        }

    except Exception as e:
        return {'exit_code': 1, 'stdout': '', 'stderr': str(e)}
