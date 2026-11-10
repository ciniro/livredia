"""
Formulários do painel do autor.
"""
from django import forms
from django.utils.text import slugify
from .models import ConfiguracaoAutor
from apps.textos.models import Texto, Tag


class ConfiguracaoAutorForm(forms.ModelForm):
    """
    Formulário para configurações personalizadas da área do autor.

    Permite ao autor escolher:
    - Cor de background (12 opções de cores terrosas claras)
    - Emoji de marca d'água (12 opções populares)
    """

    class Meta:
        model = ConfiguracaoAutor
        fields = ['cor_background', 'emoji_marca_dagua']

        widgets = {
            'cor_background': forms.RadioSelect(attrs={
                'class': 'hidden'  # Vamos usar seleção visual customizada
            }),
            'emoji_marca_dagua': forms.RadioSelect(attrs={
                'class': 'hidden'  # Vamos usar seleção visual customizada
            }),
        }

        labels = {
            'cor_background': 'Escolha a cor de fundo da sua área',
            'emoji_marca_dagua': 'Escolha um ícone de marca d\'água',
        }

        help_texts = {
            'cor_background': 'Selecione uma cor terrosa clara para personalizar o fundo da sua área.',
            'emoji_marca_dagua': 'Escolha um ícone que aparecerá sutilmente no fundo de suas páginas.',
        }


