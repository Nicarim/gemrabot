import json

import requests
from django.conf import settings
from gitlab import Gitlab, GitlabGetError
from rest_framework.response import Response

from api.destinations.messages import get_view_add_project
from api.models import GitlabRepoChMapping


def add_project_to_channel(access_token, trigger_id, response_url):
    requests.post('https://slack.com/api/views.open', {
        'token': access_token,
        'trigger_id': trigger_id,
        'view': json.dumps(get_view_add_project())
    })
    requests.post(response_url, json={
        "delete_original": True
    })
    return Response({})


def approve_mr_action(action_name, project_id, pull_request_id):
    gl_client = Gitlab('https://gitlab.com', private_token=settings.GITLAB_API_KEY)
    if action_name == "approve":
        gl_project = gl_client.projects.get(project_id)
        gl_mr = gl_project.mergerequests.get(pull_request_id)
        gl_mr.approve()
    return Response({})


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
