# Generated by Django 2.2.7 on 2019-11-25 11:45

import colorfield.fields
import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dpnk', '0139_auto_20190819_1626'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='main_color',
            field=colorfield.fields.ColorField(default='#1EA04F', max_length=18, verbose_name='Deprecated: Hlavní barva kampaně'),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='track_required',
            field=models.BooleanField(default=False, verbose_name='DEPRECATED'),
        ),
        migrations.AlterField(
            model_name='userattendance',
            name='distance',
            field=models.FloatField(blank=True, default=None, help_text='DEPRECATED', null=True, verbose_name='DEPRECATED'),
        ),
        migrations.AlterField(
            model_name='userattendance',
            name='dont_want_insert_track',
            field=models.BooleanField(default=False, verbose_name='DEPRECATED'),
        ),
        migrations.AlterField(
            model_name='userattendance',
            name='track',
            field=django.contrib.gis.db.models.fields.MultiLineStringField(blank=True, geography=True, help_text='\n<br/>\n<strong><a href="/help/" target="_blank">Klikněte zde pro nápovědu k editaci tras.</a></strong>\n<br/>\n\nTrasa slouží k výpočtu vzdálenosti a pomůže nám lépe určit potřeby lidí pohybujících se ve městě na kole.\n<br/>Trasy všech účastníků budou v anonymizované podobě zobrazené na <a href="https://mapa.prahounakole.cz/?zoom=13&lat=50.08741&lon=14.4211&layers=_Wgt">mapě Prahou na kole</a>.\n', null=True, srid=4326, verbose_name='DEPRECATED'),
        ),
    ]
