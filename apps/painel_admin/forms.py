"""
Formulários do painel administrativo.
"""
from django import forms
from django.contrib.auth.hashers import make_password
from apps.usuarios.models import User
from apps.core.models import PaginaEstatica
from .models import ContatoAdministrativo


class NovoAutorForm(forms.ModelForm):
    """
    Formulário para cadastro de novo autor pelo admin.

    O admin preenche os dados básicos do autor e o sistema:
    1. Cria o usuário com role=AUTOR e is_active=False
    2. Gera um token de convite único (7 dias de validade)
    3. Exibe o link de ativação para o admin copiar
    """

    # Campo username (ID de usuário único para login e perfil público)
    username = forms.CharField(
        max_length=30,
        min_length=3,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border-2 border-primary/60 bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pl-12 text-base font-normal leading-normal lowercase',
            'placeholder': '',
            'autocomplete': 'off',
            'id': 'id_username',
            'style': 'text-transform: lowercase;'
        }),
        label='ID de Usuário',
        help_text='@ único do autor para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome completo'
        }),
        label='Nome Real',
        help_text='Nome completo do autor (será dividido em primeiro e último nome)'
    )

    # Campo país como ChoiceField (dropdown)
    pais = forms.ChoiceField(
        required=True,
        initial='Brasil',
        choices=[
            ('', 'Selecione'),
            ('Brasil', '🇧🇷 Brasil'),
            ('Portugal', '🇵🇹 Portugal'),
            ('Angola', '🇦🇴 Angola'),
            ('Moçambique', '🇲🇿 Moçambique'),
            ('Outro', '🌍 Outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='País'
    )

    sexo = forms.ChoiceField(
        required=True,
        choices=[
            ('', 'Selecione'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
            ('N', 'Prefiro não declarar'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Identificação de Gênero',
        help_text='Obrigatório. Usado para personalizar mensagens e selos de reconhecimento.',
        error_messages={
            'required': 'Por favor, selecione a identificação de gênero.'
        }
    )

    tipo_autor = forms.ChoiceField(
        required=False,
        initial='contemporaneo',
        choices=[
            ('contemporaneo', 'Contemporâneo'),
            ('classico', 'Clássico'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Tipo de Autor',
        help_text='Clássico: obra reconhecida historicamente. Contemporâneo: em atividade criativa atual.'
    )

    data_nascimento = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-input flex w-full min-w-0 max-w-full flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'type': 'date',
                'autocomplete': 'off'
            }
        ),
        input_formats=['%Y-%m-%d'],
        label='Data de Nascimento',
        help_text='Usado para estatísticas demográficas e personalização de conteúdo',
        error_messages={
            'required': 'Por favor, informe a data de nascimento.'
        }
    )

    remover_foto = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'remover_foto'
        }),
        label='Remover foto e usar avatar com iniciais'
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'telefone',
            'cidade',
            'foto',
            'bio',
            'pseudonimo',
            'email_contato',
            'data_nascimento',
        ]

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'nome.sobrenome@email.com'
            }),

            'telefone': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': '(XX) XXXXX-XXXX'
            }),

            'cidade': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: São Paulo'
            }),

            'foto': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'dropzone-file',
                'accept': 'image/png,image/jpeg,image/jpg,image/gif'
            }),

            'bio': forms.Textarea(attrs={
                'class': 'form-textarea flex w-full min-w-0 flex-1 resize-y overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark min-h-32 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Escreva uma breve biografia sobre o autor...',
                'rows': 5
            }),

            'pseudonimo': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: Machado de Assis (opcional)'
            }),

            'email_contato': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'contato@autor.com (opcional)'
            }),
        }

        labels = {
            'email': 'E-mail (Login)',
            'telefone': 'Telefone',
            'cidade': 'Cidade',
            'foto': 'Foto (Upload)',
            'bio': 'Bio (Resumo)',
            'pseudonimo': 'Pseudônimo',
            'email_contato': 'E-mail de Contato',
        }

        help_texts = {
            'email': 'Este será o login do autor no sistema',
            'telefone': 'Telefone de contato (opcional)',
            'cidade': 'Cidade onde o autor reside',
            'foto': 'Foto de perfil (PNG, JPG, GIF - máx 800x400px)',
            'bio': 'Breve biografia do autor (exibida na galeria)',
            'pseudonimo': 'Se vazio, autor só pode publicar com nome real',
            'email_contato': 'Se vazio, ícone de contato não aparece na galeria',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Se estiver editando (instance.pk existe), preencher nome_completo, username, país e sexo
        if self.instance and self.instance.pk:
            # Preencher nome completo
            nome_completo = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.initial['nome_completo'] = nome_completo

            # Preencher username atual do autor
            if self.instance.username:
                self.initial['username'] = self.instance.username

            # Preencher país atual do autor
            if self.instance.pais:
                self.initial['pais'] = self.instance.pais

            # Preencher sexo atual do autor
            if self.instance.sexo:
                self.initial['sexo'] = self.instance.sexo

            # Preencher tipo de autor (clássico/contemporâneo)
            self.initial['tipo_autor'] = 'classico' if self.instance.is_classico else 'contemporaneo'

            # Preencher data de nascimento no formato correto para input type="date" (YYYY-MM-DD)
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')
        else:
            # Definir Brasil como país padrão e "Prefiro não declarar" como sexo padrão (apenas ao criar)
            if not self.initial.get('pais'):
                self.initial['pais'] = 'Brasil'
            if not self.initial.get('sexo'):
                self.initial['sexo'] = 'N'
            if not self.initial.get('tipo_autor'):
                self.initial['tipo_autor'] = 'contemporaneo'

        # Marcar campos OBRIGATÓRIOS
        self.fields['username'].required = True
        self.fields['nome_completo'].required = True
        self.fields['email'].required = True
        self.fields['cidade'].required = True
        self.fields['pais'].required = True
        self.fields['data_nascimento'].required = True

        # Campos opcionais
        self.fields['telefone'].required = False
        self.fields['foto'].required = False
        self.fields['bio'].required = False
        self.fields['pseudonimo'].required = False
        self.fields['email_contato'].required = False

        # Ao editar: tornar email readonly (é usado para login, não pode ser alterado)
        if self.instance and self.instance.pk:
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] += ' bg-gray-100 dark:bg-gray-800 cursor-not-allowed'
            self.fields['email'].help_text = 'O e-mail é o login do autor e não pode ser alterado.'

    def clean_username(self):
        """
        Valida o username seguindo as regras:
        - Apenas letras minúsculas, números, hífen e sublinhado
        - Mínimo 3 caracteres, máximo 30
        - Único no sistema (exceto para o próprio usuário ao editar)
        """
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

        if username:
            # Validar formato (apenas a-z, 0-9, -, _)
            if not re.match(r'^[a-z0-9_-]+$', username):
                raise forms.ValidationError(
                    'Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_).'
                )

            # Validar tamanho mínimo
            if len(username) < 3:
                raise forms.ValidationError('O ID de usuário deve ter no mínimo 3 caracteres.')

            # Validar tamanho máximo
            if len(username) > 30:
                raise forms.ValidationError('O ID de usuário deve ter no máximo 30 caracteres.')

            # Validar se não começa ou termina com hífen ou sublinhado
            if username[0] in ['-', '_'] or username[-1] in ['-', '_']:
                raise forms.ValidationError('O ID de usuário não pode começar ou terminar com hífen ou sublinhado.')

            # Validar unicidade (excluindo o próprio usuário ao editar)
            query = User.objects.filter(username=username)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError('Este ID de usuário já está em uso. Escolha outro.')

        return username

    def clean_email(self):
        """
        Valida se o email já está cadastrado no sistema.

        IMPORTANTE: Ao editar, o email NÃO PODE ser alterado (é o login do autor).
        """
        email = self.cleaned_data.get('email')

        if email:
            # Se estiver editando, verificar se tentaram alterar o email
            if self.instance.pk:
                # IMPORTANTE: Email não pode ser alterado ao editar (é o login)
                if self.instance.email != email:
                    raise forms.ValidationError(
                        'O e-mail não pode ser alterado pois é o login do autor. '
                        'Caso necessário, exclua o autor e crie um novo cadastro.'
                    )
            else:
                # Criando novo usuário: verificar se email já existe
                if User.objects.filter(email=email).exists():
                    raise forms.ValidationError('Este e-mail já está cadastrado no sistema.')

        return email

    def save(self, commit=True):
        """
        Salva o autor dividindo nome_completo em first_name e last_name.
        Define role=AUTOR, is_active=False e username fornecido (apenas ao criar).
        Salva o país do campo personalizado.
        Remove foto se checkbox estiver marcado.

        IMPORTANTE: Ao editar, preserva is_active e username (não altera status do autor).
        IMPORTANTE: Autores clássicos recebem a senha padrão e is_active=True automaticamente.
        """
        from .models import ConfiguracaoSistema

        user = super().save(commit=False)

        # Dividir nome completo em first_name e last_name
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        user.first_name = partes[0]
        user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''

        # Salvar país, sexo, tipo de autor e data de nascimento dos campos customizados
        user.pais = self.cleaned_data['pais']
        user.sexo = self.cleaned_data.get('sexo', 'N')
        user.is_classico = (self.cleaned_data.get('tipo_autor', 'contemporaneo') == 'classico')
        user.data_nascimento = self.cleaned_data['data_nascimento']

        # Configurar autor (APENAS ao criar novo autor, não ao editar)
        # Usa self.instance.pk para verificar se é edição ou criação
        if not self.instance.pk:
            user.role = 'AUTOR'
            user.username = self.cleaned_data['username']  # Username fornecido pelo admin

            # Se é autor clássico, aplicar senha padrão e ativar automaticamente
            if user.is_classico:
                config = ConfiguracaoSistema.get_config()
                if config.senha_autores_classicos:
                    user.set_password(config.senha_autores_classicos)
                user.is_active = True  # Autor clássico já está ativo
            else:
                user.is_active = False  # Autor contemporâneo aguarda ativação via link
        # Ao editar: is_active, role e username são preservados automaticamente

        # Remover foto se checkbox estiver marcado
        if self.cleaned_data.get('remover_foto'):
            import os
            if user.foto:
                # Deletar arquivo físico
                if os.path.isfile(user.foto.path):
                    os.remove(user.foto.path)
                # Limpar campo no banco
                user.foto = None

        if commit:
            user.save()

        return user


