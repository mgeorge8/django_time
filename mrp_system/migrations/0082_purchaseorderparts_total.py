# Generated by Django 2.1.2 on 2019-01-31 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0081_purchaseorder_vendor'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorderparts',
            name='total',
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=6, null=True),
        ),
    ]
