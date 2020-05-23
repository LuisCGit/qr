# Generated by Django 3.0.6 on 2020-05-22 22:52

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('restaurant_admin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_paid', models.BooleanField(default=False)),
                ('cash_code', models.CharField(max_length=255, null=True)),
                ('menu_items', models.ManyToManyField(to='restaurant_admin.MenuItem')),
            ],
        ),
    ]
