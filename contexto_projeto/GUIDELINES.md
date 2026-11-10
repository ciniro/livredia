Assunto: Especificação de Requisitos de Software (ERS)
Projeto: LIVRE DIA
Arquitetura: Monolítico Moderno (Django)
Stack V1.0: Python 3.13.0, Django 5.2.7 (LTS), PostgreSQL 17.4, Tailwind CSS, HTMX, Alpine.js, Chart.js, Quill.js
Total de Telas: 22 (10 públicas, 5 autor, 7 admin)
Última Atualização: 26 de Outubro de 2025

IMPORTANTE: Este documento organiza as telas por ZONA funcional (Pública, Autor, Admin).
Para a SEQUÊNCIA DE DESENVOLVIMENTO por FASE, consulte CLAUDE.md.

1. Diretrizes Conceituais e Visão Geral
1.1. Conceito Central
O "LIVRE DIA" é uma plataforma de curadoria focada na autenticidade da produção textual humana (crônicas, poesias, ensaios). Funciona como um "oásis" em contraponto ao conteúdo gerado por IA, conectando autores verificados (curadoria manual) a leitores que valorizam a escrita autêntica. O "Selo Livre de IA" é um pilar conceitual, baseado na confiança e declaração do autor.

1.2. Identidade Visual
Estética: "Naturalista Acadêmico" / "Enciclopédia Vintage".

