from enum import Enum
from typing import Any, List

from pydantic import BaseModel, AnyHttpUrl


class PatchedFileRepr(str):
    def __init__(self, pf):
        super().__init__()
        self.pf = pf

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
    closed = 'closed'


class PullRequestFile(BaseModel):
    filename: str
    action: FileAction
    diff: PatchedFileRepr


class PullRequest(BaseModel):
    id: Any
    title: str
    description: str
    status: PullRequestStatus
    author_name: str
    author_url: AnyHttpUrl
    repository_id: int
    repository_name: str
    repository_url: AnyHttpUrl
    approvals: str
    approval_count: int
    pr_url: AnyHttpUrl
    changes: List[PullRequestFile] = []
