# Generated by Django 2.1.2 on 2019-01-29 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0061_auto_20190124_2231'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manufacturer',
            name='name',
            field=models.CharField(max_length=128, unique=True),
        ),
    ]