# Generated by Django 2.1.2 on 2019-01-17 12:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='payroll',
            field=models.BooleanField(default=True),
        ),
    ]
