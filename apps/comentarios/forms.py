from django import forms
from .models import Comentario


class ComentarioForm(forms.ModelForm):
    """
    Formulário para criar comentários em textos.

    Usado na Tela 8 (Leitura de Texto) para permitir que leitores
    comentem nos textos. Suporta comentários anônimos (se habilitado
    pelo autor do texto).
    """

    publicado_anonimamente = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 rounded border-2 border-gray-400 dark:border-gray-500 text-primary focus:ring-2 focus:ring-primary/50 bg-white dark:bg-gray-700 cursor-pointer',
            'id': 'publicar_anonimamente'
        }),
        label='Publicar como Anônimo'
    )

    class Meta:
        model = Comentario
        fields = ['conteudo', 'publicado_anonimamente', 'pai']
        widgets = {
            'conteudo': forms.Textarea(attrs={
                'class': 'form-textarea w-full min-h-[100px] resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark p-4 text-base font-normal leading-normal placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark',
                'placeholder': 'Deixe seu comentário...',
                'rows': 4,
                'autocomplete': 'off'
            }),
            'pai': forms.HiddenInput(),  # Para respostas aninhadas
        }
        labels = {
            'conteudo': 'Comentário',
        }

    def clean_conteudo(self):
        """Valida o conteúdo do comentário."""
        conteudo = self.cleaned_data.get('conteudo')

        # Remover espaços em branco extras
        conteudo = conteudo.strip()

        # Validar tamanho mínimo
        if len(conteudo) < 3:
            raise forms.ValidationError('O comentário deve ter pelo menos 3 caracteres.')

        # Validar tamanho máximo
        if len(conteudo) > 2000:
            raise forms.ValidationError('O comentário não pode ter mais de 2000 caracteres.')

        return conteudo
