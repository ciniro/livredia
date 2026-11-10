"""
Comando de gerenciamento Django para LIMPAR COMPLETAMENTE o banco de dados.

DELETA TUDO:
- Todos os textos, tags, visualizações, comentários
- Todos os usuários (incluindo admin)
- Todas as páginas estáticas
- Todos os convites
- Todos os selos
- Todas as notificações
- Tudo mesmo!

RESETA TODAS AS SEQUÊNCIAS:
- Todas as chaves auto incremento voltam para 1
- Banco fica completamente limpo/vazio
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'LIMPA COMPLETAMENTE o banco de dados - APAGA TUDO e reseta todas as sequências'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🗑️  LIMPANDO BANCO DE DADOS COMPLETAMENTE...'))
        self.stdout.write(self.style.ERROR('⚠️  ATENÇÃO: Isso vai APAGAR TUDO!'))
        self.stdout.write('')

        # 0. Limpar arquivos de mídia (fotos de perfil)
        self._limpar_arquivos_midia()

        with connection.cursor() as cursor:
            # 1. Desabilitar constraints temporariamente
            self.stdout.write(self.style.WARNING('🔓 Desabilitando constraints...'))
            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            self.stdout.write(self.style.SUCCESS('✅ Constraints desabilitadas'))
            self.stdout.write('')

            # 2. Obter todas as tabelas do projeto (exceto tabelas do Django)
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'auth_%'
                AND tablename NOT LIKE 'django_%'
                ORDER BY tablename
            """)

            tables = cursor.fetchall()
            total_deletado = 0

            self.stdout.write(self.style.WARNING('🗑️  Deletando dados de todas as tabelas...'))

            for (table_name,) in tables:
                try:
                    # Contar registros antes de deletar
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]

                    if count > 0:
                        # Deletar todos os registros
                        cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                        total_deletado += count
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ {table_name}: {count} registro(s) deletado(s)'
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ❌ Erro ao deletar {table_name}: {e}'
                        )
                    )

            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ TOTAL: {total_deletado} registros deletados'
                )
            )
            self.stdout.write('')

            # 3. Resetar TODAS as sequências de auto incremento
            self.stdout.write(self.style.WARNING('🔄 Resetando todas as sequências...'))

            cursor.execute("""
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'public'
                ORDER BY sequence_name
            """)

            sequences = cursor.fetchall()
            total_sequences = len(sequences)

            for (seq_name,) in sequences:
                try:
                    cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ {seq_name} → resetada para 1')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Erro ao resetar {seq_name}: {e}')
                    )

            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {total_sequences} sequências resetadas'
                )
            )
            self.stdout.write('')

            # 4. Reabilitar constraints
            self.stdout.write(self.style.WARNING('🔒 Reabilitando constraints...'))
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            self.stdout.write(self.style.SUCCESS('✅ Constraints reabilitadas'))
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('🎉 BANCO DE DADOS COMPLETAMENTE LIMPO!'))
        self.stdout.write(self.style.WARNING('📌 Próximo passo: Executar migrate + criar SUPER ADMIN'))

    def _limpar_arquivos_midia(self):
        """
        Deleta todos os arquivos de mídia (fotos de perfil, capas, etc.)
        """
        self.stdout.write(self.style.WARNING('📁 Limpando arquivos de mídia...'))

        # Pastas a serem limpas
        pastas_midia = [
            'perfis',      # Fotos de perfil dos autores
            'capas',       # Capas de perfil
            'textos',      # Arquivos anexos de textos (se houver)
        ]

        total_arquivos = 0
        total_pastas = 0

        media_root = Path(settings.MEDIA_ROOT)

        for pasta_nome in pastas_midia:
            pasta_path = media_root / pasta_nome

            if pasta_path.exists() and pasta_path.is_dir():
                # Contar arquivos antes de deletar
                arquivos = list(pasta_path.glob('*'))
                num_arquivos = len([f for f in arquivos if f.is_file()])

                if num_arquivos > 0:
                    # Deletar todos os arquivos da pasta
                    for arquivo in arquivos:
                        if arquivo.is_file():
                            try:
                                arquivo.unlink()
                                total_arquivos += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  ❌ Erro ao deletar {arquivo.name}: {e}'
                                    )
                                )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ {pasta_nome}/: {num_arquivos} arquivo(s) deletado(s)'
                        )
                    )
                    total_pastas += 1

        if total_arquivos > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ TOTAL: {total_arquivos} arquivo(s) de mídia deletados de {total_pastas} pasta(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✅ Nenhum arquivo de mídia para deletar'
                )
            )

        self.stdout.write('')
