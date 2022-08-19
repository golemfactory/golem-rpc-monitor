import requests
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
