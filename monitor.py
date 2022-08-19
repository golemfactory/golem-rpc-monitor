import argparse
import json
import os
import time
import requests
from discord_manager import DiscordManager
import logging
from golem_rpc_endpoint_check import check_endpoint_health, CheckEndpointException
from datetime import timedelta

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

webhook_id = os.getenv("DISCORD_WEBHOOK_ID")
if not webhook_id:
    raise Exception("environment variable DISCORD_WEBHOOK_ID is needed to run monitor")

webhook_token = os.getenv("DISCORD_WEBHOOK_TOKEN")
if not webhook_token:
    raise Exception("environment variable DISCORD_WEBHOOK_TOKEN is needed to run monitor")

parser = argparse.ArgumentParser(description='Golem rpc monitor params')
parser.add_argument('--endpoint', dest="endpoint", type=str, help='Endpoint to check',
                    default="https://gateway.golem.network/mumbai/instances")
parser.add_argument('--check-interval', dest="check_interval", type=int,
                    help='Check interval (in seconds)', default="10")
parser.add_argument('--success-interval', dest="success_interval", type=int,
                    help='Success message anti spam interval (in seconds)', default="60")
parser.add_argument('--error-interval', dest="error_interval", type=int,
                    help='Failure message anti spam interval (in seconds)', default="60")
parser.set_defaults(dumpjournal=True)

args = parser.parse_args()

logger.info("Creating discord manager...")

discord_manager = DiscordManager(webhook_id, webhook_token,
                                 min_resend_error_time=timedelta(seconds=args.error_interval),
                                 min_resend_success_time=timedelta(seconds=args.success_interval))

logger.info("Checking discord webhook...")

discord_manager.check_webhook()

while True:
    try:
        endpoint = args.endpoint

        logger.info(f"Checking endpoint {endpoint}")

        health_status = None
        try:
            health_status = check_endpoint_health(endpoint, 2)
        except CheckEndpointException as ex:
            discord_manager.post_failure_message("main", f"Failure when validating {endpoint}\n{ex}")
        except Exception as ex:
            discord_manager.post_failure_message("main", f"Other exception when validating {endpoint}\n{ex}")

        if health_status:
            health_status_formatted = json.dumps(health_status, indent=4, default=str)
            discord_manager.post_success_message("main",
                                                 f"Successfully validated {endpoint} \n```{health_status_formatted}```")
    except Exception as ex:
        logger.error(f"Discord manager exception: {ex}")

    time.sleep(10)
