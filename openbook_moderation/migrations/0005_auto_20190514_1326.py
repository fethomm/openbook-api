# Generated by Django 2.2 on 2019-05-14 11:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('openbook_moderation', '0004_auto_20190512_2031'),
    ]

    operations = [
        migrations.RenameField(
            model_name='moderatedobjectlog',
            old_name='log_type',
            new_name='type',
        ),
        migrations.AddField(
            model_name='moderatedobjectlog',
            name='actor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='moderatedobject',
            constraint=models.UniqueConstraint(fields=('object_type', 'object_id'), name='reporter_moderated_object_constraint'),
        ),
        migrations.AddConstraint(
            model_name='moderationreport',
            constraint=models.UniqueConstraint(fields=('reporter', 'moderated_object'), name='reporter_moderated_object_constraint'),
        ),
    ]
