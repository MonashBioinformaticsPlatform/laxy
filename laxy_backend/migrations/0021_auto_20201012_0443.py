# Generated by Django 2.2.10 on 2020-10-12 04:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("laxy_backend", "0020_pipeline_metadata"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="pipeline",
            options={"permissions": (("run_pipeline", "Can run this pipeline"),)},
        ),
    ]
