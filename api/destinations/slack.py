import requests
from requests import exceptions as requests_exc

from api.data_models import PullRequest, PullRequestStatus
from api.destinations.messages import get_closed_message, get_merged_message, get_opened_message
from api.models import PrMessage


class SlackClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}'
        })

    def _post(self, url, **kwargs):
        response = self.session.post(url, **kwargs)
        response.raise_for_status()
        json = response.json()
        if not json['ok']:
            raise requests_exc.RequestException(json)
        return json

    def post_message(self, json):
        return self._post('https://slack.com/api/chat.postMessage', json=json)

    def update_message(self, json):
        return self._post('https://slack.com/api/chat.update', json=json)


class SlackNotifier:
    def __init__(self, slack_access_token, channel_id):
        self.slack_client = SlackClient(slack_access_token)
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
            response = self.slack_client.post_message({
                'channel': self.channel_id,
                'blocks': message['blocks']
            })
            channel = response['channel']
            ts = response['ts']
            PrMessage.objects.create(
                message_channel=channel,
                message_ts=ts,
                pr_id=pull_request.id,
                repository_id=pull_request.repository_id
            )
        else:
            self.slack_client.update_message({
                'channel': pr_message.message_channel,
                'ts': pr_message.message_ts,
                'blocks': message['blocks']
            })
