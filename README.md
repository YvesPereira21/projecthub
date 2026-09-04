# Projecthub

O **ProjectHub** é uma aplicação web feita sob medida para desenvolvedores centralizarem e acompanharem a evolução de seus projetos pessoais. Ele se integra diretamente ao seu cofre de anotações do **Obsidian** (ou qualquer pasta com arquivos Markdown/Texto), unindo documentação, cálculo automático de métricas e status com base no histórico real de commits do Git e um terminal integrado para comandos rápidos.

---

## Funcionalidades principais

- **Dashboard com métricas em tempo real:**
  - Quantidade total de projetos monitorados;
  - Contagem por status: *Em desenvolvimento*, *Concluído*, *Parado* e *Ideia*;
  - Total geral de pendências abertas;
  - Gráfico/lista de tecnologias mais utilizadas entre todos os projetos;
  - Painel consolidado com todas as tarefas pendentes de todos os projetos em um só lugar.
- **Gerenciamento de projetos através de notas:**
  - Leitura estruturada de pastas de projetos;
  - Suporte completo a arquivos `.md` e `.txt`;
  - A nota `sobre.md` é sempre priorizada no topo da listagem;
  - Visualização formatada de Markdown e editor com auto-save em tempo real;
  - Preservação inteligente de frontmatter YAML.
- **Status dinâmico:**
  - O status é calculado e sincronizado automaticamente no frontmatter da nota `sobre.md`:
    - **Concluído:** Todas as pendências foram concluídas e o último commit no Git foi realizado há menos de 30 dias.
    - **Em desenvolvimento:** Possui pendências abertas e commits recentes (últimos 30 dias).
    - **Parado:** Possui pendências abertas, mas o último commit foi realizado há mais de 30 dias.
    - **Ideia:** O projeto ainda não possui repositório Git iniciado ou commits registrados.
- **Atualização em tempo real via SSE:**
  - Monitoramento da pasta de anotações via `watchfiles` e Server-Sent Events (SSE). Quando você altera uma nota no Obsidian ou no disco, o frontend atualiza instantaneamente sem necessidade de recarregamento manual.
- **Terminal flutuante:**
  - Permite rodar comandos rápidos de terminal direto na interface;
  - Atalho inteligente `docker_run` para subir projetos no Docker com `docker compose up -d --build`.

---

## Tecnologias utilizadas

