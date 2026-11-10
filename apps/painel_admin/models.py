"""
Modelos do painel administrativo.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid


class ConviteAutor(models.Model):
    """
    Modelo para gerenciar convites de onboarding de novos autores.

    Quando um admin ou autor cria um novo autor, o sistema gera um token único
    que expira em 7 dias. O autor usa esse token para acessar a página
    de boas-vindas e definir sua senha.

    O campo convidado_por registra qual autor fez o convite (None = admin).
    Quando o convite é ativado, conta como convite utilizado do autor convidante.
    """

    autor = models.OneToOneField(
        'usuarios.User',
        on_delete=models.CASCADE,
        related_name='convite',
        verbose_name='Autor',
        help_text='Usuário autor que receberá o convite'
    )

    convidado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='convites_enviados',
        verbose_name='Convidado por',
        help_text='Autor que fez o convite (None = convite do admin)'
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name='Token de Ativação',
        help_text='Token único gerado automaticamente (UUID4)'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação',
        help_text='Data e hora em que o convite foi gerado'
    )

    data_expiracao = models.DateTimeField(
        verbose_name='Data de Expiração',
        help_text='Data e hora de expiração do convite (7 dias após criação)'
    )

    ativado = models.BooleanField(
        default=False,
        verbose_name='Convite Ativado',
        help_text='Define se o autor já acessou o link e ativou sua conta'
    )

    class Meta:
        verbose_name = 'Convite de Autor'
        verbose_name_plural = 'Convites de Autores'
        ordering = ['-data_criacao']

    def __str__(self):
        status = "✅ Ativado" if self.ativado else ("⏳ Pendente" if not self.expirado() else "❌ Expirado")
        return f"{self.autor.get_display_name()} - {status}"

    def save(self, *args, **kwargs):
        """
        Sobrescreve save para definir token e data_expiracao automaticamente.
        - Token: UUID4 único
        - Data de expiração = data_criacao + 7 dias
        """
        # Gerar token se não existir
        if not self.token:
            self.token = str(uuid.uuid4())

        # Definir data de expiração se não existir
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    def expirado(self):
        """
        Verifica se o convite está expirado.

        Returns:
            bool: True se expirado, False caso contrário
        """
        return timezone.now() > self.data_expiracao

    def valido(self):
        """
        Verifica se o convite é válido (não expirado e não ativado).

        Returns:
            bool: True se válido, False caso contrário
        """
        return not self.expirado() and not self.ativado

    def get_link_ativacao(self, request=None):
        """
        Retorna o link completo de ativação do convite.

        Args:
            request: HttpRequest object para construir URL absoluta

        Returns:
            str: URL completa para ativação do convite
        """
        from django.urls import reverse

        if request:
            # URL absoluta com domínio
            return request.build_absolute_uri(
                reverse('painel_admin:convite_autor', kwargs={'token': self.token})
            )
        else:
            # URL relativa
            return reverse('painel_admin:convite_autor', kwargs={'token': self.token})


class ContatoAdministrativo(models.Model):
    """
    Modelo para gerenciar e-mails de contato administrativo do LIVRE DIA.

    E-mails cadastrados aqui recebem mensagens do formulário de contato público
    e outras notificações administrativas importantes.
    """

    nome = models.CharField(
        max_length=150,
        verbose_name='Nome do Contato',
        help_text='Nome da pessoa responsável por este e-mail (para identificação)'
    )

    email = models.EmailField(
        unique=True,
        verbose_name='E-mail',
        help_text='Endereço de e-mail que receberá as mensagens'
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo',
        help_text='Define se este contato está ativo e receberá mensagens'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Cadastro'
    )

    class Meta:
        verbose_name = 'Contato Administrativo'
        verbose_name_plural = 'Contatos Administrativos'
        ordering = ['nome']

    def __str__(self):
        status = '✅' if self.ativo else '❌'
        return f"{status} {self.nome} ({self.email})"


class ConfiguracaoSistema(models.Model):
    """
    Configurações gerais do sistema LIVRE DIA.

    Usa o padrão Singleton - apenas um registro deve existir.
    Acessível via ConfiguracaoSistema.get_config()
    """

    limite_convites_autor = models.PositiveIntegerField(
        default=5,
        verbose_name='Limite de Convites por Autor',
        help_text='Quantidade máxima de autores que cada autor pode convidar'
    )

    # Configurações de Autores Clássicos
    senha_autores_classicos = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name='Senha dos Autores Clássicos',
        help_text='Senha padrão para todos os autores clássicos (visível para o admin)'
    )

    autores_classicos_podem_login = models.BooleanField(
        default=False,
        verbose_name='Autores Clássicos Podem Fazer Login',
        help_text='Define se autores clássicos podem acessar o sistema'
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )

    class Meta:
        verbose_name = 'Configuração do Sistema'
        verbose_name_plural = 'Configurações do Sistema'

    def __str__(self):
        return f"Configurações do Sistema (atualizado em {self.data_atualizacao.strftime('%d/%m/%Y %H:%M')})"

    def save(self, *args, **kwargs):
        """
        Garante que só existe um registro (Singleton).
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """
        Retorna a configuração do sistema.
        Cria automaticamente se não existir.
        """
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class ComunicacaoGeral(models.Model):
    """
    Modelo para gerenciar comunicações em massa (e-mail marketing) do LIVRE DIA.

    Permite que administradores enviem e-mails para usuários da plataforma
    com filtros avançados e tracking de abertura.
    """

    class TipoComunicacao(models.TextChoices):
        NOVIDADE = 'NOVIDADE', 'Novidade do LIVRE DIA'
        PARCEIROS = 'PARCEIROS', 'Anúncio de parceiros'
        AMBOS = 'AMBOS', 'Ambos'

    class StatusEnvio(models.TextChoices):
        ENVIANDO = 'ENVIANDO', 'Enviando'
        ENVIADO = 'ENVIADO', 'Enviado'
        ERRO = 'ERRO', 'Erro no envio'

    titulo = models.CharField(
        max_length=255,
        verbose_name='Título',
        help_text='Título do e-mail que será enviado'
    )

    conteudo = models.TextField(
        verbose_name='Conteúdo',
        help_text='Conteúdo HTML do e-mail (gerado pelo editor Quill.js)'
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoComunicacao.choices,
        verbose_name='Tipo de Comunicação',
        help_text='Define quais usuários receberão baseado nas preferências'
    )

    # Filtros opcionais
    filtro_sexo = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        verbose_name='Filtro por Sexo',
        help_text='F=Feminino, M=Masculino, O=Outro, vazio=Todos'
    )

    filtro_idade_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Idade Mínima',
        help_text='Idade mínima dos destinatários'
    )

    filtro_idade_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Idade Máxima',
        help_text='Idade máxima dos destinatários'
    )

    filtro_segue_autores = models.ManyToManyField(
        'usuarios.User',
        blank=True,
        related_name='comunicacoes_filtro_autor',
        verbose_name='Segue Autores',
        help_text='Apenas usuários que seguem estes autores'
    )

    filtro_tempo_leitura = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ('POUCO', 'Pouco (< 1 hora)'),
            ('MEDIO', 'Médio (1-10 horas)'),
            ('MUITO', 'Muito (> 10 horas)'),
        ],
        verbose_name='Tempo de Leitura',
        help_text='Filtrar por tempo total de leitura na plataforma'
    )

    # Estatísticas
    total_destinatarios = models.PositiveIntegerField(
        default=0,
        verbose_name='Total de Destinatários',
        help_text='Quantidade de e-mails enviados'
    )

    total_aberturas = models.PositiveIntegerField(
        default=0,
        verbose_name='Total de Aberturas',
        help_text='Quantidade de e-mails abertos (tracking por pixel)'
    )

    status = models.CharField(
        max_length=20,
        choices=StatusEnvio.choices,
        default='ENVIANDO',
        verbose_name='Status do Envio'
    )

    erro_mensagem = models.TextField(
        blank=True,
        verbose_name='Mensagem de Erro',
        help_text='Detalhes do erro caso o envio falhe'
    )

    # Metadados
    criado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='comunicacoes_criadas',
        verbose_name='Criado por'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )

    data_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Envio',
        help_text='Data e hora em que o envio foi concluído'
    )

    class Meta:
        verbose_name = 'Comunicação Geral'
        verbose_name_plural = 'Comunicações Gerais'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"{self.titulo} ({self.get_status_display()})"

    def taxa_abertura(self):
        """Retorna a taxa de abertura em percentual."""
        if self.total_destinatarios > 0:
            return round((self.total_aberturas / self.total_destinatarios) * 100, 1)
        return 0

    def get_filtros_descricao(self):
        """Retorna uma descrição legível dos filtros aplicados."""
        filtros = []

        if self.filtro_sexo:
            sexo_map = {'F': 'Feminino', 'M': 'Masculino', 'O': 'Outro'}
            filtros.append(f"Sexo: {sexo_map.get(self.filtro_sexo, self.filtro_sexo)}")

        if self.filtro_idade_min or self.filtro_idade_max:
            idade_str = ""
            if self.filtro_idade_min and self.filtro_idade_max:
                idade_str = f"{self.filtro_idade_min}-{self.filtro_idade_max} anos"
            elif self.filtro_idade_min:
                idade_str = f"≥ {self.filtro_idade_min} anos"
            else:
                idade_str = f"≤ {self.filtro_idade_max} anos"
            filtros.append(f"Idade: {idade_str}")

        if self.filtro_tempo_leitura:
            tempo_map = {
                'POUCO': '< 1 hora',
                'MEDIO': '1-10 horas',
                'MUITO': '> 10 horas'
            }
            filtros.append(f"Tempo de leitura: {tempo_map.get(self.filtro_tempo_leitura)}")

        if self.filtro_segue_autores.exists():
            autores = ', '.join([a.get_display_name() for a in self.filtro_segue_autores.all()[:3]])
            if self.filtro_segue_autores.count() > 3:
                autores += f" (+{self.filtro_segue_autores.count() - 3})"
            filtros.append(f"Segue: {autores}")

        return filtros if filtros else ['Sem filtros (todos os usuários elegíveis)']