Paleta: Tons terrosos (Pergaminho #FDFBF6, Verde Floresta #3A4D39, Sépia #4F4A45, Preto Textual #1A1A1A).

Tipografia:

Display (Títulos): Fonte serifada, forte, clássica (estilo jornal).

Corpo (Leitura): Fonte serifada de alta legibilidade (ex: Literata, Merriweather) para conforto em leitura longa.

Responsividade: O livre dia deve ser totalmente responsivo se adaptando a telas mobile, tablets ou monitores caso a navegação seja feita via browser.

1.3. Filosofia de Arquitetura (Stack V1.0)
A arquitetura é um Monolítico Django com renderização no servidor (Server-Side Rendering - SSR) para garantir performance, simplicidade de deploy e SEO máximo nas páginas de conteúdo.

Backend: Python 3.13.0, Django 5.2.7 (LTS).

Banco de Dados: PostgreSQL 17.4.

Renderização: Django Template Engine (DTL).

CSS: Tailwind CSS. A identidade visual customizada exige um framework utility-first.

Ícones: Usar sempre que possível os ícones de https://heroicons.com/outline. Quando precisar ser um pouco mais criativo, usar os ícones da pasta static/img.

Interatividade (Client-side): Alpine.js. Usado para manipulações de DOM que não requerem o servidor (ex: abrir/fechar menus, dropdowns, e o Seletor de Tema de Leitura).

Interatividade (Server-driven): HTMX. Usado para interações de UI que atualizam partes da página (fragmentos de HTML) sem full refresh (ex: moderação de comentários, filtros de tabelas nos painéis de admin, envio de formulários).

Editor de Texto: Quill.js. Um editor JS moderno para o formulário do Autor. O Django salvará o HTML limpo gerado por ele.

Gráficos: Chart.js. Usado no Dashboard do Autor. O Django fornecerá os dados (JSON) via contexto do template.

Notificações Toast: Toastr.js. Usado em todo o projeto para exibir mensagens de feedback (sucesso, erro, aviso, info). Configuração: posição top-right, duração de 3 segundos, com barra de progresso e botão de fechar.

1.4. Plataformas de desenvolvimento

Versionamento: O projeto está versionado usando git e está sincronizado com um repositório privado no GitHub em https://github.com/ciniro/livredia. A branch principal se chama main.

Desenvolvimento: VSCode.

Ambiente: O sistema deve usar um ambiente virtual independente 'venv' python contendo todas as bibliotecas do projeto na pasta raiz.

2. Modelo de Dados (Estrutura models.py)
Abaixo está o esquema de dados essencial para o PostgreSQL, representado como modelos Django.

Python

# app/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Modelo de Usuário customizado.
    Armazena Leitores, Autores e Admins.
    """
    class Role(models.TextChoices):
        LEITOR = "LEITOR", "Leitor"
        AUTOR = "AUTOR", "Autor"
        ADMIN = "ADMIN", "Administrador"

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.LEITOR)
    
    # Perfil (comum a todos)
    foto = models.ImageField(upload_to='perfis/', null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    pais = models.CharField(max_length=100, null=True, blank=True)
    
    # Perfil (específico do Autor)
    bio = models.TextField(null=True, blank=True)
    pseudonimo = models.CharField(max_length=255, null=True, blank=True)
    email_contato = models.EmailField(null=True, blank=True) # E-mail público para contato
    telefone = models.CharField(max_length=20, null=True, blank=True)
    
    # Controle de Suspensão/Ativação
    # is_active (herdado do AbstractUser): False = conta suspensa, True = ativa
    # IMPORTANTE: is_active=False bloqueia login E oculta conteúdo nas queries públicas
    # Ver decisões 9.6-9.12 em CLAUDE.md para detalhes completos

    def get_display_name(self):
        # Lógica para retornar pseudônimo ou nome real
        return self.pseudonimo if self.pseudonimo else self.get_full_name()

NOTA TÉCNICA - EXCLUSÃO vs SUSPENSÃO:
======================================
1. EXCLUSÃO (user.delete()):
   - Direito ao esquecimento (LGPD/GDPR)
   - CASCADE DELETE: apaga textos, comentários, visualizações (TUDO)
   - Irreversível
   - Pode ser feita por: próprio usuário (área de configurações) ou admin

2. SUSPENSÃO (is_active=False):
   - Bloqueia login: mensagem "Conta suspensa, contate equipe"
   - Oculta conteúdo: textos/comentários somem das listagens públicas
   - Dados preservados: tudo permanece no banco
   - Reversível: admin pode reativar a qualquer momento
   - Apenas admin pode suspender/reativar

3. IMPLEMENTAÇÃO:
   - Queries públicas SEMPRE filtram: .filter(autor__is_active=True)
   - Admin vê TODOS os usuários (ativos + suspensos) com badges visuais
   - ForeignKeys configuradas com on_delete=models.CASCADE

class Tag(models.Model):
    """ Tags livres (Folksonomia) criadas pelos Autores """
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

class Texto(models.Model):
    """ A entidade principal: um texto publicado por um Autor """
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        PUBLICADO = "PUBLICADO", "Publicado"

    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='textos')
    titulo = models.CharField(max_length=255)
    subtitulo = models.CharField(max_length=255, null=True, blank=True)
    conteudo = models.TextField() # Armazena o HTML limpo gerado pelo Quill.js
    slug = models.SlugField(max_length=255, unique_for_date='data_publicacao')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    
    # Metadados
    tags = models.ManyToManyField(Tag, blank=True, related_name='textos')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_publicacao = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # O Selo
    selo_livre_ia = models.BooleanField(default=False)
    
    # Configurações de Interação
    permite_comentarios = models.BooleanField(default=True)
    moderacao_automatica = models.BooleanField(default=True) # Se false, requer aprovação manual
    permite_comentarios_anonimos = models.BooleanField(default=False)
    
    # Configuração de Autoria (preferência no momento da postagem)
    # ex: 'REAL', 'PSEUDONIMO', 'AMBOS'
    display_autoria = models.CharField(max_length=20, default='REAL')
    
    # Métricas (podem ser cacheadas aqui ou calculadas)
    # views_unicas = models.PositiveIntegerField(default=0)

class Comentario(models.Model):
    """ Comentários feitos nos Textos """
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADO = "APROVADO", "Aprovado"
        REJEITADO = "REJEITADO", "Rejeitado"

    texto = models.ForeignKey(Texto, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios')
    pai = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='respostas')
    
    conteudo = models.TextField()
    data_publicacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    
    # Controle de Anonimato
    publicado_anonimamente = models.BooleanField(default=False)

class ConviteAutor(models.Model):
    """
    Token de convite/onboarding para autores.
    Usado para primeira ativação E reset de senha.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='convites')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()  # Expiração: 7 dias após criação
    usado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-criado_em']

    def is_valido(self):
        """Verifica se token não expirou e não foi usado"""
        from django.utils import timezone
        return not self.usado and self.expira_em > timezone.now()

