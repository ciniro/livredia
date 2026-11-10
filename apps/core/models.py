from django.db import models
from django.conf import settings


class PaginaEstatica(models.Model):
    """
    Modelo para o CMS (Manifesto, Quem Somos, Selo, etc.).
    Permite gerenciar conteúdo estático através do Django Admin.
    """
    slug = models.SlugField(
        max_length=100,
        unique=True,
        primary_key=True,
        verbose_name="Slug",
        help_text="Identificador único da página (ex: manifesto, quem-somos)"
    )
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título"
    )
    conteudo = models.TextField(
        verbose_name="Conteúdo",
        help_text="HTML do conteúdo da página (pode usar Quill.js)"
    )
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Atualização"
    )

    class Meta:
        verbose_name = "Página Estática"
        verbose_name_plural = "Páginas Estáticas"
        ordering = ['titulo']

    def __str__(self):
        return self.titulo


class MotivoNotificacao(models.Model):
    """
    Catálogo de motivos/tipos de notificação.
    Permite adicionar novos tipos sem alterar código.

    Exemplos:
    - MENCAO_COMENTARIO: Usuário foi mencionado em comentário
    - RESPOSTA_COMENTARIO: Alguém respondeu seu comentário
    - NOVO_TEXTO_AUTOR: Autor favorito publicou novo texto
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código",
        help_text="Identificador único (ex: MENCAO_COMENTARIO)"
    )
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome",
        help_text="Nome legível (ex: Menção em comentário)"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Explicação detalhada do motivo"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Permite desativar tipos de notificação"
    )

    class Meta:
        verbose_name = "Motivo de Notificação"
        verbose_name_plural = "Motivos de Notificação"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Notificacao(models.Model):
    """
    Sistema de notificações do LIVRE DIA.
    Armazena histórico de eventos que usuários devem ser notificados.

    Funcionalidades:
    - Notificar menções em comentários
    - Notificar respostas a comentários
    - Notificar novos textos de autores favoritos
    - Histórico completo de notificações
    - Limite configurável por usuário
    """
    # Motivo da notificação
    motivo = models.ForeignKey(
        'MotivoNotificacao',
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name="Motivo"
    )

    # Usuários envolvidos
    usuario_origem = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificacoes_enviadas',
        verbose_name="Usuário de Origem",
        help_text="Usuário que gerou a notificação (pode ser null para notificações do sistema)"
    )
    usuario_destino = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes_recebidas',
        verbose_name="Usuário de Destino",
        help_text="Usuário que receberá a notificação"
    )

    # Conteúdo da notificação
    texto = models.TextField(
        verbose_name="Texto",
        help_text="Mensagem da notificação (ex: '@ciniro marcou você em um comentário')"
    )
    link_destino = models.CharField(
        max_length=500,
        verbose_name="Link de Destino",
        help_text="URL para onde o usuário será direcionado ao clicar"
    )

    # Controle
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )
    lida = models.BooleanField(
        default=False,
        verbose_name="Lida",
        help_text="Indica se a notificação já foi visualizada pelo usuário"
    )

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['usuario_destino', 'lida', '-data_criacao']),
            models.Index(fields=['usuario_destino', '-data_criacao']),
        ]

    def __str__(self):
        return f"{self.motivo.nome} para {self.usuario_destino.username}"


class TemaLeitura(models.Model):
    """
    Temas de leitura customizáveis.
    Permite criar e gerenciar temas CSS para a experiência de leitura.

    Sistema modular:
    - Cada tema tem um arquivo CSS próprio em static/css/themes/
    - Temas podem ser ativados/desativados
    - Ordem customizável de exibição
    - Tema 'padrao' é obrigatório e não pode ser deletado

    Futuro: CRUD no painel admin para criar novos temas
    """
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name="Slug",
        help_text="Identificador único do tema (ex: padrao, sepia, noturno)"
    )
    nome_exibicao = models.CharField(
        max_length=100,
        verbose_name="Nome de Exibição",
        help_text="Nome amigável exibido no dropdown (ex: Padrão, Sépia)"
    )
    arquivo_css = models.CharField(
        max_length=100,
        verbose_name="Arquivo CSS",
        help_text="Nome do arquivo CSS em static/css/themes/ (ex: padrao.css)"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Breve descrição do tema (opcional)"
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Ordem de exibição no dropdown (menor aparece primeiro)"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Permite desativar temas temporariamente"
    )

    class Meta:
        verbose_name = "Tema de Leitura"
        verbose_name_plural = "Temas de Leitura"
        ordering = ['ordem', 'nome_exibicao']

    def __str__(self):
        return self.nome_exibicao

    def delete(self, *args, **kwargs):
        """
        Impede deleção do tema padrão.
        O tema padrão é obrigatório pois é usado como fallback.
        """
        if self.slug == 'padrao':
            raise models.ProtectedError(
                "O tema padrão não pode ser deletado pois é usado como fallback.",
                [self]
            )
        super().delete(*args, **kwargs)
