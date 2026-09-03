document.addEventListener('DOMContentLoaded', () => {
    setupSidebarNav();
    projectSelection();
    fileSelection();
    modeSelection();
    setupAutoSave();
    setupSSE();
    setupSearch();
    renderMarkdown();
})

function setupSidebarNav() {
    const navItems = document.querySelectorAll('.sidebar-nav div');
    const mainViewport = document.querySelector('main.main-viewport');
    if (!mainViewport || navItems.length === 0) return;

    navItems.forEach(item => {
        item.addEventListener('click', async () => {
            if (item.classList.contains('active')) return;

            navItems.forEach(n => {
                n.classList.remove('active');
                n.classList.add('text-slate-400');
            });
            item.classList.add('active');
            item.classList.remove('text-slate-400');

            const view = item.getAttribute('data-view') || item.querySelector('span')?.innerText.trim().toLowerCase();

            if (view === 'dashboard' || view?.includes('dashboard')) {
                try {
                    const response = await axios.get('/api/v1/metrics');
                    mainViewport.innerHTML = response.data;
                } catch (error) {
                    console.error('Erro ao carregar Dashboard com Axios:', error);
                }
            } else {
                const activeCard = document.querySelector('.project-card.active') || document.querySelector('.project-card');
                if (activeCard) {
                    const relativePath = activeCard.getAttribute('data-project-path');
                    if (relativePath) {
                        try {
                            const response = await axios.get(`/api/v1/projects/${relativePath}`);
                            mainViewport.innerHTML = response.data;
                            renderMarkdown();
                        } catch (error) {
                            console.error('Erro ao carregar projeto com Axios:', error);
                        }
                    }
                }
            }
        });
    });
}

function projectSelection() {
    const projects = document.querySelectorAll('.project-card');
    const mainViewport = document.querySelector('main.main-viewport');

    if (projects.length === 0 || !mainViewport) return;

    projects.forEach(card => {
        card.addEventListener('click', async () => {
            projects.forEach(c => c.classList.remove('active'));
            card.classList.add('active');

            // Garante que a aba 'Projetos' fique ativa caso estivesse no Dashboard
            const navProjects = document.querySelector('.sidebar-nav div[data-view="projects"]') || document.querySelector('.sidebar-nav div:first-child');
            const navDashboard = document.querySelector('.sidebar-nav div[data-view="dashboard"]') || document.querySelector('.sidebar-nav div:last-child');
            if (navProjects && navDashboard) {
                navProjects.classList.add('active');
                navProjects.classList.remove('text-slate-400');
                navDashboard.classList.remove('active');
                navDashboard.classList.add('text-slate-400');
            }

            const relativePath = card.getAttribute('data-project-path');
            if (!relativePath) return;

            try {
                const response = await axios.get(`/api/v1/projects/${relativePath}`);
                mainViewport.innerHTML = response.data;
                renderMarkdown();
            }
            catch (error) {
                console.error('Erro ao carregar detalhes do projeto com Axios:', error);
            }
        });
    });
}

function formatMarkdownContent(text) {
    if (!text) return '';
    const trimmed = text.trim();

    // If file has frontmatter AND content after it, show the body content
    const hasBodyAfterFrontmatter = /^---[\s\S]*?---\s*\S/.test(trimmed);
    if (hasBodyAfterFrontmatter) {
        return trimmed.replace(/^---[\s\S]*?---\s*/, '');
    }

    // If file contains ONLY frontmatter, convert it to clean readable markdown
    if (/^---[\s\S]*?---\s*$/.test(trimmed)) {
        return trimmed.replace(/^---\n?/, '').replace(/\n?---$/, '');
    }

    return text;
}

function renderMarkdown() {
    const editorArea = document.getElementById('editor-area');
    const previewArea = document.getElementById('preview-area');
    if (editorArea && previewArea && typeof marked !== 'undefined') {
        const cleanContent = formatMarkdownContent(editorArea.value);
        previewArea.innerHTML = marked.parse(cleanContent, { breaks: true });
    }
}