NOTA: Sempre gerar NOVO token quando "Reenviar Convite" (invalida anteriores).
Token pode ser usado para: 1) Primeira ativação (PENDENTE) ou 2) Reset de senha (ATIVO).

class PaginaEstatica(models.Model):
    """ Modelo para o CMS (Manifesto, Quem Somos, Selo, etc.) """
    slug = models.SlugField(max_length=100, unique=True, primary_key=True)
    titulo = models.CharField(max_length=255)
    conteudo = models.TextField() # Pode usar Quill.js aqui também
    data_atualizacao = models.DateTimeField(auto_now=True)
(Nota: O modelo User herda de AbstractUser para incluir os campos username, email, password, first_name, last_name, is_staff (Admin), is_active).

3. Especificação Funcional Detalhada por Tela
Esta seção é o blueprint para views.py, urls.py e os templates HTML.

DECISÕES DE UX E ARQUITETURA IMPLEMENTADAS (FASE 3 - Outubro/2025)
===================================================================

Para documentação completa, consulte CLAUDE.md seção 9 (Decisões de Design e Melhorias Implementadas).

RESUMO EXECUTIVO:

1. SISTEMA DE CONVITE/ONBOARDING:
   - Admin cadastra autor sem senha → gera token único (7 dias validade)
   - Link exibido na tela (sem SMTP) → admin copia e envia manualmente
   - Token serve para: primeira ativação (PENDENTE) ou reset de senha (ATIVO)
   - "Reenviar Convite" sempre gera NOVO token (invalida anteriores)

2. SIDEBAR RECOLHÍVEL:
   - Todas as telas de painel (admin + autor) usam sidebar lateral
   - Estados: colapsada (só ícones) ou expandida (ícones + texto)
   - Ícones Heroicons discretos para cada opção do menu

3. EXCLUSÃO vs SUSPENSÃO:
   - EXCLUSÃO (user.delete()): CASCADE apaga TUDO (textos, comentários, dados)
     * Irreversível, direito ao esquecimento (LGPD)
     * Pode ser feita por: próprio usuário ou admin
   - SUSPENSÃO (is_active=False): bloqueia login, oculta conteúdo, preserva dados
     * Reversível, apenas admin pode suspender/reativar
     * Queries públicas filtram: .filter(autor__is_active=True)

4. ÁREA ADMINISTRATIVA:
   - Listagem mostra TODOS (ativos + suspensos) com badges visuais
   - Botões condicionais: "Suspender" se ativo, "Reativar" se suspenso
   - Confirmações: sem confirmação para reversíveis, FORTE para exclusão de autores
   - Admin pode editar TODOS os campos do usuário (exceto senha - usa reset)

5. MODERAÇÃO GLOBAL:
   - Admin só vê comentários PENDENTES (decisão do autor é final)
   - MAS admin pode EXCLUIR qualquer comentário (poder supremo)

6. PÁGINA DE BOAS-VINDAS (Tela 12):
   - Conteúdo editável via CMS (slug='mensagem-boas-vindas-autor')
   - Campos dinâmicos: {nome}, {email}, {pseudonimo}, {data_cadastro}
   - Link para "Meus Dados de Autor" (primeira senha)

ZONA 1: TELAS PÚBLICAS
1. Tela: Home (Página Inicial)

Rota: / (URL name: home)

