# Generated by Django 2.1.2 on 2018-11-14 18:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fieldType', models.CharField(choices=[('char1', 'Character 1'), ('char2', 'Character 2'), ('integer1', 'Integer 1'), ('integer2', 'Integer 2')], max_length=15)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.AddField(
            model_name='type',
            name='field',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='type', to='mrp_system.Field'),
        ),
    ]
