from django.db import migrations, models
from django.db.models import F


def marcar_usados_como_resgatados(apps, schema_editor):
    # Antes desta migracao, "resgatado" era o uso pelo profissional.
    # Quem ja usou o cupom necessariamente o pegou: copia a data.
    Cliente = apps.get_model('agendamentos', 'Cliente')
    Cliente.objects.filter(cupom_usado_em__isnull=False).update(cupom_resgatado_em=F('cupom_usado_em'))


class Migration(migrations.Migration):

    dependencies = [
        ('agendamentos', '0007_emails_e_avaliacoes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cliente',
            old_name='cupom_resgatado_em',
            new_name='cupom_usado_em',
        ),
        migrations.AddField(
            model_name='cliente',
            name='cupom_resgatado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(marcar_usados_como_resgatados, migrations.RunPython.noop),
    ]