Perfil: Público.

Objetivo: Apresentar o propósito, curadoria (autores) e conteúdo recente.

Backend (View HomeView):

Buscar PaginaEstatica (slug='home-proposito').

Buscar N Autores (ex: 10 mais recentes ou em destaque, User.objects.filter(role='AUTOR', is_active=True)).

Buscar N Textos (ex: 10 mais recentes, Texto.objects.filter(status='PUBLICADO').order_by('-data_publicacao')).

Buscar Tags populares (Tag.objects.annotate(num_textos=Count('textos')).order_by('-num_textos')).

Enviar todos os querysets para o template home.html.

Interatividade:

Alpine.js: Controlar o menu mobile (se houver).

2. Tela: Leitura de Texto (Article View)

Rota: /texto/<slug:slug>/ (URL name: leitura_texto)

Perfil: Público.

Objetivo: Consumo do texto, troca de temas, interação (comentários).

Backend (View TextoDetailView):

Buscar Texto pelo slug (e status='PUBLICADO').

Buscar Comentario.objects.filter(texto=texto, status='APROVADO', pai=None) (comentários raiz).

Processar o formulário de comentário (se request.method == 'POST').

Lógica de Comentário: Verificar se texto.moderacao_automatica é True para definir status='APROVADO' ou PENDENTE.

Interatividade:

Alpine.js (CRÍTICO):

x-data="{ tema: 'padrao', fonte: 16 }".

Seletor de Tema: Botões que mudam o valor de tema (@click="tema = 'sepia'").

Binding: <body :class="tema"> (onde 'sepia', 'noturno' são classes do Tailwind).

Controle de Fonte: Botões que mudam fonte (@click="fonte++").

Binding: <div class="article-body" :style="{ fontSize: fonte + 'px' }">.

HTMX (Comentários):

O formulário de comentário deve usar hx-post para esta mesma URL.

hx-target="#lista-comentarios" e hx-swap="beforeend" (para adicionar o novo comentário) OU hx-target="#form-comentario" (para mostrar erro de validação).

A view do Django, ao processar o POST, deve retornar o template parcial _comentario_item.html (se sucesso) ou _form_comentario.html (se erro).

3. Tela: Acervo de Textos

Rota: /acervo/ (URL name: acervo_textos)

Perfil: Público.

Objetivo: Listar todos os textos publicados com filtros, ordenação e paginação.

Backend (View AcervoTextos):

Buscar todos os textos publicados (Texto.objects.filter(status='PUBLICADO')).

Implementar filtros combinados:
- Filtro por autor: ?autor=<id>
- Filtro por título: ?titulo=<termo> (busca parcial case-insensitive)
- Filtro por tag: ?tag=<slug>
- Filtro por data: ?data_inicio=<date>&data_fim=<date>

Implementar ordenação:
- Mais recentes: -data_publicacao (padrão)
- Menos recentes: data_publicacao
- Mais views: -total_views (requer anotação com Count de visualizações)
- Autor alfabético: autor__first_name (ou autor__username)

Implementar paginação:
- Padrão: 30 textos por página
- Configurável: ?per_page=30|50|100

Usar select_related('autor') e prefetch_related('tags') para otimização.

Para cada texto, enviar ao template:
- Foto do autor (avatar)
- Nome do autor
- Título e subtítulo do texto
- Data de publicação
- Tags associadas
- Quantidade de views (anotar)
- Preview do conteúdo (primeiros 300 caracteres)
- Link "Ler agora" (URL: leitura_texto)

Contador de resultados: "X resultados encontrados"

Interatividade:

HTMX (Filtros):

Formulário de filtros usa hx-get para esta URL.

hx-target="#lista-textos" (substitui apenas a lista, não a página toda).

hx-push-url="true" (atualiza a URL do navegador com os filtros).

hx-indicator="#loading-indicator" (mostra spinner durante carregamento).

