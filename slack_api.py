import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def get_access_token(code):
    client_id = os.getenv('SLACK_CLIENT_ID')
    client_secret = os.getenv('SLACK_CLIENT_SECRET')
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://slack.com/api/oauth.v2.access',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
            },
        )
        json = response.json()
        logger.info(json)
        return json
