# Generated by Django 2.1.2 on 2018-11-14 18:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0003_auto_20181114_1133'),
    ]

    operations = [
        migrations.RenameField(
            model_name='field',
            old_name='fieldType',
            new_name='fields',
        ),
    ]
