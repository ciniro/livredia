from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Tag(models.Model):
    """
    Tags livres (Folksonomia) criadas pelos Autores.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="Slug"
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['nome']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Texto(models.Model):
    """
    A entidade principal: um texto publicado por um Autor.
    """
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        PUBLICADO = "PUBLICADO", "Publicado"

    class DisplayAutoria(models.TextChoices):
        REAL = "REAL", "Nome Real"
        PSEUDONIMO = "PSEUDONIMO", "Pseudônimo"
        AMBOS = "AMBOS", "Ambos"

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='textos',
        verbose_name="Autor"
    )
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título"
    )
    subtitulo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Subtítulo"
    )
    conteudo = models.TextField(
        verbose_name="Conteúdo",
        help_text="HTML limpo gerado pelo Quill.js"
    )
    slug = models.SlugField(
        max_length=255,
        unique_for_date='data_publicacao',
        verbose_name="Slug"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RASCUNHO,
        verbose_name="Status"
    )
    is_suspended = models.BooleanField(
        default=False,
        verbose_name="Suspenso",
        help_text="Texto suspenso fica invisível em toda a plataforma até ser reativado"
    )

    # Metadados
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='textos',
        verbose_name="Tags"
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )
    data_publicacao = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Data de Publicação"
    )

    # O Selo
    selo_livre_ia = models.BooleanField(
        default=False,
        verbose_name="Selo Livre de IA",
        help_text="Declara que este texto foi escrito por um humano"
    )

    # Domínio Público
    is_dominio_publico = models.BooleanField(
        default=False,
        verbose_name="Domínio Público",
        help_text="Declara que este texto está em domínio público"
    )

    # Conteúdo para Maiores de 18 anos
    is_maioridade = models.BooleanField(
        default=False,
        verbose_name="Conteúdo para Maiores de 18 anos",
        help_text="Indica que o texto contém conteúdo sensível adequado apenas para maiores de 18 anos"
    )

    # Local de Escrita
    local_escrita = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Local de Escrita",
        help_text="Onde você estava quando escreveu este texto (opcional, até 100 caracteres)"
    )

    # Configurações de Interação
    permite_comentarios = models.BooleanField(
        default=True,
        verbose_name="Permite Comentários"
    )
    moderacao_automatica = models.BooleanField(
        default=True,
        verbose_name="Moderação Automática",
        help_text="Se desativado, comentários precisam de aprovação manual"
    )
    permite_comentarios_anonimos = models.BooleanField(
        default=False,
        verbose_name="Permite Comentários Anônimos"
    )

    # Configuração de Autoria
    display_autoria = models.CharField(
        max_length=20,
        choices=DisplayAutoria.choices,
        default=DisplayAutoria.REAL,
        verbose_name="Exibir Autoria Como"
    )

    class Meta:
        verbose_name = "Texto"
        verbose_name_plural = "Textos"
        ordering = ['-data_publicacao', '-data_criacao']
        indexes = [
            models.Index(fields=['-data_publicacao']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} - {self.autor.get_display_name()}"


class Visualizacao(models.Model):
    """
    Rastreamento de visualizações/leituras de textos.
    Usado para métricas e análise de engajamento.
    """
    texto = models.ForeignKey(
        Texto,
        on_delete=models.CASCADE,
        related_name='visualizacoes',
        verbose_name="Texto"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visualizacoes',
        verbose_name="Usuário",
        help_text="Usuário logado que visualizou (null para anônimos)"
    )
    data_visualizacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da Visualização",
        db_index=True
    )
    tempo_permanencia = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Tempo de Permanência (segundos)",
        help_text="Tempo que o usuário passou lendo o texto"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereço IP"
    )
    sessao_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ID da Sessão",
        help_text="Para identificar visualizações únicas"
    )

    class Meta:
        verbose_name = "Visualização"
        verbose_name_plural = "Visualizações"
        ordering = ['-data_visualizacao']
        indexes = [
            models.Index(fields=['texto', '-data_visualizacao']),
            models.Index(fields=['-data_visualizacao']),
        ]

    def __str__(self):
        usuario_display = self.usuario.get_display_name() if self.usuario else "Anônimo"
        return f"Visualização de '{self.texto.titulo}' por {usuario_display}"


class CartaoBiblioteca(models.Model):
    """
    Assinaturas do Cartão da Biblioteca.

    Resgata a experiência nostálgica dos antigos cartões de controle de empréstimo
    de bibliotecas físicas, onde leitores deixavam suas assinaturas demonstrando
    apreço pelos livros que tocaram seus corações.

    Funcionalidades:
    - Relacionamento M2M entre textos e usuários
    - Cada usuário pode assinar cada texto apenas uma vez (autenticado)
    - Ordem cronológica preservada (como nos cartões reais)
    - Gera notificação para o autor quando alguém assina
    """
    texto = models.ForeignKey(
        Texto,
        on_delete=models.CASCADE,
        related_name='assinaturas',
        verbose_name="Texto"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cartoes_assinados',
        verbose_name="Usuário"
    )
    data_assinatura = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da Assinatura",
        db_index=True
    )

    class Meta:
        verbose_name = "Assinatura do Cartão"
        verbose_name_plural = "Assinaturas dos Cartões"
        ordering = ['data_assinatura']  # Ordem cronológica (mais antigas primeiro)
        unique_together = ('texto', 'usuario')  # Um usuário assina apenas uma vez
        indexes = [
            models.Index(fields=['texto', 'data_assinatura']),
            models.Index(fields=['usuario', 'data_assinatura']),
        ]

    def __str__(self):
        return f"{self.usuario.get_full_name()} → {self.texto.titulo}"


class TextoFavorito(models.Model):
    """
    Textos salvos como "melhores" (favoritos) pelos leitores.

    Item 2.2.1 do ROADMAP - Permite que leitores marquem textos que mais gostaram.
    Este modelo serve como relacionamento M2M entre usuários e textos, e pode ser
    reutilizado no futuro para outros recursos que precisem associar leitores a textos.

    Funcionalidades:
    - Cada leitor pode favoritar múltiplos textos
    - Cada texto pode ser favoritado por múltiplos leitores
    - Um leitor só pode favoritar o mesmo texto uma vez (unique_together)
    - Ordem cronológica preservada (data_favoritado)
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='textos_favoritos',
        verbose_name="Usuário"
    )
    texto = models.ForeignKey(
        Texto,
        on_delete=models.CASCADE,
        related_name='favoritado_por',
        verbose_name="Texto"
    )
    data_favoritado = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Favoritação",
        db_index=True
    )

    class Meta:
        verbose_name = "Texto Favorito"
        verbose_name_plural = "Textos Favoritos"
        ordering = ['-data_favoritado']  # Mais recentes primeiro
        unique_together = ('usuario', 'texto')  # Um usuário favorita cada texto apenas uma vez
        indexes = [
            models.Index(fields=['usuario', '-data_favoritado']),
            models.Index(fields=['texto', '-data_favoritado']),
        ]

    def __str__(self):
        return f"{self.usuario.get_display_name()} favoritou '{self.texto.titulo}'"


