# Generated manually for Phase 3 - Vilarejo Management

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("vilarejo", "0001_initial"),
    ]

    operations = [
        # MoradorPermanente: renomear convidado_em -> data_convite
        migrations.RenameField(
            model_name="moradorpermanente",
            old_name="convidado_em",
            new_name="data_convite",
        ),
        # MoradorPermanente: adicionar convidado_por
        migrations.AddField(
            model_name="moradorpermanente",
            name="convidado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="convites_morador_feitos",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Convidado por",
            ),
        ),
        # MoradorPermanente: alterar ordering
        migrations.AlterModelOptions(
            name="moradorpermanente",
            options={
                "ordering": ["-data_convite"],
                "verbose_name": "Morador Permanente",
                "verbose_name_plural": "Moradores Permanentes",
            },
        ),

        # BanimentoVilarejo: renomear banido_em -> data_banimento
        migrations.RenameField(
            model_name="banimentovilarejo",
            old_name="banido_em",
            new_name="data_banimento",
        ),
        # BanimentoVilarejo: adicionar banido_por
        migrations.AddField(
            model_name="banimentovilarejo",
            name="banido_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="banimentos_feitos",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Banido por",
            ),
        ),
        # BanimentoVilarejo: adicionar motivo
        migrations.AddField(
            model_name="banimentovilarejo",
            name="motivo",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Motivo",
            ),
        ),
        # BanimentoVilarejo: alterar ordering
        migrations.AlterModelOptions(
            name="banimentovilarejo",
            options={
                "ordering": ["-data_banimento"],
                "verbose_name": "Banimento do Vilarejo",
                "verbose_name_plural": "Banimentos do Vilarejo",
            },
        ),

        # HistoricoCondominio: remover campo 'tipo' e 'usuario'
        migrations.RemoveField(
            model_name="historicocondominio",
            name="tipo",
        ),
        migrations.RemoveField(
            model_name="historicocondominio",
            name="usuario",
        ),
        # HistoricoCondominio: adicionar tipo_evento
        migrations.AddField(
            model_name="historicocondominio",
            name="tipo_evento",
            field=models.CharField(
                choices=[
                    ("ENTRADA", "Se mudou para o vilarejo"),
                    ("SAIDA", "Se mudou para outro vilarejo"),
                    ("MORADOR_ADICIONADO", "Morador permanente adicionado"),
                    ("MORADOR_REMOVIDO", "Morador permanente removido"),
                    ("USUARIO_BANIDO", "Usuário banido"),
                    ("USUARIO_DESBANIDO", "Usuário desbanido"),
                    ("NOME_ALTERADO", "Nome do vilarejo alterado"),
                ],
                default="ENTRADA",
                max_length=20,
                verbose_name="Tipo de evento",
            ),
            preserve_default=False,
        ),
        # HistoricoCondominio: adicionar usuario_alvo
        migrations.AddField(
            model_name="historicocondominio",
            name="usuario_alvo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="historico_alvo_vilarejos",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Usuário alvo",
            ),
        ),
        # HistoricoCondominio: adicionar realizado_por
        migrations.AddField(
            model_name="historicocondominio",
            name="realizado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="acoes_vilarejo",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Realizado por",
            ),
        ),
        # HistoricoCondominio: adicionar detalhes
        migrations.AddField(
            model_name="historicocondominio",
            name="detalhes",
            field=models.CharField(
                blank=True,
                default="",
                max_length=300,
                verbose_name="Detalhes",
            ),
        ),
    ]
