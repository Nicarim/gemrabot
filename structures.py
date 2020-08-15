from enum import Enum
from typing import Any, Optional, List

from pydantic import BaseModel, AnyHttpUrl


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
    diff: Optional[str]


class PullRequest(BaseModel):
    id: Any
    title: str
    description: str
    status: PullRequestStatus
    author_name: str
    author_url: AnyHttpUrl
    repository_name: str
    repository_url: AnyHttpUrl
    pr_url: AnyHttpUrl
    changes: List[PullRequestFile] = []
