# Generated by Django 2.2 on 2019-04-23 17:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openbook_posts', '0028_auto_20190414_1953'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='public_comments',
        ),
        migrations.AddField(
            model_name='post',
            name='comments_enabled',
            field=models.BooleanField(default=True, editable=False, verbose_name='comments enabled'),
        ),
    ]
