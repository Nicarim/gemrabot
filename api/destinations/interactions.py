import requests
from django.conf import settings
from gitlab import Gitlab, GitlabGetError, GitlabAuthenticationError
from rest_framework.response import Response

from api.destinations.messages import get_view_add_project, get_view_auth_with_gitlab
from api.destinations.slack import SlackClient
from api.models import GitlabRepoChMapping, UserGitlabAccessToken


def add_project_to_channel(access_token, trigger_id, response_url):
    client = SlackClient(access_token)
    client.views_open({
        'trigger_id': trigger_id,
        'view': get_view_add_project()
    })
    requests.post(response_url, json={
        "delete_original": True
    })
    return Response({})


def add_gitlab_auth_token(access_token, trigger_id, response_url):
    client = SlackClient(access_token)
    client.views_open({
        'trigger_id': trigger_id,
        'view': get_view_auth_with_gitlab()
    })
    requests.post(response_url, json={
        "delete_original": True
    })
    return Response({})


def approve_mr_action(action_name, project_id, pull_request_id, gl_auth: UserGitlabAccessToken):
    gl_client = Gitlab('https://gitlab.com', private_token=gl_auth.gitlab_access_token)
    if action_name == "approve":
        gl_project = gl_client.projects.get(project_id)
        gl_mr = gl_project.mergerequests.get(pull_request_id)
        gl_mr.approve()
    return Response({})


def view_submission_add_gitlab_user_auth_submit(slack_user, payload):
    all_values = [v for _, v in payload['view']['state']['values'].items()]
    result = {}
    for v in all_values:
        result.update(v)
    private_token = result['add_gitlab_user_auth_token']['value']
    gl_client = Gitlab('https://gitlab.com', private_token=private_token)
    try:
        gl_client.auth()
    except GitlabAuthenticationError:
        return Response({
            "response_action": "errors",
            "errors": {
                "personal_access_token_bl": "This token has been marked as invalid by gitlab.com, "
                                            "make sure it is correct"
            }
        })
    user = gl_client.user
    slack_person_id = payload['user']['id']
    UserGitlabAccessToken.objects.create(
        user_id=slack_person_id,
        user_name=user.name,
        gitlab_access_token=private_token,
        slack_user=slack_user
    )
    return Response({
        "response_action": "clear",
    })


def view_submission_add_gl_project_to_ch_submit(slack_user, payload):
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
