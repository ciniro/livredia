from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, AuthenticationForm
from django_cf_turnstile.fields import TurnstileCaptchaField
from .models import User, ConfiguracaoUsuario


class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulário de autenticação customizado com Cloudflare Turnstile.

    Item 7 do ROADMAP: Adiciona verificação de segurança na tela de login
    para aumentar a segurança contra bots e acessos automatizados maliciosos.
    """

    turnstile = TurnstileCaptchaField(
        label='',
        error_messages={
            'required': 'Por favor, complete a verificação de segurança.',
            'invalid': 'Falha na verificação de segurança. Tente novamente.',
        }
    )


class LeitorCadastroForm(UserCreationForm):
    """
    Formulário de cadastro customizado para Leitores.

    Baseado no protótipo HTML em prototipos_telas/página_de_cadastro_(leitor)/
    Campos: username, nome completo, email, senha, foto, cidade, país, sexo
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
        help_text='Seu @ único para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    # Campo para nome completo (será dividido em first_name e last_name)
    nome_completo = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Seu nome completo',
            'autocomplete': 'off'
        }),
        label='Nome Completo'
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-base font-normal leading-normal',
            'placeholder': 'seu.email@exemplo.com',
            'autocomplete': 'off'
        }),
        label='E-mail'
    )

    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark py-[15px] pl-12 pr-12 text-base font-normal leading-normal',
            'placeholder': 'Crie uma senha forte',
            'autocomplete': 'new-password'
        }),
        label='Senha'
    )

    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark py-[15px] pl-12 pr-12 text-base font-normal leading-normal',
            'placeholder': 'Confirme sua senha',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Senha'
    )

    foto = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'dropzone-file',
            'accept': 'image/png,image/jpeg,image/gif'
        }),
        label='Foto (Opcional)'
    )

    cidade = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Ex.: Belo Horizonte, Minas Gerais',
            'autocomplete': 'off'
        }),
        label='Cidade e Estado'
    )

    pais = forms.ChoiceField(
        required=False,
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
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='País'
    )

    sexo = forms.ChoiceField(
        required=False,
        initial='N',
        choices=[
            ('N', 'Prefiro não declarar'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Sexo',
        help_text='Usado para personalizar mensagens e selos de reconhecimento'
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
            'required': 'Por favor, informe sua data de nascimento.'
        }
    )

    aceito_termos = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-6 w-6 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'terms'
        }),
        label='Li e aceito os Termos de Uso e Responsabilidade',
        error_messages={
            'required': 'Você precisa aceitar os Termos de Uso para se cadastrar.'
        }
    )

    class Meta:
        model = User
        fields = ['username', 'nome_completo', 'email', 'password1', 'password2', 'foto', 'cidade', 'pais', 'sexo', 'data_nascimento']

    def clean_username(self):
        """
        Valida o username seguindo as regras:
        - Apenas letras minúsculas, números, hífen e sublinhado
        - Mínimo 3 caracteres, máximo 30
        - Único no sistema
        """
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

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

    def clean_email(self):
        """Valida se o email já não está cadastrado."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado. Faça login ou recupere sua senha.')
        return email

    def clean_nome_completo(self):
        """Valida se o nome completo tem pelo menos 2 partes (nome e sobrenome)."""
        nome_completo = self.cleaned_data.get('nome_completo')
        partes = nome_completo.strip().split()
        if len(partes) < 2:
            raise forms.ValidationError('Por favor, insira seu nome e sobrenome.')
        return nome_completo

    def save(self, commit=True):
        """
        Salva o usuário dividindo nome_completo em first_name e last_name.
        Define role='LEITOR' automaticamente.
        Usa username fornecido pelo usuário (já validado).
        """
        user = super().save(commit=False)

        # Dividir nome completo em first_name e last_name
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        user.first_name = partes[0]
        user.last_name = ' '.join(partes[1:])

        # Definir email, username e role
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['username']  # Username fornecido pelo usuário
        user.role = User.Role.LEITOR

        # Campos opcionais
        user.cidade = self.cleaned_data.get('cidade', '')
        user.pais = self.cleaned_data.get('pais', '')
        user.sexo = self.cleaned_data.get('sexo', 'N')  # Padrão: Prefiro não declarar

        # Campo obrigatório: data_nascimento
        user.data_nascimento = self.cleaned_data['data_nascimento']

        if commit:
            user.save()
            # Salvar foto separadamente (se fornecida)
            if self.cleaned_data.get('foto'):
                user.foto = self.cleaned_data['foto']
                user.save()

        return user


class EditarPerfilForm(forms.ModelForm):
    """
    Formulário para edição de perfil do usuário (Leitor, Autor ou Admin).
    Permite alterar foto, nome, cidade, país, bio, etc.
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
        help_text='Seu @ único para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    nome_completo = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Seu nome completo'
        }),
        label='Nome Completo'
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'seu.email@exemplo.com'
        }),
        label='E-mail'
    )

    pseudonimo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Seu pseudônimo (opcional)'
        }),
        label='Pseudônimo'
    )

    foto = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'dropzone-file',
            'accept': 'image/png,image/jpeg,image/gif'
        }),
        label='Foto de Perfil (Opcional)'
    )

    remover_foto = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'remover_foto'
        }),
        label='Remover foto e usar avatar com iniciais'
    )

    cidade = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Sua cidade'
        }),
        label='Cidade'
    )

    pais = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Selecione'),
            ('Brasil', '🇧🇷 Brasil'),
            ('Portugal', '🇵🇹 Portugal'),
            ('Angola', '🇦🇴 Angola'),
            ('Moçambique', '🇲🇿 Moçambique'),
            ('Outro', '🌍 Outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='País'
    )

    sexo = forms.ChoiceField(
        required=False,
        initial='N',
        choices=[
            ('N', 'Prefiro não declarar'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Sexo',
        help_text='Usado para personalizar mensagens e selos de reconhecimento'
    )

    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea flex w-full min-w-0 flex-1 resize-y overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark min-h-32 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Conte um pouco sobre você, sua trajetória literária, inspirações...',
            'rows': 5
        }),
        label='Biografia',
        help_text='Sua bio aparece no seu perfil público'
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
            'required': 'Por favor, informe sua data de nascimento.'
        }
    )

    class Meta:
        model = User
        # IMPORTANTE: 'foto' NÃO está aqui - será processada manualmente no save()
        fields = ['username', 'nome_completo', 'email', 'pseudonimo', 'cidade', 'pais', 'sexo', 'data_nascimento', 'bio']

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # Pré-preencher nome completo
        if self.instance:
            self.fields['nome_completo'].initial = f"{self.instance.first_name} {self.instance.last_name}".strip()

            # Pré-preencher data de nascimento no formato correto para input type="date" (YYYY-MM-DD)
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')

        # Remover campo 'bio' se o usuário NÃO for autor
        if user and user.role != User.Role.AUTOR:
            self.fields.pop('bio', None)

    def clean_username(self):
        """
        Valida o username seguindo as regras:
        - Apenas letras minúsculas, números, hífen e sublinhado
        - Mínimo 3 caracteres, máximo 30
        - Único no sistema (exceto para o próprio usuário)
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

            # Validar unicidade (exceto para o próprio usuário)
            if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Este ID de usuário já está em uso. Escolha outro.')

        return username

    def clean_email(self):
        """Valida se o email já não está cadastrado (exceto para o próprio usuário)."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está sendo usado por outro usuário.')
        return email

    def clean_nome_completo(self):
        """Valida se o nome completo tem pelo menos 2 partes (nome e sobrenome)."""
        nome_completo = self.cleaned_data.get('nome_completo')
        partes = nome_completo.strip().split()
        if len(partes) < 2:
            raise forms.ValidationError('Por favor, insira seu nome e sobrenome.')
        return nome_completo

    def save(self, commit=True):
        """
        Salva o usuário dividindo nome_completo em first_name e last_name.
        Se remover_foto=True, remove a foto atual do usuário.
        Se uma nova foto foi enviada, substitui a foto existente.

        IMPORTANTE: 'foto' NÃO está em Meta.fields, então é processada manualmente aqui.
        Isso evita que o Django ModelForm resete o campo foto automaticamente.
        """
        # Preservar a foto atual
        foto_atual = self.instance.foto if self.instance else None

        # Obter nova foto e flag de remoção dos dados do form
        # 'foto' e 'remover_foto' estão definidos no form, então vêm via cleaned_data
        nova_foto = self.cleaned_data.get('foto')
        remover_foto_flag = self.cleaned_data.get('remover_foto', False)

        user = super().save(commit=False)

        # Dividir nome completo em first_name e last_name
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        user.first_name = partes[0]
        user.last_name = ' '.join(partes[1:])

        # Atualizar email
        user.email = self.cleaned_data['email']
        # IMPORTANTE: Username não é alterado aqui - é readonly e preservado automaticamente

        # Atualizar pseudônimo (se fornecido)
        user.pseudonimo = self.cleaned_data.get('pseudonimo', '').strip() or None

        # Atualizar sexo
        user.sexo = self.cleaned_data.get('sexo', 'N')

        # Atualizar data de nascimento
        user.data_nascimento = self.cleaned_data['data_nascimento']

        # Atualizar bio (apenas para autores)
        if user.role == User.Role.AUTOR:
            user.bio = self.cleaned_data.get('bio', '').strip() or None

        # Processar foto manualmente
        if remover_foto_flag:
            # Remover foto se solicitado
            if foto_atual:
                import os
                try:
                    if os.path.isfile(foto_atual.path):
                        os.remove(foto_atual.path)
                except:
                    pass
            user.foto = None
        elif nova_foto:
            # Nova foto foi enviada - deletar antiga e salvar nova
            if foto_atual:
                import os
                try:
                    if os.path.isfile(foto_atual.path):
                        os.remove(foto_atual.path)
                except:
                    pass
            user.foto = nova_foto
        # IMPORTANTE: Se não está removendo e não enviou nova foto,
        # NÃO fazemos nada - o Django automaticamente preserva foto_atual
        # porque 'foto' não está em Meta.fields

        if commit:
            user.save()

        return user