Botão "Limpar Filtros" usa hx-get="/acervo/" para resetar.

HTMX (Paginação):

Links de paginação usam hx-get com ?page=N.

hx-target="#lista-textos".

hx-push-url="true".

Alpine.js (Opções de visualização):

Select para escolher quantidade por página (30, 50, 100).

@change dispara hx-get com o novo valor.

4. Tela: Galeria de Autores

Rota: /autores/ (URL name: galeria_autores)

Perfil: Público.

Objetivo: Descobrir todos os autores da plataforma.

Backend (View AutoresListView):

Buscar todos os Autores (User.objects.filter(role='AUTOR', is_active=True)).

Anotar (.annotate()) a contagem de textos e a soma de visualizações (requer modelo de View/Métrica).

Buscar todas as Tags (Tag.objects.all()) para o filtro.

Se houver filtro de tag (query param ?tag=...), filtrar o queryset de autores.

Interatividade:

HTMX (Filtro):

O formulário de filtro (Tags) deve usar hx-get para esta URL.

hx-target="#grid-autores" (substitui apenas o grid de autores, não a página toda).

hx-push-url="true" (para atualizar a URL do navegador com o filtro).

HTMX (Modal Contato):

O botão "Falar com [Nome]" usa hx-get para uma URL (ex: /autores/<id>/contato/) que retorna o template parcial _modal_contato.html.

O formulário dentro do modal usa hx-post para enviar a mensagem.

5. Tela: Página de Login

Rota: /contas/login/ (URL name: login)

Perfil: Público.

Objetivo: Autenticar usuários.

Backend (View): Usar a LoginView padrão do Django. Configurar o template_name.

Interatividade: Nenhuma (POST padrão do navegador). (O "Login com Google" requer django-allauth).

6. Tela: Página de Cadastro (Leitor)

Rota: /contas/cadastro/ (URL name: cadastro_leitor)

Perfil: Público.

Objetivo: Registrar novos Leitores.

Backend (View CadastroView):

Um CreateView ou FormView customizado usando um UserCreationForm (baseado no User customizado).

Campos: first_name, last_name, email, password, foto, cidade, pais.

Lógica: Definir role='LEITOR'. Implementar fluxo de confirmação de e-mail (definir is_active=False e enviar e-mail).

Interatividade: Nenhuma (POST padrão).

7. Tela: Página Manifesto

Rota: /manifesto/ (URL name: pagina_manifesto)

Perfil: Público.

Objetivo: Exibir o manifesto.

Backend (View PaginaEstaticaView):

View genérica que busca PaginaEstatica.objects.get(slug='manifesto') e renderiza em pagina_estatica.html.

8. Tela: Página Quem Somos

Rota: /quem-somos/ (URL name: pagina_quem_somos)

Backend: A mesma PaginaEstaticaView, buscando slug='quem-somos'.

9. Tela: Página Selo Livre de IA

Rota: /selo-livre-de-ia/ (URL name: pagina_selo)

Backend: A mesma PaginaEstaticaView, buscando slug='selo-livre-de-ia'.

10. Tela: Página Fale Conosco

Rota: /fale-conosco/ (URL name: pagina_fale_conosco)

Perfil: Público.

Objetivo: Formulário de contato para o Admin.

Backend (View FaleConoscoView):

FormView padrão do Django.

Lógica form_valid(): Enviar e-mail para o Admin e exibir mensagem de sucesso.

Interatividade: (Pode usar HTMX para envio sem refresh).

ZONA 2: TELAS DO AUTOR (Requer @login_required e verificação de role ou group)
11. Tela: Painel do Autor (Dashboard)

Rota: /autor/dashboard/ (URL name: autor_dashboard)

Perfil: Autor.

Objetivo: Visão geral de métricas e performance.

Backend (View AutorDashboardView):

Buscar request.user.

Métricas de KPI: Texto.objects.filter(autor=request.user).count(), Comentario.objects.filter(texto__autor=request.user).count(), etc.

