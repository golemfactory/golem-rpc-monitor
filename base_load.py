import logging
import time
import argparse
from env_default import EnvDefault

import batch_rpc_provider
from batch_rpc_provider import BatchRpcProvider, BatchRpcException

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



batch_rpc_provider.logger.setLevel(logging.WARN)


def burst_call(target_url, token_holder, token_address, number_calls):
    number_of_success_req = 0
    number_of_failed_req = 0
    p = BatchRpcProvider(target_url, 20)

    try:
        latest_block = p.get_latest_block()
    except Exception as ex:
        logger.error(f"Other error when getting request: {ex}")
        raise ex

    token_address = token_address

    single_holder_array = [token_holder]

    current_block = latest_block

    max_steps = number_calls
    while max_steps > 0:
        max_steps -= 1
        success = False
        try:
            resp = p.get_erc20_balances(single_holder_array, token_address, f"0x{current_block:x}")
            balance = resp[0]
            b = int(balance, 16) / 10 ** 18
            logger.debug(f"{current_block} {b}")
            success = True
        except BatchRpcException as ex:
            logger.error(f"BatchRpcException when getting request: {ex}")
            raise ex
        except Exception as ex:
            logger.error(f"Other error when getting request: {ex}")
            raise ex

        if success:
            number_of_success_req += 1
        else:
            number_of_failed_req += 1

    logger.info(f"Number of success requests: {number_of_success_req}")
    logger.info(f"Number of failed requests: {number_of_failed_req}")

    return (number_of_success_req, number_of_failed_req)


def baseload_loop(args_sleep_time, target_url, token_holder, token_address, number_calls):
    total_number_of_success_req = 0
    total_number_of_failed_req = 0
    while True:

        (number_of_success_req, number_of_failed_req) = burst_call(target_url, token_holder, token_address, number_calls)
        total_number_of_success_req += number_of_success_req
        total_number_of_failed_req += number_of_failed_req

        logger.info(f"Total number of success requests: {total_number_of_success_req}")
        logger.info(f"Total number of failed requests: {total_number_of_failed_req}")

        time.sleep(args_sleep_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test params')

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

    baseload_loop(args.sleep_time, args.target_url, args.token_holder, args.token_address, args.request_burst)


