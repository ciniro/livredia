"""
Comando de gerenciamento Django para criar um usuário administrador.

Uso:
    python manage.py criar_admin

O comando solicitará interativamente:
- Username
- Email
- Nome completo
- Data de nascimento
- Senha (com confirmação)

Validações:
- Username único
- Email único
- Data de nascimento válida
- Senha com mínimo de 8 caracteres
- Confirmação de senha
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from apps.usuarios.models import User
from datetime import datetime
import getpass


class Command(BaseCommand):
    help = 'Cria um novo usuário administrador via shell interativo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('CRIAR NOVO ADMINISTRADOR'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write('')

        # 1. SOLICITAR USERNAME
        while True:
            username = input('Username (login): ').strip()

            if not username:
                self.stdout.write(self.style.ERROR('❌ Username não pode estar vazio.'))
                continue

            # Verificar se username já existe
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.ERROR(f'❌ Username "{username}" já existe. Escolha outro.'))
                continue

            break

        # 2. SOLICITAR EMAIL
        while True:
            email = input('Email: ').strip()

            if not email:
                self.stdout.write(self.style.ERROR('❌ Email não pode estar vazio.'))
                continue

            # Validar formato de email
            try:
                validate_email(email)
            except ValidationError:
                self.stdout.write(self.style.ERROR('❌ Email inválido. Digite um email válido.'))
                continue

            # Verificar se email já existe
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR(f'❌ Email "{email}" já cadastrado. Use outro email.'))
                continue

            break

        # 3. SOLICITAR NOME COMPLETO
        while True:
            nome_completo = input('Nome Completo: ').strip()

            if not nome_completo:
                self.stdout.write(self.style.ERROR('❌ Nome completo não pode estar vazio.'))
                continue

            # Dividir nome completo em first_name e last_name
            partes_nome = nome_completo.split()

            if len(partes_nome) < 2:
                self.stdout.write(self.style.ERROR('❌ Digite nome e sobrenome (ex: João Silva).'))
                continue

            # Primeiro nome = first_name, resto = last_name
            first_name = partes_nome[0]
            last_name = ' '.join(partes_nome[1:])

            break

        # 4. SOLICITAR DATA DE NASCIMENTO
        while True:
            data_nasc_str = input('Data de Nascimento (DD/MM/AAAA): ').strip()

            if not data_nasc_str:
                self.stdout.write(self.style.ERROR('❌ Data de nascimento não pode estar vazia.'))
                continue

            # Validar formato e converter para date
            try:
                data_nascimento = datetime.strptime(data_nasc_str, '%d/%m/%Y').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('❌ Data inválida. Use o formato DD/MM/AAAA (ex: 15/03/1990).'))
                continue

            # Validar se é uma data válida (não no futuro)
            if data_nascimento > datetime.now().date():
                self.stdout.write(self.style.ERROR('❌ Data de nascimento não pode ser no futuro.'))
                continue

            break

        # 5. SOLICITAR SENHA
        while True:
            password = getpass.getpass('Senha (mínimo 8 caracteres): ')

            if len(password) < 8:
                self.stdout.write(self.style.ERROR('❌ Senha deve ter no mínimo 8 caracteres.'))
                continue

            password_confirm = getpass.getpass('Confirme a senha: ')

            if password != password_confirm:
                self.stdout.write(self.style.ERROR('❌ As senhas não coincidem. Tente novamente.'))
                continue

            break

        # 6. CONFIRMAR CRIAÇÃO
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('📋 DADOS DO NOVO ADMINISTRADOR:'))
        self.stdout.write(f'   Username: {username}')
        self.stdout.write(f'   Email: {email}')
        self.stdout.write(f'   Nome: {first_name} {last_name}')
        self.stdout.write(f'   Data de Nascimento: {data_nascimento.strftime("%d/%m/%Y")}')
        self.stdout.write('')

        confirmar = input('Confirma a criação do administrador? (s/n): ').strip().lower()

        if confirmar != 's':
            self.stdout.write(self.style.ERROR('❌ Operação cancelada pelo usuário.'))
            return

        # 7. CRIAR ADMINISTRADOR
        try:
            admin = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                data_nascimento=data_nascimento,
                role=User.Role.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_admin=True,
                email_verified=True,
                is_suspended=False,
                is_classico=False,
            )

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('✅ ADMINISTRADOR CRIADO COM SUCESSO!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            self.stdout.write(f'ID: {admin.id}')
            self.stdout.write(f'Username: {admin.username}')
            self.stdout.write(f'Email: {admin.email}')
            self.stdout.write(f'Nome: {admin.get_full_name()}')
            self.stdout.write(f'Role: {admin.get_role_display()}')
            self.stdout.write('')
            self.stdout.write('O administrador pode fazer login em:')
            self.stdout.write('  → http://127.0.0.1:8000/contas/login/')
            self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao criar administrador: {e}'))
            raise CommandError(f'Falha na criação do administrador: {e}')
