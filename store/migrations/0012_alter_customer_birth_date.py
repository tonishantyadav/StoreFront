# Generated by Django 4.1.5 on 2023-01-29 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_alter_order_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='birth_date',
            field=models.DateField(null=True),
            preserve_default=False,
        ),
    ]
