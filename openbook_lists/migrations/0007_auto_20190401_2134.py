# Generated by Django 2.2b1 on 2019-04-01 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openbook_lists', '0006_auto_20190401_2036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='list',
            name='follows',
            field=models.ManyToManyField(db_index=True, related_name='lists', to='openbook_follows.Follow'),
        ),
    ]
