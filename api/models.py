from uuid import uuid4

from django.db import models


class SlackUser(models.Model):
    user_id = models.CharField(max_length=255, db_index=True)
    bot_user_id = models.CharField(max_length=255, db_index=True)
    team_id = models.CharField(max_length=255, db_index=True)
    team_name = models.CharField(max_length=255)

    access_token = models.CharField(max_length=255)


class GitlabRepoChMapping(models.Model):
    channel_id = models.CharField(max_length=255, db_index=True)
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    repository_id = models.IntegerField(db_index=True)
    repository_name = models.CharField(max_length=255)


class UserGitlabOAuthToken(models.Model):
    gitlab_user_id = models.IntegerField(default=None, null=True)
    gitlab_user_name = models.CharField(max_length=255, default=None, null=True)
    state_hash = models.UUIDField(default=uuid4)
    gitlab_access_token = models.CharField(max_length=255, default=None, null=True)
    gitlab_refresh_token = models.CharField(max_length=255, default=None, null=True)

    slack_owner_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=255)
    slack_team_id = models.CharField(max_length=255)


class UserGitlabAccessToken(models.Model):
    user_id = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255)
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    gitlab_access_token = models.CharField(max_length=255)


class PrMessage(models.Model):
    message_channel = models.CharField(max_length=255)
    message_ts = models.CharField(max_length=255)
    pr_id = models.IntegerField()
    repository_id = models.IntegerField()
