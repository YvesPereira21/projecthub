from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import command, metric, project, watcher

version = 'v1'

description = """
Uma aplicação para acompanhar os projetos pessoais, centralizando anotações
sobre os projetos no Obsidian (ideias, implementações, links, testes, etc.)
e fornecendo estatísticas como andamento do projeto (Em andamento, Concluído,
Parado, No papel), quantidade de pendências de acordo com as anotações
para cada projeto e uma tela de métricas que mostra um apanhado geral como:
total de projetos, quantidade para cada status do projeto, quantidade de
todas as pendências do projeto, um componente mostrando todas as tecnologias
usadas em projetos e a quantidade de vezes, e por fim um componente com uma
lista de todos as pendências dos projetos com o nome e o projeto a qual
pertence
"""

app = FastAPI(title='ProjectHub', description=description, version=version)

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

app.include_router(
    command.command_router,
    prefix=f'/api/{version}/commands',
    tags=['commands'],
)
app.include_router(
    metric.metric_router, prefix=f'/api/{version}/metrics', tags=['metrics']
)
app.include_router(
    project.project_router,
    prefix=f'/api/{version}/projects',
    tags=['projects'],
)
app.include_router(
    watcher.watcher_router,
    prefix=f'/api/{version}/watchers',
    tags=['watchers'],
)
