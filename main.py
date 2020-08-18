import logging
import os

import uvicorn
from fastapi import FastAPI, Request

from sources.gitlab import GitlabWebhook

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
GITLAB_API_KEY = os.getenv("GITLAB_API_KEY")
app = FastAPI()

logger = logging.getLogger("app")


@app.post('/webhooks/gitlab')
async def webhooks_gitlab(request: Request):
    webhook = GitlabWebhook(request, GITLAB_API_KEY)
    is_valid = await webhook.validate()
    if not is_valid:
        logger.info("Dropping on x_gitlab_event")
        return
    pull_request = await webhook.parse()
    logger.info("Got pull request")
    return pull_request.json()


if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True, log_level="debug")
