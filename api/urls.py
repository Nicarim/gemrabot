from django.urls import path
from . import views

urlpatterns = [
   path('webhooks/gitlab/', views.webhooks_gitlab),
   path('oauth/redirect/slack/', views.oauth_slack),
   path('slack/command/', views.slack_command),
   path('slack/interactive/', views.slack_interactivity),
]
