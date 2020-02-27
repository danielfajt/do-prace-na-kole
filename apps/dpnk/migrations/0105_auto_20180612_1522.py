# Generated by Django 2.0.4 on 2018-06-12 15:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dpnk', '0104_auto_20180610_1730'),
    ]

    operations = [
        migrations.AddField(
            model_name='diplomafield',
            name='alignment',
            field=models.CharField(choices=[('left', 'Left'), ('right', 'Right'), ('center', 'Center')], default='left', max_length=36, verbose_name='alignment'),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='sandwich_type',
            field=models.ForeignKey(blank=True, default='', null=True, on_delete=django.db.models.deletion.SET_NULL, to='smmapdfs.PdfSandwichType'),
        ),
        migrations.AlterField(
            model_name='diplomafield',
            name='x',
            field=models.FloatField(default=0, verbose_name='X (mm)'),
        ),
        migrations.AlterField(
            model_name='diplomafield',
            name='y',
            field=models.FloatField(default=0, verbose_name='Y (mm)'),
        ),
        migrations.AlterField(
            model_name='phase',
            name='phase_type',
            field=models.CharField(choices=[('registration', 'registrační'), ('payment', 'placení startovného'), ('competition', 'soutěžní'), ('entry_enabled', 'zápis jízd umožněn'), ('results', 'výsledková'), ('admissions', 'přihlašovací do soutěží'), ('invoices', 'vytváření faktur')], default='registration', max_length=16, verbose_name='Typ fáze'),
        ),
    ]