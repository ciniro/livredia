"""
Comando de gerenciamento Django para baixar fotos de autores clássicos.

Usa Wikimedia Commons para buscar fotos dos autores.
"""

import os
import time
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.usuarios.models import User


class Command(BaseCommand):
    help = 'Baixa fotos de autores clássicos da Wikimedia Commons'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('📸 BAIXANDO FOTOS DOS AUTORES CLÁSSICOS'))
        self.stdout.write('=' * 80)
        self.stdout.write('')

        autores = User.objects.filter(is_classico=True).order_by('id')
        total = autores.count()

        sucessos = 0
        falhas = 0
        ja_tem = 0

        for idx, autor in enumerate(autores, 1):
            self.stdout.write(f'[{idx}/{total}] {autor.pseudonimo}...')

            # Se já tem foto, pular
            if autor.foto:
                self.stdout.write(self.style.SUCCESS('  ✅ Já possui foto'))
                ja_tem += 1
                continue

            # Tentar baixar foto da Wikimedia Commons
            foto_content = self._baixar_foto_wikimedia(autor.pseudonimo)

            if foto_content:
                # Salvar foto
                filename = f'{autor.username}.jpg'
                autor.foto.save(filename, foto_content, save=True)
                self.stdout.write(self.style.SUCCESS(f'  ✅ Foto baixada e salva: {filename}'))
                sucessos += 1
            else:
                self.stdout.write(self.style.WARNING('  ⚠️  Não foi possível baixar foto'))
                falhas += 1

            # Delay entre requisições para evitar rate limiting
            if idx < total:
                time.sleep(1)  # 1 segundo entre cada autor

            self.stdout.write('')

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ CONCLUÍDO!'))
        self.stdout.write(f'📸 Fotos já existentes: {ja_tem}/{total}')
        self.stdout.write(f'📸 Fotos baixadas: {sucessos}/{total}')
        self.stdout.write(f'⚠️  Falhas: {falhas}/{total}')

    def _baixar_foto_wikimedia(self, nome_autor):
        """Busca e baixa foto do autor usando DuckDuckGo Images"""
        try:
            from duckduckgo_search import DDGS

            # Buscar imagem usando DuckDuckGo
            query = f'{nome_autor} escritor retrato'

            with DDGS() as ddgs:
                resultados = list(ddgs.images(
                    keywords=query,
                    max_results=3,
                    safesearch='off'
                ))

                if resultados:
                    # Tentar baixar a primeira imagem
                    for resultado in resultados:
                        img_url = resultado.get('image')

                        if img_url:
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                            }

                            img_response = requests.get(img_url, headers=headers, timeout=10)

                            if img_response.status_code == 200:
                                return ContentFile(img_response.content)

            return None

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Erro ao baixar foto: {e}'))
            return None
