import requests

from api.data_models import PullRequest, PullRequestStatus
from api.destinations.messages import get_closed_message, get_merged_message, get_opened_message
from api.models import PrMessage


class SlackNotifier:
    def __init__(self, slack_access_token, channel_id):
        self.slack_access_token = slack_access_token
        self.channel_id = channel_id

    @staticmethod
    def get_slack_message(pull_request):
        func_mapper = {
            PullRequestStatus.opened: get_opened_message,
            PullRequestStatus.closed: get_closed_message,
            PullRequestStatus.merged: get_merged_message,
        }
        return func_mapper[pull_request.status](pull_request)

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
