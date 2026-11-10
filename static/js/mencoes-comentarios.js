/**
 * Sistema de Menções (@username) nos Comentários - LIVRE DIA
 *
 * Funcionalidades:
 * - Detecta @ no textarea de comentários
 * - Busca usuários via AJAX em tempo real
 * - Exibe dropdown autocomplete responsivo
 * - Navegação: ENTER/TAB (confirmar), ESC/click-fora (cancelar), Setas (navegar)
 * - Totalmente responsivo: desktop (teclado) + mobile (touch)
 *
 * @version 1.0
 * @date 2025-11-08
 */

class SistemaMencoes {
    constructor(textareaId) {
        this.textarea = document.getElementById(textareaId);
        if (!this.textarea) {
            console.warn('Sistema de Menções: Textarea não encontrado:', textareaId);
            return;
        }

        this.dropdown = null;
        this.usuarios = [];
        this.indiceAtivo = -1;
        this.posicaoMencao = -1;
        this.debounceTimer = null;

        this.init();
    }

    init() {
        console.log('Sistema de Menções inicializado');

        // Criar dropdown
        this.criarDropdown();

        // Event listeners
        this.textarea.addEventListener('input', this.onInput.bind(this));
        this.textarea.addEventListener('keydown', this.onKeyDown.bind(this));
        document.addEventListener('click', this.onClickFora.bind(this));

        // Reposicionar dropdown ao fazer scroll ou resize
        window.addEventListener('scroll', () => {
            if (!this.dropdown.classList.contains('hidden')) {
                this.posicionarDropdown();
            }
        }, true); // useCapture=true para pegar scroll de qualquer elemento

        window.addEventListener('resize', () => {
            if (!this.dropdown.classList.contains('hidden')) {
                this.posicionarDropdown();
            }
        });
    }

    criarDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.id = `autocomplete-mencoes-${this.textarea.id}`;
        this.dropdown.className = 'hidden fixed bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto';
        this.dropdown.style.zIndex = '9999'; // Z-index muito alto para ficar sempre visível
        this.dropdown.style.webkitOverflowScrolling = 'touch'; // iOS smooth scroll
        this.dropdown.style.touchAction = 'manipulation'; // Prevenir zoom em double-tap

