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


import json

@watcher_router.get('/stream', response_class=EventSourceResponse)
async def watch_folder():
    async for changes in awatch(MONITORED_FOLDER):
        for change_type, file_path in changes:
            try:
                rel_path = str(Path(file_path).relative_to(MONITORED_FOLDER))
            except ValueError:
                rel_path = Path(file_path).name

            event_data = {
                "type": change_type.name,
                "file": rel_path
            }
            yield ServerSentEvent(data=json.dumps(event_data))
