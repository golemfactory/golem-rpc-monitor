import logging
import time
import argparse

import batch_rpc_provider
from batch_rpc_provider import BatchRpcProvider, BatchRpcException

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description='Test params')
parser.add_argument('--target-url', dest="target_url", type=str, help='Node url', default="http://54.38.192.207:8545")
parser.add_argument('--token-address', dest="token_address", type=str, help='Token address', default="0x2036807B0B3aaf5b1858EE822D0e111fDdac7018")
parser.add_argument('--token-holder', dest="token_holder", type=str, help='Token holder to check', default="0xc596aee002ebe98345ce3f967631aaf79cfbdf41")

args = parser.parse_args()

batch_rpc_provider.logger.setLevel(logging.WARN)

def test_block_history():
    while True:
        p = BatchRpcProvider(args.target_url, 20)
        latest_block = p.get_latest_block()

        token_address = args.token_address

        single_holder_array = [args.token_holder]

        current_block = latest_block

        max_steps = 100
        while max_steps > 0:
            max_steps -= 1
            success = True
            try:
                resp = p.get_erc20_balances(single_holder_array, token_address, f"0x{current_block:x}")
                balance = resp[0]
                b = int(balance, 16) / 10 ** 18
                logger.info(f"{current_block} {b}")
                success = True
            except BatchRpcException as ex:
                logger.error(f"BatchRpcException when getting request: {ex}")
                success = False
            except Exception as ex:
                logger.error(f"Other error when getting request: {ex}")
                success = False

        time.sleep(10)


if __name__ == "__main__":
    test_block_history()


