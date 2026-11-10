"""
Comando para restaurar backup do banco de dados desabilitando sinais temporariamente.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models.signals import post_save
from django.apps import apps


class Command(BaseCommand):
    help = 'Restaura backup do banco de dados desabilitando sinais temporariamente'

    def add_arguments(self, parser):
        parser.add_argument('fixture_file', type=str, help='Caminho para o arquivo de fixture JSON')

    def handle(self, *args, **options):
        fixture_file = options['fixture_file']

        self.stdout.write(self.style.WARNING('Desabilitando sinais...'))

        # Desabilitar sinais post_save de todos os modelos
        sinais_desabilitados = []
        for model in apps.get_models():
            receivers = post_save._live_receivers(model)
            if receivers:
                for receiver in receivers:
                    post_save.disconnect(receiver, sender=model)
                    sinais_desabilitados.append((receiver, model))
                    self.stdout.write(f'  Desabilitado post_save para {model.__name__}')

        try:
            self.stdout.write(self.style.SUCCESS(f'\nCarregando fixture: {fixture_file}'))
            call_command('loaddata', fixture_file, verbosity=2)
            self.stdout.write(self.style.SUCCESS('\nBackup restaurado com sucesso!'))

        finally:
            # Reabilitar sinais
            self.stdout.write(self.style.WARNING('\nReabilitando sinais...'))
            for receiver, model in sinais_desabilitados:
                post_save.connect(receiver, sender=model)
                self.stdout.write(f'  Reabilitado post_save para {model.__name__}')

            self.stdout.write(self.style.SUCCESS('\nProcesso concluído!'))
