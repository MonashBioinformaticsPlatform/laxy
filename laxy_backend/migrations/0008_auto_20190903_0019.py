# Generated by Django 2.2.4 on 2019-09-03 00:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('laxy_backend', '0007_auto_20190805_0451'),
    ]

    operations = [
        migrations.AlterField(
            model_name='samplecart',
            name='job',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='samplecarts', to='laxy_backend.Job'),
        ),
        migrations.AlterField(
            model_name='samplecart',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='samplecarts', to=settings.AUTH_USER_MODEL),
        ),
    ]