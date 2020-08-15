import json
import logging

from fastapi import Request

from structures import PullRequest, PullRequestStatus

logger = logging.getLogger(__name__)


class GitlabWebhook:
    def __init__(self, request: Request):
        self.request = request

    async def validate(self) -> bool:
        x_gitlab_event = self.request.headers.get('X-Gitlab-Event', 'Invalid')
        if x_gitlab_event != "Merge Request Hook":
            logger.error(f"Expected MR hook, got instead {x_gitlab_event}")
            return True
        return True

    @staticmethod
    def get_mr_status(data) -> PullRequestStatus:
        if data['object_attributes']['state'] == 'opened':
            return PullRequestStatus.opened
        elif data['object_attributes']['state'] == 'closed':
            return PullRequestStatus.closed
        logger.error(f"Unexpected state, expected closed/opened, got {data['object_attributes']['state']}")
        raise ValueError("Unexpected MR state")

    async def get_data(self):
        f = open('gitlab_test_data.json')
        return json.loads(f.read())
        # return await self.request.json()

    async def parse(self) -> PullRequest:
        data = await self.get_data()
        pr = PullRequest(
            id=data['object_attributes']['iid'],  # Preferring internal ID as this will be used as reference
            title=data['object_attributes']['title'],
            description=data['object_attributes']['description'],
            status=self.get_mr_status(data),
            # This may be incorrect as this suggest caller of webhook and not owner of MR
            # Actually, yeah, see 'object_attributes'.'author_id'
            # TODO: need to create getter for that
            author_name=data['user']['name'],
            author_url='https://gitlab.com/FIXME',
            repository_name=data['object_attributes']['target']['name'],
            repository_url=data['object_attributes']['target']['web_url'],
            pr_url=data['object_attributes']['url'],
            changes=[],
        )
        return pr
