# Generated manually for Phase 4 - Vilarejo Notifications

from django.db import migrations


def criar_motivos_vilarejo(apps, schema_editor):
    """
    Cria os motivos de notificacao do vilarejo:
    - MENCAO_VILAREJO: quando mencionado com @ no chat do vilarejo
    - MENSAGEM_VILAREJO: quando alguem posta no vilarejo do dono
    """
    MotivoNotificacao = apps.get_model('core', 'MotivoNotificacao')

    MotivoNotificacao.objects.create(
        codigo='MENCAO_VILAREJO',
        nome='Mencao no vilarejo',
        descricao='Voce foi mencionado em uma mensagem no vilarejo',
        ativo=True
    )

    MotivoNotificacao.objects.create(
        codigo='MENSAGEM_VILAREJO',
        nome='Mensagem no seu vilarejo',
        descricao='Alguem postou uma mensagem no seu vilarejo',
        ativo=True
    )


def remover_motivos_vilarejo(apps, schema_editor):
    """
    Remove os motivos de notificacao do vilarejo.
    Usado para reverter a migration se necessario.
    """
    MotivoNotificacao = apps.get_model('core', 'MotivoNotificacao')
    MotivoNotificacao.objects.filter(
        codigo__in=['MENCAO_VILAREJO', 'MENSAGEM_VILAREJO']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_adicionar_motivo_selo_leitor_especial"),
    ]

    operations = [
        migrations.RunPython(criar_motivos_vilarejo, remover_motivos_vilarejo),
    ]
