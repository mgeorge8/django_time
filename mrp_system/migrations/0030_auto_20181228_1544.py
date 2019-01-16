# Generated by Django 2.1.2 on 2018-12-28 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0029_digikeyapi'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='digikeyapi',
            name='site',
        ),
        migrations.AddField(
            model_name='digikeyapi',
            name='name',
            field=models.CharField(default='Digikey', max_length=100),
            preserve_default=False,
        ),
    ]