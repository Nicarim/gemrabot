import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from gitlab import Gitlab, GitlabAuthenticationError
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api.destinations.interactions import add_project_to_channel, approve_mr_action, \
    view_submission_add_gl_project_to_ch_submit, add_gitlab_auth_token, view_submission_add_gitlab_user_auth_submit
from api.destinations.messages import get_config_empty_message, get_config_project_list, get_gl_authorization_empty, \
    get_gl_authorization_show
from api.destinations.slack import SlackNotifier, slack_oauth_request
from api.models import SlackUser, GitlabRepoChMapping, UserGitlabAccessToken, UserGitlabOAuthToken
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
    response = slack_oauth_request(code)
    SlackUser.objects.create(
        bot_user_id=response['bot_user_id'],
        team_id=response['team']['id'],
        team_name=response['team']['name'],
        user_id=response['authed_user']['id'],
        access_token=response['access_token']
    )
    return SlackRedirect('slack://open')


@api_view(['GET'])
def oauth_gitlab(request: Request):
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    redirect_uri = request.build_absolute_uri(reverse('gitlab_oauth'))
    response = requests.post(f'{settings.GITLAB_HOST}/oauth/token', {
        'client_id': settings.GITLAB_APP_ID,
        'client_secret': settings.GITLAB_APP_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
    })
    response.raise_for_status()
    response_json = response.json()
    gl_oauth_token = UserGitlabOAuthToken.objects.get(state_hash=state)
    gl_oauth_token.gitlab_refresh_token = response_json['refresh_token']
    gl_oauth_token.gitlab_access_token = response_json['access_token']
    gl_oauth_token.save()
    client = Gitlab(settings.GITLAB_HOST, oauth_token=gl_oauth_token.gitlab_access_token)
    try:
        client.auth()
    except GitlabAuthenticationError:
        logger.error("User has no access after auth, something went wrong!")
        return Response({'error': 'no_access_after_auth'})
    user = client.user
    gl_oauth_token.gitlab_user_name = user.name
    gl_oauth_token.gitlab_user_id = user.id
    gl_oauth_token.save()
    return SlackRedirect('slack://open')


@api_view(['POST'])
def slack_command(request: Request):
    team_id = request.data.get('team_id')
    user_id = request.data.get('user_id')
    slack_user = SlackUser.objects.filter(team_id=team_id).first()
    gl_mappings = GitlabRepoChMapping.objects.filter(slack_user=slack_user).all()
    gl_auth = UserGitlabOAuthToken.objects.filter(slack_user_id=user_id,
                                                  slack_team_id=team_id,
                                                  slack_owner_user=slack_user).all()
    if len(gl_mappings) <= 0:
        response = get_config_empty_message()
    else:
        response = get_config_project_list(gl_mappings)
    if len(gl_auth) <= 0:
        redirect_uri = request.build_absolute_uri(reverse('gitlab_oauth'))
        gl_oauth_token, created = UserGitlabOAuthToken.objects.get_or_create(
            slack_owner_user=slack_user,
            slack_user_id=user_id,
            slack_team_id=team_id
        )
        gl_oauth_url = f'{settings.GITLAB_HOST}/oauth/authorize' \
                       f'?client_id={settings.GITLAB_APP_ID}' \
                       f'&redirect_uri={redirect_uri}' \
                       f'&response_type=code' \
                       f'&state={gl_oauth_token.state_hash}' \
                       f'&scope=api'

        for block in get_gl_authorization_empty(gl_oauth_url)['blocks']:
            response['blocks'].append(block)
    else:
        for block in get_gl_authorization_show(gl_auth[0])['blocks']:
            response['blocks'].append(block)
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
            return add_project_to_channel(slack_user.access_token, trigger_id, payload['response_url'])
        if "add_gl_auth_to_user" in action_ids:
            return add_gitlab_auth_token(slack_user.access_token, trigger_id, payload['response_url'])
        if "approve_mr_action" in action_ids:
            action_name, project_id, pull_request_id = payload['actions'][0]['value'].split('-')
            user_id = payload['user']['id']
            gl_auth = UserGitlabOAuthToken.objects.filter(slack_user_id=user_id,
                                                          slack_team_id=team_id,
                                                          slack_owner_user=slack_user).all()
            if len(gl_auth) <= 0:
                requests.post(payload['response_url'], json={
                    'replace_original': False,
                    'response_type': 'ephemeral',
                    'text': "Sorry you're not authorized with GitLab, type `/gemrabot` to authorize"
                })
                logger.error("User not authorized with GL")
                return Response({})
            return approve_mr_action(action_name, project_id, pull_request_id, gl_auth[0])
        if "add_gl_auth_via_app_to_user" in action_ids:
            # no actions need since its redirect
            return Response({})
        if "remove_gl_auth_via_app_to_user" in action_ids:
            user_id = payload['user']['id']
            gl_auth = UserGitlabOAuthToken.objects.filter(slack_user_id=user_id,
                                                          slack_team_id=team_id,
                                                          slack_owner_user=slack_user).all()
            # call revoke authorization
            response = requests.post(f'{settings.GITLAB_HOST}/oauth/revoke', {
                'token': gl_auth[0].gitlab_access_token,
                'client_id': settings.GITLAB_APP_ID,
                'client_secret': settings.GITLAB_APP_SECRET,
            }, headers={
                'Authorization': f'Bearer {gl_auth[0].gitlab_access_token}'
            })
            # foolish are you - this endpoint always returns 200 so you cannot know if it was successful or not ;)
            response.raise_for_status()
            gl_auth[0].delete()
            return Response({})
    if payload['type'] == "view_submission":
        if payload['view']['callback_id'] == "add_gitlab_project_to_channel_cb":
            return view_submission_add_gl_project_to_ch_submit(slack_user, payload)
        if payload['view']['callback_id'] == "add_gitlab_user_auth_cb":
            return view_submission_add_gitlab_user_auth_submit(slack_user, payload)
    logger.error("Unknown interaction has been reached")
    logger.error(request.data.get('payload'))
    return Response({})
