import httpx

from structures import PullRequest


class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def get_files_message(self, changes):
        changes_list = []
        for change in changes[:5]:
            changes_list.append({
                "type": "divider"
            })
            changes_list.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Filename:* {change.filename}\n```{change.diff}```"
                }
            })
        return changes_list

    def get_slack_message(self, pull_request):
        headline = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "New pull request is pending review\n*{name_of_pr}*"
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
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Approve"
                    },
                    "style": "primary",
                    "value": "click_me_123"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "emoji": True,
                        "text": "Deny"
                    },
                    "style": "danger",
                    "value": "click_me_123"
                }
            ]
        })
        return {
            "blocks": blocks
        }

    async def notify_of_pull_request(self, pull_request: PullRequest):
        message = self.get_slack_message(pull_request)
        async with httpx.AsyncClient() as client:
            r = await client.post(self.webhook_url, json=message)
            if r.status_code == 400:
                raise Exception(r)
