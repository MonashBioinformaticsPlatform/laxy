# Generated by Django 2.2.4 on 2019-11-21 02:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0015_computeresource_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='computeresource',
            name='disposable',
            field=models.BooleanField(default=False),
        ),
    ]
