from django.db import migrations, models, transaction
import django.db.models.deletion


def _change_dict_key(the_dict, old_key, new_key, default=None):
    """
    Changes a dictionary key name from old_key to new_key.
    If old_key doesn't exist the value of new_key becomes and empty dictionary
    (or the value of `default`, if set).
    """
    if default is None:
        default = dict()

    v = the_dict.get(old_key, default)
    if new_key not in the_dict:
        the_dict[new_key] = v
    if old_key in the_dict:
        del the_dict[old_key]

    return the_dict


def change_sampleset_to_samplecart(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Job = apps.get_model('laxy_backend', 'Job')

    for job in Job.objects.using(db_alias).all():
        params = job.params
        job.params = _change_dict_key(params, 'sample_set', 'sample_cart')
        job.save()


def undo_sampleset_to_samplecart(apps, schema_editor):
    """
    This will probably never be run, but is here to make the migration reversible if required.
    """
    db_alias = schema_editor.connection.alias
    Job = apps.get_model('laxy_backend', 'Job')

    for job in Job.objects.using(db_alias).all():
        params = job.params
        job.params = _change_dict_key(params, 'sample_cart', 'sample_set')
        job.save()


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0008_auto_20190903_0019'),
    ]

    operations = [
        migrations.RunPython(change_sampleset_to_samplecart, reverse_code=undo_sampleset_to_samplecart),
    ]
