import requests
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DiscordManager:
    def __init__(self, webhook_id, webhook_token):
        self._webhook_id = webhook_id
        self._webhook_token = webhook_token
        self._api_url = "https://discordapp.com/api/webhooks"

        self._last_send_success = {}
        self._last_send_failure = {}

    def check_webhook(self):
        discord_url = f"{self._api_url}/{self._webhook_id}/{self._webhook_token}"
        resp = requests.get(discord_url)

        webhook_info = resp.json()
        logger.debug(f"Webhook info: {webhook_info}")
        if webhook_info["id"] != self._webhook_id:
            raise Exception("Webhook id check failed")
        if webhook_info["token"] != self._webhook_token:
            raise Exception("Webhook token check failed")

    def post_failure_message(self, topic, message):
        discord_url = f"{self._api_url}/{self._webhook_id}/{self._webhook_token}"
        data = {"content": 'abc'}
        response = requests.post(discord_url, json=data)




    def post_success_message(self, topic, message):
        discord_url = f"{self._api_url}/{self._webhook_id}/{self._webhook_token}"
        data = {"content": 'abc'}
        response = requests.post(discord_url, json=data)
