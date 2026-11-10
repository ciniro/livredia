"""
Modelos do painel do autor.
"""
from django.db import models
from django.conf import settings


class ConfiguracaoAutor(models.Model):
    """
    Configurações personalizadas da área do autor.

    Permite ao autor personalizar:
    - Cor de background para light mode (tons terrosos claros)
    - Cor de background para dark mode (tons escuros elegantes)
    - Emoji de marca d'água (8 opções)
    """

    # Cores para Light Mode (tons terrosos claros)
    class CorBackgroundLight(models.TextChoices):
        PERGAMINHO = '#FDFBF6', 'Papel Velho (Padrão)'
        BEGE_CLARO = '#F5F5DC', 'Verdinho Azulejo'
        AMENDOA = '#FFEBCD', 'Post-it da Papelaria'
        LINHO = '#FAF0E6', 'Língua Saudável'
        CASCA_DE_OVO = '#F8F8F0', 'Casca de Ovo'
        MARFIM = '#FFFFF0', 'Bege Fusquinha'
        AVEIA = '#F5E6D3', 'Caramelo Derretido'
        CHAMPAGNE = '#F7E7CE', 'Maçã com Canela'

    # Cores para Dark Mode (tons escuros elegantes)
    class CorBackgroundDark(models.TextChoices):
        NOITE_ESTRELADA = '#1a1a2e', 'Noite Estrelada (Padrão)'
        CAFE_FORTE = '#2d1f1a', 'Café Forte'
        FLORESTA_NOTURNA = '#1a2e1a', 'Floresta Noturna'
        OCEANO_PROFUNDO = '#1a1f2e', 'Oceano Profundo'
        CHOCOLATE_AMARGO = '#2a1f1f', 'Chocolate Amargo'
        GRAFITE = '#252525', 'Grafite Elegante'
        VINHO_TINTO = '#2e1a1f', 'Vinho Tinto'
        CARVAO_VEGETAL = '#1f2020', 'Carvão Vegetal'

    # 8 Ícones populares (renderizados como ícones Heroicons outline)
    class EmojiMarcaDagua(models.TextChoices):
        CORACAO = 'heart', 'Sempre amando'
        ESTRELA = 'star', 'Xerife Gramatical'
        SOL = 'sun', 'Faço fotossíntese'
        LUA = 'moon', 'Coruja Escritora'
        MONTANHA = 'mountain', 'Meus textos, minhas fotos'
        LIVRO = 'book-open', 'Leio até folhetos'
        CANETA = 'pencil', 'Prefiro lápis a caneta'
        FLOR = 'flower', 'Xaini'

    # Relacionamento com o autor
    autor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configuracao_autor',
        verbose_name='Autor'
    )

    # Cor para Light Mode
    cor_background = models.CharField(
        'Cor de Background (Light)',
        max_length=7,
        choices=CorBackgroundLight.choices,
        default=CorBackgroundLight.PERGAMINHO,
        help_text='Cor de fundo da área do autor no modo claro'
    )

    # Cor para Dark Mode
    cor_background_dark = models.CharField(
        'Cor de Background (Dark)',
        max_length=7,
        choices=CorBackgroundDark.choices,
        default=CorBackgroundDark.NOITE_ESTRELADA,
        help_text='Cor de fundo da área do autor no modo escuro'
    )

    emoji_marca_dagua = models.CharField(
        'Emoji de Marca d\'água',
        max_length=20,
        choices=EmojiMarcaDagua.choices,
        default=EmojiMarcaDagua.LIVRO,
        blank=True,
        null=True,
        help_text='Emoji que aparece como marca d\'água no fundo'
    )

    # Metadados
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Configuração do Autor'
        verbose_name_plural = 'Configurações dos Autores'
        ordering = ['-atualizado_em']

    def __str__(self):
        return f'Configurações de {self.autor.get_display_name()}'

    def get_cor_background_nome(self):
        """Retorna o nome legível da cor de background (light mode)."""
        return self.get_cor_background_display()

    def get_cor_background_dark_nome(self):
        """Retorna o nome legível da cor de background (dark mode)."""
        return self.get_cor_background_dark_display()

    def get_emoji_nome(self):
        """Retorna o nome legível do emoji."""
        return self.get_emoji_marca_dagua_display()