Dados do Gráfico (Chart.js): Preparar um queryset de leituras agrupadas por dia/mês. Passar como JSON (via json.dumps e |safe no template).

Rankings: Top 5 textos, Top 5 tags.

Interatividade:

Alpine.js: Usado para inicializar o Chart.js, lendo os dados JSON injetados pelo Django no template.

12. Tela: Meus Textos (Listagem)

Rota: /autor/textos/ (URL name: autor_textos)

Perfil: Autor.

Objetivo: Gerenciar (CRUD) todos os textos.

Backend (View AutorTextoListView):

ListView de Texto, filtrado por autor=request.user.

Permitir filtragem por status (?status=...).

Interatividade:

HTMX (Filtro):

Os botões/abas ("Todos", "Publicados", "Rascunhos") usam hx-get para esta URL.

hx-target="#tabela-textos-container" (atualiza apenas a tabela).

HTMX (Excluir):

Botão "Excluir" usa hx-delete para uma URL (/autor/textos/<id>/excluir/).

hx-target="closest tr" (remove a linha da tabela).

13. Tela: Editor de Texto (Criar/Editar)

Rota: /autor/textos/novo/ (Criar) e /autor/textos/editar/<int:pk>/ (Editar)

Perfil: Autor.

Objetivo: Escrever e gerenciar metadados de um texto.

Backend (View TextoCreateView/TextoUpdateView):

ModelForm complexo para o Texto.

Frontend: O template deve inicializar o Quill.js em um <div>.

Lógica de POST: Antes de validar o ModelForm, o JavaScript (via onsubmit) deve copiar o HTML do Quill para o textarea oculto do Django (id_conteudo).

Interatividade:

Quill.js: Controla a edição do conteudo.

Alpine.js: Controla a lógica de UI no sidebar (ex: desabilitar "Permitir Anonimato" se "Permitir Comentários" estiver desmarcado).

14. Tela: Gestão de Comentários (Autor)

Rota: /autor/comentarios/ (URL name: autor_comentarios)

Perfil: Autor.

Objetivo: Moderar comentários pendentes.

Backend (View AutorComentariosView):

ListView de Comentario, filtrado por texto__autor=request.user.

Filtro por status (?status=...).

Interatividade:

HTMX (Ações):

Botões "Aprovar" (hx-post="/autor/comentarios/<id>/aprovar/") e "Rejeitar".

hx-target="closest .comentario-card" (substitui o card do comentário pelo seu novo estado "Aprovado" ou o remove da fila).

As views de ação (aprovar_comentario) devem retornar um fragmento HTML (_comentario_card.html) atualizado.

15. Tela: Editar Perfil (Autor)

Rota: /autor/perfil/ (URL name: autor_perfil)

Perfil: Autor.

Objetivo: Gerenciar dados pessoais, pseudônimo e exportação.

Backend (View AutorPerfilView):

UpdateView para o User, usando request.user como object.

Lógica separada para "Exportar Dados" (gerar .zip com .txt).

Lógica separada para "Excluir Conta".

Interatividade: Nenhuma (POSTs padrão).

ZONA 3: TELAS DO ADMINISTRADOR (Requer @login_required, @staff_member_required ou verificação de role)
16. Tela: Painel Admin (Dashboard)

Rota: /admin/dashboard/ (URL name: admin_dashboard)

Perfil: Admin.

Objetivo: Visão global da plataforma.

Backend (View AdminDashboardView):

Métricas globais: User.objects.filter(role='AUTOR').count(), User.objects.filter(role='LEITOR').count(), Comentario.objects.filter(status='PENDENTE').count().

Interatividade:

(Deve usar o Django Admin padrão ou um dashboard customizado seguindo o AutorDashboardView). Recomendação: Usar o Django Admin padrão e estendê-lo.

17. Tela: Gestão de Autores (Admin)

Rota: /admin/gestao/autores/ (URL name: admin_autores)

