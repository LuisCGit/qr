# Generated by Django 3.0.6 on 2020-05-31 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0004_feedback'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='email',
            field=models.EmailField(max_length=200),
        ),
    ]