class TextoForm(forms.ModelForm):
    """
    Formulário para criar/editar textos.

    Características:
    - Validações customizadas (título min 3 chars, conteúdo min 100 chars)
    - Tags: campo ManyToMany com widget customizado
    - Geração automática de slug único
    - Suporte a rascunho e publicação
    """

    # Campo customizado para moderação (sobrescreve o BooleanField do modelo)
    moderacao_automatica = forms.TypedChoiceField(
        coerce=lambda x: x == 'True',
        choices=((True, 'Automática'), (False, 'Manual')),
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio h-4 w-4 text-primary focus:ring-primary bg-transparent border-border-light dark:border-border-dark',
        }),
        initial=True,
        label='Tipo de Moderação'
    )

    class Meta:
        model = Texto
        fields = [
            'titulo',
            'subtitulo',
            'conteudo',
            'tags',
            'selo_livre_ia',
            'is_dominio_publico',
            'is_maioridade',
            'local_escrita',
            'permite_comentarios',
            'moderacao_automatica',
            'permite_comentarios_anonimos',
            'display_autoria',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-input w-full text-4xl font-bold border-0 border-b-2 border-border-light dark:border-border-dark bg-transparent focus:ring-0 focus:border-primary p-4 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark font-display',
                'placeholder': 'Título',
                'maxlength': '255',
                'required': 'required',
            }),
            'subtitulo': forms.TextInput(attrs={
                'class': 'form-input w-full text-xl border-0 border-b border-border-light dark:border-border-dark bg-transparent focus:ring-0 focus:border-primary p-3 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark',
                'placeholder': 'Subtítulo (opcional)',
                'maxlength': '255',
            }),
            'conteudo': forms.Textarea(attrs={
                'id': 'quill-editor-content',
                'class': 'hidden',  # Oculto - Quill.js exibe WYSIWYG
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'hidden',  # Campo oculto - seleção via grid customizado
                'id': 'id_tags',
            }),
            'selo_livre_ia': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
                'id': 'selo-livre-ia',
                'checked': True,  # Marcado por padrão
            }),
            'is_dominio_publico': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
                'id': 'is-dominio-publico',
            }),
            'is_maioridade': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
                'id': 'is-maioridade',
            }),
            'local_escrita': forms.TextInput(attrs={
                'class': 'form-input w-full border border-border-light dark:border-border-dark bg-transparent focus:ring-0 focus:border-primary p-3 rounded placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark',
                'placeholder': 'Ex: Cafeteria do campus, Varanda de casa, Biblioteca municipal...',
                'maxlength': '100',
            }),
            'permite_comentarios': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
                'id': 'permite-comentarios',
                'checked': True,  # Marcado por padrão
            }),
            # moderacao_automatica: Campo customizado definido acima (TypedChoiceField)
            'permite_comentarios_anonimos': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
                'id': 'permite-anonimos',
            }),
            'display_autoria': forms.RadioSelect(attrs={
                'class': 'form-radio h-4 w-4 text-primary focus:ring-primary bg-transparent border-border-light dark:border-border-dark',
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializar formulário com defaults.
        """
        self.autor = kwargs.pop('autor', None)
        super().__init__(*args, **kwargs)

        # Definir valores padrão apenas para novo texto (não tem instance.pk)
        if not self.instance.pk:
            self.initial['selo_livre_ia'] = True
            self.initial['permite_comentarios'] = True
            self.initial['moderacao_automatica'] = True
            self.initial['permite_comentarios_anonimos'] = False
            self.initial['display_autoria'] = Texto.DisplayAutoria.REAL

        # Customizar choices do campo display_autoria se autor não tem pseudônimo
        if self.autor and not self.autor.pseudonimo:
            # Filtrar apenas opção "Nome Real"
            self.fields['display_autoria'].choices = [
                (Texto.DisplayAutoria.REAL, 'Nome Real'),
            ]
            self.fields['display_autoria'].help_text = (
                'Para usar pseudônimo, cadastre um em '
                '<a href="/contas/minha-conta/" class="text-primary hover:underline font-medium" target="_blank">Minha Conta</a>.'
            )

    def clean_titulo(self):
        """
        Validar título: mínimo 1 caractere (apenas não-vazio).
        """
        titulo = self.cleaned_data.get('titulo')

        if not titulo or len(titulo.strip()) < 1:
            raise forms.ValidationError('O título é obrigatório.')

        return titulo.strip()

    def clean_conteudo(self):
        """
        Validar conteúdo: mínimo 1 caractere (apenas não-vazio).
        """
        import re
        from django.utils.html import strip_tags

        conteudo = self.cleaned_data.get('conteudo')

        if not conteudo:
            raise forms.ValidationError('O conteúdo é obrigatório.')

        # Remover tags HTML e contar caracteres
        texto_puro = strip_tags(conteudo).strip()

        # Remover espaços múltiplos e quebras de linha
        texto_puro = re.sub(r'\s+', ' ', texto_puro)

        if len(texto_puro) < 1:
            raise forms.ValidationError('O conteúdo não pode estar vazio.')

        return conteudo

    def clean_tags(self):
        """
        Validar tags: mínimo 1, máximo 6.
        """
        tags = self.cleaned_data.get('tags')

        if not tags or tags.count() < 1:
            raise forms.ValidationError('Selecione pelo menos 1 tema para o texto.')

        if tags.count() > 6:
            raise forms.ValidationError('Selecione no máximo 6 temas para o texto.')

        return tags

    def clean_display_autoria(self):
        """
        Validar opção de display_autoria: impedir uso de pseudônimo se autor não tiver cadastrado.
        """
        display_autoria = self.cleaned_data.get('display_autoria')

        # Verificar se autor existe e se tem pseudônimo
        if self.autor and not self.autor.pseudonimo:
            # Se escolheu PSEUDONIMO ou AMBOS sem ter pseudônimo cadastrado
            if display_autoria in [Texto.DisplayAutoria.PSEUDONIMO, Texto.DisplayAutoria.AMBOS]:
                raise forms.ValidationError(
                    'Você precisa cadastrar um pseudônimo em Minha Conta antes de usar esta opção.'
                )

        return display_autoria

    def gerar_slug_unico(self, titulo):
        """
        Gerar slug único a partir do título.

        Lógica:
        1. Converter título para slug
        2. Se slug já existir, adicionar sufixo numérico (-2, -3, etc.)
        3. Retornar slug único
        """
        base_slug = slugify(titulo)[:50]  # Limitar a 50 caracteres
        slug = base_slug
        contador = 1

        # Verificar se slug já existe
        while Texto.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            contador += 1
            slug = f"{base_slug}-{contador}"

        return slug

    def save(self, commit=True):
        """
        Salvar texto com slug automático.
        """
        texto = super().save(commit=False)

        # Gerar slug automaticamente se não existir
        if not texto.slug:
            texto.slug = self.gerar_slug_unico(texto.titulo)

        # Associar autor (se fornecido via kwargs)
        if self.autor:
            texto.autor = self.autor

        if commit:
            texto.save()
            self.save_m2m()  # Salvar relacionamento ManyToMany (tags)

        return texto


class MonetizacaoForm(forms.Form):
    """
    Formulário para cadastro/edição de chave PIX para monetização.

    Item 1 do ROADMAP - Sistema de Monetização via PIX.

    Permite que autores cadastrem chave PIX para receber doações voluntárias
    dos leitores. Implementa validação rigorosa de formato e aceite de termos.

    Campos:
    - tipo_chave_pix: Tipo da chave (CPF, CNPJ, EMAIL, TELEFONE, ALEATORIA)
    - chave_pix: A chave PIX em si
    - pix_nome_completo: Nome completo para exibição na tela de confirmação do PIX (max 300 chars)
    - pix_nome_banco: Nome do banco onde a chave está cadastrada
    - pix_valor_padrao: Valor fixo sugerido (opcional)
    - aceite_termos: Checkbox confirmando leitura dos termos
    - aceite_responsabilidade: Checkbox declarando que a chave PIX é própria
    """
    from apps.usuarios.models import MonetizacaoPix

    tipo_chave_pix = forms.ChoiceField(
        choices=MonetizacaoPix.TipoChavePix.choices,
        required=True,
        initial='CPF',  # CPF como padrão
        widget=forms.Select(attrs={
            'class': 'form-select w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3',
            'id': 'tipo_chave_pix',
            'x-model': 'tipoChave',
            '@change': '$nextTick(() => { const chavePix = document.getElementById(\'chave_pix\'); if (chavePix) chavePix.value = \'\'; })',
        }),
        label='Tipo de Chave PIX',
        help_text='Escolha o tipo da sua chave PIX conforme cadastrada no seu banco.'
    )

    chave_pix = forms.CharField(
        max_length=77,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3',
            'id': 'chave_pix',
            'x-bind:placeholder': 'getPlaceholder()',
            '@input': 'validarChavePix($event)',
        }),
        label='Chave PIX',
        help_text='Digite a chave PIX exatamente como está cadastrada no seu banco.'
    )

    pix_nome_completo = forms.CharField(
        max_length=300,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3 uppercase',
            'id': 'pix_nome_completo',
            'placeholder': 'Ex: JOAO SILVA',
            'maxlength': '300',
            'oninput': 'this.value = this.value.toUpperCase()',
            'style': 'text-transform: uppercase;',
        }),
        label='Nome Completo (para exibição no PIX)',
        help_text='Nome em CAIXA ALTA que aparecerá na tela de confirmação do PIX. Limite de 300 caracteres.'
    )

    pix_nome_banco = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3',
            'id': 'pix_nome_banco',
            'placeholder': 'Digite o código ou nome do banco...',
            'autocomplete': 'off',
        }),
        label='Banco',
        help_text='Digite o código ou o nome do banco para buscar.'
    )

    pix_codigo_banco = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.HiddenInput(attrs={
            'id': 'pix_codigo_banco',
        }),
        label='Código do Banco'
    )

    pix_valor_padrao_informado = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
            'id': 'pix_valor_padrao_informado',
            'x-model': 'valorPadraoMarcado',
        }),
        label='Definir valor sugerido de doação',
        help_text=''  # Help text dinâmico será controlado no template
    )

    pix_valor_padrao = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 p-3',
            'id': 'pix_valor_padrao',
            'placeholder': '0,00',
            'step': '0.01',
            'min': '0.01',
        }),
        label='Valor Sugerido de Doação'
    )

    aceite_termos = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
            'id': 'aceite_termos',
        }),
        label='Li e aceito os termos',
        error_messages={
            'required': 'Você precisa ler e aceitar os termos para continuar.'
        }
    )

    aceite_responsabilidade = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-border-light dark:border-border-dark text-primary focus:ring-primary bg-transparent',
            'id': 'aceite_responsabilidade',
        }),
        label='Declaro que esta chave PIX é minha e autorizo receber pagamentos',
        error_messages={
            'required': 'Você precisa declarar que a chave PIX é sua para continuar.'
        }
    )

    def clean(self):
        """
        Validação customizada do formulário.

        Valida a chave PIX de acordo com o tipo selecionado usando
        os validadores rigorosos de apps.usuarios.validators.
        """
        from apps.usuarios.validators import validar_chave_pix
        from django.core.exceptions import ValidationError

        cleaned_data = super().clean()

        tipo_chave = cleaned_data.get('tipo_chave_pix')
        chave = cleaned_data.get('chave_pix')

        # Validar chave PIX apenas se ambos os campos foram preenchidos
        if tipo_chave and chave:
            # Se for TELEFONE e não começar com +55, adicionar automaticamente
            if tipo_chave == 'TELEFONE' and not chave.startswith('+55'):
                chave = '+55' + chave
                cleaned_data['chave_pix'] = chave

            try:
                # Usar validador rigoroso
                chave_validada = validar_chave_pix(tipo_chave, chave)
                # Atualizar com chave normalizada
                cleaned_data['chave_pix'] = chave_validada
            except ValidationError as e:
                # Adicionar erro ao campo chave_pix
                self.add_error('chave_pix', e.message)

        # Validar nome completo (máximo 300 caracteres)
        pix_nome_completo = cleaned_data.get('pix_nome_completo')
        if pix_nome_completo and len(pix_nome_completo) > 300:
            self.add_error('pix_nome_completo', 'O nome completo não pode exceder 300 caracteres.')

        # Validar valor padrão
        # Se pix_valor_padrao_informado = True, então o campo pix_valor_padrao é obrigatório e deve ser > 0
        pix_valor_padrao_informado = cleaned_data.get('pix_valor_padrao_informado', False)
        pix_valor_padrao = cleaned_data.get('pix_valor_padrao')

        if pix_valor_padrao_informado:
            # Checkbox marcada: valor é obrigatório
            if not pix_valor_padrao:
                self.add_error('pix_valor_padrao', 'Você marcou para definir um valor, mas não informou o valor. Informe o valor ou desmarque a opção.')
            elif pix_valor_padrao <= 0:
                self.add_error('pix_valor_padrao', 'O valor sugerido deve ser maior que zero.')
        else:
            # Checkbox desmarcada: limpar o valor (garantir que seja None)
            cleaned_data['pix_valor_padrao'] = None

        return cleaned_data
