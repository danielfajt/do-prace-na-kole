# -*- coding: utf-8 -*-
# Generated by Django 1.9.5.dev20160321164524 on 2016-05-25 15:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dpnk', '0029_auto_20160505_1218'),
    ]

    operations = [
        migrations.AddField(
            model_name='choice',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
