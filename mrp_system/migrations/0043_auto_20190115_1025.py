# Generated by Django 2.1.2 on 2019-01-15 10:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mrp_system', '0042_auto_20190114_1853'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock', models.IntegerField(blank=True, null=True)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mrp_system.Location')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='url',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='productlocation',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mrp_system.Product'),
        ),
        migrations.AddField(
            model_name='product',
            name='location',
            field=models.ManyToManyField(through='mrp_system.ProductLocation', to='mrp_system.Location'),
        ),
    ]
