# Generated by Django 2.1.2 on 2018-12-28 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0030_auto_20181228_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='digikeyapi',
            name='date',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
