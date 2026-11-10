import os
import uuid
from datetime import timedelta
from django.db import models
from django.core import validators
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


def user_photo_path(instance, filename):
    """
    Gera um nome único para a foto do usuário usando UUID.
    Formato: perfis/<uuid>.<extensao>
    Exemplo: perfis/a1b2c3d4e5f6.jpg
    """
    ext = filename.split('.')[-1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    return f'perfis/{filename}'


class User(AbstractUser):
    """
    Modelo de Usuário customizado.
    Armazena Leitores, Autores e Admins.
    """
    class Role(models.TextChoices):
        LEITOR = "LEITOR", "Leitor"
        AUTOR = "AUTOR", "Autor"
        ADMIN = "ADMIN", "Administrador"

    class Sexo(models.TextChoices):
        FEMININO = "F", "Feminino"
        MASCULINO = "M", "Masculino"
        OUTRO = "O", "Outro"
        NAO_DECLARAR = "N", "Prefiro não declarar"

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.LEITOR,
        verbose_name="Perfil"
    )

    sexo = models.CharField(
        max_length=1,
        choices=Sexo.choices,
        default=Sexo.NAO_DECLARAR,
        verbose_name="Sexo",
        help_text="Informação usada para personalizar mensagens e selos de reconhecimento"
    )

    # Permissão administrativa adicional
    is_admin = models.BooleanField(
        default=False,
        verbose_name="É Administrador",
        help_text="Indica se o usuário tem permissões administrativas. "
                  "Autores com is_admin=True podem acessar o painel admin E o painel de autor. "
                  "Usuários role=ADMIN sem serem autores SÓ podem acessar o painel admin."
    )

    # Perfil (comum a todos)
    foto = models.ImageField(
        upload_to=user_photo_path,
        null=True,
        blank=True,
        verbose_name="Foto de Perfil"
    )
    cidade = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Cidade"
    )
    pais = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="País"
    )
    data_nascimento = models.DateField(
        verbose_name="Data de Nascimento",
        help_text="Usado para estatísticas demográficas e personalização de conteúdo"
    )

    # Perfil (específico do Autor)
    bio = models.TextField(
        null=True,
        blank=True,
        verbose_name="Biografia"
    )
    pseudonimo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Pseudônimo"
    )
    email_contato = models.EmailField(
        null=True,
        blank=True,
        verbose_name="E-mail para Contato",
        help_text="E-mail público para que leitores possam entrar em contato"
    )
    telefone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Telefone"
    )

    # Status administrativo (específico do Autor)
    is_suspended = models.BooleanField(
        default=False,
        verbose_name="Suspenso",
        help_text="Indica se o autor está temporariamente suspenso pelo administrador. "
                  "Autores suspensos não podem fazer login e seu conteúdo fica oculto."
    )

    # Classificação do autor (específico do Autor)
    is_classico = models.BooleanField(
        default=False,
        verbose_name="Autor Clássico",
        help_text="Indica se o autor é classificado como clássico. "
                  "Autores clássicos são aqueles cuja obra já é reconhecida historicamente. "
                  "Autores contemporâneos são aqueles em atividade criativa atual."
    )

    # Status de verificação de email (específico do Leitor)
    email_verified = models.BooleanField(
        default=False,
        verbose_name="E-mail Verificado",
        help_text="Indica se o leitor confirmou seu e-mail de cadastro. "
                  "Leitores com e-mail não verificado aparecem como PENDENTE no painel admin."
    )

    # Privacidade do perfil público (Item 5.3 do ROADMAP)
    perfil_privado = models.BooleanField(
        default=False,
        verbose_name="Perfil Privado",
        help_text="Se ativado, a página pública do perfil (/@username) exibirá apenas uma "
                  "mensagem informando que o perfil é privado, ocultando dados pessoais."
    )

    # NOTA: Dados de monetização via PIX foram movidos para o modelo MonetizacaoPix
    # (relacionamento OneToOne acessível via user.monetizacao_pix)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['-date_joined']

    def get_display_name(self):
        """
        Retorna o nome de exibição do usuário.
        Para autores: retorna pseudônimo se existir, senão nome completo.
        Para outros: retorna nome completo.
        """
        if self.role == self.Role.AUTOR and self.pseudonimo:
            return self.pseudonimo
        return self.get_full_name() or self.username

    def get_avatar_url(self):
        """
        Retorna a URL do avatar do usuário.
        Se houver foto: retorna a URL da foto.
        Se não houver foto: retorna avatar placeholder com iniciais (ui-avatars.com).

        O avatar placeholder usa:
        - Cor de fundo: #e69019 (laranja principal do projeto)
        - Cor do texto: #fff (branco)
        - Tamanho: 200px
        - Negrito: sim
        """
        if self.foto:
            return self.foto.url
        else:
            # Usar nome completo para gerar iniciais
            nome_completo = self.get_full_name() or self.username
            # Codificar para URL (espaços viram +)
            nome_encoded = nome_completo.replace(' ', '+')
            # Gerar avatar com iniciais usando ui-avatars.com
            return f"https://ui-avatars.com/api/?name={nome_encoded}&size=200&background=e69019&color=fff&bold=true&font-size=0.4"

    def pode_acessar_painel_admin(self):
        """
        Verifica se o usuário pode acessar o painel administrativo.
        Retorna True se:
        - role = ADMIN (independente de is_admin), OU
        - role = AUTOR e is_admin = True
        """
        return self.role == self.Role.ADMIN or (self.role == self.Role.AUTOR and self.is_admin)

    def pode_acessar_painel_autor(self):
        """
        Verifica se o usuário pode acessar o painel de autor.
        Retorna True se:
        - role = AUTOR (independente de is_admin)
        """
        return self.role == self.Role.AUTOR

    def __str__(self):
        return f"{self.get_display_name()} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para deletar foto antiga quando uma nova é enviada.
        Garante que cada usuário tenha apenas uma foto no servidor.
        """
        # Se é uma atualização (não é novo cadastro)
        if self.pk:
            try:
                # Buscar instância antiga do banco
                old_instance = User.objects.get(pk=self.pk)

                # Se havia foto antiga e ela foi alterada
                if old_instance.foto and old_instance.foto != self.foto:
                    # Deletar arquivo físico da foto antiga
                    if os.path.isfile(old_instance.foto.path):
                        os.remove(old_instance.foto.path)
            except User.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Sobrescreve o método delete para remover a foto do servidor quando a conta for deletada.
        """
        # Deletar foto se existir
        if self.foto:
            if os.path.isfile(self.foto.path):
                os.remove(self.foto.path)

        super().delete(*args, **kwargs)


