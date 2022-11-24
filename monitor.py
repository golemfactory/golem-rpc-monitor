import argparse
import asyncio
import json
import os
import time
import random

import requests
from aiohttp import web

from base_load import burst_call
from client_info import ClientInfo, RequestType
from discord_manager import DiscordManager
import logging

from env_default import EnvDefault
from golem_rpc_endpoint_check import check_endpoint_health, CheckEndpointException
from datetime import timedelta, datetime
import aiohttp_jinja2
import jinja2


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description='Golem rpc monitor params')
parser.add_argument('--work-mode', dest="work_mode", type=str,
                    action=EnvDefault, envvar='MONITOR_WORK_MODE',
                    help='Possible values: health_check, baseload_check',
                    default="health_check")
parser.add_argument('--title', dest="title", type=str,
                    action=EnvDefault, envvar='MONITOR_TITLE',
                    help='Title of the monitor',
                    default="default_title")
parser.add_argument('--no-discord', dest="no_discord", action='store_true')
parser.set_defaults(no_discord=False)

# arguments for work mode health_check
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
parser.add_argument('--expected-instances', dest="expected_instances", type=int,
                    action=EnvDefault, envvar='EXPECTED_INSTANCES',
                    help='How many instances are expected', default="2")

# arguments for work mode baseload_check
# noinspection DuplicatedCode
parser.add_argument('--target-url', dest="target_url", type=str, help='Node url',
                    action=EnvDefault, envvar='BASELOAD_ENDPOINT',
                    default="http://54.38.192.207:8545")
parser.add_argument('--token-address', dest="token_address", type=str, help='Token address',
                    action=EnvDefault, envvar='BASELOAD_TOKEN_ADDRESS',
                    default="0x2036807B0B3aaf5b1858EE822D0e111fDdac7018")
parser.add_argument('--token-holder', dest="token_holder", type=str, help='Token holder to check',
                    action=EnvDefault, envvar='BASELOAD_TOKEN_HOLDER',
                    default="0xc596aee002ebe98345ce3f967631aaf79cfbdf41")
parser.add_argument('--request-burst', dest="request_burst", type=int, help='Number of requests to sent at once',
                    action=EnvDefault, envvar='BASELOAD_REQUEST_BURST',
                    default=500)
parser.add_argument('--sleep-time', dest="sleep_time", type=float, help='Number of requests to sent at once',
                    action=EnvDefault, envvar='BASELOAD_SLEEP_TIME',
                    default=5.0)


def post_failure_message(discord_manager, topic, message):
    if discord_manager:
        discord_manager.post_failure_message(topic, message)
    else:
        logger.error(message)


def post_success_message(discord_manager, topic, message):
    if discord_manager:
        discord_manager.post_success_message(topic, message)
    else:
        logger.info(message)


async def main_loop(discord_manager, args, context):
    context['client_info'] = ClientInfo(1, "apikey")
    while True:
        try:

            endpoint = args.endpoint
            if args.work_mode == "health_check":
                logger.info(f"Checking endpoint {endpoint}")
                health_status = None
                try:
                    health_status = check_endpoint_health(endpoint, args.expected_instances)
                except CheckEndpointException as ex:
                    post_failure_message(discord_manager, "main", f"Failure when validating {endpoint}\n{ex}")
                except Exception as ex:
                    post_failure_message(discord_manager, "main", f"Other exception when validating {endpoint}\n{ex}")

                if health_status:
                    health_status_formatted = json.dumps(health_status, indent=4, default=str)
                    post_success_message("main",
                                         f"Successfully validated {endpoint} \n```{health_status_formatted}```")
            elif args.work_mode == "baseload_check":
                target_url = args.target_url
                logger.info(f"Checking target url: {target_url}")
                try:
                    if random.randint(0, 1) < 1:
                        target_url = target_url.replace("8", "7")
                    # burst_call returns success_request_count and failure_request_count
                    (s_r, f_r) = await burst_call(context, target_url, args.token_holder, args.token_address,
                                                  args.request_burst)
                    if f_r == 0 and s_r > 0:
                        context["last_success"] = datetime.now()
                        context["last_result"] = "success"
                        context['client_info'].add_request("test", RequestType.Succeeded)
                        post_success_message(discord_manager, "baseload", f"Successfully called {s_r} times")
                    else:
                        context["last_result"] = "failure"
                        context['client_info'].add_request("test", RequestType.Failed)
                        post_failure_message(discord_manager, "baseload", f"Failed to call {f_r} times")
                except Exception as ex:
                    context["last_result"] = "error"
                    context["last_err"] = ex
                    context["last_err_time"] = datetime.now()
                    context['client_info'].add_request("test", RequestType.Failed)
                    post_failure_message(discord_manager, "baseload",
                                         f"Other exception when calling burst call {target_url}\n{ex}")
                context["last_call"] = datetime.now()
            else:
                raise Exception(f"Unknown work mode {args.work_mode}")
        except Exception as ex:
            logger.error(f"Discord manager exception: {ex}")

        await asyncio.sleep(args.check_interval)


routes = web.RouteTableDef()


@routes.get('/')
async def hello(request):
    ctx = request.app['context']

    def get_history(buckets, title):
        hist = []
        for key in reversed(buckets):
            time1 = key
            el = buckets[key]
            if el.request_count > 0 and el.request_failed_count:
                class_name = "warning"
            elif el.request_failed_count > 0:
                class_name = "error"
            elif el.request_count > 0:
                class_name = "success"
            else:
                class_name = "warning"


            hist.append({
                "time": time1,
                "requests": el.request_count,
                "failures": el.request_failed_count,
                'class': class_name
            })
        return {
            "hist": hist,
            "title": title
        }

    hist_seconds = get_history(ctx['client_info'].time_buckets_seconds["test"], "Seconds")
    hist_minutes = get_history(ctx['client_info'].time_buckets_minutes["test"], "Minutes")
    hist_hours = get_history(ctx['client_info'].time_buckets_hours["test"], "Hours")
    hist_days = get_history(ctx['client_info'].time_buckets_days["test"], "Days")


    ctx["current"] = {
        "block_age": int(time.time()) - ctx["block_timestamp"] if "block_timestamp" in ctx else 0,
        "call_age": int(time.time()) - int(ctx["last_call"].timestamp()),
        "history": [hist_seconds, hist_minutes,hist_hours, hist_days],
    }
    response = aiohttp_jinja2.render_template('status.jinja2',
                                              request,
                                              ctx
                                              )
    return response


async def main():
    args = parser.parse_args()

    if args.no_discord:
        webhook_url = None
    else:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            raise Exception("environment variable DISCORD_WEBHOOK_URL is needed to run monitor")

    logger.info("Starting rpc monitor...")
    logger.debug(json.dumps(args.__dict__, indent=4))

    if args.no_discord:
        discord_manager = None
        logger.info("Running without discord messaging...")
    else:
        discord_manager = DiscordManager(webhook_url=webhook_url,
                                         min_resend_error_time=timedelta(seconds=args.error_interval),
                                         min_resend_success_time=timedelta(seconds=args.success_interval))

        logger.info("Checking discord webhook...")
        discord_manager.check_webhook()

    app = web.Application()
    app.add_routes(routes)
    app['context'] = {
        'title': args.title,
    }
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    app_task = asyncio.create_task(
        web._run_app(app, port=8080, handle_signals=False)  # noqa
    )
    await main_loop(discord_manager, args, app['context'])


if __name__ == '__main__':
    asyncio.run(main())
