# Generated by Django 2.2.4 on 2019-10-29 05:26

from django.db import migrations, models
import django.db.models.deletion
import laxy_backend.models
import laxy_backend.util


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0010_job_metadata'),
    ]

    operations = [
        migrations.RenameField(
            model_name='file',
            old_name='location',
            new_name='_location',
        ),
        migrations.AlterField(
            model_name='file',
            name='_location',
            field=laxy_backend.models.ExtendedURIField(db_column='location', max_length=2048),
        ),
        migrations.CreateModel(
            name='FileLocation',
            fields=[
                ('id', models.CharField(default=laxy_backend.util.generate_uuid, editable=False, max_length=24, primary_key=True, serialize=False)),
                ('url', laxy_backend.models.ExtendedURIField(max_length=2048)),
                ('default', models.BooleanField(default=False)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='locations', to='laxy_backend.File')),
            ],
            options={
                'unique_together': {('url', 'file')},
            },
        ),
    ]