class AlterarSenhaForm(PasswordChangeForm):
    """
    Formulário para alteração de senha do usuário.
    Baseado no PasswordChangeForm do Django com widgets customizados.
    """

    old_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'id': 'id_old_password',
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-12 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-sm font-normal leading-normal',
            'placeholder': 'Digite sua senha atual',
            'autocomplete': 'current-password'
        }),
        label='Senha Atual'
    )

    new_password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'id': 'id_new_password1',
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-12 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-sm font-normal leading-normal',
            'placeholder': 'Digite a nova senha',
            'autocomplete': 'new-password'
        }),
        label='Nova Senha'
    )

    new_password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'id': 'id_new_password2',
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-12 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-sm font-normal leading-normal',
            'placeholder': 'Confirme a nova senha',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Nova Senha'
    )


class DefinirSenhaForm(forms.Form):
    """
    Formulário para definir senha pela primeira vez.

    Usado por usuários que se cadastraram via Google e ainda não possuem senha.
    Não exige senha atual pois o usuário não tem uma.
    """

    new_password1 = forms.CharField(
        required=True,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'id': 'id_new_password1',
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-12 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-sm font-normal leading-normal',
            'placeholder': 'Digite a nova senha',
            'autocomplete': 'new-password'
        }),
        label='Nova Senha'
    )

    new_password2 = forms.CharField(
        required=True,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'id': 'id_new_password2',
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-12 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-sm font-normal leading-normal',
            'placeholder': 'Confirme a nova senha',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Nova Senha'
    )

    def clean(self):
        """Valida que as duas senhas são iguais."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('As senhas não coincidem.')

        return cleaned_data

    def save(self, user):
        """Define a senha para o usuário."""
        user.set_password(self.cleaned_data['new_password1'])
        user.save(update_fields=['password'])
        return user


class ExcluirContaForm(forms.Form):
    """
    Formulário para confirmação de exclusão de conta.
    Requer que o usuário digite "EXCLUIR" para confirmar.
    """

    confirmacao = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-red-500 border border-red-300 dark:border-red-800 bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite EXCLUIR para confirmar',
            'autocomplete': 'off'
        }),
        label='Confirmação'
    )

    def clean_confirmacao(self):
        """Valida se o usuário digitou exatamente 'EXCLUIR'."""
        confirmacao = self.cleaned_data.get('confirmacao')
        if confirmacao != 'EXCLUIR':
            raise forms.ValidationError('Você precisa digitar EXCLUIR (em maiúsculas) para confirmar.')
        return confirmacao


class ConfiguracoesForm(forms.ModelForm):
    """
    Formulário de configurações do usuário.

    Permite ao usuário configurar:
    - Personalização do Perfil (Item 1.1 do ROADMAP): capa/banner personalizado
    - Conforto de Leitura (Item 4.1.2 do ROADMAP): tema CSS e nível de zoom
    - Notificações (Item 4.1.3 do ROADMAP): preferências de e-mail e exibição do sininho

    Baseado no modelo ConfiguracaoUsuario.
    Refatorado: agora busca temas dinamicamente do banco de dados (TemaLeitura).
    """

    class Meta:
        model = ConfiguracaoUsuario
        fields = [
            'tema_plataforma',
            'capa_escolhida',
            'alinhamento_vertical_capa',
            'tema_leitura_padrao',
            'nivel_zoom_padrao',
            'receber_email_autores_favoritos',
            'receber_email_promocional',
            'receber_email_parceiros',
            'exibir_sininho_notificacoes',
            'exibir_email_perfil',
            'mostrar_aviso_maioridade'
        ]

        widgets = {
            'tema_plataforma': forms.RadioSelect(attrs={
                'class': 'form-radio'
            }),
            'alinhamento_vertical_capa': forms.RadioSelect(attrs={
                'class': 'form-radio'
            }),
            'tema_leitura_padrao': forms.Select(attrs={
                'class': 'form-select w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3'
            }),
            'nivel_zoom_padrao': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg appearance-none cursor-pointer accent-primary',
                'min': '1',
                'max': '10',
                'step': '1',
                'type': 'range',
                'id': 'id_nivel_zoom_padrao'
            }),
            'receber_email_autores_favoritos': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            }),
            'receber_email_promocional': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            }),
            'receber_email_parceiros': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            }),
            'exibir_sininho_notificacoes': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            }),
            'exibir_email_perfil': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            }),
            'mostrar_aviso_maioridade': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-2 border-border-light dark:border-border-dark text-primary focus:ring-2 focus:ring-primary/50 bg-background-light dark:bg-background-dark cursor-pointer'
            })
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário customizando o queryset do campo tema_leitura_padrao.
        Busca apenas temas ativos do banco de dados, ordenados por 'ordem'.
        """
        super().__init__(*args, **kwargs)

        # Importar TemaLeitura localmente para evitar import circular
        from apps.core.models import TemaLeitura

        # Configurar queryset do campo tema_leitura_padrao
        # Busca apenas temas ativos, ordenados por 'ordem'
        self.fields['tema_leitura_padrao'].queryset = TemaLeitura.objects.filter(ativo=True)

        # Customizar label_from_instance para exibir nome_exibicao ao invés do __str__
        self.fields['tema_leitura_padrao'].label_from_instance = lambda obj: obj.nome_exibicao

        # MELHORIA 73: Inverter a lógica da checkbox mostrar_aviso_maioridade
        # Campo no banco: mostrar_aviso_maioridade (True = mostrar avisos, False = não mostrar)
        # Label desejado: "Não exibir avisos..." (marcado = não mostrar)
        # Solução: Inverter o valor inicial no campo
        self.fields['mostrar_aviso_maioridade'].label = (
            "Não exibir avisos de conteúdo sensível e inapropriado para menores de 18 anos."
        )

        # Inverter o valor inicial para exibição
        # Se no banco está True (mostrar) → exibir checkbox desmarcada (False)
        # Se no banco está False (não mostrar) → exibir checkbox marcada (True)
        if self.instance and self.instance.pk:
            valor_banco = self.instance.mostrar_aviso_maioridade
            self.initial['mostrar_aviso_maioridade'] = not valor_banco

    def clean_mostrar_aviso_maioridade(self):
        """
        MELHORIA 73: Inverte a lógica da checkbox.

        Label: "Não exibir avisos..." (quando marcado = não exibir = False no banco)
        Campo no banco: mostrar_aviso_maioridade (True = exibir, False = não exibir)

        Inversão:
        - Checkbox marcada (True) → salva False no banco (não exibir)
        - Checkbox desmarcada (False) → salva True no banco (exibir)
        """
        # Obter valor da checkbox (True se marcada, False se desmarcada)
        nao_exibir = self.cleaned_data.get('mostrar_aviso_maioridade', False)

        # Inverter a lógica para salvar no banco
        # Se checkbox marcada (True) → retornar False (não mostrar avisos)
        # Se checkbox desmarcada (False) → retornar True (mostrar avisos)
        return not nao_exibir

    def clean_nivel_zoom_padrao(self):
        """Valida se o nível de zoom está entre 1 e 10."""
        nivel = self.cleaned_data.get('nivel_zoom_padrao')
        if nivel < 1 or nivel > 10:
            raise forms.ValidationError('O nível de zoom deve estar entre 1 e 10.')
        return nivel

    def clean_limite_notificacoes(self):
        """Valida se o limite de notificações está entre 30 e 100."""
        limite = self.cleaned_data.get('limite_notificacoes')
        if limite < 30 or limite > 100:
            raise forms.ValidationError('O limite de notificações deve estar entre 30 e 100.')
        return limite


