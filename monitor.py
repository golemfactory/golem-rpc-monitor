import argparse
import json
import os
import time
import requests

from base_load import burst_call
from discord_manager import DiscordManager
import logging

from env_default import EnvDefault
from golem_rpc_endpoint_check import check_endpoint_health, CheckEndpointException
from datetime import timedelta

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
if not webhook_url:
    raise Exception("environment variable DISCORD_WEBHOOK_URL is needed to run monitor")

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
parser.add_argument('--work-mode', dest="work_mode", type=str,
                    action=EnvDefault, envvar='MONITOR_WORK_MODE',
                    help='Possible values: health_check, baseload_check',
                    default="health_check")

parser.add_argument('--target-url', dest="target_url", type=str, help='Node url',
                    action=EnvDefault, envvar='BASELOAD_ENDPOINT',
                    default="http://54.38.192.207:8545")
parser.add_argument('--token-address', dest="token_address", type=str, help='Token address',
                    action=EnvDefault, envvar='BASELOAD_TOKEN_ADDRESS',
                    default="0x2036807B0B3aaf5b1858EE822D0e111fDdac7018")
parser.add_argument('--token-holder', dest="token_holder", type=str, help='Token holder to check',
                    action=EnvDefault, envvar='BASELOAD_TOKEN_HOLDER',
                    default="0xc596aee002ebe98345ce3f967631aaf79cfbdf41")
parser.add_argument('--request_burst', dest="request_burst", type=int, help='Number of requests to sent at once',
                    action=EnvDefault, envvar='BASELOAD_REQUEST_BURST',
                    default=50)
parser.add_argument('--sleep-time', dest="sleep_time", type=float, help='Number of requests to sent at once',
                    action=EnvDefault, envvar='BASELOAD_SLEEP_TIME',
                    default=5.0)


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

        if args.work_mode == "health_check":
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
        elif args.work_mode == "baseload_check":
            target_url = args.target_url
            logger.info(f"Checking target url: {target_url}")
            try:
                (number_of_success_req, number_of_failed_req) = burst_call(args.target_url, args.token_holder,
                                                                           args.token_address, args.request_burst)
            except Exception as ex:
                discord_manager.post_failure_message("baseload",
                                                     f"Other exception when calling burst call {endpoint}\n{ex}")

            if number_of_failed_req == 0 and number_of_success_req > 0:
                discord_manager.post_success_message("baseload",
                                                     f"Successfully called {number_of_success_req} times")
            else:
                discord_manager.post_failure_message("baseload",
                                                     f"Failed to call {number_of_failed_req} times")

        else:
            raise Exception(f"Unknown work mode {args.work_mode}")
    except Exception as ex:
        logger.error(f"Discord manager exception: {ex}")

    time.sleep(10)
