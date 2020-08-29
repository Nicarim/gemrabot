# Generated by Django 3.1 on 2020-08-29 09:16

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_usergitlabaccesstoken_user_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGitlabOAuthToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gitlab_user_id', models.IntegerField(default=None, null=True)),
                ('gitlab_user_name', models.CharField(default=None, max_length=255, null=True)),
                ('state_hash', models.UUIDField(default=uuid.uuid4)),
                ('gitlab_access_token', models.CharField(default=None, max_length=255, null=True)),
                ('gitlab_refresh_token', models.CharField(default=None, max_length=255, null=True)),
                ('slack_user_id', models.CharField(max_length=255)),
                ('slack_team_id', models.CharField(max_length=255)),
                ('slack_owner_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.slackuser')),
            ],
        ),
    ]
