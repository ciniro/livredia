from django.db import models
from django.conf import settings


class Comentario(models.Model):
    """
    Comentários feitos nos Textos.
    Suporta comentários aninhados (respostas).
    """
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADO = "APROVADO", "Aprovado"
        REJEITADO = "REJEITADO", "Rejeitado"

    texto = models.ForeignKey(
        'textos.Texto',
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name="Texto"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name="Autor"
    )
    pai = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='respostas',
        verbose_name="Comentário Pai",
        help_text="Comentário ao qual este é uma resposta"
    )

    conteudo = models.TextField(
        verbose_name="Conteúdo"
    )
    data_publicacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Publicação"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name="Status"
    )

    # Controle de Anonimato
    publicado_anonimamente = models.BooleanField(
        default=False,
        verbose_name="Publicado Anonimamente",
        help_text="Se verdadeiro, o nome do autor não será exibido"
    )

    class Meta:
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"
        ordering = ['data_publicacao']
        indexes = [
            models.Index(fields=['texto', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        autor_display = "Anônimo" if self.publicado_anonimamente else self.autor.get_display_name()
        return f"Comentário de {autor_display} em '{self.texto.titulo}'"
