# Generated by Django 2.2.20 on 2021-07-08 05:45

from django.db import migrations, models
import laxy_backend.models


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0022_systemstatus'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemstatus',
            name='end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='systemstatus',
            name='link_url',
            field=laxy_backend.models.ExtendedURIField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='systemstatus',
            name='long_message',
            field=models.CharField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='systemstatus',
            name='priority',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='systemstatus',
            name='start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='systemstatus',
            name='message',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]