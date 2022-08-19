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


while True:
    discord_manager.post_success_message("main", "Message 1")
    discord_manager.post_failure_message("main", "Message 2")
    discord_manager.post_failure_message("main", "Message 3")
    discord_manager.post_success_message("main", "Message 4")
    logger.info("Checking endpoint")
    time.sleep(4)
