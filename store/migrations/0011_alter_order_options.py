# Generated by Django 4.1.5 on 2023-01-29 07:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0010_remove_customer_store_custo_last_na_2e448d_idx_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'permissions': [('cancel_order', 'Can cancel order')]},
        ),
    ]