class AberturaEmail(models.Model):
    """
    Modelo para tracking de abertura de e-mails.

    Registra quando um usuário abre um e-mail de comunicação geral,
    usando a técnica de pixel de rastreamento (imagem 1x1 invisível).
    """

    comunicacao = models.ForeignKey(
        ComunicacaoGeral,
        on_delete=models.CASCADE,
        related_name='aberturas',
        verbose_name='Comunicação'
    )

    usuario = models.ForeignKey(
        'usuarios.User',
        on_delete=models.CASCADE,
        related_name='emails_abertos',
        verbose_name='Usuário'
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Token de Tracking',
        help_text='Token único para identificar este destinatário'
    )

    aberto = models.BooleanField(
        default=False,
        verbose_name='E-mail Aberto',
        help_text='Indica se o usuário abriu o e-mail'
    )

    data_abertura = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Abertura'
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Endereço IP'
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent',
        help_text='Informações do cliente de e-mail/navegador'
    )

    data_envio = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Envio'
    )

    class Meta:
        verbose_name = 'Abertura de E-mail'
        verbose_name_plural = 'Aberturas de E-mail'
        unique_together = ['comunicacao', 'usuario']
        ordering = ['-data_abertura']

    def __str__(self):
        status = '✅ Aberto' if self.aberto else '📨 Enviado'
        return f"{self.usuario.email} - {status}"

    def save(self, *args, **kwargs):
        """Gera token único se não existir."""
        if not self.token:
            self.token = str(uuid.uuid4())
        super().save(*args, **kwargs)
