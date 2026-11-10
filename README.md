# LIVRE DIA

> Plataforma de curadoria de textos humanos autênticos: crônicas, poesias e ensaios escritos por pessoas, sem IA.

**Status: projeto descontinuado.** O LIVRE DIA ficou no ar em `livredia.com.br` por cerca de 12 meses e foi encerrado em novembro de 2026. O código completo está publicado aqui, sob licença AGPL-3.0, para que qualquer pessoa possa estudar, reutilizar ou dar continuidade ao projeto.

---

## O que é

O LIVRE DIA nasceu como um "oásis" em contraponto ao conteúdo gerado por inteligência artificial. A plataforma conectava **autores verificados** por curadoria manual a **leitores** que valorizam a escrita autêntica. O **Selo Livre de IA** era o pilar conceitual: uma declaração de confiança do autor de que o texto é integralmente humano.

A identidade visual segue uma estética "Naturalista Acadêmico", com tons terrosos, tipografia serifada e textura de papel.

## Funcionalidades

**Zona pública**
- Acervo de textos com busca, tags e temas
- Galeria de autores com perfis públicos (`/@usuario`)
- Leitura com 8 temas visuais (padrão, noturno, e-ink, jornal, envelhecido, CRT, arco-íris, paixão)
- Comentários com menções, favoritos, lidos, "ler depois" e cartão de biblioteca assinável
- Acervo de 179 textos de domínio público de autores clássicos brasileiros
- Páginas estáticas editáveis e formulário de contato
- PWA instalável com página offline

**Leitores**
- Cadastro com confirmação de e-mail ou login com Google
- Seguir autores, notificações, selos especiais
- Vilarejo Literário: chat em tempo real (WebSocket) entre "vizinhos literários" calculados por similaridade de gosto, com moradores permanentes, banimentos e histórico

**Autores**
- Painel com dashboard e estatísticas (Chart.js)
- Editor de texto rico (Quill) com imagens, vídeos e links
- Moderação dos próprios comentários, lista de seguidores
- Monetização por Pix com QR Code
- Sistema de convites para novos autores

**Administração**
- Gestão de autores, leitores, administradores, obras e temas
- Moderação global de comentários
- Comunicação geral por e-mail com rastreamento de abertura
- Configurações do sistema e páginas estáticas

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.13, Django 5.2 |
| Banco | PostgreSQL 17 |
| Tempo real | Django Channels, Daphne, Redis |
| Frontend | Tailwind CSS 4, Alpine.js, HTMX, Quill.js, Chart.js |
| Auth | django-allauth (Google), Cloudflare Turnstile |
| Produção | Nginx + Gunicorn (HTTP) + Daphne (WebSocket), Ubuntu |

## Estrutura

```
apps/
  core/          home, páginas estáticas, notificações, temas de leitura, Pix
  usuarios/      modelo de usuário, autenticação, perfis, seguir autores, logs
  textos/        textos, tags, favoritos, lidos, cartão de biblioteca
  comentarios/   comentários e menções
  painel_autor/  área do autor (dashboard, editor, moderação, monetização)
  painel_admin/  área administrativa (gestão global, convites, comunicação)
  vilarejo/      Vilarejo Literário (chat WebSocket, vizinhos, moderação)
config/          settings, urls, asgi/wsgi, middleware
templates/       templates HTML por app
static/          CSS (Tailwind + temas), JS, imagens, manifest PWA
contexto_projeto/  documentação de projeto (requisitos, design, roadmap, deploy)
```

## Rodando localmente

Pré-requisitos: Python 3.13, PostgreSQL, Redis, Node.js (só para recompilar o CSS).

```bash
# 1. Clonar e criar o ambiente
git clone https://github.com/ciniro/livredia.git
cd livredia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# edite .env com SECRET_KEY, credenciais do PostgreSQL etc.

# 3. Criar o banco e aplicar migrations
createdb db_livredia
python manage.py migrate

# 4. Criar um administrador
python manage.py criar_admin

# 5. (Opcional) Popular o banco com dados fictícios de teste
python manage.py populate_fase2

# 6. Rodar
python manage.py runserver
# http://127.0.0.1:8000/
```

O chat do Vilarejo precisa de Redis rodando em `localhost:6379`. Sem Redis, o restante do site funciona normalmente.

Para alterar estilos, recompile o Tailwind:

```bash
npm install
npm run css:build   # ou css:watch
```

## Deploy

Os arquivos de referência para produção estão em `contexto_projeto/`:

- `nginx-livredia.conf`: configuração do Nginx com proxy HTTP e WebSocket (`/ws/`)
- `daphne.service`: unidade systemd para o servidor ASGI
- `ANDROID.md`: plano de empacotamento como PWA + TWA para a Play Store

Em produção o Django roda com `DEBUG=False`, o que ativa HTTPS obrigatório, HSTS e cookies seguros. Veja `config/settings.py`.

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| `contexto_projeto/GUIDELINES.md` | Especificação de requisitos e visão conceitual |
| `contexto_projeto/DESIGN.md` | Paleta, tipografia e decisões de UX |
| `contexto_projeto/ROADMAP.md` | Especificação do Vilarejo Literário |
| `contexto_projeto/PROGRESSO.md` | Histórico de fases e status final |
| `contexto_projeto/COMANDOS.md` | Comandos úteis de desenvolvimento |
| `contexto_projeto/GIT.md` e `WORKFLOW.md` | Fluxo de branches e protocolo de desenvolvimento |

## Sobre os dados

Este repositório contém apenas o **código**. O banco de dados de produção, com textos, autores e leitores, não está incluído por conter dados pessoais. Os 179 textos de domínio público foram cadastrados manualmente pela interface administrativa e também não acompanham o repositório.

## Licença

Distribuído sob a [GNU Affero General Public License v3.0](LICENSE). Você pode usar, modificar e redistribuir este software, inclusive como serviço web, desde que mantenha a mesma licença e disponibilize o código-fonte das suas modificações.

## Autor

Desenvolvido por **Ciniro Nametala** ([@ciniro](https://github.com/ciniro)), 2025–2026.
