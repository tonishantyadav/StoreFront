# Generated by Django 4.1.7 on 2023-02-24 02:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0014_producimage'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ProducImage',
            new_name='ProductImage',
        ),
    ]