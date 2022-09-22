import time
import json
import logging
import urllib.request

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_post(url, data):
    data_bytes = data.encode('utf-8')   # needs to be bytes

    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    req.add_header('Content-Length', len(data_bytes))
    response = urllib.request.urlopen(req, data_bytes)
    return response


def _erc20_get_balance_call(token_address, wallet, block):
    strip_wallet = wallet.replace("0x", "")
    abi_method = "70a08231000000000000000000000000"
    return {
        'method': 'eth_call',
        'params': [
            {
                'to': token_address,
                'data': f"0x{abi_method}{strip_wallet}"
            },
            block]
    }


def _erc1155_get_balance_call(token_address, wallet, token_id, block):
    strip_wallet = wallet.replace("0x", "")
    abi_method = "00fdd58e000000000000000000000000"
    return {
        'method': 'eth_call',
        'params': [
            {
                'to': token_address,
                'data': f"0x{abi_method}{strip_wallet}{token_id:064x}"
            },
            block]
    }


class BatchRpcException(Exception):
    pass


class BatchRpcProvider:
    def __init__(self, endpoint, batch_size=1):
        if batch_size <= 0:
            raise Exception("Batch size must be greater than 0")
        self._endpoint = endpoint
        self._batch_size = batch_size
        self.number_of_batches_sent = 0

    def _single_call(self, call_data_param):
        call_data = {
            "jsonrpc": "2.0",
            "method": call_data_param["method"],
            "params": call_data_param["params"],
            "id": 1
        }

        raw_json = json.dumps(call_data)
        logger.debug(f"Request json size {len(raw_json)}")
        r = send_post(self._endpoint, data=raw_json)

        if r.status != 200:
            raise BatchRpcException(f"Other error {r}")

        content = r.read()
        rpc_resp = json.loads(content)

        if 'error' in rpc_resp:
            logger.error(f"Error during request number {call_data['id']}:")
            logger.error(f"\tCall data: {call_data}")
            logger.error(f"\tRPC returned error: {rpc_resp['error']}")
            raise BatchRpcException("RPC error, check log for details")

        return rpc_resp['result']

    def _multi_call(self, call_data_params, max_in_req):
        total_multi_call_time = 0
        total_request_size = 0
        total_response_size = 0
        call_data_array = []
        rpc_id = 1
        for call_data_param in call_data_params:
            call_data = {
                "jsonrpc": "2.0",
                "method": call_data_param["method"],
                "params": call_data_param["params"],
                "id": rpc_id
            }
            call_data_array.append(call_data)
            rpc_id += 1

        result_array = []
        if len(call_data_array) == 0:
            return result_array


        batch_count = (len(call_data_array) - 1) // max_in_req + 1
        for batch_no in range(0, batch_count):

            start_idx = batch_no * max_in_req
            end_idx = min(len(call_data_array), batch_no * max_in_req + max_in_req)

            logger.info(f"Requesting responses {start_idx} to {end_idx}")

            raw_json = json.dumps(call_data_array[start_idx:end_idx])
            logger.debug(f"Request json size {len(raw_json)}")
            total_request_size += len(raw_json)
            start = time.time()
            r = send_post(self._endpoint, data=raw_json)

            end = time.time()
            total_multi_call_time += end - start
            logger.debug(f"Request time {end - start:0.3f}s")

            if r.status == 413:
                logger.error(
                    f"Data exceeded RPC limit, data size {len(raw_json)} try lowering batch size, current batch_count: f{batch_count}")
                raise BatchRpcException("Data too big")
            if r.status != 200:
                raise BatchRpcException(f"Other error {r}")

            total_response_size += len(raw_json)
            content = r.read()
            logger.debug(f"Response json size {len(content)}")
            self.number_of_batches_sent += 1
            rpc_resp_array = json.loads(content)

            for call_data in call_data_array[start_idx:end_idx]:
                found_response = False
                for rpc_resp in rpc_resp_array:
                    if rpc_resp["id"] == call_data["id"]:
                        found_response = True
                        break

                if not found_response:
                    raise Exception(f"One of calls response not found {call_data['id']}")

                if 'error' in rpc_resp:
                    logger.error(f"Error during request number {call_data['id']}:")
                    logger.error(f"\tCall data: {call_data}")
                    logger.error(f"\tRPC returned error: {rpc_resp['error']}")
                    raise BatchRpcException("RPC error, check log for details")

                result_array.append(rpc_resp["result"])
        logger.debug(f"Total call time {total_multi_call_time:0.3f}s. ")
        logger.debug(f"Total request size: {total_request_size}. Total response size: {total_response_size} ")
        return result_array

    def get_latest_block(self):
        call_data_param = {
            "method": "eth_blockNumber",
            "params": []
        }
        resp = self._single_call(call_data_param)
        block_num = int(resp, 0)
        return block_num

    def get_chain_id(self):
        call_data_param = {
            "method": "eth_chainId",
            "params": []
        }
        resp = self._single_call(call_data_param)
        chain_id = int(resp, 0)
        return chain_id

    def get_erc20_balance(self, holder, token_address, block_no='latest'):
        call_data_params = []
        call_params = _erc20_get_balance_call(token_address, holder, block_no)

        resp = self._single_call(call_params)
        return resp

    def get_balance(self, wallet_address, block):
        call_data_param = {
            "method": "eth_getBalance",
            "params": [wallet_address, block]
        }
        resp = self._single_call(call_data_param)
        if resp == "0x":
            raise Exception("Unknown value 0x")
        balance = int(resp, 0)
        return balance

    def get_block_by_number(self, block, full_info):
        if type(block) == int:
            block = hex(block)
        call_data_param = {
            "method": "eth_getBlockByNumber",
            "params": [block, full_info]
        }
        resp = self._single_call(call_data_param)
        return resp

    def get_blocks_by_range(self, block, number_of_blocks, full_info):

        call_data_params = []
        for i in range(0, number_of_blocks):
            call_data_param = {
                "method": "eth_getBlockByNumber",
                "params": [hex(block + i), full_info]
            }
            call_data_params.append(call_data_param)

        resp = self._multi_call(call_data_params, self._batch_size)
        return resp

    def get_transaction_by_hash(self, transaction_hash):
        call_data_param = {
            "method": "eth_getTransactionByHash",
            "params": [transaction_hash]
        }
        resp = self._single_call(call_data_param)
        return resp

    def get_transaction_by_block_number_and_index(self, block_number, transaction_idx):
        call_data_param = {
            "method": "eth_getTransactionByBlockNumberAndIndex",
            "params": [hex(block_number), hex(transaction_idx)]
        }
        resp = self._single_call(call_data_param)
        return resp

    def get_erc20_balances(self, holders, token_address, block_no='latest'):
        call_data_params = []
        for holder in holders:
            call_params = _erc20_get_balance_call(token_address, holder, block_no)
            call_data_params.append(call_params)

        resp = self._multi_call(call_data_params, self._batch_size)
        return resp

    def get_erc1155_balances(self, holder_id_pairs, token_address, block_no='latest'):
        call_data_params = []
        for holder_id_pair in holder_id_pairs:
            call_params = _erc1155_get_balance_call(token_address, holder_id_pair[0], holder_id_pair[1], block_no)
            call_data_params.append(call_params)

        resp = self._multi_call(call_data_params, self._batch_size)
        return resp
