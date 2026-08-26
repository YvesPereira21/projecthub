import os
import time
from collections import Counter
from pathlib import Path

import frontmatter
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status

from schemas.metric import Pendency, ProjectMetrics, Technology
from utils.helpers_methods import get_last_commit

load_dotenv()

folder_path = os.getenv('FOLDER_PATH')
if not folder_path:
    raise ValueError(
        'A variável FOLDER_PATH não foi encontrada no arquivo .env!'
    )

MONITORED_FOLDER = Path(folder_path)
FOLDER_NOT_FOUND_MSG = (
    'A pasta monitorada configurada no .env não existe no sistema.'
)

metric_router = APIRouter()


def _count_note_pendencies(note: Path) -> int:
    try:
        return note.read_text(encoding='utf-8').count('- [ ]')
    except Exception:
        return 0


def _load_frontmatter(file_path: Path) -> dict:
    try:
        post = frontmatter.load(file_path)
        return post.metadata
    except Exception:
        return {}


def _extract_pendencies(note: Path, project_name: str) -> list[Pendency]:
    try:
        content = note.read_text(encoding='utf-8')
    except Exception:
        return []

    results = []
    for line in content.splitlines():
        clean = line.strip()
        if clean.startswith(('- [ ]', '* [ ]')):
            text = clean[5:].strip()
            if text:
                results.append(Pendency(name=text, project_name=project_name))
    return results


@metric_router.get('', response_model=ProjectMetrics)
async def get_metrics():
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    project_statuses = {
        'Em desenvolvimento': 0,
        'Concluído': 0,
        'Parado': 0,
        'Ideia': 0,
    }

    total_projects = 0
    pendency_count = 0
    time_now = time.time()
    thirty_days = 30 * 24 * 60 * 60

    try:
        projects = [
            p
            for p in MONITORED_FOLDER.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao calcular métricas: {str(e)}',
        )

    for project in projects:
        total_projects += 1
        current_status = 'Ideia'
        project_code_path = ''

        for note in project.iterdir():
            if not (note.is_file() and note.suffix == '.md'):
                continue

            pendency_count += _count_note_pendencies(note)

            if note.name == 'sobre.md':
                info = _load_frontmatter(note)
                current_status = str(info.get('status', 'Ideia'))
                if current_status not in project_statuses:
                    project_statuses[current_status] = 0
                project_statuses[current_status] += 1
                project_code_path = str(info.get('project_code_path', ''))

        if current_status == 'Em desenvolvimento':
            last_commit = get_last_commit(project_code_path)
            if last_commit == 0:
                project_statuses['Em desenvolvimento'] -= 1
                project_statuses['Ideia'] += 1
            elif (time_now - last_commit) > thirty_days:
                project_statuses['Em desenvolvimento'] -= 1
                project_statuses['Parado'] += 1

    return ProjectMetrics(
        total_projects=total_projects,
        in_progress_count=project_statuses.get('Em desenvolvimento', 0),
        completed_count=project_statuses.get('Concluído', 0),
        stopped_count=project_statuses.get('Parado', 0),
        ideas_count=project_statuses.get('Ideia', 0),
        pendency_count=pendency_count,
    )


@metric_router.get('/technologies', response_model=list[Technology])
async def get_technologies_used():
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    technologies = Counter()
    try:
        projects = [
            p
            for p in MONITORED_FOLDER.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao buscar tecnologias: {str(e)}',
        )

    for project in projects:
        note_target = project / 'sobre.md'
        if note_target.exists() and note_target.is_file():
            info = _load_frontmatter(note_target)
            raw_techs = info.get('techs', [])
            if isinstance(raw_techs, list):
                for tech in raw_techs:
                    name = str(tech).strip()
                    if name:
                        technologies[name] += 1

    return [
        Technology(name=name, count=quantity)
        for name, quantity in technologies.most_common()
    ]


@metric_router.get('/pendencies', response_model=list[Pendency])
async def get_project_pendencies():
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    pendencies: list[Pendency] = []
    try:
        projects = [
            p
            for p in MONITORED_FOLDER.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao buscar pendências: {str(e)}',
        )

    for project in projects:
        for note in project.iterdir():
            if note.is_file() and note.suffix == '.md':
                pendencies.extend(_extract_pendencies(note, project.name))

    return pendencies
