import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse, RedirectResponse

from destinations.slack import SlackNotifier
from slack_api import get_access_token
from sources.gitlab import GitlabWebhook

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
GITLAB_API_KEY = os.getenv("GITLAB_API_KEY")
app = FastAPI()

logger = logging.getLogger("app")
logging.basicConfig()


@app.post('/webhooks/gitlab')
async def webhooks_gitlab(request: Request):
    webhook = GitlabWebhook(request, GITLAB_API_KEY)
    is_valid = await webhook.validate()
    if not is_valid:
        logger.info("Dropping on x_gitlab_event")
        return
    pull_request = await webhook.parse()
    logger.info("Got pull request")
    json_data = jsonable_encoder(pull_request)
    slack = SlackNotifier(SLACK_WEBHOOK_URL)
    await slack.notify_of_pull_request(pull_request)
    return JSONResponse(json_data)


@app.get('/oauth/redirect/slack')
async def oauth_redirect_slack(code: str, state: str):
    response = await get_access_token(code)
    return RedirectResponse('slack://open')


if __name__ == "__main__":
    # db.create_tables([models.User, models.Item])
    load_dotenv()
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True, log_level="debug")