class EmailConfirmationToken(models.Model):
    """
    Token de confirmação de e-mail para leitores.

    Gerado automaticamente quando um leitor se cadastra.
    O token é único (UUID4) e expira após 7 dias.
    Após confirmação bem-sucedida, o token é deletado.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_confirmation_token',
        verbose_name="Usuário"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Token"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Token de Confirmação de E-mail"
        verbose_name_plural = "Tokens de Confirmação de E-mail"
        ordering = ['-created_at']

    def is_expired(self):
        """
        Verifica se o token expirou.
        Tokens expiram após 7 dias da criação.

        Returns:
            bool: True se expirado, False caso contrário
        """
        return (timezone.now() - self.created_at) > timedelta(days=7)

    def __str__(self):
        return f"Token para {self.user.email} (criado em {self.created_at.strftime('%d/%m/%Y %H:%M')})"


class PasswordResetToken(models.Model):
    """
    Token de recuperação de senha.

    Gerado quando usuário solicita recuperação de senha.
    O token é único (UUID4) e expira após 24 horas.
    Após redefinição bem-sucedida, o token é deletado.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_token',
        verbose_name="Usuário"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Token"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Token de Recuperação de Senha"
        verbose_name_plural = "Tokens de Recuperação de Senha"
        ordering = ['-created_at']

    def is_expired(self):
        """
        Verifica se o token expirou.
        Tokens expiram após 24 horas da criação.

        Returns:
            bool: True se expirado, False caso contrário
        """
        return (timezone.now() - self.created_at) > timedelta(hours=24)

    def __str__(self):
        return f"Token de recuperação para {self.user.email} (criado em {self.created_at.strftime('%d/%m/%Y %H:%M')})"


