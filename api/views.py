import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from gitlab import Gitlab, GitlabGetError
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from api.destinations.interactions import add_project_to_channel, approve_mr_action, \
    view_submission_add_gl_project_to_ch_submit
from api.destinations.messages import get_config_empty_message, get_config_project_list, get_view_add_project
from api.destinations.slack import SlackNotifier
from api.models import SlackUser, GitlabRepoChMapping
from api.sources.gitlab import GitlabWebhook
from gemrabot.redirects import SlackRedirect

logger = logging.getLogger(__name__)


@api_view(['POST'])
def webhooks_gitlab(request: Request):
    webhook = GitlabWebhook(request, settings.GITLAB_API_KEY)
    is_valid = webhook.validate()
    if not is_valid:
        logger.info("Dropping on x_gitlab_event")
        return
    pull_request = webhook.parse()
    logger.info("Got pull request")
    gl_mapping = GitlabRepoChMapping.objects.filter(repository_id=pull_request.repository_id).first()

    slack = SlackNotifier(gl_mapping.slack_user.access_token, gl_mapping.channel_id)
    slack.notify_of_pull_request(pull_request)
    return Response(pull_request.dict())


@api_view(['GET'])
def oauth_slack(request: Request):
    code = request.query_params.get('code')
    response = requests.post('https://slack.com/api/oauth.v2.access', {
        'code': code,
        'client_id': settings.SLACK_CLIENT_ID,
        'client_secret': settings.SLACK_CLIENT_SECRET,
    })
    json_response = response.json()
    SlackUser.objects.create(
        bot_user_id=json_response['bot_user_id'],
        team_id=json_response['team']['id'],
        team_name=json_response['team']['name'],
        user_id=json_response['authed_user']['id'],
        access_token=json_response['access_token']
    )
    return SlackRedirect('slack://open')


@api_view(['POST'])
def slack_command(request: Request):
    team_id = request.data.get('team_id')
    slack_user = SlackUser.objects.filter(team_id=team_id).first()
    gl_mappings = GitlabRepoChMapping.objects.filter(slack_user=slack_user).all()
    if len(gl_mappings) <= 0:
        return JsonResponse(get_config_empty_message())
    return JsonResponse(get_config_project_list(gl_mappings))


@api_view(['POST'])
def slack_interactivity(request: Request):
    payload = json.loads(request.data.get('payload'))
    team_id = payload['team']['id']
    trigger_id = payload['trigger_id']
    slack_user = SlackUser.objects.filter(team_id=team_id).first()

    if payload['type'] == "block_actions":
        action_ids = [p['action_id'] for p in payload['actions']]
        if "add_project_to_channel" in action_ids:
            return add_project_to_channel(slack_user.access_token, trigger_id, payload['response_url'])
        if "approve_mr_action" in action_ids:
            action_name, project_id, pull_request_id = payload['actions'][0]['value'].split('-')
            return approve_mr_action(action_name, project_id, pull_request_id)
    if payload['type'] == "view_submission":
        if payload['view']['callback_id'] == "add_gitlab_project_to_channel_cb":
            return view_submission_add_gl_project_to_ch_submit(slack_user, payload)

    logger.error("Unknown interaction has been reached")
    logger.error(request.data.get('payload'))
    return Response({})
