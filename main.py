from fastapi import FastAPI

version = 'v1'

description = """
Uma API REST que mapeia pontos turísticos do estado da Paraíba
"""

app = FastAPI(
    title='Terras Paraibana', description=description, version=version
)


@app.get('/')
async def ola_mundo():
    return {'mensagem': 'ola_mundo'}
