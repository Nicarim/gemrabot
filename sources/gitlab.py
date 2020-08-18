from typing import List
from aioify import aioify
from gitlab import Gitlab
from gitlab.v4.objects import Project
from unidiff import PatchSet, PatchedFile
from structures import PullRequest, PullRequestStatus, FileAction, PullRequestFile, PatchedFileRepr
    def __init__(self, request: Request, gitlab_access_key: str):
        self.api_key = gitlab_access_key
        self.client = Gitlab('https://gitlab.com', private_token=self.api_key)
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

        user = await self.get_user_by_id(data['object_attributes']['author_id'])
        project = await self.get_project_by_id(data['object_attributes']['target_project_id'])
        merge_request = await self.get_project_merge_request_by_iid(project, data['object_attributes']['iid'])
        changes = await self.get_merge_request_changes(merge_request)
        patch_set = self.build_patch_set(changes)
        pr_files = self.get_pull_request_files_from_patch_set(patch_set)

            author_name=user.name,
            author_url=user.web_url,
            changes=pr_files,