function setupSearch() {
    const searchInput = document.getElementById('input-search');
    const searchForm = document.querySelector('.search-form');

    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
        });
    }

    if (!searchInput) return;

    searchInput.addEventListener('input', (event) => {
        const query = event.target.value.toLowerCase();
        const projectCards = document.querySelectorAll('.project-card');

        projectCards.forEach(card => {
            const projectName = card.querySelector('.project-card-header span:first-child')?.innerText.toLowerCase() || '';
            if (projectName.includes(query)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    });
}



function fileSelection() {
    document.addEventListener('click', async (event) => {
        const clickedTab = event.target.closest('.files .tab-item');
        if (!clickedTab || clickedTab.classList.contains('active')) return;

        // Se houver um salvamento pendente, salva a aba atual ANTES de trocar
        if (saveTimeOut) {
            clearTimeout(saveTimeOut);
            await saveContent();
            saveTimeOut = null;
        }

        const allTabs = document.querySelectorAll('.files .tab-item');
        allTabs.forEach(t => {
            t.classList.remove('active');
            t.classList.add('text-slate-400');
        });

        clickedTab.classList.add('active');
        clickedTab.classList.remove('text-slate-400');

        const newContent = clickedTab.getAttribute('data-note-content');
        const editorArea = document.getElementById('editor-area');
        if (editorArea && newContent !== null) {
            editorArea.value = newContent;
            renderMarkdown();
        }
    });
}

function modeSelection() {
    document.addEventListener('click', (event) => {
        const clickedMode = event.target.closest('.see-file div');
        if (!clickedMode) return;

        const modes = document.querySelectorAll('.see-file div');
        modes.forEach(mode => {
            mode.classList.remove('active', 'text-slate-200');
            mode.classList.add('text-slate-400');
        })

        clickedMode.classList.add('active', 'text-slate-200');
        clickedMode.classList.remove('text-slate-400');

        const mode = clickedMode.getAttribute('data-mode');
        const workspace = document.querySelector('article.workspace');

        if (workspace && mode) {
            workspace.setAttribute('data-mode', mode);
        }

        const editorArea = document.getElementById('editor-area');
        if (editorArea && mode) {
            editorArea.readOnly = (mode !== 'edit');
        }

        renderMarkdown();
    })
}

let saveTimeOut = null;

function setupAutoSave() {
    document.addEventListener('input', (event) => {
        if (event.target.id === 'editor-area') {
            renderMarkdown(); // Atualiza o preview de markdown em tempo real

            clearTimeout(saveTimeOut);

            saveTimeOut = setTimeout(async () => {
                await saveContent();
            }, 3000);
        }
    });
}

async function saveContent() {
    const activeTab = document.querySelector('.files .tab-item.active');
    const modeSelected = document.querySelector('.see-file div.active')?.dataset.mode;
    const editorArea = document.getElementById('editor-area');

    if (!activeTab || !editorArea || modeSelected !== 'edit') return;

    const notePath = activeTab.dataset.notePath;
    const newContent = editorArea.value;

    try {
        const response = await axios.put(`/api/v1/projects/${notePath}`, {
            content: newContent
        });
        activeTab.setAttribute('data-note-content', newContent);

        // Atualiza a contagem de pendências após 6 segundos
        setTimeout(() => {
            const pendencyCount = response.data.pendency_count;
            if (pendencyCount !== undefined) {
                // Atualiza na barra lateral
                const activeProjectCard = document.querySelector('.project-card.active');
                if (activeProjectCard) {
                    const pendencySpan = activeProjectCard.querySelector('.pendency-count');
                    if (pendencySpan) {
                        pendencySpan.innerText = `${pendencyCount} pendência(s)`;
                    }
                }

                // Atualiza no painel principal
                const pendencyBadge = document.getElementById('pendency-badge');
                if (pendencyBadge) {
                    const countText = pendencyBadge.querySelector('.pendency-count-text');
                    if (countText) countText.innerText = `${pendencyCount} pendência(s)`;

                    if (pendencyCount > 0) {
                        pendencyBadge.classList.remove('!hidden');
                    } else {
                        pendencyBadge.classList.add('!hidden');
                    }
                }
            }
        }, 2000);

        // Aplica as cores e remove a borda inferior:
        const classes = [
            '!bg-cyan-500/15',
            '!ring-1',
            '!ring-cyan-500/30',
            '!text-cyan-400',
            '!border-b-transparent',
            'transition-all',
            'duration-500'
        ];
        activeTab.classList.add(...classes);

        setTimeout(() => {
            // Remove as classes suavemente ao terminar
            activeTab.classList.remove(...classes);
        }, 1500);
    } catch (error) {
        console.error('Erro ao salvar automaticamente:', error);
        alert('Erro ao salvar automaticamente.');
    }
}

function setupSSE() {
    const eventSource = new EventSource('/api/v1/watchers/stream');

    eventSource.onmessage = async (event) => {
        try {
            const data = JSON.parse(event.data);
            const activeTab = document.querySelector('.files .tab-item.active');
            const activeProjectCard = document.querySelector('.project-card.active');
            const workspace = document.querySelector('article.workspace');
            const mode = workspace ? workspace.getAttribute('data-mode') : 'view';

            if (activeProjectCard && activeTab && mode !== 'edit') {
                const projectPath = activeProjectCard.getAttribute('data-project-path');

                if (data.file && data.file.startsWith(projectPath)) {
                    const activeTabName = activeTab.querySelector('span') ? activeTab.querySelector('span').innerText : '';

                    const mainViewport = document.querySelector('main.main-viewport');
                    const response = await axios.get(`/api/v1/projects/${projectPath}`);
                    mainViewport.innerHTML = response.data;

                    // Restaurar estado (aba e modo)
                    const newWorkspace = document.querySelector('article.workspace');
                    if (newWorkspace) newWorkspace.setAttribute('data-mode', mode);

                    const newTabs = document.querySelectorAll('.files .tab-item');
                    newTabs.forEach(tab => {
                        const span = tab.querySelector('span');
                        if (span && span.innerText === activeTabName) {
                            newTabs.forEach(t => {
                                t.classList.remove('active');
                                t.classList.add('text-slate-400');
                            });
                            tab.classList.add('active');
                            tab.classList.remove('text-slate-400');

                            const editorArea = document.getElementById('editor-area');
                            if (editorArea) {
                                editorArea.value = tab.getAttribute('data-note-content');
                                editorArea.readOnly = (mode !== 'edit');
                            }
                        }
                    });

                    renderMarkdown();
                }
            }
        } catch (e) {
            // Ignorar mensagens que não sejam JSON estruturado do watcher
        }
    };
}

// Floating Terminal Logic
function toggleTerminal() {
    const terminal = document.getElementById('terminalOverlay');
    if (terminal) terminal.classList.toggle('terminal-open');
}

async function runCmd(cmd, cwd = '') {
    const terminal = document.getElementById('terminalOverlay');
    const logs = document.getElementById('terminalLogs');
    
    if (terminal && !terminal.classList.contains('terminal-open')) {
        toggleTerminal();
    }
    
    if (logs) {
        let displayCmd = cmd === 'docker_run' ? 'docker compose up -d --build' : cmd;
        logs.innerHTML += `<div class="mb-[6px] text-slate-100 font-semibold">$ ${displayCmd}</div>`;
        if (cmd === 'docker_run') {
            logs.innerHTML += `<div class="mb-[6px] text-teal-400 font-mono text-xs"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Iniciando containers Docker em background...</div>`;
        }
        logs.scrollTop = logs.scrollHeight;
        
        try {
            const response = await axios.post('/api/v1/commands', {
                command: cmd,
                cwd: cwd || null
            });
            
            const data = response.data;
            if (data.stdout) {
                logs.innerHTML += `<div class="mb-[6px] text-slate-300 text-xs whitespace-pre-wrap">${data.stdout}</div>`;
            }
            if (data.stderr) {
                let colorClass = data.exit_code === 0 ? 'text-slate-400 text-xs' : 'text-amber-400 text-xs';
                logs.innerHTML += `<div class="mb-[6px] ${colorClass} whitespace-pre-wrap">${data.stderr}</div>`;
            }
            
            if (data.exit_code === 0) {
                if (cmd === 'docker_run') {
                    logs.innerHTML += `<div class="mb-[6px] text-emerald-400 font-semibold flex items-center gap-1.5"><i class="fa-solid fa-circle-check"></i> [DOCKER] A aplicação Docker está rodando com sucesso!</div>`;
                } else if (cmd.startsWith('code')) {
                    logs.innerHTML += `<div class="mb-[6px] text-emerald-400">[OK] VSCode aberto com sucesso.</div>`;
                } else {
                    logs.innerHTML += `<div class="mb-[6px] text-emerald-400">[OK] Comando executado com sucesso.</div>`;
                }
            } else {
                logs.innerHTML += `<div class="mb-[6px] text-red-500">[ERRO] Falha ao executar. Código: ${data.exit_code}</div>`;
            }
        } catch (error) {
            let errorMsg = 'Erro de comunicação com a API local.';
            if (error.response?.data?.stderr) {
                errorMsg = error.response.data.stderr;
            } else if (error.response?.data?.detail) {
                errorMsg = error.response.data.detail;
            } else if (error.message) {
                errorMsg = error.message;
            }
            logs.innerHTML += `<div class="mb-[6px] text-red-500 whitespace-pre-wrap">[FALHA] ${errorMsg}</div>`;
            console.error(error);
        }
        
        logs.scrollTop = logs.scrollHeight;
    }
}

function clearLogs() {
    const logs = document.getElementById('terminalLogs');
    if (logs) logs.innerHTML = '';
}