class ComplementoCadastroGoogleForm(forms.Form):
    """
    Formulário de complemento de cadastro para usuários que se cadastram via Google.

    O Google fornece: email, nome completo (opcional), foto (opcional)
    Este formulário coleta os dados obrigatórios que faltam:
    - username (ID de usuário @)
    - senha (obrigatória para permitir login sem Google no futuro)
    - data_nascimento
    - aceito_termos

    Campos opcionais também disponíveis:
    - cidade
    - pais
    - sexo

    IMPORTANTE: A senha é obrigatória mesmo para cadastro via Google, para que o
    usuário possa fazer login com email/senha caso desvincule a conta Google.
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
        help_text='Seu @ único para login e perfil público. Use apenas letras minúsculas, números, hífen (-) ou sublinhado (_). Mínimo 3 caracteres.'
    )

    # Nome completo (pode vir preenchido do Google, mas editável)
    nome_completo = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Seu nome completo',
            'autocomplete': 'off'
        }),
        label='Nome Completo'
    )

    # Email (vem do Google, apenas leitura)
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-gray-100 dark:bg-gray-800 h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] pr-12 text-base font-normal leading-normal cursor-not-allowed',
            'readonly': 'readonly',
            'autocomplete': 'off'
        }),
        label='E-mail (Google)'
    )

    # Campos de senha (obrigatórios para permitir login sem Google no futuro)
    password1 = forms.CharField(
        required=True,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark py-[15px] pl-12 pr-12 text-base font-normal leading-normal',
            'placeholder': 'Crie uma senha forte',
            'autocomplete': 'new-password'
        }),
        label='Senha',
        help_text='Mínimo 4 caracteres. Será usada para login com email/senha.'
    )

    password2 = forms.CharField(
        required=True,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark py-[15px] pl-12 pr-12 text-base font-normal leading-normal',
            'placeholder': 'Confirme sua senha',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Senha'
    )

    cidade = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Ex.: Belo Horizonte, Minas Gerais',
            'autocomplete': 'off'
        }),
        label='Cidade e Estado'
    )

    pais = forms.ChoiceField(
        required=False,
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
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='País'
    )

    sexo = forms.ChoiceField(
        required=False,
        initial='N',
        choices=[
            ('N', 'Prefiro não declarar'),
            ('F', 'Feminino'),
            ('M', 'Masculino'),
            ('O', 'Não-binário, neutro ou outro'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal appearance-none'
        }),
        label='Sexo',
        help_text='Usado para personalizar mensagens e selos de reconhecimento'
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
            'required': 'Por favor, informe sua data de nascimento.'
        }
    )

    aceito_termos = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-6 w-6 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'terms'
        }),
        label='Li e aceito os Termos de Uso e Responsabilidade',
        error_messages={
            'required': 'Você precisa aceitar os Termos de Uso para se cadastrar.'
        }
    )

    def clean_username(self):
        """
        Valida o username seguindo as regras:
        - Apenas letras minúsculas, números, hífen e sublinhado
        - Mínimo 3 caracteres, máximo 30
        - Único no sistema
        """
        import re
        username = self.cleaned_data.get('username', '').lower().strip()

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

    def clean_nome_completo(self):
        """Valida se o nome completo tem pelo menos 2 partes (nome e sobrenome)."""
        nome_completo = self.cleaned_data.get('nome_completo')
        partes = nome_completo.strip().split()
        if len(partes) < 2:
            raise forms.ValidationError('Por favor, insira seu nome e sobrenome.')
        return nome_completo

    def clean(self):
        """Valida que as duas senhas são iguais."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'As senhas não coincidem.')

        return cleaned_data

    def save(self):
        """
        Cria o usuário com os dados do formulário + dados do Google.

        IMPORTANTE: Define senha para o usuário para que ele possa fazer login
        com email/senha mesmo se desvincular a conta Google no futuro.

        Retorna o usuário criado.
        """
        # Dividir nome completo em first_name e last_name
        nome_completo = self.cleaned_data['nome_completo']
        partes = nome_completo.strip().split()
        first_name = partes[0]
        last_name = ' '.join(partes[1:])

        # Criar o usuário
        user = User.objects.create(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=first_name,
            last_name=last_name,
            role=User.Role.LEITOR,
            cidade=self.cleaned_data.get('cidade', ''),
            pais=self.cleaned_data.get('pais', ''),
            sexo=self.cleaned_data.get('sexo', 'N'),
            data_nascimento=self.cleaned_data['data_nascimento'],
            email_verified=True,  # Email do Google é verificado automaticamente
        )

        # Definir senha para o usuário (permite login com email/senha)
        user.set_password(self.cleaned_data['password1'])
        user.save()

        return user
