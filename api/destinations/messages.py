from datetime import timedelta
from typing import List

from api.models import GitlabRepoChMapping
from api.utils import td_format


def get_closed_message(pull_request):
    return {
        'blocks': [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Pull request has been closed by *{pull_request.closed_by}*\n "
                        f"*<{pull_request.pr_url}|{pull_request.title} by {pull_request.author_name}>*"
            }
        }]
    }


def get_merged_message(pull_request):
    it_took = timedelta(seconds=pull_request.time_to_merge)
    return {
        'blocks': [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":fire: Pull request has been merged by *{pull_request.merged_by}* "
                        f"in {td_format(it_took)} :fire:\n "
                        f"*<{pull_request.pr_url}|{pull_request.title} by {pull_request.author_name}>*"
            }
        }]
    }


def _get_files_message(changes):
    changes_list = []
    for change in changes[:5]:
        changes_list.append({
            "type": "divider"
        })
        fmt_message = '\n'.join(change.diff.split('\n')[4:])
        changes_list.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Filename:* {change.filename}\n```{fmt_message}```"
            }
        })
    return changes_list


def get_opened_message(pull_request):
    headline = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"New pull request is pending review\n "
                    f"*<{pull_request.pr_url}|{pull_request.title} by {pull_request.author_name}>*"
        }
    }
    blocks = [headline]
    for m in _get_files_message(pull_request.changes):
        blocks.append(m)
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "action_id": "approve_mr_action",
                "text": {
                    "type": "plain_text",
                    "emoji": True,
                    "text": "Approve this"
                },
                "style": "primary",
                "value": f"approve-{pull_request.repository_id}-{pull_request.id}"
            }
        ]
    })
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "plain_text",
                "text": f"Approved by ({pull_request.approval_count}): {pull_request.approvals}",
                "emoji": True
            }
        ]
    })
    return {
        "blocks": blocks
    }


def _get_config_buttons():
    return {
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
    }


def _get_gl_auth_buttons():
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "action_id": "add_gl_auth_to_user",
                "text": {
                    "type": "plain_text",
                    "text": "Auth with gitlab"
                }
            }
        ]
    }


def get_gl_authorization_empty():
    return {
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': "You're currently not connected to any gitlab account"
                }
            },
            _get_gl_auth_buttons()
        ]
    }


def get_config_empty_message():
    return {
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': 'Currently no channels are added, please use buttons below to add new channels'
                }
            },
            _get_config_buttons()
        ]
    }


def get_config_project_list(gl_mappings: List[GitlabRepoChMapping]):
    result = {
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'You have {len(gl_mappings)} project connected: '
                }
            }
        ]
    }
    for mapping in gl_mappings:
        result['blocks'].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'- Project *{mapping.repository_name}* is connected to channel *<#{mapping.channel_id}>*'
            }
        })
    result['blocks'].append(_get_config_buttons())
    return result


def get_view_add_project():
    return {
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
