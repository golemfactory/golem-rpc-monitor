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

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
if not webhook_url:
    raise Exception("environment variable DISCORD_WEBHOOK_URL is needed to run monitor")


# helper class from stack overflow to add env to argparse
class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parse, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


parser = argparse.ArgumentParser(description='Golem rpc monitor params')
parser.add_argument('--endpoint', dest="endpoint", type=str,
                    action=EnvDefault, envvar='MONITOR_ENDPOINT',
                    help='Endpoint to check',
                    default="https://gateway.golem.network/mumbai/instances")
parser.add_argument('--check-interval', dest="check_interval", type=int,
                    action=EnvDefault, envvar='MONITOR_CHECK_INTERVAL',
                    help='Check interval (in seconds)', default="10")
parser.add_argument('--success-interval', dest="success_interval", type=int,
                    action=EnvDefault, envvar='MONITOR_SUCCESS_INTERVAL',
                    help='Success message anti spam interval (in seconds)', default="60")
parser.add_argument('--error-interval', dest="error_interval", type=int,
                    action=EnvDefault, envvar='MONITOR_ERROR_INTERVAL',
                    help='Failure message anti spam interval (in seconds)', default="60")

args = parser.parse_args()

logger.info("Starting rpc monitor...")
logger.debug(json.dumps(args.__dict__, indent=4))


discord_manager = DiscordManager(webhook_url=webhook_url,
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
