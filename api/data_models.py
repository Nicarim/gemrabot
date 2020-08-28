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


class PullRequest(BaseModel):
    id: Any
    title: str
    description: str
    status: PullRequestStatus
    closed_by: Optional[str]
    merged_by: Optional[str]
    author_name: str
    author_url: AnyHttpUrl
    repository_id: int
    repository_name: str
    repository_url: AnyHttpUrl
    approvals: str
    approval_count: int
    pr_url: AnyHttpUrl
    time_to_merge: int
    changes: List[PullRequestFile] = []
