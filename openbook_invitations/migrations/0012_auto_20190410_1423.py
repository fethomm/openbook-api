# Generated by Django 2.2 on 2019-04-10 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openbook_invitations', '0011_auto_20190205_1941'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvite',
            name='nickname',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='userinvite',
            name='invited_date',
            field=models.DateTimeField(verbose_name='invited datetime'),
        ),
    ]
