from django.db import migrations, models, transaction
import django.db.models.deletion


def populate_filelocation(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    File = apps.get_model('laxy_backend', 'File')
    FileLocation = apps.get_model('laxy_backend', 'FileLocation')

    for file in File.objects.using(db_alias).exclude(_location__exact=''):
        fileloc = FileLocation(url=file._location, file=file, default=True)
        fileloc.save()


def undo_populate_filelocation(apps, schema_editor):
    """
    This will probably never be run, but is here to make the migration reversible if required.
    """
    db_alias = schema_editor.connection.alias
    File = apps.get_model('laxy_backend', 'File')
    FileLocation = apps.get_model('laxy_backend', 'FileLocation')

    for file in File.objects.using(db_alias).exclude(_location__exact=''):
        fileloc = FileLocation.objects.filter(file=file).first()
        file._location = fileloc.url
        file.save()
        fileloc.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0011_auto_20191029_0526'),
    ]

    operations = [
        migrations.RunPython(populate_filelocation, reverse_code=undo_populate_filelocation),
    ]
