import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent
from watchfiles import awatch

load_dotenv()

folder_path = os.getenv('FOLDER_PATH')
if not folder_path:
    raise ValueError(
        'A variável FOLDER_PATH não foi encontrada no arquivo .env!'
    )

MONITORED_FOLDER = Path(folder_path)

watcher_router = APIRouter()


@watcher_router.get('/stream', response_class=EventSourceResponse)
async def watch_folder():
    async for changes in awatch(MONITORED_FOLDER):
        for change_type, file_path in changes:
            file_name = Path(file_path).name

            match change_type.name:
                case 'added':
                    message = f'Arquivo {file_name} foi adicionado!'
                    yield ServerSentEvent(data=message)

                case 'modified':
                    message = f'Arquivo {file_name} foi modificado!'
                    yield ServerSentEvent(data=message)

                case 'deleted':
                    message = f'Arquivo {file_name} foi deletado!'
                    yield ServerSentEvent(data=message)
