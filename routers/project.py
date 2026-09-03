import os
from pathlib import Path
from typing import Optional

import frontmatter
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from schemas.project import (
    Note,
    NoteUpdate,
    Project,
    ProjectList,
)
from utils.helpers_methods import get_last_commit, time_formatter

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

project_router = APIRouter()
templates = Jinja2Templates(directory="templates")

def _load_frontmatter(file_path: Path) -> dict:
    try:
        post = frontmatter.load(file_path)
        return post.metadata
    except Exception:
        return {}


def _count_note_pendencies(note: Path) -> int:
    try:
        return note.read_text(encoding='utf-8').count('- [ ]')
    except Exception:
        return 0


@project_router.get('', response_class=HTMLResponse)
async def get_projects(request: Request, q: Optional[str] | None = None):
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    try:
        dir_items = [
            p
            for p in MONITORED_FOLDER.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao listar projetos: {str(e)}',
        )

    projects: list[ProjectList] = []
    for project in dir_items:
        if q and q.lower() not in project.name.lower():
            continue

        status_value = 'Ideia'
        technologies = []
        note_target = project / 'sobre.md'
        project_pendencies = 0
        
        try:
            for note in project.iterdir():
                if note.is_file() and note.suffix == '.md':
                    project_pendencies += _count_note_pendencies(note)
        except Exception:
            pass

        if note_target.exists() and note_target.is_file():
            note_info = _load_frontmatter(note_target)
            status_value = str(note_info.get('status', 'Ideia'))
            raw_techs = note_info.get('techs', [])
            if isinstance(raw_techs, list):
                technologies = [str(t) for t in raw_techs]

        rel_path = str(project.relative_to(MONITORED_FOLDER))
        projects.append(
            ProjectList(
                name=project.name,
                relative_path=rel_path,
                status=status_value,
                technologies=technologies,
                pendency_count=project_pendencies,
            )
        )

    selected_project = None
    if projects:
        try:
            resp = await get_project(request, projects[0].relative_path)
            selected_project = resp.context.get('project')
        except Exception:
            selected_project = None

    return templates.TemplateResponse(
        request=request,
        name="pages/projects.html",
        context={"projects": projects, "project": selected_project}
    )


@project_router.get('/{relative_path:path}', response_class=HTMLResponse)
async def get_project(request: Request, relative_path: str):
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    full_path = MONITORED_FOLDER / relative_path

    if not full_path.is_relative_to(MONITORED_FOLDER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Caminho inválido ou tentativa de acesso não autorizado.',
        )

    if not full_path.exists() or not full_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Projeto não encontrado.',
        )

    try:
        dir_notes = [
            n
            for n in full_path.iterdir()
            if n.is_file() and not n.name.startswith('.')
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao carregar detalhes do projeto: {str(e)}',
        )

    notes = []
    status_value = 'Ideia'
    technologies = []
    project_code_path = ''
    pendency_count = 0

    for note in dir_notes:
        if not (note.is_file() and note.suffix == '.md'):
            continue

        note_content = ''
        try:
            note_content = note.read_text(encoding='utf-8')
        except Exception:
            note_content = ''

        notes.append(
            Note(
                name=note.name,
                path=str(note.relative_to(MONITORED_FOLDER)),
                content=note_content,
            )
        )

        pendency_count += _count_note_pendencies(note)

        if note.name == 'sobre.md':
            info = _load_frontmatter(note)
            status_value = str(info.get('status', 'Ideia'))
            raw_techs = info.get('techs', [])
            if isinstance(raw_techs, list):
                technologies = [str(t) for t in raw_techs]

            project_code_path = str(info.get('project_code_path', ''))

    commit_timestamp = get_last_commit(project_code_path)
    formatted_commit_time = time_formatter(commit_timestamp)

    notes.sort(
        key=lambda n: (0 if n.name.lower() == 'sobre.md' else 1, n.name.lower())
    )

    project_data = Project(
        name=full_path.name,
        status=status_value,
        technologies=technologies,
        project_code_path=project_code_path,
        pendency_count=pendency_count,
        last_commit=formatted_commit_time,
        notes=notes,
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/project-details.html",
        context={"project": project_data}
    )


@project_router.put('/{relative_path:path}')
async def update_note(relative_path: str, note: NoteUpdate):
    if not MONITORED_FOLDER.exists() or not MONITORED_FOLDER.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=FOLDER_NOT_FOUND_MSG,
        )

    full_path = MONITORED_FOLDER / relative_path

    if not full_path.is_relative_to(MONITORED_FOLDER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Caminho inválido ou tentativa de acesso não autorizado.',
        )

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Arquivo não encontrado.',
        )

    try:
        full_path.write_text(note.content, encoding='utf-8')
        
        project_dir = full_path.parent
        project_pendencies = 0
        try:
            for n in project_dir.iterdir():
                if n.is_file() and n.suffix == '.md':
                    project_pendencies += _count_note_pendencies(n)
        except Exception:
            pass

        return {
            'status': 'success',
            'message': f'Arquivo {full_path.name} atualizado!',
            'pendency_count': project_pendencies,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao salvar arquivo: {str(e)}',
        )
