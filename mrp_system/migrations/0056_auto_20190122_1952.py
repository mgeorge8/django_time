# Generated by Django 2.1.2 on 2019-01-22 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0055_auto_20190121_2007'),
    ]

    operations = [
        migrations.AlterField(
            model_name='type',
            name='prefix',
            field=models.CharField(max_length=4),
        ),
    ]
