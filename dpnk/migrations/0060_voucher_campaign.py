# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-04-14 13:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dpnk', '0059_auto_20170412_2136'),
    ]

    operations = [
        migrations.AddField(
            model_name='voucher',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dpnk.Campaign'),
        ),
    ]
