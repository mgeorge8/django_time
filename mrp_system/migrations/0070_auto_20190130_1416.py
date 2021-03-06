# Generated by Django 2.1.2 on 2019-01-30 14:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0069_auto_20190130_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manufacturerrelationship',
            name='manufacturer',
            field=models.ForeignKey(limit_choices_to={'vendor_type': 'manufacturer'}, on_delete=django.db.models.deletion.CASCADE, to='mrp_system.Vendor'),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='name',
            field=models.CharField(max_length=128),
        ),
    ]
