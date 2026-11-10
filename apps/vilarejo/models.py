"""
Modelos do Vilarejo Literário

Este módulo define os modelos de dados para o sistema de Vilarejo Literário,
incluindo o vilarejo em si, mensagens de chat, moradores permanentes,
banimentos e histórico de mudanças.
"""

import os
import uuid
from django.db import models
from django.conf import settings


def vilarejo_capa_path(instance, filename):
    """
    Gera um nome único para a capa do vilarejo usando UUID.
    Formato: banners_vilarejo/<uuid>.<extensao>
    """
    ext = filename.split('.')[-1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    return f'banners_vilarejo/{filename}'


class Vilarejo(models.Model):
    """
    Representa o vilarejo de um usuário.

    Cada usuário pode ter apenas um vilarejo, onde é o anfitrião.
    O vilarejo contém até 9 vizinhos baseados em similaridade literária,
    além de moradores permanentes convidados pelo dono.
    """
    dono = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vilarejo',
        verbose_name='Dono'
    )
    nome = models.CharField(
        max_length=100,
        verbose_name='Nome do Vilarejo',
        help_text='Nome personalizado do vilarejo'
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    capa_personalizada = models.ImageField(
        upload_to=vilarejo_capa_path,
        null=True,
        blank=True,
        verbose_name='Capa Personalizada',
        help_text='Imagem personalizada para o banner do vilarejo'
    )

    class Meta:
        verbose_name = 'Vilarejo'
        verbose_name_plural = 'Vilarejos'
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Define nome padrão se não fornecido
        if not self.nome:
            self.nome = f'Vilarejo de {self.dono.nome or self.dono.username}'

        # Se é uma atualização, deletar capa antiga se foi alterada
        if self.pk:
            try:
                old_instance = Vilarejo.objects.get(pk=self.pk)
                if old_instance.capa_personalizada and old_instance.capa_personalizada != self.capa_personalizada:
                    if os.path.isfile(old_instance.capa_personalizada.path):
                        os.remove(old_instance.capa_personalizada.path)
            except Vilarejo.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Deletar capa personalizada se existir
        if self.capa_personalizada:
            if os.path.isfile(self.capa_personalizada.path):
                os.remove(self.capa_personalizada.path)
        super().delete(*args, **kwargs)


class MensagemVilarejo(models.Model):
    """
    Representa uma mensagem no chat do vilarejo.

    Mensagens são limitadas a 500 caracteres e podem conter
    texto puro, emojis e links. Cada vilarejo tem limite de 2000 mensagens.
    """
    vilarejo = models.ForeignKey(
        Vilarejo,
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name='Vilarejo'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_vilarejo',
        verbose_name='Autor'
    )
    conteudo = models.CharField(
        max_length=500,
        verbose_name='Conteúdo'
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    editado_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Editado em'
    )

    class Meta:
        verbose_name = 'Mensagem do Vilarejo'
        verbose_name_plural = 'Mensagens do Vilarejo'
        ordering = ['criado_em']
        indexes = [
            models.Index(fields=['vilarejo', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.autor.username}: {self.conteudo[:50]}...'


class MoradorPermanente(models.Model):
    """
    Representa um morador permanente do vilarejo.

    Moradores permanentes são vizinhos que não "se mudam" mesmo que
    a similaridade diminua. Só podem ser convidados usuários que
    já foram vizinhos alguma vez.
    """
    vilarejo = models.ForeignKey(
        Vilarejo,
        on_delete=models.CASCADE,
        related_name='moradores_permanentes',
        verbose_name='Vilarejo'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='morador_permanente_em',
        verbose_name='Usuário'
    )
    convidado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='convites_morador_feitos',
        verbose_name='Convidado por'
    )
    data_convite = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data do convite'
    )

    class Meta:
        verbose_name = 'Morador Permanente'
        verbose_name_plural = 'Moradores Permanentes'
        unique_together = ['vilarejo', 'usuario']
        ordering = ['-data_convite']

    def __str__(self):
        return f'{self.usuario.username} em {self.vilarejo.nome}'


class BanimentoVilarejo(models.Model):
    """
    Representa um banimento de usuário do vilarejo.

    Banimentos são mútuos: se A bane B, nenhum dos dois aparece
    no vilarejo do outro. Banimentos podem ser desfeitos.
    """
    vilarejo = models.ForeignKey(
        Vilarejo,
        on_delete=models.CASCADE,
        related_name='banimentos',
        verbose_name='Vilarejo'
    )
    usuario_banido = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='banido_de_vilarejos',
        verbose_name='Usuário Banido'
    )
    banido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banimentos_feitos',
        verbose_name='Banido por'
    )
    motivo = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Motivo'
    )
    data_banimento = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data do banimento'
    )

    class Meta:
        verbose_name = 'Banimento do Vilarejo'
        verbose_name_plural = 'Banimentos do Vilarejo'
        unique_together = ['vilarejo', 'usuario_banido']
        ordering = ['-data_banimento']

    def __str__(self):
        return f'{self.usuario_banido.username} banido de {self.vilarejo.nome}'


