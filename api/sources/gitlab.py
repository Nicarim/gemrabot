import logging
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

import requests
from dateutil.parser import parse
from django.conf import settings
from gitlab.v4.objects import Project
from unidiff import PatchSet, PatchedFile

from api.data_models import PullRequest, PullRequestStatus, FileAction, PullRequestFile, PatchedFileRepr, \
    GitlabMRWebhook
from api.utils import measure

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


class GitlabMergeRequest:
    def __init__(self, gl_mr_webhook: GitlabMRWebhook, api_key):
        self.gl_mr_webhook = gl_mr_webhook
        self.api_key = api_key
        self.user = None
        self.project = None
        self.merge_request = None
        self.approvals = None
        self.changes = None

    def get_client(self):
        session = requests.session()
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
        return session

    def _get(self, url, **kwargs):
        client = self.get_client()
        response = client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def set_user(self, user_id: int):
        self.user = self._get(f'{settings.GITLAB_HOST}/api/v4/users/{user_id}')

    def set_project(self, project_id: int):
        self.project = self._get(f'{settings.GITLAB_HOST}/api/v4/projects/{project_id}')

    def set_merge_request(self, project_id, merge_request_id: int):
        self.merge_request = self._get(
            f'{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}'
        )

    def set_changes(self, project_id, merge_request_id):
        self.changes = self._get(
            f'{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}/changes'
        )

    def set_approvals(self, project_id, merge_request_id):
        self.approvals = self._get(
            f'{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}/approvals'
        )

    @measure
    def fetch_all(self):
        project_id = self.gl_mr_webhook.object_attributes.target_project_id
        mr_id = self.gl_mr_webhook.object_attributes.iid
        with ThreadPoolExecutor(max_workers=5) as e:
            e.submit(self.set_user, self.gl_mr_webhook.object_attributes.author_id)
            e.submit(self.set_project, project_id)
            e.submit(self.set_merge_request, project_id, mr_id)
            e.submit(self.set_changes, project_id, mr_id)
            e.submit(self.set_approvals, project_id, mr_id)

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

    @measure
    def parse(self) -> PullRequest:
        self.fetch_all()
        approval_names = [x['user']['name'] for x in self.approvals['approved_by']]
        closed_by = ""
        merged_by = ""
        time_to_merge = 0
        state = self.gl_mr_webhook.object_attributes.state
        if state == PullRequestStatus.closed:
            closed_by = self.merge_request['closed_by']['name']
        if state == PullRequestStatus.merged:
            merged_at = parse(self.merge_request['merged_at'])
            created_at = parse(self.merge_request['created_at'])
            diff = merged_at - created_at
            time_to_merge = diff.total_seconds()
            merged_by = self.merge_request['merged_by']['name']
        patch_set = self.build_patch_set(self.changes)
        pr_files = self.get_pull_request_files_from_patch_set(patch_set)
        return PullRequest(
            gitlab_mr_webhook=self.gl_mr_webhook,
            closed_by=closed_by,
            merged_by=merged_by,
            author_name=self.user['name'],
            author_url=self.user['web_url'],
            approvals=','.join(approval_names),
            approval_count=len(approval_names),
            time_to_merge=time_to_merge,
            changes=pr_files,
        )
