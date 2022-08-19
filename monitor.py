import json
import os
import time
import requests
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



class CheckEndpointException(Exception):
    pass


def check_endpoint_health(endpoint, expected_instances_count):
    resp = requests.get(endpoint)
    if resp.status_code != 200:
        raise CheckEndpointException(f"Endpoint {endpoint} returned {resp.status_code}")
    data = resp.json()

    if len(data["instances"]) != expected_instances_count:
        raise CheckEndpointException(f"Number of instances should be {expected_instances_count}")

    health_status = {}
    number_of_failed_instances = 0
    for instance_id in data["instances"]:
        instance = data["instances"][instance_id]
        if "error" in instance["block_info"]:
            number_of_failed_instances += 1
            health_status[instance_id] = {
                "error": instance["block_info"]["error"],
            }
            continue
        if "timestamp" not in instance["block_info"]:
            number_of_failed_instances += 1
            continue

        health_status[instance_id] = {
            "timestamp": instance["block_info"]["timestamp"],
            "number": instance["block_info"]["number"],
        }
        logger.info(f"Found {instance}")

    if number_of_failed_instances >= expected_instances_count:
        raise CheckEndpointException(f"Seems like all instances are failing")

    return health_status


while True:
    try:
        endpoint = "https://gateway.golem.network/mumbai/instances"

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
            discord_manager.post_success_message("main", f"Successfully validated {endpoint} \n```{health_status_formatted}```")
    except Exception as ex:
        logger.error(f"Discord manager exception: {ex}")

    time.sleep(10)