- **Backend:**
  - [Python 3.12+](https://www.python.org/)
  - [FastAPI](https://fastapi.tiangolo.com/) (Framework web moderno e assíncrono)
  - [Uvicorn](https://www.uvicorn.org/) (Servidor ASGI)
  - [Watchfiles](https://watchfiles.helpmanual.io/) (Monitoramento assíncrono de arquivos via kernel/inotify)
  - [python-frontmatter](https://github.com/eyeseast/python-frontmatter) (Parsing e manipulação de frontmatter YAML)
  - [Jinja2](https://palletsprojects.com/p/jinja/) (Renderização de templates HTML)
  - [Poetry](https://python-poetry.org/) (Gerenciamento de dependências e ambientes virtuais)
- **Frontend:**
  - [Tailwind CSS](https://tailwindcss.com/)
  - [Axios](https://axios-http.com/)
  - [FontAwesome](https://fontawesome.com/)
  - Vanilla JavaScript & Showdown Parser

---

## Estrutura das anotações dos projetos

O ProjectHub espera que a pasta configurada em `FOLDER_PATH` contenha subpastas para cada projeto:

```text
seu-cofre-de-notas/
├── meu-projeto-1/
│   ├── sobre.md       <-- Arquivo principal dos metadados do seu projeto
│   ├── backlog.md
│   └── arquitetura.txt
└── meu-projeto-2/
    ├── sobre.md
    └── notas.md
```

### Exemplo de `sobre.md`:
```markdown
---
status: Em desenvolvimento
techs:
  - Python
  - FastAPI
  - Docker
  - Tailwind
project_code_path: /home/seu_usuario/caminho/para/seu/projeto/meu-projeto-1
---

# Sobre o projeto
Descrição geral do projeto...

## Pendências
- [ ] Implementar autenticação JWT
- [x] Configurar banco de dados PostgreSQL
```

- **`project_code_path`:** Caminho absoluto no seu computador onde fica o código-fonte do projeto (onde está a pasta `.git`).
- **`- [ ]`:** Checkboxes desmarcados são contabilizados automaticamente como pendências.

### Avisos e regras importantes

> **1. Criação obrigatória do `sobre.md`:**
> Cada subpasta de projeto **deve obrigatoriamente** conter um arquivo chamado `sobre.md` em sua raiz. É nele que o ProjectHub busca os metadados do frontmatter YAML (`status`, `project_code_path`, `techs`). Sem esse arquivo, o projeto não terá tecnologias computadas e assumirá o status padrão `Ideia`.

> **2. Padronização estrita dos nomes de status:**
> O ProjectHub possui regras automatizadas para sincronizar o status do projeto. Os nomes dos status **devem ser escritos exatamente como estabelecido** (respeitando maiúsculas, minúsculas e acentuação):
> - `Em desenvolvimento`
> - `Concluído`
> - `Parado`
> - `Ideia`
> 
> *Atenção:* Grafias diferentes como `"Em Desenvolvimento"`, `"concluido"`, `"Concluido"`, `"finalizado"` ou `"Em andamento"` **não serão reconhecidas** pelo sistema de métricas e quebrarão os contadores do dashboard.

> **3. Requisito de Dockerfile e docker compose para execução:**
> Para que um projeto possa ser executado através do ProjectHub (por meio do comando `docker_run` no terminal flutuante), é fundamental que o repositório do projeto em questão possua um `Dockerfile` e um arquivo `docker-compose.yml` (ou `docker-compose.yaml`) na raiz do seu código-fonte (`project_code_path`). Caso esses arquivos não existam, o sistema impedirá a execução e exibirá uma mensagem solicitando a configuração do Docker no projeto.

---

## Instalação e execução local (modo desenvolvimento)

### 1. Clonar o repositório
```bash
git clone https://github.com/YvesPereira21/projecthub.git
cd projecthub
```

### 2. Instalar as dependências

Você pode utilizar o **Poetry** (gerenciador padrão do projeto) ou o **pip** tradicional:

#### Opção A: usando Poetry (recomendado)
```bash
poetry install
```

#### Opção B: usando pip e ambiente virtual (`venv`)
```bash
# 1. Criar o ambiente virtual na raiz do projeto
python3 -m venv .venv

# 2. Ativar o ambiente virtual no Linux
source .venv/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente
Copie o exemplo de `.env` e configure o caminho absoluto da sua pasta de anotações:
```bash
cp .env-example .env
```
Edite o arquivo `.env`:
```ini
FOLDER_PATH="/home/seu_usuario/caminho/para/as/notas"
```

### 4. Executar em modo desenvolvimento

- **Se estiver usando Poetry:**
  ```bash
  poetry run task dev
  # ou diretamente: poetry run uvicorn main:app --reload
  ```

- **Se estiver usando pip (com o `.venv` ativado):**
  ```bash
  uvicorn main:app --reload
  ```

Acesse no navegador: **`http://localhost:8000`**

### 5. Comandos úteis (Taskipy - apenas Poetry)
- `poetry run task lint`: Executa a verificação estática de código com o `ruff`.
- `poetry run task format`: Formata o código de acordo com os padrões do projeto.

---

## Configuração permanente no Linux com systemd

Para que o **ProjectHub** fique sempre rodando em segundo plano no Linux (sem precisar de terminal aberto) e inicie automaticamente assim que a máquina ligar e conectar na rede, a configuração ideal é usar o **systemd a nível de usuário (`systemd --user`)**.

### Motivos:
- **Sem `sudo`:** Roda com o seu próprio usuário, evitando conflito de permissões nos arquivos do Obsidian.
- **Início no boot:** Inicia assim que a rede estiver online.
- **Auto-recuperação:** Reinicia sozinho caso ocorra qualquer falha inesperada.
- **Acesso nativo:** Consegue ler qualquer diretório do Git da sua máquina sem necessidade de configurações de volumes.

---

### Passo a passo de configuração

#### 1. Identificar o caminho do executável `uvicorn`

O systemd precisa do caminho absoluto do `uvicorn` para iniciar a aplicação:

- **Se você usou o Poetry:**
  Descubra o caminho do ambiente virtual com:
  ```bash
  poetry env info -p
  ```
  O executável estará em `<caminho_do_ambiente>/bin/uvicorn`.  
  *Exemplo:* `/home/seu_usuario/.cache/pypoetry/virtualenvs/projecthub-py3.12/bin/uvicorn`

- **Se você usou o pip (`.venv` na pasta do projeto):**
  O executável estará diretamente dentro da pasta `.venv`:  
  *Exemplo:* `/home/seu_usuario/caminho/para/seu/projeto/projecthub/.venv/bin/uvicorn`

---

#### 2. Criar o diretório de serviços do usuário
```bash
mkdir -p ~/.config/systemd/user
```

---

#### 3. Criar o arquivo de serviço
Crie o arquivo `~/.config/systemd/user/projecthub.service`:

```bash
nano ~/.config/systemd/user/projecthub.service
```

Cole o conteúdo abaixo (ajuste os caminhos para o seu usuário se necessário):

```ini
[Unit]
Description=ProjectHub - Painel de Projetos e Notas
# Aguarda a rede do computador estar completamente conectada e online
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/seu_usuario/caminho/para/seu/projeto/projecthub
EnvironmentFile=/home/seu_usuario/caminho/para/seu/projeto/projecthub/.env

# Opção 1: para quem instalou com Poetry
ExecStart=/home/seu_usuario/.cache/pypoetry/virtualenvs/projecthub-py3.12/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# Opção 2: para quem instalou com pip (descomente a linha abaixo e comente a de cima)
# ExecStart=/home/seu_usuario/caminho/para/seu/projeto/projecthub/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# Política de reinicialização automática em caso de falhas
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

> **Atenção ao `ExecStart` com pip:** caso você tenha utilizado o `pip` e criado o ambiente virtual na raiz do projeto (`.venv`), altere a linha `ExecStart` para utilizar o caminho do `uvicorn` da pasta `.venv` do projeto em vez do caminho do Poetry.

---

#### 4. Ativar e iniciar o serviço

Execute os comandos a seguir para recarregar o systemd, habilitar a inicialização automática e iniciar a aplicação:

```bash
# 1. Recarrega o daemon do systemd
systemctl --user daemon-reload

# 2. Habilita o serviço para iniciar no boot
systemctl --user enable projecthub.service

# 3. Inicia o serviço agora mesmo
systemctl --user start projecthub.service
```

---

#### 5. Permitir execução antes do login gráfico (`linger`)

Por padrão, serviços de usuário no Linux só disparam após você fazer o login manual na sessão gráfica. Para que o ProjectHub inicie **imediatamente após o boot da máquina** (assim que a rede conectar), execute:

```bash
loginctl enable-linger $USER
```

---

### Comandos de gerenciamento do serviço

| Ação | Comando |
| :--- | :--- |
| **Ver status da aplicação** | `systemctl --user status projecthub.service` |
| **Ver logs em tempo real** | `journalctl --user -u projecthub.service -f` |
| **Reiniciar a aplicação** | `systemctl --user restart projecthub.service` |
| **Parar a aplicação** | `systemctl --user stop projecthub.service` |
| **Desabilitar inicialização no boot** | `systemctl --user disable projecthub.service` |
