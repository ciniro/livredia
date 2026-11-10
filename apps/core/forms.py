from django import forms


class FaleConoscoForm(forms.Form):
    """
    Formulário de contato público para envio de mensagens ao Admin.

    Campos: nome, email, assunto, mensagem
    Não salva no banco de dados - apenas envia email.
    """

    nome = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite seu nome'
        }),
        label='Nome'
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Digite seu e-mail'
        }),
        label='E-mail'
    )

    assunto = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-14 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Sobre o que você gostaria de falar?'
        }),
        label='Assunto'
    )

    mensagem = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-lg text-text-light dark:text-text-dark focus:outline-0 focus:ring-2 focus:ring-primary/50 border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark h-48 placeholder:text-placeholder-light dark:placeholder:text-placeholder-dark p-[15px] text-base font-normal leading-normal',
            'placeholder': 'Escreva sua mensagem aqui...',
            'rows': 6
        }),
        label='Mensagem'
    )
