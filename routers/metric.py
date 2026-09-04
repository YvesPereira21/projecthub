import os
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from schemas.metric import ProjectMetrics, Technology
from utils.helpers_methods import (
    collect_project_data,
    get_last_commit,
)

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
templates = Jinja2Templates(directory="templates")


@metric_router.get('', response_class=HTMLResponse)
async def get_metrics(request: Request):
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

    tech_counter = Counter()
    all_pendencies = []

    for project in projects:
        total_projects += 1
        p_count, current_status, project_code_path = collect_project_data(
            project, tech_counter, all_pendencies
        )
        pendency_count += p_count

        if current_status not in project_statuses:
            project_statuses[current_status] = 0
        project_statuses[current_status] += 1

        if current_status == 'Em desenvolvimento':
            last_commit = get_last_commit(project_code_path)
            if last_commit == 0:
                project_statuses['Em desenvolvimento'] -= 1
                project_statuses['Ideia'] += 1
            elif (time_now - last_commit) > thirty_days:
                project_statuses['Em desenvolvimento'] -= 1
                project_statuses['Parado'] += 1

    tech_data = [
        Technology(name=name, count=quantity)
        for name, quantity in tech_counter.most_common()
    ]

    metrics_data = ProjectMetrics(
        total_projects=total_projects,
        in_progress_count=project_statuses.get('Em desenvolvimento', 0),
        completed_count=project_statuses.get('Concluído', 0),
        stopped_count=project_statuses.get('Parado', 0),
        ideas_count=project_statuses.get('Ideia', 0),
        pendency_count=pendency_count,
    )

    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context={
            "metrics": metrics_data,
            "technologies": tech_data,
            "pendencies": all_pendencies,
        }
    )
