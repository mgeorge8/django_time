# Generated by Django 2.1.2 on 2018-12-06 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0011_auto_20181206_1145'),
    ]

    operations = [
        migrations.AddField(
            model_name='part',
            name='engimusingPartNumber',
            field=models.CharField(default='0', editable=False, max_length=30),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='part',
            name='partNumber',
            field=models.CharField(blank=True, editable=False, max_length=30),
        ),
    ]