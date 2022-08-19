import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DiscordManager:
    def __init__(self, webhook_id, webhook_token,
                 min_resend_error_time=timedelta(seconds=30),
                 min_resend_success_time=timedelta(seconds=30)
                 ):
        self._webhook_id = webhook_id
        self._webhook_token = webhook_token
        self._api_url = "https://discordapp.com/api/webhooks"
        self._discord_url = f"{self._api_url}/{self._webhook_id}/{self._webhook_token}"

        self._last_send_success = {}
        self._last_send_failure = {}
        self._min_resend_error_time = min_resend_error_time
        self._min_resend_success_time = min_resend_success_time

    def check_webhook(self):
        resp = requests.get(self._discord_url)

        webhook_info = resp.json()
        logger.debug(f"Webhook info: {webhook_info}")
        if webhook_info["id"] != self._webhook_id:
            raise Exception("Webhook id check failed")
        if webhook_info["token"] != self._webhook_token:
            raise Exception("Webhook token check failed")

    # noinspection DuplicatedCode
    def post_failure_message(self, topic, message):
        logger.debug(f"Sending failure message. topic: {topic}, message: {message}")
        if topic in self._last_send_failure:
            last_failure_sent_diff = datetime.utcnow() - self._last_send_failure[topic]
            logger.debug(f"Last failure message sent {last_failure_sent_diff}")
            if last_failure_sent_diff < self._min_resend_error_time:
                logger.debug(f"Skipping sent {last_failure_sent_diff} < {self._min_resend_error_time}")
                return

        data = {"content": message}
        response = requests.post(self._discord_url, json=data)

        self._last_send_failure[topic] = datetime.utcnow()
        if topic in self._last_send_success:
            del self._last_send_success[topic]

    # noinspection DuplicatedCode
    def post_success_message(self, topic, message):
        logger.debug(f"Sending success message. topic: {topic}, message: {message}")
        if topic in self._last_send_success:
            last_success_sent_diff = datetime.utcnow() - self._last_send_success[topic]
            logger.debug(f"Last success message sent {last_success_sent_diff}")
            if last_success_sent_diff < self._min_resend_success_time:
                logger.debug(f"Skipping sent {last_success_sent_diff} < {self._min_resend_success_time}")
                return

        data = {"content": message}
        response = requests.post(self._discord_url, json=data)

        self._last_send_success[topic] = datetime.utcnow()
        if topic in self._last_send_failure:
            del self._last_send_failure[topic]
