# Generated by Django 2.0.3 on 2018-08-06 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dpnk', '0110_competition_recreational'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='club_membership_integration',
            field=models.BooleanField(default=True, verbose_name='Integrace s klubem přátel'),
        ),
    ]
