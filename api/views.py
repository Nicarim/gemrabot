import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from gitlab import Gitlab, GitlabGetError
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

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
    channel_id = request.data.get('channel_id')
    token = slack_user.access_token
    gl_mappings = GitlabRepoChMapping.objects.filter(slack_user=slack_user).all()
    append_response = []
    if len(gl_mappings) <= 0:
        append_response.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': 'Currently no channels are added, please use buttons below to add new channels'
            }
        })
    else:
        append_response.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'You have {len(gl_mappings)} project connected: '
            }
        })
        for mapping in gl_mappings:
            append_response.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'- Project *{mapping.repository_name}* is connected to channel *<#{mapping.channel_id}>*'
                }
            })
    response = {
        'blocks': []
    }
    for x in append_response:
        response['blocks'].append(x)
    response['blocks'].append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "action_id": "add_project_to_channel",
                "text": {
                    "type": "plain_text",
                    "text": "Add new project to a channel"
                }
            }
        ]
    })
    return JsonResponse(response)


@api_view(['POST'])
def slack_interactivity(request: Request):
    payload = json.loads(request.data.get('payload'))
    team_id = payload['team']['id']
    trigger_id = payload['trigger_id']
    slack_user = SlackUser.objects.filter(team_id=team_id).first()

    if payload['type'] == "block_actions":
        action_ids = [p['action_id'] for p in payload['actions']]
        if "add_project_to_channel" in action_ids:
            modal = {
                "title": {
                    "type": "plain_text",
                    "text": "Add project",
                    "emoji": True
                },
                "callback_id": "add_gitlab_project_to_channel_cb",
                "submit": {
                    "type": "plain_text",
                    "text": "Add",
                    "emoji": True
                },
                "type": "modal",
                "close": {
                    "type": "plain_text",
                    "text": "Cancel",
                    "emoji": True
                },
                "blocks": [
                    {
                        "type": "input",
                        "label": {
                            "type": "plain_text",
                            "text": "Select channel to which it should post",
                            "emoji": True
                        },
                        "element": {
                            "type": "channels_select",
                            "action_id": "add_gitlab_channel_id",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Choose list",
                                "emoji": True
                            }
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "project_id_bl",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "add_gitlab_project_id"
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Here put project id (seen in settings) of gitlab project",
                            "emoji": True
                        }
                    }
                ]
            }
            requests.post('https://slack.com/api/views.open', {
                'token': slack_user.access_token,
                'trigger_id': trigger_id,
                'view': json.dumps(modal)
            })
            requests.post(payload['response_url'], json={
                "delete_original": True
            })
        if "approve_mr_action" in action_ids:
            gl_client = Gitlab('https://gitlab.com', private_token=settings.GITLAB_API_KEY)
            action_name, project_id, pull_request_id = payload['actions'][0]['value'].split('-')
            if action_name == "approve":
                gl_project = gl_client.projects.get(project_id)
                gl_mr = gl_project.mergerequests.get(pull_request_id)
                gl_mr.approve()
    if payload['type'] == "view_submission":
        if payload['view']['callback_id'] == "add_gitlab_project_to_channel_cb":
            all_values = [v for _, v in payload['view']['state']['values'].items()]
            result = {}
            for v in all_values:
                result.update(v)
            channel_id = result['add_gitlab_channel_id']['selected_channel']
            project_id = result['add_gitlab_project_id']['value']
            gl_client = Gitlab('https://gitlab.com', private_token=settings.GITLAB_API_KEY)
            try:
                gl_project = gl_client.projects.get(project_id)
            except GitlabGetError:
                return Response({
                    "response_action": "errors",
                    "errors": {
                        "project_id_bl": "This project doesn't exist in gitlab.com for your access key\n"
                                         "Can be either numeric ID or full project path 'group_name/project_name'"
                    }
                })
            # throw error if such combination already exists
            GitlabRepoChMapping.objects.create(
                slack_user=slack_user,
                channel_id=channel_id,
                repository_id=gl_project.id,
                repository_name=gl_project.name,
            )
            return Response({
                "response_action": "clear",
            })

    return Response({})