        // Adicionar ao body (não ao parent do textarea) para evitar problemas de overflow
        document.body.appendChild(this.dropdown);
    }

    onInput(e) {
        const texto = this.textarea.value;
        const cursorPos = this.textarea.selectionStart;

        // Buscar @ antes do cursor
        const textoAntesCursor = texto.substring(0, cursorPos);
        const ultimoArroba = textoAntesCursor.lastIndexOf('@');

        if (ultimoArroba !== -1) {
            // Extrair termo de busca após @
            const termoBusca = textoAntesCursor.substring(ultimoArroba + 1);

            // Se termo não contém espaço ou quebra de linha (ainda está digitando username)
            // Permite letras, números, underscores e hífens
            if (!termoBusca.includes(' ') && !termoBusca.includes('\n')) {
                this.posicaoMencao = ultimoArroba;

                // Debounce para não fazer requisição a cada tecla
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.buscarUsuarios(termoBusca);
                }, 150); // 150ms de delay
                return;
            }
        }

        // Fechar dropdown se não há menção ativa
        this.fecharDropdown();
    }

    async buscarUsuarios(termo) {
        try {
            const response = await fetch(`/texto/api/usuarios/buscar/?q=${encodeURIComponent(termo)}`);

            if (!response.ok) {
                throw new Error('Erro ao buscar usuários');
            }

            const data = await response.json();
            this.usuarios = data.usuarios || [];
            this.renderizarDropdown();
        } catch (error) {
            console.error('Erro ao buscar usuários:', error);
            this.fecharDropdown();
        }
    }

    renderizarDropdown() {
        if (this.usuarios.length === 0) {
            this.fecharDropdown();
            return;
        }

        this.indiceAtivo = 0;

        let html = '<div class="p-1">';
        this.usuarios.forEach((usuario, index) => {
            const activeClass = index === 0 ? 'bg-orange-50 dark:bg-orange-900/20' : '';

            // Determinar quais badges mostrar
            const badgeAutor = usuario.role === 'AUTOR' ?
                '<img src="/static/img/badge_autor.png" alt="Autor" title="Autor Verificado" class="w-3 h-3 inline-block">' : '';

            const badgeAdmin = (usuario.role === 'ADMIN' || usuario.is_admin) ?
                '<img src="/static/img/badge_administrador.png" alt="Admin" title="Administrador" class="w-3 h-3 inline-block">' : '';

            html += `
                <div class="usuario-item flex items-center gap-2 p-1.5 rounded cursor-pointer hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors ${activeClass}"
                     data-index="${index}"
                     data-username="${this.escapeHtml(usuario.username)}">
                    <img src="${this.escapeHtml(usuario.avatar_url)}"
                         class="w-5 h-5 rounded-full object-cover flex-shrink-0"
                         alt="${this.escapeHtml(usuario.username)}"
                         loading="lazy">
                    <div class="flex-1 min-w-0">
                        <div class="font-semibold text-xs text-gray-900 dark:text-gray-100 truncate flex items-center gap-1">
                            <span>@${this.escapeHtml(usuario.username)}</span>
                            ${badgeAutor}
                            ${badgeAdmin}
                        </div>
                        <div class="text-[10px] text-gray-600 dark:text-gray-400 truncate">
                            ${this.escapeHtml(usuario.nome_completo)}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        this.dropdown.innerHTML = html;

        // Posicionar dropdown (fixed position calculada)
        this.posicionarDropdown();

        this.dropdown.classList.remove('hidden');

        // Event listeners para click/tap
        this.dropdown.querySelectorAll('.usuario-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const username = item.dataset.username;
                this.selecionarUsuario(username);
            });
        });
    }

    posicionarDropdown() {
        // Calcular posição do textarea na tela
        const rect = this.textarea.getBoundingClientRect();

        // Posicionar dropdown logo abaixo do textarea
        // Como o dropdown tem position: fixed, não precisa somar scroll
        this.dropdown.style.left = rect.left + 'px';
        this.dropdown.style.top = rect.bottom + 'px';
        this.dropdown.style.width = rect.width + 'px';
    }

    onKeyDown(e) {
        if (this.dropdown.classList.contains('hidden')) return;

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navegarDropdown(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navegarDropdown(-1);
                break;
            case 'Enter':
            case 'Tab':
                e.preventDefault();
                const username = this.usuarios[this.indiceAtivo]?.username;
                if (username) this.selecionarUsuario(username);
                break;
            case 'Escape':
                e.preventDefault();
                this.fecharDropdown();
                break;
        }
    }

    navegarDropdown(direcao) {
        // Atualizar índice ativo
        this.indiceAtivo = Math.max(0, Math.min(this.usuarios.length - 1, this.indiceAtivo + direcao));

        // Atualizar visual
        this.dropdown.querySelectorAll('.usuario-item').forEach((item, index) => {
            if (index === this.indiceAtivo) {
                item.classList.add('bg-orange-50', 'dark:bg-orange-900/20');
                // Scroll suave para o item ativo
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('bg-orange-50', 'dark:bg-orange-900/20');
            }
        });
    }

    selecionarUsuario(username) {
        const texto = this.textarea.value;
        const antes = texto.substring(0, this.posicaoMencao);
        const depois = texto.substring(this.textarea.selectionStart);

        // Inserir @username + espaço
        this.textarea.value = antes + '@' + username + ' ' + depois;

        // Posicionar cursor após menção
        const novaPosicao = antes.length + username.length + 2; // +2 para @ e espaço
        this.textarea.setSelectionRange(novaPosicao, novaPosicao);
        this.textarea.focus();

        this.fecharDropdown();
    }

    fecharDropdown() {
        this.dropdown.classList.add('hidden');
        this.dropdown.innerHTML = '';
        this.usuarios = [];
        this.indiceAtivo = -1;
    }

    onClickFora(e) {
        // Fechar dropdown se click/tap foi fora dele e do textarea
        if (!this.dropdown.contains(e.target) && e.target !== this.textarea) {
            this.fecharDropdown();
        }
    }

    // Utilitário: escape HTML para prevenir XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar ao carregar página
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar menções em todos os textareas de comentários (principal + respostas)
    inicializarMencoesEmTextareas();

    // Observar quando novos formulários de resposta são exibidos (Alpine.js toggle)
    observarNovosTextareas();
});

/**
 * Inicializa sistema de menções em todos os textareas existentes.
 */
function inicializarMencoesEmTextareas() {
    const textareas = document.querySelectorAll('textarea[name="conteudo"]');

    textareas.forEach((textarea, index) => {
        // Evitar inicializar múltiplas vezes
        if (textarea.dataset.mencoesInicializadas === 'true') {
            return;
        }

        // Adicionar ID único se não existir
        if (!textarea.id) {
            textarea.id = `textarea-comentario-${index}-${Date.now()}`;
        }

        // Inicializar sistema de menções
        new SistemaMencoes(textarea.id);

        // Marcar como inicializado
        textarea.dataset.mencoesInicializadas = 'true';
    });
}

/**
 * Observa mutações no DOM para detectar novos textareas (formulários de respostas).
 */
function observarNovosTextareas() {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            // Verificar se houve mudança de classes (Alpine.js remove 'hidden')
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                const target = mutation.target;

                // Se é um formulário de resposta que foi exibido
                if (target.classList && !target.classList.contains('hidden')) {
                    // Tentar encontrar textarea dentro deste elemento
                    const textarea = target.querySelector('textarea[name="conteudo"]');
                    if (textarea && textarea.dataset.mencoesInicializadas !== 'true') {
                        // Inicializar menções neste novo textarea
                        if (!textarea.id) {
                            textarea.id = `textarea-resposta-${Date.now()}`;
                        }
                        new SistemaMencoes(textarea.id);
                        textarea.dataset.mencoesInicializadas = 'true';
                    }
                }
            }
        });
    });

    // Observar todo o body
    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class'],
        subtree: true
    });
}
