import os
import time

from discord_manager import DiscordManager
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

webhook_id = os.getenv("DISCORD_WEBHOOK_ID")
if not webhook_id:
    raise Exception("environment variable DISCORD_WEBHOOK_ID is needed to run monitor")

webhook_token = os.getenv("DISCORD_WEBHOOK_TOKEN")
if not webhook_token:
    raise Exception("environment variable DISCORD_WEBHOOK_TOKEN is needed to run monitor")

logger.info("Creating discord manager...")

discord_manager = DiscordManager(webhook_id, webhook_token)

logger.info("Checking discord webhook...")

discord_manager.check_webhook()

discord_manager.post_message()
while True:
    logger.info("Checking endpoint")
    break
    time.sleep(5)
