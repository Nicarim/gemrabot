from datetime import timedelta

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