Perfil: Admin.

Backend (View AdminAutoresListView):

ListView de User, filtrado por role='AUTOR'.

Interatividade (HTMX):

Ações de "Desativar" ou "Reenviar Convite" usam hx-post para atualizar o status na linha da tabela.

18. Tela: Formulário de Novo Autor (Admin)

Rota: /admin/gestao/autores/novo/ (URL name: admin_autor_novo)

Perfil: Admin.

Backend (View AdminAutorCreateView):

CreateView para User.

form_valid(): Define role='AUTOR', is_active=False e gera token único de ativação (expiração: 7 dias).

Exibe link de ativação na tela para admin copiar/colar (sem envio de email SMTP).

Campos do formulário:
- Nome Real (obrigatório)
- E-mail (Login) (obrigatório, único)
- Telefone (opcional)
- Cidade (opcional)
- País (opcional, padrão: Brasil)
- Foto (Upload, opcional)
- Bio (Resumo) (opcional)
- Pseudônimo (opcional - se vazio, autor só pode publicar com nome real)
- E-mail de Contato (opcional - se vazio, ícone de contato não aparece na galeria)

Interatividade: Exibir link copiável após submit (Alpine.js para botão "Copiar Link").

19. Tela: Página de Boas-Vindas ao Autor

Rota: /convite/<str:token>/ (URL name: convite_autor)

Perfil: Público (sem autenticação, mas requer token válido e não expirado).

Objetivo: Página acolhedora exibida quando autor clica no link de ativação.

Backend (View ConviteAutorView):

Valida token (verifica se existe, não expirou, e autor ainda está PENDENTE).

Se token inválido/expirado: exibe erro amigável.

Se válido: busca PaginaEstatica com slug='mensagem-boas-vindas-autor' e renderiza conteúdo.

Substitui campos dinâmicos no conteúdo:
- {nome} → user.first_name + user.last_name
- {email} → user.email
- {pseudonimo} → user.pseudonimo (se existir)
- {data_cadastro} → user.date_joined formatado

Conteúdo editável: Admin pode editar via Gestão de Páginas (Tela 21) a página "Mensagem de Boas-Vindas ao Autor".

Conteúdo padrão deve incluir:
- Texto de boas-vindas caloroso e personalizado
- Importância do trabalho do autor no LIVRE DIA
- Breve manual de instruções sobre o painel_autor (dashboard, criar textos, moderar comentários)
- Link destacado: "Acessar Meus Dados de Autor" → redireciona para edição de perfil (onde autor define senha)

Interatividade: Nenhuma (página estática com link).

20. Tela: Gestão de Leitores (Admin)

Rota: /admin/gestao/leitores/ (URL name: admin_leitores)

Perfil: Admin.

Backend: ListView de User, filtrado por role='LEITOR'.

Interatividade (HTMX): Ações de "Desativar" (atualiza linha da tabela).

21. Tela: Moderação Global (Admin)

Rota: /admin/moderacao/ (URL name: admin_moderacao)

Perfil: Admin.

Backend: ListView de Comentario, filtrado por status='PENDENTE' (admin só vê comentários que autor ainda não moderou).

Importante: Admin NÃO vê comentários já aprovados/rejeitados pelo autor (decisão do autor é final).

Admin pode EXCLUIR qualquer comentário (pendente, aprovado ou rejeitado) - poder supremo.

Interatividade (HTMX): Sistema de tabs (Pendentes, Aprovados, Rejeitados), botões de Aprovar/Rejeitar/Excluir.

22. Tela: Gestão de Páginas

Rota: /admin/cms/ (Listagem) e /admin/cms/editar/<slug:slug>/ (Edição)

Perfil: Admin.

Backend:

ListView de PaginaEstatica.

UpdateView de PaginaEstatica.

O template de edição deve inicializar o Quill.js para o campo conteudo.

Interatividade: Quill.js no formulário de edição.