class HistoricoCondominio(models.Model):
    """
    Registra eventos importantes do vilarejo.

    Inclui entradas/saídas de vizinhos e ações administrativas
    como convites de moradores, banimentos e alterações de nome.
    """
    TIPO_ENTRADA = 'ENTRADA'
    TIPO_SAIDA = 'SAIDA'
    TIPO_MORADOR_ADICIONADO = 'MORADOR_ADICIONADO'
    TIPO_MORADOR_REMOVIDO = 'MORADOR_REMOVIDO'
    TIPO_USUARIO_BANIDO = 'USUARIO_BANIDO'
    TIPO_USUARIO_DESBANIDO = 'USUARIO_DESBANIDO'
    TIPO_NOME_ALTERADO = 'NOME_ALTERADO'

    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Se mudou para o vilarejo'),
        (TIPO_SAIDA, 'Se mudou para outro vilarejo'),
        (TIPO_MORADOR_ADICIONADO, 'Morador permanente adicionado'),
        (TIPO_MORADOR_REMOVIDO, 'Morador permanente removido'),
        (TIPO_USUARIO_BANIDO, 'Usuário banido'),
        (TIPO_USUARIO_DESBANIDO, 'Usuário desbanido'),
        (TIPO_NOME_ALTERADO, 'Nome do vilarejo alterado'),
    ]

    vilarejo = models.ForeignKey(
        Vilarejo,
        on_delete=models.CASCADE,
        related_name='historico',
        verbose_name='Vilarejo'
    )
    tipo_evento = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de evento'
    )
    usuario_alvo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='historico_alvo_vilarejos',
        verbose_name='Usuário alvo'
    )
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acoes_vilarejo',
        verbose_name='Realizado por'
    )
    detalhes = models.CharField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='Detalhes'
    )
    data = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data'
    )

    class Meta:
        verbose_name = 'Histórico do Condomínio'
        verbose_name_plural = 'Históricos do Condomínio'
        ordering = ['-data']
        indexes = [
            models.Index(fields=['vilarejo', '-data']),
        ]

    def __str__(self):
        return f'{self.get_tipo_evento_display()} em {self.vilarejo.nome}'


class HistoricoVizinho(models.Model):
    """
    Registra quem já foi vizinho de um usuário.

    Usado para validar convites de morador permanente:
    só pode convidar quem já foi vizinho alguma vez.
    """
    vilarejo = models.ForeignKey(
        Vilarejo,
        on_delete=models.CASCADE,
        related_name='historico_vizinhos',
        verbose_name='Vilarejo'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='foi_vizinho_de',
        verbose_name='Usuário'
    )
    primeira_vez_vizinho = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Primeira vez vizinho'
    )

    class Meta:
        verbose_name = 'Histórico de Vizinho'
        verbose_name_plural = 'Histórico de Vizinhos'
        unique_together = ['vilarejo', 'usuario']

    def __str__(self):
        return f'{self.usuario.username} foi vizinho de {self.vilarejo.nome}'
