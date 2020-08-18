import json
import logging

from aioify import aioify
from fastapi import Request
from gitlab import Gitlab
from gitlab.v4.objects import Project
from unidiff import PatchSet

from structures import PullRequest, PullRequestStatus

logger = logging.getLogger(__name__)


class GitlabWebhook:
    def __init__(self, request: Request, gitlab_access_key: str):
        self.request = request
        self.api_key = gitlab_access_key
        self.client = Gitlab('https://gitlab.com', private_token=self.api_key)

    async def validate(self) -> bool:
        x_gitlab_event = self.request.headers.get('X-Gitlab-Event', 'Invalid')
        if x_gitlab_event != "Merge Request Hook":
            logger.error(f"Expected MR hook, got instead {x_gitlab_event}")
            return True
        return True

    async def get_user_by_id(self, user_id: int):
        gl_get_users = aioify(obj=self.client.users.get)
        return await gl_get_users(user_id)

    async def get_project_by_id(self, project_id: int):
        gl_get_project = aioify(obj=self.client.projects.get)
        return await gl_get_project(project_id)

    async def get_project_merge_request_by_iid(self, project: Project, merge_request_id: int):
        gl_get_mr = aioify(obj=project.mergerequests.get)
        return await gl_get_mr(merge_request_id)

    async def get_merge_request_changes(self, mr):
        gl_get_changes = aioify(obj=mr.changes)
        return await gl_get_changes()

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

    def build_patch_set(self, changes):
        all_changes = ""
        for change in changes['changes']:
            changes_txt: str = change['diff']
            header = f"diff --git a/{change['old_path']} b/{change['new_path']}\n"
            if change['new_file']:
                header += f"new file mode {change['b_mode']} \n"
            header += f"index 0000000..0000000 100644\n"
            if "Binary files" not in changes_txt:
                header += f"--- a/{change['old_path']}\n"
                header += f"+++ b/{change['new_path']}\n"
            all_changes += header
            all_changes += changes_txt

        patch = PatchSet(all_changes)
        return patch

    async def parse(self) -> PullRequest:
        data = await self.get_data()
        user = await self.get_user_by_id(data['object_attributes']['author_id'])
        project = await self.get_project_by_id(data['object_attributes']['target_project_id'])
        merge_request = await self.get_project_merge_request_by_iid(project, data['object_attributes']['iid'])
        changes = await self.get_merge_request_changes(merge_request)
        patch_set = self.build_patch_set(changes)

        pr = PullRequest(
            id=data['object_attributes']['iid'],  # Preferring internal ID as this will be used as reference
            title=data['object_attributes']['title'],
            description=data['object_attributes']['description'],
            status=self.get_mr_status(data),
            author_name=user.name,
            author_url=user.web_url,
            repository_name=data['object_attributes']['target']['name'],
            repository_url=data['object_attributes']['target']['web_url'],
            pr_url=data['object_attributes']['url'],
            changes=[],
        )
        return pr
