import requests
from django.conf import settings
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

    def _json_post(self, url, **kwargs):
        response = self.session.post(url, **kwargs)
        response.raise_for_status()
        json = response.json()
        if not json['ok']:
            raise requests_exc.RequestException(json)
        return json

    def post_message(self, json):
        return self._json_post('https://slack.com/api/chat.postMessage', json=json)

    def update_message(self, json):
        return self._json_post('https://slack.com/api/chat.update', json=json)

    def views_open(self, json):
        return self._json_post('https://slack.com/api/views.open', json=json)


def slack_oauth_request(code):
    response = requests.post('https://slack.com/api/oauth.v2.access', {
        'code': code,
        'client_id': settings.SLACK_CLIENT_ID,
        'client_secret': settings.SLACK_CLIENT_SECRET,
    })
    response.raise_for_status()
    json = response.json()
    if not json['ok']:
        raise requests_exc.RequestException(json)
    return json


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
        return func_mapper[pull_request.state](pull_request)

    def notify_of_pull_request(self, pull_request: PullRequest):
        message = self.get_slack_message(pull_request)

        pr_message = PrMessage.objects.filter(
            pr_id=pull_request.id,
            repository_id=pull_request.repository_id
        ).first()
        if not pr_message:
            self.create_message(message, pull_request)
        else:
            self.update_message(message, pr_message)

    def update_message(self, message, pr_message):
        self.slack_client.update_message({
            'channel': pr_message.message_channel,
            'ts': pr_message.message_ts,
            'blocks': message['blocks']
        })

    def create_message(self, message, pull_request):
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