class Capa(models.Model):
    """
    Modelo para armazenar as capas/banners disponíveis para personalização de perfil.

    Item 1.1 do ROADMAP - Sistema de Capas/Banners Personalizados:
    Cada usuário pode escolher uma capa para exibir no topo de sua página de perfil.
    As capas são imagens de domínio público de fotógrafos renomados.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome da Capa",
        help_text="Nome descritivo da capa (ex: Abstrata, Árvores)"
    )
    caminho_imagem = models.CharField(
        max_length=255,
        verbose_name="Caminho da Imagem",
        help_text="Caminho relativo da imagem em static/ (ex: img/banners/banner_abstrata.jpg)"
    )
    fotografo = models.CharField(
        max_length=200,
        verbose_name="Fotógrafo",
        help_text="Nome do fotógrafo que produziu a imagem"
    )
    fonte_url = models.URLField(
        verbose_name="URL da Fonte",
        help_text="Link para a fonte original da imagem na internet"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Indica se esta capa está disponível para seleção"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Capa de Perfil"
        verbose_name_plural = "Capas de Perfil"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (por {self.fotografo})"


class ConfiguracaoUsuario(models.Model):
    """
    Configurações personalizadas do usuário.

    Armazena preferências de leitura e notificações.
    Relacionamento OneToOne com User (cada usuário tem uma configuração).
    """

    class TemaPlataforma(models.TextChoices):
        LIGHT = "light", "Claro"
        DARK = "dark", "Escuro"

    # Relacionamento OneToOne com User
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='configuracao',
        verbose_name="Usuário"
    )

    # TEMA DA PLATAFORMA (Light/Dark)
    tema_plataforma = models.CharField(
        max_length=10,
        choices=TemaPlataforma.choices,
        default=TemaPlataforma.LIGHT,
        verbose_name="Tema da Plataforma",
        help_text="Escolha entre o tema claro ou escuro para a interface da plataforma"
    )

    # PERSONALIZAÇÃO DO PERFIL (Item 1.1 do ROADMAP)
    capa_escolhida = models.ForeignKey(
        'Capa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name="Capa do Perfil",
        help_text="Capa/banner personalizado para exibir no topo da página de perfil"
    )

    class AlinhamentoVertical(models.TextChoices):
        TOPO = "top", "Alinhar no alto"
        CENTRO = "center", "Centralizar"
        BAIXO = "bottom", "Alinhar abaixo"

    alinhamento_vertical_capa = models.CharField(
        max_length=10,
        choices=AlinhamentoVertical.choices,
        default=AlinhamentoVertical.CENTRO,
        verbose_name="Alinhamento Vertical da Capa",
        help_text="Define qual parte da imagem de capa será exibida no banner do perfil"
    )

    # CONFORTO DE LEITURA (Item 4.1.2 do ROADMAP)
    # Refatorado: agora usa ForeignKey para TemaLeitura (sistema modular de temas)
    tema_leitura_padrao = models.ForeignKey(
        'core.TemaLeitura',
        on_delete=models.SET_DEFAULT,
        default=1,  # ID do tema 'padrao' (criado na data migration 0006_popular_temas_leitura)
        related_name='configuracoes',
        verbose_name="Tema de Leitura",
        help_text="Produzimos temas com muito carinho para sua leitura ser a mais confortável possível, escolha um!"
    )
    nivel_zoom_padrao = models.PositiveIntegerField(
        default=5,
        validators=[
            validators.MinValueValidator(1, 'O nível de zoom deve ser no mínimo 1.'),
            validators.MaxValueValidator(10, 'O nível de zoom deve ser no máximo 10.')
        ],
        verbose_name="Tamanho do Texto",
        help_text="Ajuste o tamanho das letras para ler sem esforço."
    )

    # NOTIFICAÇÕES (Item 4.1.3 do ROADMAP)
    receber_email_autores_favoritos = models.BooleanField(
        default=False,
        verbose_name="Avisar quando meus autores favoritos publicarem",
        help_text="Receba um e-mail sempre que seus autores favoritos publicarem textos novos"
    )
    receber_email_promocional = models.BooleanField(
        default=True,
        verbose_name="Receber novidades do Livre Dia",
        help_text="Fique por dentro das novidades e recursos que preparamos para você"
    )
    receber_email_parceiros = models.BooleanField(
        default=False,
        verbose_name="Receber ofertas de parceiros",
        help_text="Ofertas especiais de parceiros selecionados com carinho por nós"
    )
    exibir_sininho_notificacoes = models.BooleanField(
        default=True,
        verbose_name="Mostrar sininho de notificações",
        help_text="Exibir o ícone do sininho no menu superior para acompanhar suas notificações"
    )
    exibir_email_perfil = models.BooleanField(
        default=True,
        verbose_name="Exibir meu e-mail pessoal na tela de perfil",
        help_text="Quando ativado, seu e-mail será exibido publicamente no seu perfil para que outras pessoas possam entrar em contato"
    )

    # RESTRIÇÃO DE IDADE (MELHORIA 73)
    mostrar_aviso_maioridade = models.BooleanField(
        default=True,
        verbose_name="Exibir avisos de conteúdo sensível",
        help_text="Exibir avisos de conteúdo sensível e inapropriado para menores de 18 anos. "
                  "Usuários menores de 18 anos sempre verão estes avisos."
    )

    class Meta:
        verbose_name = "Configuração de Usuário"
        verbose_name_plural = "Configurações de Usuários"

    def clean(self):
        """
        Valida os campos antes de salvar.
        """
        from django.core.exceptions import ValidationError

        # Validar nível de zoom (1 a 10)
        if self.nivel_zoom_padrao < 1 or self.nivel_zoom_padrao > 10:
            raise ValidationError({
                'nivel_zoom_padrao': 'O nível de zoom deve estar entre 1 e 10.'
            })

    def __str__(self):
        return f"Configurações de {self.usuario.username}"


# Signal: Criar ConfiguracaoUsuario automaticamente ao criar User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def criar_configuracao_usuario(sender, instance, created, **kwargs):
    """
    Signal que cria ConfiguracaoUsuario automaticamente ao criar um novo User.

    Args:
        sender: Model que enviou o signal (User)
        instance: Instância do User criado
        created (bool): True se foi criação, False se foi atualização
    """
    if created:
        ConfiguracaoUsuario.objects.create(usuario=instance)


class AutorSeguido(models.Model):
    """
    Relacionamento entre leitores e autores que eles seguem (favoritam).

    Item 3 do ROADMAP - 'Autores seguidos':
    Permite que leitores sigam (favoritem) autores para acompanhar suas publicações.
    Somente usuários com role='AUTOR' podem ser seguidos.

    Funcionalidades:
    - Cada leitor pode seguir múltiplos autores
    - Cada autor pode ser seguido por múltiplos leitores
    - Um leitor só pode seguir o mesmo autor uma vez (unique_together)
    - Ordem cronológica preservada (data_seguimento)
    """
    seguidor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='autores_seguidos',
        verbose_name="Seguidor",
        help_text="Usuário que está seguindo o autor"
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='seguidores',
        limit_choices_to={'role': User.Role.AUTOR},
        verbose_name="Autor",
        help_text="Autor que está sendo seguido (apenas usuários com role=AUTOR)"
    )
    data_seguimento = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Seguimento",
        db_index=True
    )

    # ITEM 1 DO ROADMAP - Sistema de Selos de Leitor Especial
    is_leitor_especial = models.BooleanField(
        default=False,
        verbose_name="Leitor Especial",
        help_text="Indica se o autor marcou este seguidor como leitor especial"
    )
    selo_especial_modal_exibido = models.BooleanField(
        default=False,
        verbose_name="Modal de Selo Exibido",
        help_text="Controla se o modal de parabéns já foi exibido para este selo"
    )

    class Meta:
        verbose_name = "Autor Seguido"
        verbose_name_plural = "Autores Seguidos"
        ordering = ['-data_seguimento']  # Mais recentes primeiro
        unique_together = ('seguidor', 'autor')  # Um usuário segue cada autor apenas uma vez
        indexes = [
            models.Index(fields=['seguidor', '-data_seguimento']),
            models.Index(fields=['autor', '-data_seguimento']),
            models.Index(fields=['autor', 'is_leitor_especial']),  # ITEM 1 ROADMAP - filtrar leitores especiais
        ]

    def clean(self):
        """
        Valida se o usuário sendo seguido é realmente um autor.
        """
        from django.core.exceptions import ValidationError

        if self.autor.role != User.Role.AUTOR:
            raise ValidationError({
                'autor': 'Apenas usuários com perfil de Autor podem ser seguidos.'
            })

        if self.seguidor == self.autor:
            raise ValidationError({
                'seguidor': 'Um autor não pode seguir a si mesmo.'
            })

    def __str__(self):
        return f"{self.seguidor.get_display_name()} segue {self.autor.get_display_name()}"


class TipoLog(models.Model):
    """
    Tipos de log do sistema (genérico para qualquer operação auditável).

    Exemplos de tipos:
    - PIX_INCLUSAO: Inclusão de chave PIX
    - PIX_ALTERACAO: Alteração de chave PIX
    - PIX_REMOCAO: Remoção de chave PIX
    - USER_LOGIN: Login de usuário
    - USER_LOGOUT: Logout de usuário
    - etc.

    Sistema flexível que permite adicionar novos tipos sem alterar código.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código",
        help_text="Código único identificador do tipo (ex: PIX_INCLUSAO)"
    )
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome",
        help_text="Nome descritivo do tipo de log (ex: Inclusão de chave PIX)"
    )
    descricao = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição detalhada do tipo de log"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Indica se este tipo de log está ativo no sistema"
    )

    class Meta:
        verbose_name = "Tipo de Log"
        verbose_name_plural = "Tipos de Log"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Log(models.Model):
    """
    Sistema genérico de logs de auditoria.

    Registra todas as operações importantes do sistema com rastreamento
    de IP para fins de segurança e investigação de possíveis fraudes.

    Funcionalidades:
    - Auditoria de operações de monetização (PIX)
    - Auditoria de login/logout de usuários
    - Auditoria de operações administrativas
    - Auditoria de qualquer operação futura (extensível)
    """

    # Relacionamento com User (usuário que realizou a operação)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Usuário",
        help_text="Usuário que realizou a operação"
    )

    # Tipo de log (chave estrangeira para TipoLog)
    tipo_log = models.ForeignKey(
        TipoLog,
        on_delete=models.PROTECT,  # PROTECT para não deletar logs se tipo for removido
        related_name='logs',
        verbose_name="Tipo de Log",
        help_text="Tipo da operação registrada"
    )

    # Dados específicos da operação (JSON flexível para diferentes tipos de log)
    # Para PIX: tipo_chave_pix, chave_pix, pix_nome_completo, pix_nome_banco, pix_valor_padrao
    # Para Login: ip_anterior, navegador, sistema_operacional, etc.
    dados = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Dados da Operação",
        help_text="Dados específicos da operação em formato JSON"
    )

    # Metadados de auditoria
    ip_address = models.GenericIPAddressField(
        verbose_name="Endereço IP",
        help_text="IP do usuário que realizou a operação"
    )
    data_operacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da Operação",
        db_index=True
    )

    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ['-data_operacao']  # Mais recentes primeiro
        indexes = [
            models.Index(fields=['usuario', '-data_operacao']),
            models.Index(fields=['tipo_log', '-data_operacao']),
        ]

    def __str__(self):
        return f"{self.tipo_log.nome} - {self.usuario.username} em {self.data_operacao.strftime('%d/%m/%Y %H:%M')}"


