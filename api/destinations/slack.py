import requests

from api.data_models import PullRequest
from api.models import PrMessage


class SlackNotifier:
    def __init__(self, slack_access_token, channel_id):
        self.slack_access_token = slack_access_token
        self.channel_id = channel_id

    def get_files_message(self, changes):
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

    def get_slack_message(self, pull_request):
        headline = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"New pull request is pending review\n *<{pull_request.pr_url}|{pull_request.title}>*"
            }
        }
        blocks = [headline]
        for m in self.get_files_message(pull_request.changes):
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
                },
                {
                    "type": "button",
                    "action_id": "deny_mr_action",
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Deny"
                    },
                    "style": "danger",
                    "value": f"deny-{pull_request.repository_id}-{pull_request.id}"
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

    def notify_of_pull_request(self, pull_request: PullRequest):
        message = self.get_slack_message(pull_request)

        pr_message = PrMessage.objects.filter(pr_id=pull_request.id, repository_id=pull_request.repository_id).first()
        if not pr_message:
            r = requests.post('https://slack.com/api/chat.postMessage', json={
                'channel': self.channel_id,
                'blocks': message['blocks']
            }, headers={
                'Authorization': f'Bearer {self.slack_access_token}'
            })
            response_json = r.json()
            if not response_json['ok']:
                raise Exception(response_json)
            channel = response_json['channel']
            ts = response_json['ts']
            PrMessage.objects.create(
                message_channel=channel,
                message_ts=ts,
                pr_id=pull_request.id,
                repository_id=pull_request.repository_id
            )
        else:
            r = requests.post('https://slack.com/api/chat.update', headers={
                'Authorization': f'Bearer {self.slack_access_token}'
            }, json={
                'channel': pr_message.message_channel,
                'ts': pr_message.message_ts,
                'blocks': message['blocks']
            })
            response_json = r.json()
            if not response_json['ok']:
                raise Exception(response_json)
