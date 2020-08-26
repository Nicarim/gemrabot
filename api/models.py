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


class UserGitlabAccessToken(models.Model):
    user_id = models.CharField(max_length=255)
    slack_user = models.ForeignKey(SlackUser, on_delete=models.CASCADE)
    gitlab_access_token = models.CharField(max_length=255)


class PrMessage(models.Model):
    message_channel = models.CharField(max_length=255)
    message_ts = models.CharField(max_length=255)
    pr_id = models.IntegerField()
    repository_id = models.IntegerField()
