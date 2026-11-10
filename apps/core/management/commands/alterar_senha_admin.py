"""
Comando de gerenciamento Django para alterar a senha de um administrador.

Uso:
    python manage.py alterar_senha_admin

O comando solicitará interativamente:
- Username ou Email do administrador
- Nova senha (com confirmação)

Validações:
- Usuário deve existir e ser ADMIN
- Senha com mínimo de 8 caracteres
- Confirmação de senha
"""

from django.core.management.base import BaseCommand, CommandError
from apps.usuarios.models import User
import getpass


class Command(BaseCommand):
    help = 'Altera a senha de um usuário administrador existente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('ALTERAR SENHA DE ADMINISTRADOR'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write('')

        # 1. SOLICITAR IDENTIFICAÇÃO DO ADMIN (username ou email)
        while True:
            identificacao = input('Username ou Email do administrador: ').strip()

            if not identificacao:
                self.stdout.write(self.style.ERROR('❌ Você deve fornecer um username ou email.'))
                continue

            # Buscar administrador por username ou email
            try:
                # Tenta buscar por username primeiro
                admin = User.objects.get(username=identificacao, role=User.Role.ADMIN)
            except User.DoesNotExist:
                try:
                    # Se não encontrar, tenta por email
                    admin = User.objects.get(email=identificacao, role=User.Role.ADMIN)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f'❌ Administrador com username/email "{identificacao}" não encontrado.'
                    ))
                    self.stdout.write(self.style.WARNING(
                        '   Certifique-se de que o usuário existe e tem role=ADMIN.'
                    ))
                    continue

            # Administrador encontrado
            break

        # 2. EXIBIR DADOS DO ADMIN
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Administrador encontrado:'))
        self.stdout.write(f'   ID: {admin.id}')
        self.stdout.write(f'   Username: {admin.username}')
        self.stdout.write(f'   Email: {admin.email}')
        self.stdout.write(f'   Nome: {admin.get_full_name()}')
        self.stdout.write(f'   Role: {admin.get_role_display()}')
        self.stdout.write('')

        # 3. SOLICITAR NOVA SENHA
        while True:
            password = getpass.getpass('Nova senha (mínimo 8 caracteres): ')

            if len(password) < 8:
                self.stdout.write(self.style.ERROR('❌ Senha deve ter no mínimo 8 caracteres.'))
                continue

            password_confirm = getpass.getpass('Confirme a nova senha: ')

            if password != password_confirm:
                self.stdout.write(self.style.ERROR('❌ As senhas não coincidem. Tente novamente.'))
                continue

            break

        # 4. CONFIRMAR ALTERAÇÃO
        self.stdout.write('')
        confirmar = input(f'Confirma a alteração de senha para "{admin.username}"? (s/n): ').strip().lower()

        if confirmar != 's':
            self.stdout.write(self.style.ERROR('❌ Operação cancelada pelo usuário.'))
            return

        # 5. ALTERAR SENHA
        try:
            admin.set_password(password)
            admin.save()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('✅ SENHA ALTERADA COM SUCESSO!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            self.stdout.write(f'Administrador: {admin.username} ({admin.get_full_name()})')
            self.stdout.write('A nova senha está ativa e pode ser usada imediatamente.')
            self.stdout.write('')
            self.stdout.write('Login em: http://127.0.0.1:8000/contas/login/')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao alterar senha: {e}'))
            raise CommandError(f'Falha na alteração da senha: {e}')
