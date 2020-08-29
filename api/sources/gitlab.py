from api.data_models import (
    PullRequest,
    PullRequestStatus,
    FileAction,
    PullRequestFile,
    PatchedFileRepr,
    GitlabMRWebhook,
)
        return cls(
            settings.GITLAB_HOST, settings.GITLAB_APP_ID, settings.GITLAB_APP_SECRET
        )
    def get_oauth_redirect_url(self, redirect_uri, state, scope="api"):
        return (
            f"{self.host}/oauth/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
            f"&scope={scope}"
        )
        response = requests.post(
            f"{self.host}/oauth/revoke",
            {
                "token": token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        response = requests.post(
            f"{self.host}/oauth/token",
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.user = self._get(f"{settings.GITLAB_HOST}/api/v4/users/{user_id}")
        self.project = self._get(f"{settings.GITLAB_HOST}/api/v4/projects/{project_id}")
            f"{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}"
            f"{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}/changes"
            f"{settings.GITLAB_HOST}/api/v4/projects/{project_id}/merge_requests/{merge_request_id}/approvals"
        for change in changes["changes"]:
            changes_txt: str = change["diff"]
            if change["new_file"]:
    def get_pull_request_files_from_patch_set(
        self, patch_set: List[PatchedFile]
    ) -> List[PullRequestFile]:
                    filename=file.path, action=action, diff=PatchedFileRepr(file)
        approval_names = [x["user"]["name"] for x in self.approvals["approved_by"]]
            closed_by = self.merge_request["closed_by"]["name"]
            merged_at = parse(self.merge_request["merged_at"])
            created_at = parse(self.merge_request["created_at"])
            merged_by = self.merge_request["merged_by"]["name"]
            author_name=self.user["name"],
            author_url=self.user["web_url"],
            approvals=",".join(approval_names),
    gitlab_header_event = request.META.get("HTTP_X_GITLAB_EVENT")
        logger.error(f"Invalid x-gitlab-event hook detected, got {gitlab_header_event}")
        raise exceptions.ValidationError(
            "x-gitlab-event doesn't match merge request hook"
        )
    gitlab_header_token = request.META.get("HTTP_X_GITLAB_TOKEN")