class AtivarAutorForm(forms.ModelForm):
    """
    Formulário de ativação de conta do autor (via link de boas-vindas).

    O autor pode:
    - Confirmar/editar dados cadastrados pelo admin
    - Definir senha
    - Fazer upload de foto (opcional)
    - Aceitar termos de uso
    """

    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite seu nome completo'
        }),
        label='Nome Completo'
    )

    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Crie uma senha forte',
            'autocomplete': 'new-password'
        }),
        label='Senha'
    )

    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Confirme sua senha',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Senha'
    )

    aceito_termos = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-6 w-6 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'terms'
        }),
        label='Li e aceito os Termos de Uso e Responsabilidade',
        error_messages={
            'required': 'Você precisa aceitar os Termos de Uso para ativar sua conta.'
        }
    )

    remover_foto = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-red-600 focus:ring-2 focus:ring-red-500/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'remover_foto'
        }),
        label='Não usar foto (usar avatar com iniciais)'
    )

    # Campo hidden para persistir base64 da foto cropada quando há erro de validação
    foto_base64 = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'foto_base64'})
    )

    class Meta:
        model = User
        fields = ['email', 'foto', 'cidade', 'pais', 'telefone', 'pseudonimo', 'email_contato', 'bio']

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'seu.email@exemplo.com',
                'readonly': True  # Email não pode ser alterado (é o login)
            }),

            'foto': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'dropzone-file',
                'accept': 'image/png,image/jpeg,image/gif'
            }),

            'cidade': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Sua cidade'
            }),

            'telefone': forms.TextInput(attrs={
                'class': 'form-input w-full min-w-0 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': '(XX) XXXXX-XXXX'
            }),

            'pseudonimo': forms.TextInput(attrs={
                'class': 'form-input w-full min-w-0 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: Machado de Assis (opcional)'
            }),

            'email_contato': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'contato@autor.com (opcional)'
            }),

            'bio': forms.Textarea(attrs={
                'class': 'form-textarea flex w-full min-w-0 flex-1 resize-y overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark min-h-32 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Escreva uma breve biografia sobre você...',
                'rows': 5
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Preencher nome completo do autor
        if self.instance:
            self.fields['nome_completo'].initial = f"{self.instance.first_name} {self.instance.last_name}".strip()

        # País como ChoiceField (não está em Meta.fields, então criar aqui)
        self.fields['pais'] = forms.ChoiceField(
            required=True,
            choices=[
                ('', 'Selecione'),
                ('Brasil', '🇧🇷 Brasil'),
                ('Portugal', '🇵🇹 Portugal'),
                ('Angola', '🇦🇴 Angola'),
                ('Moçambique', '🇲🇿 Moçambique'),
                ('Outro', '🌍 Outro'),
            ],
            widget=forms.Select(attrs={
                'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
            }),
            label='País',
            initial=self.instance.pais if self.instance else 'Brasil'
        )

        # Sexo como ChoiceField (não está em Meta.fields, então criar aqui)
        self.fields['sexo'] = forms.ChoiceField(
            required=False,
            choices=[
                ('N', 'Prefiro não declarar'),
                ('F', 'Feminino'),
                ('M', 'Masculino'),
                ('O', 'Não-binário, neutro ou outro'),
            ],
            widget=forms.Select(attrs={
                'class': 'form-select w-full min-w-0 rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 px-4 pr-10 text-base font-normal leading-normal cursor-pointer',
                'style': "background-image: url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e\"); background-position: right 0.75rem center; background-repeat: no-repeat; background-size: 1.25em 1.25em; -webkit-appearance: none; -moz-appearance: none; appearance: none;"
            }),
            label='Sexo',
            help_text='Usado para personalizar mensagens e selos de reconhecimento',
            initial=self.instance.sexo if self.instance else 'N'
        )

    def clean_password2(self):
        """Valida se as senhas coincidem."""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('As senhas não coincidem.')

        return password2

    def save(self, commit=True):
        """
        Salva o autor com senha e divide nome_completo em first_name e last_name.
        Ativa o usuário (is_active=True).
        Remove foto se checkbox estiver marcado.
        Processa foto_base64 se não houver arquivo enviado.
        """
        user = super().save(commit=False)

        # Dividir nome completo
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        user.first_name = partes[0]
        user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''

        # Definir senha
        user.set_password(self.cleaned_data['password1'])

        # Salvar país e sexo
        user.pais = self.cleaned_data['pais']
        user.sexo = self.cleaned_data.get('sexo', 'N')

        # Ativar conta
        user.is_active = True

        # Remover foto se checkbox estiver marcado
        if self.cleaned_data.get('remover_foto'):
            import os
            if user.foto:
                # Deletar arquivo físico
                if os.path.isfile(user.foto.path):
                    os.remove(user.foto.path)
                # Limpar campo no banco
                user.foto = None
        # Processar foto_base64 se não houver arquivo enviado via input file
        elif self.cleaned_data.get('foto_base64') and not self.files.get('foto'):
            import base64
            import uuid
            from django.core.files.base import ContentFile

            foto_base64 = self.cleaned_data['foto_base64']
            # Remover prefixo data:image/xxx;base64, se existir
            if ';base64,' in foto_base64:
                formato, base64_data = foto_base64.split(';base64,')
                extensao = formato.split('/')[-1]
                if extensao == 'jpeg':
                    extensao = 'jpg'
            else:
                base64_data = foto_base64
                extensao = 'png'

            # Decodificar base64 para bytes
            foto_bytes = base64.b64decode(base64_data)

            # Criar arquivo com nome único
            nome_arquivo = f"{uuid.uuid4().hex}.{extensao}"
            user.foto.save(nome_arquivo, ContentFile(foto_bytes), save=False)

        if commit:
            user.save()

        return user


class EditarLeitorForm(forms.ModelForm):
    """
    Formulário para edição de leitor pelo admin.

    Permite ao admin editar:
    - Nome completo
    - Foto
    - Cidade
    - País
    - Sexo

    NÃO permite editar:
    - Email (é o login, readonly)

    Leitores não possuem campos de autor (bio, pseudônimo, email_contato, telefone).
    """

    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome completo'
        }),
        label='Nome Completo',
        help_text='Nome completo do leitor'
    )

    # Campo username (ID de usuário único para login e perfil público)
    username = forms.CharField(
        max_length=30,
        min_length=3,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border-2 border-primary/60 bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pl-12 text-base font-normal leading-normal lowercase',
            'placeholder': '',
            'autocomplete': 'off',
            'id': 'id_username',
            'style': 'text-transform: lowercase;'
        }),
        label='ID de Usuário',
        help_text='@ único do leitor para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    # Campo país como ChoiceField (dropdown)
    pais = forms.ChoiceField(
        required=True,
        initial='Brasil',
        choices=[
            ('', 'Selecione'),
            ('Brasil', '🇧🇷 Brasil'),
            ('Portugal', '🇵🇹 Portugal'),
            ('Angola', '🇦🇴 Angola'),
            ('Moçambique', '🇲🇿 Moçambique'),
            ('Outro', '🌍 Outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='País'
    )

    sexo = forms.ChoiceField(
        required=True,
        choices=[
            ('', 'Selecione'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
            ('N', 'Prefiro não declarar'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Identificação de Gênero',
        help_text='Obrigatório. Usado para personalizar mensagens e selos de reconhecimento.',
        error_messages={
            'required': 'Por favor, selecione a identificação de gênero.'
        }
    )

    data_nascimento = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-input flex w-full min-w-0 max-w-full flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'type': 'date',
                'autocomplete': 'off'
            }
        ),
        input_formats=['%Y-%m-%d'],
        label='Data de Nascimento',
        help_text='Usado para estatísticas demográficas e personalização de conteúdo',
        error_messages={
            'required': 'Por favor, informe a data de nascimento.'
        }
    )

    remover_foto = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'remover_foto'
        }),
        label='Remover foto e usar avatar com iniciais'
    )

    class Meta:
        model = User
        fields = [
            'email',
            'cidade',
            'foto',
            'data_nascimento',
        ]

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'nome.sobrenome@email.com',
                'readonly': True  # Email não pode ser alterado
            }),

            'cidade': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: São Paulo'
            }),

            'foto': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'dropzone-file',
                'accept': 'image/png,image/jpeg,image/jpg,image/gif'
            }),
        }

        labels = {
            'email': 'E-mail (Login)',
            'cidade': 'Cidade',
            'foto': 'Foto (Upload)',
        }

        help_texts = {
            'email': 'Este é o login do leitor no sistema (não pode ser alterado)',
            'cidade': 'Cidade onde o leitor reside',
            'foto': 'Foto de perfil (PNG, JPG, GIF - máx 800x400px)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Preencher nome completo, username, país e sexo ao editar
        if self.instance and self.instance.pk:
            # Preencher nome completo
            nome_completo = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.initial['nome_completo'] = nome_completo

            # Preencher username atual do leitor
            if self.instance.username:
                self.initial['username'] = self.instance.username

            # Preencher país atual do leitor
            if self.instance.pais:
                self.initial['pais'] = self.instance.pais

            # Preencher sexo atual do leitor
            if self.instance.sexo:
                self.initial['sexo'] = self.instance.sexo

            # Preencher data de nascimento no formato correto para input type="date" (YYYY-MM-DD)
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')
        else:
            # Definir Brasil como país padrão e "Prefiro não declarar" como sexo padrão (caso seja criação, o que não deveria acontecer)
            if not self.initial.get('pais'):
                self.initial['pais'] = 'Brasil'
            if not self.initial.get('sexo'):
                self.initial['sexo'] = 'N'

        # Marcar campos OBRIGATÓRIOS
        self.fields['nome_completo'].required = True
        self.fields['email'].required = True
        self.fields['cidade'].required = True
        self.fields['pais'].required = True

        # Campos opcionais
        self.fields['foto'].required = False

        # Tornar email readonly (é o login, não pode ser alterado)
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['class'] += ' bg-gray-100 dark:bg-gray-800 cursor-not-allowed'
        self.fields['email'].help_text = 'O e-mail é o login do leitor e não pode ser alterado.'

    def clean_username(self):
        """Valida username permitindo edição"""
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

        if username:
            # Validar formato (apenas a-z, 0-9, -, _)
            if not re.match(r'^[a-z0-9_-]+$', username):
                raise forms.ValidationError('Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_).')

            # Validar tamanho mínimo/máximo
            if len(username) < 3:
                raise forms.ValidationError('O ID de usuário deve ter no mínimo 3 caracteres.')
            if len(username) > 30:
                raise forms.ValidationError('O ID de usuário deve ter no máximo 30 caracteres.')

            # Validar se não começa ou termina com hífen ou sublinhado
            if username[0] in ['-', '_'] or username[-1] in ['-', '_']:
                raise forms.ValidationError('O ID de usuário não pode começar ou terminar com hífen ou sublinhado.')

            # Validar unicidade (excluindo o próprio usuário ao editar)
            query = User.objects.filter(username=username)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError('Este ID de usuário já está em uso. Escolha outro.')

        return username

    def clean_email(self):
        """
        Valida que o email não foi alterado.

        IMPORTANTE: Ao editar, o email NÃO PODE ser alterado (é o login do leitor).
        """
        email = self.cleaned_data.get('email')

        if email and self.instance.pk:
            # IMPORTANTE: Email não pode ser alterado ao editar
            if self.instance.email != email:
                raise forms.ValidationError(
                    'O e-mail não pode ser alterado pois é o login do leitor. '
                    'Caso necessário, exclua o leitor e solicite novo cadastro.'
                )

        return email

    def save(self, commit=True):
        """
        Salva o leitor dividindo nome_completo em first_name e last_name.
        Salva o país do campo personalizado.
        Remove foto se checkbox estiver marcado.

        IMPORTANTE: Preserva role=LEITOR, is_active e username.
        """
        user = super().save(commit=False)

        # Dividir nome completo em first_name e last_name
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        user.first_name = partes[0]
        user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''

        # Salvar username, país, sexo e data de nascimento dos campos customizados
        user.username = self.cleaned_data['username']
        user.pais = self.cleaned_data['pais']
        user.sexo = self.cleaned_data.get('sexo', 'N')
        user.data_nascimento = self.cleaned_data['data_nascimento']

        # Remover foto se checkbox estiver marcado
        if self.cleaned_data.get('remover_foto'):
            import os
            if user.foto:
                # Deletar arquivo físico
                if os.path.isfile(user.foto.path):
                    os.remove(user.foto.path)
                # Limpar campo no banco
                user.foto = None

        if commit:
            user.save()

        return user


class EditarPaginaForm(forms.ModelForm):
    """
    Formulário para edição de páginas estáticas pelo admin.

    Permite editar:
    - Título da página
    - Conteúdo (com Quill.js WYSIWYG)

    NÃO permite editar:
    - Slug (é a chave primária, readonly)
    """

    class Meta:
        model = PaginaEstatica
        fields = ['titulo', 'conteudo']

        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Título da página'
            }),

            'conteudo': forms.Textarea(attrs={
                'id': 'quill-editor-content',
                'class': 'hidden'  # Oculto, será controlado pelo Quill.js
            }),
        }

        labels = {
            'titulo': 'Título da Página',
            'conteudo': 'Conteúdo',
        }

        help_texts = {
            'titulo': 'Título exibido no topo da página',
            'conteudo': '',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Marcar campos como obrigatórios
        self.fields['titulo'].required = True
        self.fields['conteudo'].required = True


class NovoAdminForm(forms.ModelForm):
    """
    Formulário para cadastro de novo administrador puro (role=ADMIN).

    Apenas administradores puros (role=ADMIN) podem criar novos admins puros.
    Similar ao comando criar_admin do Django.
    """

    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome completo'
        }),
        label='Nome Completo',
        help_text='Nome completo do administrador'
    )

    # Campo username (ID de usuário único para login e perfil público)
    username = forms.CharField(
        max_length=30,
        min_length=3,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border-2 border-primary/60 bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pl-12 text-base font-normal leading-normal lowercase',
            'placeholder': '',
            'autocomplete': 'off',
            'id': 'id_username',
            'style': 'text-transform: lowercase;'
        }),
        label='ID de Usuário',
        help_text='@ único do administrador para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    password = forms.CharField(
        max_length=128,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Senha forte'
        }),
        label='Senha',
        help_text='Senha de acesso (mínimo 8 caracteres)'
    )

    password_confirm = forms.CharField(
        max_length=128,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Confirme a senha'
        }),
        label='Confirmar Senha',
        help_text='Digite a senha novamente'
    )

    sexo = forms.ChoiceField(
        required=True,
        choices=[
            ('', 'Selecione'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
            ('N', 'Prefiro não declarar'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Identificação de Gênero',
        help_text='Obrigatório. Usado para personalizar mensagens e selos de reconhecimento.',
        error_messages={
            'required': 'Por favor, selecione a identificação de gênero.'
        }
    )

    data_nascimento = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-input flex w-full min-w-0 max-w-full flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'type': 'date',
                'autocomplete': 'off'
            }
        ),
        input_formats=['%Y-%m-%d'],
        label='Data de Nascimento',
        help_text='Usado para estatísticas demográficas e personalização de conteúdo',
        error_messages={
            'required': 'Por favor, informe a data de nascimento.'
        }
    )

    class Meta:
        model = User
        fields = ['email', 'data_nascimento']

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'admin@email.com'
            }),
        }

        labels = {
            'email': 'E-mail',
        }

        help_texts = {
            'email': 'E-mail para login e recuperação de senha',
        }

    def clean_username(self):
        """
        Valida o username seguindo as regras:
        - Apenas letras minúsculas, números, hífen e sublinhado
        - Mínimo 3 caracteres, máximo 30
        - Único no sistema
        """
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

        if username:
            # Validar formato (apenas a-z, 0-9, -, _)
            if not re.match(r'^[a-z0-9_-]+$', username):
                raise forms.ValidationError(
                    'Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_).'
                )

            # Validar tamanho mínimo
            if len(username) < 3:
                raise forms.ValidationError('O ID de usuário deve ter no mínimo 3 caracteres.')

            # Validar tamanho máximo
            if len(username) > 30:
                raise forms.ValidationError('O ID de usuário deve ter no máximo 30 caracteres.')

            # Validar se não começa ou termina com hífen ou sublinhado
            if username[0] in ['-', '_'] or username[-1] in ['-', '_']:
                raise forms.ValidationError('O ID de usuário não pode começar ou terminar com hífen ou sublinhado.')

            # Validar unicidade
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Este ID de usuário já está em uso. Escolha outro.')

        return username

    def clean(self):
        """Valida os dados do formulário."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Validar se as senhas coincidem
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('As senhas não coincidem.')

        # Validar tamanho mínimo da senha
        if password and len(password) < 8:
            raise forms.ValidationError('A senha deve ter no mínimo 8 caracteres.')

        return cleaned_data

    def save(self, commit=True):
        """Cria o usuário administrador puro."""
        user = super().save(commit=False)

        # Separar nome completo em primeiro e último nome
        nome_completo = self.cleaned_data['nome_completo']
        partes_nome = nome_completo.strip().split(maxsplit=1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        # Configurar username
        user.username = self.cleaned_data['username']

        # Configurar senha (criptografada)
        user.password = make_password(self.cleaned_data['password'])

        # Configurar sexo e data de nascimento
        user.sexo = self.cleaned_data.get('sexo', 'N')
        user.data_nascimento = self.cleaned_data['data_nascimento']

        # Configurar role e permissões
        user.role = User.Role.ADMIN
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = False
        user.is_active = True

        if commit:
            user.save()

        return user


class EditarAdminForm(forms.ModelForm):
    """
    Formulário para edição de administrador puro (role=ADMIN).

    Permite editar nome, email, username e sexo.
    Apenas administradores puros podem editar outros admins puros.
    """

    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:border-primary h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite o nome completo'
        }),
        label='Nome Completo',
        help_text='Nome completo do administrador'
    )

    # Campo username (ID de usuário único para login e perfil público)
    username = forms.CharField(
        max_length=30,
        min_length=3,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border-2 border-primary/60 bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pl-12 text-base font-normal leading-normal lowercase',
            'placeholder': '',
            'autocomplete': 'off',
            'id': 'id_username',
            'style': 'text-transform: lowercase;'
        }),
        label='ID de Usuário',
        help_text='@ único do administrador para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    sexo = forms.ChoiceField(
        required=True,
        choices=[
            ('', 'Selecione'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
            ('N', 'Prefiro não declarar'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Identificação de Gênero',
        help_text='Obrigatório. Usado para personalizar mensagens e selos de reconhecimento.',
        error_messages={
            'required': 'Por favor, selecione a identificação de gênero.'
        }
    )

    data_nascimento = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-input flex w-full min-w-0 max-w-full flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'type': 'date',
                'autocomplete': 'off'
            }
        ),
        input_formats=['%Y-%m-%d'],
        label='Data de Nascimento',
        help_text='Usado para estatísticas demográficas e personalização de conteúdo',
        error_messages={
            'required': 'Por favor, informe a data de nascimento.'
        }
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'data_nascimento']

        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'admin@email.com'
            }),
        }

        labels = {
            'email': 'E-mail',
        }

        help_texts = {
            'email': 'E-mail para login e recuperação de senha',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Preencher nome_completo e sexo com dados atuais
        if self.instance and self.instance.pk:
            nome_completo = f"{self.instance.first_name} {self.instance.last_name}".strip()
            self.fields['nome_completo'].initial = nome_completo

            # Preencher sexo atual do admin
            if self.instance.sexo:
                self.fields['sexo'].initial = self.instance.sexo

            # Preencher data de nascimento no formato correto
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')

    def clean_username(self):
        """Valida username permitindo edição"""
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

        if username:
            # Validar formato (apenas a-z, 0-9, -, _)
            if not re.match(r'^[a-z0-9_-]+$', username):
                raise forms.ValidationError('Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_).')

            # Validar tamanho mínimo/máximo
            if len(username) < 3:
                raise forms.ValidationError('O ID de usuário deve ter no mínimo 3 caracteres.')
            if len(username) > 30:
                raise forms.ValidationError('O ID de usuário deve ter no máximo 30 caracteres.')

            # Validar se não começa ou termina com hífen ou sublinhado
            if username[0] in ['-', '_'] or username[-1] in ['-', '_']:
                raise forms.ValidationError('O ID de usuário não pode começar ou terminar com hífen ou sublinhado.')

            # Validar unicidade (excluindo o próprio usuário ao editar)
            query = User.objects.filter(username=username)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                raise forms.ValidationError('Este ID de usuário já está em uso. Escolha outro.')

        return username

    def save(self, commit=True):
        """Atualiza os dados do administrador."""
        user = super().save(commit=False)

        # Atualizar nome
        nome_completo = self.cleaned_data['nome_completo']
        partes_nome = nome_completo.strip().split(maxsplit=1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        # Atualizar sexo
        user.sexo = self.cleaned_data.get('sexo', 'N')

        # Atualizar data de nascimento
        user.data_nascimento = self.cleaned_data['data_nascimento']

        if commit:
            user.save()

        return user


class ContatoAdministrativoForm(forms.ModelForm):
    """
    Formulário para cadastro/edição de contatos administrativos.

    Permite cadastrar e-mails que receberão mensagens do formulário de contato público.
    """

    class Meta:
        model = ContatoAdministrativo
        fields = ['nome', 'email', 'ativo']

        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: Equipe LIVRE DIA'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'contato@livredia.com.br'
            }),

            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
                'id': 'ativo'
            }),
        }

        labels = {
            'nome': 'Nome do Contato',
            'email': 'E-mail',
            'ativo': 'Ativo',
        }

        help_texts = {
            'nome': 'Nome para identificar o responsável por este e-mail',
            'email': 'Endereço de e-mail que receberá as mensagens',
            'ativo': 'Marque para que este contato receba mensagens',
        }


# ========================================
# FORMULÁRIO DE PERSONALIZAÇÃO DO AUTOR (Item 8 do ROADMAP)
# ========================================

class PersonalizacaoAutorForm(forms.Form):
    """
    Formulário para personalizar o painel do autor (cor + ícone).
    Usado na tela de boas-vindas após ativação da conta.
    """

    cor_background = forms.ChoiceField(
        required=False,
        choices=[
            ('#F5F5DC', '🟢 Verdinho Azulejo'),
            ('#FFEBCD', '📝 Post-it da Papelaria perto do R.U.'),
            ('#FAF0E6', '👅 Tom de língua saudável'),
            ('#F8F8F0', '🥚 Casca de Ovo Perfeita'),
            ('#FFFFF0', '🚗 Bege Fusquinha'),
            ('#FDFBF6', '📜 Papel Velho (Padrão)'),
            ('#F5E6D3', '⏱️ 30 segundos para ponto de caramelo'),
            ('#F7E7CE', '🍎 Maçã Cozida com Canela'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border-2 border-texto/20 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all bg-white text-texto font-normal text-base cursor-pointer hover:border-texto/40'
        }),
        label='Cor de Fundo do Painel',
        help_text='Escolha a cor de fundo da sua área de autor',
        initial='#FDFBF6'  # Padrão: Papel Velho (PERGAMINHO)
    )

    emoji_marca_dagua = forms.ChoiceField(
        required=False,
        choices=[
            ('heart', '❤️ Sempre amando'),
            ('star', '⭐ Xerife Gramatical'),
            ('sun', '☀️ Faço fotossíntese'),
            ('moon', '🌙 Coruja Escritora'),
            ('mountain', '🏔️ Meus textos, minhas fotos'),
            ('book-open', '📖 Leio até folhetos'),
            ('pencil', '✏️ Prefiro lápis a caneta'),
            ('flower', '🌸 Xaini'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border-2 border-texto/20 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all bg-white text-texto font-normal text-base cursor-pointer hover:border-texto/40'
        }),
        label='Ícone do Painel',
        help_text='Escolha o ícone de marca d\'água da sua área de autor',
        initial='book-open'  # Padrão: Leio até folhetos (LIVRO)
    )


# ========================================
# FORMULÁRIO DE TEMAS DE LEITURA
# ========================================

class TemaLeituraForm(forms.ModelForm):
    """
    Formulário para cadastro/edição de temas de leitura.

    Permite criar e gerenciar temas CSS customizáveis para a experiência de leitura.
    """

    class Meta:
        from apps.core.models import TemaLeitura
        model = TemaLeitura
        fields = ['slug', 'nome_exibicao', 'arquivo_css', 'descricao', 'ordem', 'ativo']

        widgets = {
            'slug': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: tema-customizado'
            }),

            'nome_exibicao': forms.TextInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Ex: Tema Customizado'
            }),

            'arquivo_css': forms.FileInput(attrs={
                'class': 'form-input w-full text-text-light dark:text-text-dark file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-primary/90 file:cursor-pointer cursor-pointer',
                'accept': '.css'
            }),

            'descricao': forms.Textarea(attrs={
                'class': 'form-textarea flex w-full min-w-0 flex-1 resize-y overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark min-h-24 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': 'Descrição detalhada do tema...',
                'rows': 3
            }),

            'ordem': forms.NumberInput(attrs={
                'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
                'placeholder': '0',
                'min': '0'
            }),

            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
                'id': 'ativo'
            }),
        }

        labels = {
            'slug': 'Slug (Identificador)',
            'nome_exibicao': 'Nome de Exibição',
            'arquivo_css': 'Arquivo CSS',
            'descricao': 'Descrição',
            'ordem': 'Ordem de Exibição',
            'ativo': 'Ativo',
        }

        help_texts = {
            'slug': 'Identificador único do tema (usado nas classes CSS). Ex: padrao, sepia, noturno',
            'nome_exibicao': 'Nome exibido nos dropdowns e interfaces. Ex: Padrão, Sépia, Noturno',
            'arquivo_css': 'Upload do arquivo CSS do tema. Será salvo em static/css/themes/',
            'descricao': 'Descrição detalhada do tema (opcional)',
            'ordem': 'Ordem de exibição no dropdown (menor primeiro)',
            'ativo': 'Marque para que este tema apareça nos dropdowns',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar arquivo_css não obrigatório ao editar (pode manter o atual)
        if self.instance and self.instance.pk:
            self.fields['arquivo_css'].required = False
            self.fields['arquivo_css'].help_text = f'Arquivo atual: {self.instance.arquivo_css}. Faça upload apenas se quiser substituir.'

    def clean_arquivo_css(self):
        """
        CRÍTICO: Preserva o arquivo_css atual ao editar sem fazer novo upload.

        Quando o campo FileInput está vazio, o Django retorna None ou string vazia.
        Precisamos preservar o valor original do banco de dados nesses casos.
        """
        arquivo_css = self.cleaned_data.get('arquivo_css')

        # Se estamos editando (instance existe) E não há novo arquivo
        if self.instance and self.instance.pk:
            # Se arquivo_css é None, string vazia, ou False, preservar o atual
            if not arquivo_css:
                return self.instance.arquivo_css

        return arquivo_css


# ========================================
# FORMULÁRIO DE GESTÃO DE AUTORES CLÁSSICOS
# ========================================

class GestaoAutoresClassicosForm(forms.Form):
    """
    Formulário para configurar autores clássicos.

    Permite:
    - Definir senha padrão para todos os autores clássicos
    - Permitir/bloquear login de autores clássicos
    """

    senha_autores_classicos = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite a senha padrão'
        }),
        label='Senha Padrão',
        help_text='Esta senha será aplicada a TODOS os autores clássicos (is_classico=True)'
    )

    autores_classicos_podem_login = forms.ChoiceField(
        required=True,
        choices=[
            ('sim', 'Sim'),
            ('nao', 'Não'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Autores clássicos podem fazer login no sistema?',
        help_text='Se "Não", autores clássicos serão impedidos de acessar o sistema mesmo com senha correta'
    )

    def __init__(self, *args, **kwargs):
        # Receber configuração atual
        config = kwargs.pop('config', None)
        super().__init__(*args, **kwargs)

        if config:
            self.fields['senha_autores_classicos'].initial = config.senha_autores_classicos
            self.fields['autores_classicos_podem_login'].initial = 'sim' if config.autores_classicos_podem_login else 'nao'

    def save(self):
        """
        Salva a configuração e atualiza a senha de todos os autores clássicos.
        """
        from .models import ConfiguracaoSistema

        config = ConfiguracaoSistema.get_config()

        nova_senha = self.cleaned_data['senha_autores_classicos']
        podem_login = self.cleaned_data['autores_classicos_podem_login'] == 'sim'

        # Atualizar configuração
        config.autores_classicos_podem_login = podem_login

        # Se uma nova senha foi informada, atualizar todos os autores clássicos
        if nova_senha:
            config.senha_autores_classicos = nova_senha

            # Atualizar senha de todos os autores clássicos
            autores_classicos = User.objects.filter(role=User.Role.AUTOR, is_classico=True)
            for autor in autores_classicos:
                autor.set_password(nova_senha)
                autor.save()

        config.save()
        return config


# ========================================
# FORMULÁRIO DE COMUNICAÇÃO GERAL (E-MAIL MARKETING)
# ========================================

class ComunicacaoGeralForm(forms.Form):
    """
    Formulário para criar e enviar comunicações em massa (e-mail marketing).

    Permite:
    - Definir título e conteúdo HTML (via Quill.js)
    - Selecionar tipo de comunicação (Novidade/Parceiros/Ambos)
    - Aplicar filtros avançados (sexo, idade, autores seguidos, tempo de leitura)
    """

    titulo = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Título do e-mail'
        }),
        label='Título da Comunicação',
        help_text='Este será o assunto do e-mail enviado'
    )

    conteudo = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'id': 'quill-editor-content',
            'class': 'hidden'
        }),
        label='Conteúdo',
        help_text='Use o editor para formatar o conteúdo do e-mail'
    )

    tipo_comunicacao = forms.ChoiceField(
        required=True,
        choices=[
            ('NOVIDADE', 'Novidade do LIVRE DIA'),
            ('PARCEIROS', 'Anúncio de parceiros'),
            ('AMBOS', 'Ambos'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Tipo de Comunicação',
        help_text='Define quais usuários receberão baseado nas preferências de e-mail'
    )

    # Filtros opcionais
    filtro_sexo = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Filtrar por Sexo'
    )

    filtro_idade_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Ex: 18'
        }),
        label='Idade Mínima'
    )

    filtro_idade_max = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Ex: 65'
        }),
        label='Idade Máxima'
    )

    filtro_segue_autores = forms.ModelMultipleChoiceField(
        required=False,
        queryset=User.objects.filter(role=User.Role.AUTOR, is_active=True).order_by('first_name', 'last_name'),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select w-full min-w-0 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark p-[15px] text-base font-normal leading-normal',
            'size': '5'
        }),
        label='Segue Autores',
        help_text='Selecione autores para filtrar apenas quem os segue (Ctrl+Click para múltiplos)'
    )

    filtro_tempo_leitura = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('POUCO', 'Pouco (< 1 hora)'),
            ('MEDIO', 'Médio (1-10 horas)'),
            ('MUITO', 'Muito (> 10 horas)'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Tempo de Leitura',
        help_text='Filtrar por tempo total de leitura na plataforma'
    )

    def clean(self):
        """Validação personalizada."""
        cleaned_data = super().clean()

        # Validar idade mínima <= idade máxima
        idade_min = cleaned_data.get('filtro_idade_min')
        idade_max = cleaned_data.get('filtro_idade_max')

        if idade_min and idade_max and idade_min > idade_max:
            raise forms.ValidationError('A idade mínima não pode ser maior que a idade máxima.')

        return cleaned_data
