# Generated by Django 2.1.10 on 2019-08-05 04:51
# Manually edited prior to commit ...

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import laxy_backend.util


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0006_sampleset_job'),
    ]

    operations = [
        migrations.RenameModel('SampleSet', 'SampleCart'),
        migrations.RenameField('PipelineRun', 'sample_set', 'sample_cart'),
    ]
