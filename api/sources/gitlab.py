import logging
from typing import List

import requests
from dateutil.parser import parse
from django.conf import settings
from gitlab import Gitlab
from gitlab.v4.objects import Project
from rest_framework.request import Request
from unidiff import PatchSet, PatchedFile

from api.data_models import PullRequest, PullRequestStatus, FileAction, PullRequestFile, PatchedFileRepr

logger = logging.getLogger(__name__)


class GitlabOAuthClient:
    def __init__(self, host, client_id, client_secret):
        self.host = host
        self.client_id = client_id
        self.client_secret = client_secret

    @classmethod
    def get_client(cls):
        return cls(settings.GITLAB_HOST, settings.GITLAB_APP_ID, settings.GITLAB_APP_SECRET)

    def get_oauth_redirect_url(self, redirect_uri, state, scope='api'):
        return f'{self.host}/oauth/authorize' \
               f'?client_id={self.client_id}' \
               f'&redirect_uri={redirect_uri}' \
               f'&response_type=code' \
               f'&state={state}' \
               f'&scope={scope}'

    def revoke_auth(self, token):
        response = requests.post(f'{self.host}/oauth/revoke', {
            'token': token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        })
        response.raise_for_status()
        return response.json()

    def complete_auth(self, code, redirect_uri):
        response = requests.post(f'{self.host}/oauth/token', {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        })
        response.raise_for_status()
        return response.json()


class GitlabWebhook:
    def __init__(self, request: Request, gitlab_access_key: str):
        self.request = request
        self.api_key = gitlab_access_key
        self.client = Gitlab(settings.GITLAB_HOST, private_token=self.api_key)

    def validate(self) -> bool:
        x_gitlab_event = self.request.headers.get('X-Gitlab-Event', 'Invalid')
        if x_gitlab_event != "Merge Request Hook":
            logger.error(f"Expected MR hook, got instead {x_gitlab_event}")
            return True
        return True

    def get_user_by_id(self, user_id: int):
        return self.client.users.get(user_id)

    def get_project_by_id(self, project_id: int):
        return self.client.projects.get(project_id)

    def get_project_merge_request_by_iid(self, project: Project, merge_request_id: int):
        return project.mergerequests.get(merge_request_id)

    def get_merge_request_changes(self, mr):
        return mr.changes()

    @staticmethod
    def get_mr_status(data) -> PullRequestStatus:
        if data['object_attributes']['state'] == 'opened':
            return PullRequestStatus.opened
        elif data['object_attributes']['state'] == 'closed':
            return PullRequestStatus.closed
        elif data['object_attributes']['state'] == 'merged':
            return PullRequestStatus.merged
        logger.error(f"Unexpected state, expected closed/opened, got {data['object_attributes']['state']}")
        raise ValueError("Unexpected MR state")

    def get_data(self):
        return self.request.data

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

    def get_pull_request_files_from_patch_set(self, patch_set: List[PatchedFile]) -> List[PullRequestFile]:
        files_list = []
        for file in patch_set:
            if file.is_added_file:
                action = FileAction.created
            elif file.is_removed_file:
                action = FileAction.removed
            elif file.is_rename:
                action = FileAction.renamed
            else:
                action = FileAction.changed
            files_list.append(
                PullRequestFile(
                    filename=file.path,
                    action=action,
                    diff=PatchedFileRepr(file)
                )
            )
        return files_list

    def parse(self) -> PullRequest:
        data = self.get_data()
        user = self.get_user_by_id(data['object_attributes']['author_id'])
        project = self.get_project_by_id(data['object_attributes']['target_project_id'])
        merge_request = self.get_project_merge_request_by_iid(project, data['object_attributes']['iid'])
        approvals = merge_request.approvals.get()
        changes = self.get_merge_request_changes(merge_request)
        patch_set = self.build_patch_set(changes)
        pr_files = self.get_pull_request_files_from_patch_set(patch_set)
        approval_names = [x['user']['name'] for x in approvals.approved_by]
        status = self.get_mr_status(data)
        closed_by = ""
        merged_by = ""
        time_to_merge = 0
        if status == PullRequestStatus.closed:
            closed_by = merge_request.closed_by['name']
        if status == PullRequestStatus.merged:
            merged_at = parse(merge_request.merged_at)
            created_at = parse(merge_request.created_at)
            diff = merged_at - created_at
            time_to_merge = diff.total_seconds()
            merged_by = merge_request.merged_by['name']
        pr = PullRequest(
            id=data['object_attributes']['iid'],  # Preferring internal ID as this will be used as reference
            title=data['object_attributes']['title'],
            description=data['object_attributes']['description'],
            status=status,
            closed_by=closed_by,
            merged_by=merged_by,
            author_name=user.name,
            author_url=user.web_url,
            approvals=','.join(approval_names),
            approval_count=len(approval_names),
            repository_id=data['object_attributes']['target_project_id'],
            repository_name=data['object_attributes']['target']['name'],
            repository_url=data['object_attributes']['target']['web_url'],
            pr_url=data['object_attributes']['url'],
            time_to_merge=time_to_merge,
            changes=pr_files,
        )
        return pr