class MonetizacaoPix(models.Model):
    """
    Modelo para armazenar dados de monetização via PIX dos autores.

    Separado do modelo User para:
    - Manter responsabilidade única (User não precisa saber de PIX)
    - Economizar espaço (só autores têm PIX, não todos os usuários)
    - Facilitar manutenção e extensão futura
    """

    class TipoChavePix(models.TextChoices):
        CPF = "CPF", "CPF"
        CNPJ = "CNPJ", "CNPJ"
        EMAIL = "EMAIL", "E-mail"
        TELEFONE = "TELEFONE", "Telefone"
        ALEATORIA = "ALEATORIA", "Chave Aleatória (EVP)"

    # Relacionamento com User (OneToOne - cada autor tem no máximo uma configuração PIX)
    autor = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='monetizacao_pix',
        verbose_name="Autor",
        help_text="Usuário autor que possui esta configuração de monetização"
    )

    # Dados da Chave PIX
    tipo_chave_pix = models.CharField(
        max_length=10,
        choices=TipoChavePix.choices,
        verbose_name="Tipo de Chave PIX",
        help_text="Tipo da chave PIX cadastrada para receber doações"
    )

    chave_pix = models.CharField(
        max_length=77,  # Tamanho suficiente para qualquer tipo de chave
        verbose_name="Chave PIX",
        help_text="Chave PIX para receber doações dos leitores. "
                  "Pode ser CPF, CNPJ, e-mail, telefone ou chave aleatória."
    )

    pix_nome_completo = models.CharField(
        max_length=300,
        verbose_name="Nome Completo (PIX)",
        help_text="Nome completo que aparecerá na tela de confirmação do PIX do doador. "
                  "Máximo 300 caracteres."
    )

    pix_nome_banco = models.CharField(
        max_length=100,
        verbose_name="Nome do Banco",
        help_text="Nome do banco onde a chave PIX está cadastrada"
    )

    pix_codigo_banco = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Código do Banco (COMPE)",
        help_text="Código COMPE do banco (ex: 001 para Banco do Brasil)"
    )

    # Valor Padrão
    pix_valor_padrao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            validators.MinValueValidator(0.01, 'O valor mínimo é R$ 0,01'),
            validators.MaxValueValidator(9999999.99, 'O valor máximo é R$ 9.999.999,99')
        ],
        verbose_name="Valor Padrão de Doação",
        help_text="Valor fixo sugerido para doações. Se não informado, o leitor pode doar qualquer valor."
    )

    pix_valor_padrao_informado = models.BooleanField(
        default=False,
        verbose_name="Informar Valor Padrão",
        help_text="Se True, o autor definiu um valor padrão para doações."
    )

    # Aceites (só precisa marcar uma vez, não novamente ao editar)
    pix_aceite_termos = models.BooleanField(
        default=False,
        verbose_name="Aceite dos Termos (PIX)",
        help_text="Indica que o autor aceitou os termos de uso para monetização via PIX."
    )

    pix_aceite_responsabilidade = models.BooleanField(
        default=False,
        verbose_name="Declaração de Titularidade (PIX)",
        help_text="Indica que o autor declarou que a chave PIX é de sua titularidade."
    )

    # Metadados
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        verbose_name = "Monetização PIX"
        verbose_name_plural = "Monetizações PIX"
        ordering = ['-criado_em']

    def __str__(self):
        return f"PIX de {self.autor.get_display_name()} ({self.tipo_chave_pix})"

    def tem_chave_cadastrada(self):
        """Verifica se há uma chave PIX válida cadastrada"""
        return bool(self.chave_pix and self.tipo_chave_pix)
