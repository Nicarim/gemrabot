import logging

import uvicorn
from fastapi import FastAPI, Request

from sources.gitlab import GitlabWebhook

WEBHOOK_URL = "https://hooks.slack.com/services/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"
app = FastAPI()

logger = logging.getLogger("app")


@app.post('/webhooks/gitlab')
async def webhooks_gitlab(request: Request):
    webhook = GitlabWebhook(request)
    is_valid = await webhook.validate()
    if not is_valid:
        logger.info("Dropping on x_gitlab_event")
        return
    pull_request = await webhook.parse()
    logger.info("Got pull request")
    return pull_request.json()


if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True, log_level="debug")