class TextoLido(models.Model):
    """
    Textos marcados como "lidos" pelos leitores.

    Item 2.2.2 do ROADMAP - Permite que leitores marquem textos que já leram.
    Este modelo serve como relacionamento M2M entre usuários e textos, e pode ser
    reutilizado no futuro para outros recursos que precisem associar leitores a textos.

    Funcionalidades:
    - Cada leitor pode marcar múltiplos textos como lidos
    - Cada texto pode ser marcado como lido por múltiplos leitores
    - Um leitor só pode marcar o mesmo texto como lido uma vez (unique_together)
    - Ordem cronológica preservada (data_marcado)
    - Usado nos botões 2.2.3, 2.2.4 e 2.2.5 para filtrar textos não lidos
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='textos_lidos',
        verbose_name="Usuário"
    )
    texto = models.ForeignKey(
        Texto,
        on_delete=models.CASCADE,
        related_name='lido_por',
        verbose_name="Texto"
    )
    data_marcado = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Marcação",
        db_index=True
    )

    class Meta:
        verbose_name = "Texto Lido"
        verbose_name_plural = "Textos Lidos"
        ordering = ['-data_marcado']  # Mais recentes primeiro
        unique_together = ('usuario', 'texto')  # Um usuário marca cada texto como lido apenas uma vez
        indexes = [
            models.Index(fields=['usuario', '-data_marcado']),
            models.Index(fields=['texto', '-data_marcado']),
        ]

    def __str__(self):
        return f"{self.usuario.get_display_name()} leu '{self.texto.titulo}'"


class TextoLeituraPosterior(models.Model):
    """
    Textos salvos para "ler mais tarde" pelos leitores.

    Item 4 do ROADMAP - Lista de Leitura.
    Permite que leitores salvem textos para ler posteriormente quando tiverem tempo.
    Este modelo serve como relacionamento M2M entre usuários e textos, similar aos
    modelos TextoFavorito e TextoLido.

    Funcionalidades:
    - Cada leitor pode salvar múltiplos textos para ler mais tarde
    - Cada texto pode ser salvo por múltiplos leitores
    - Um leitor só pode salvar o mesmo texto uma vez (unique_together)
    - Ordem cronológica preservada (data_adicionado)
    - Usado para criar uma lista personalizada de leitura para cada usuário
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='textos_leitura_posterior',
        verbose_name="Usuário"
    )
    texto = models.ForeignKey(
        Texto,
        on_delete=models.CASCADE,
        related_name='salvo_para_ler_por',
        verbose_name="Texto"
    )
    data_adicionado = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Adição",
        db_index=True
    )

    class Meta:
        verbose_name = "Texto para Ler Mais Tarde"
        verbose_name_plural = "Textos para Ler Mais Tarde"
        ordering = ['-data_adicionado']  # Mais recentes primeiro
        unique_together = ('usuario', 'texto')  # Um usuário salva cada texto para ler apenas uma vez
        indexes = [
            models.Index(fields=['usuario', '-data_adicionado']),
            models.Index(fields=['texto', '-data_adicionado']),
        ]

    def __str__(self):
        return f"{self.usuario.get_display_name()} salvou '{self.texto.titulo}' para ler mais tarde"
