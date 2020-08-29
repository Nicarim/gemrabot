from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, AnyHttpUrl
from unidiff import PatchedFile


class PatchedFileRepr(str):
    def __init__(self, pf: PatchedFile):
        super().__init__()
        self.pf = pf

    def lines_added(self):
        return self.pf.added

    def lines_removed(self):
        return self.pf.removed

    def __str__(self):
        return str(self.pf)

    def __repr__(self):
        return self.__str__()


class FileAction(str, Enum):
    changed = 'changed'
    created = 'created'
    renamed = 'renamed'
    removed = 'removed'


class PullRequestStatus(str, Enum):
    opened = 'opened'
    merged = 'merged'
    closed = 'closed'


class PullRequestFile(BaseModel):
    filename: str
    action: FileAction
    diff: PatchedFileRepr


class GitlabMRWebhookUser(BaseModel):
    name: str
    username: Optional[str]
    email: Optional[str]
    avatar_url: Optional[AnyHttpUrl]


class GitlabMRWebhookProject(BaseModel):
    id: int
    name: str
    description: str
    web_url: AnyHttpUrl
    avatar_url: Optional[AnyHttpUrl]
    git_ssh_url: str
    git_http_url: AnyHttpUrl
    namespace: str
    visibility_level: int
    path_with_namespace: str
    default_branch: str
    homepage: AnyHttpUrl
    url: str
    ssh_url: str
    http_url: AnyHttpUrl


class GitlabMRWebhookRepository(BaseModel):
    name: str
    url: str
    description: str
    homepage: AnyHttpUrl


class GitlabMRWebhookCommit(BaseModel):
    id: str
    message: str
    timestamp: datetime
    url: AnyHttpUrl
    author: GitlabMRWebhookUser


class GitlabMRWebhookObjAttributes(BaseModel):
    id: int
    target_branch: str
    source_branch: str
    source_project_id: int
    author_id: int
    assignee_id: Optional[int]
    title: str
    created_at: str
    updated_at: str
    milestone_id: Optional[int]
    state: PullRequestStatus
    merge_status: str
    target_project_id: int
    iid: int
    description: str
    source: GitlabMRWebhookProject
    target: GitlabMRWebhookProject
    last_commit: GitlabMRWebhookCommit
    work_in_progress: bool
    url: str
    action: str
    assignee: Optional[GitlabMRWebhookUser]


class GitlabMRWebhook(BaseModel):
    object_kind: str
    user: GitlabMRWebhookUser
    project: GitlabMRWebhookProject
    repository: GitlabMRWebhookRepository
    object_attributes: GitlabMRWebhookObjAttributes
    labels: List[Any]
    changes: Any


class PullRequest(BaseModel):
    gitlab_mr_webhook: GitlabMRWebhook
    closed_by: Optional[str]
    merged_by: Optional[str]
    author_url: AnyHttpUrl
    author_name: str
    approvals: str
    approval_count: int
    time_to_merge: int
    changes: List[PullRequestFile] = []

    @property
    def title(self):
        return self.gitlab_mr_webhook.object_attributes.title

    @property
    def repository_id(self):
        return self.gitlab_mr_webhook.object_attributes.target_project_id

    @property
    def id(self):
        return self.gitlab_mr_webhook.object_attributes.iid

    @property
    def state(self):
        return self.gitlab_mr_webhook.object_attributes.state

    @property
    def pr_url(self):
        return self.gitlab_mr_webhook.object_attributes.url
