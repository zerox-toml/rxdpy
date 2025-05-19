from rxdpy.transaction.transaction import Transaction, TransactionInput, TransactionOutput
from rxdpy.keys import PrivateKey
from rxdpy.script.type import P2PKH
from rxdpy.hd import seed_from_mnemonic, master_xprv_from_seed
from rxdpy.hd import bip44_derive_xprvs_from_mnemonic
from rxdpy.constants import BIP44_DERIVATION_PATH
from rxdpy.hash import sha256
from rxdpy.fee_models import SatoshisPerKilobyte

import asyncio
import websockets
import json
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def rxd_send_transaction(wif: str, to_address: str, amount: int):
    private_key = PrivateKey(wif)
    public_key = private_key.public_key()
    from_address = public_key.address()

    # Fetch UTXOs for the address
    utxos = await fetch_utxos(from_address)
    if not utxos:
        raise ValueError("No UTXOs found for address")

    # Fetch relay fee
    relay_fee = await fetch_relay_fee()
    print(f"Relay fee: {relay_fee} satoshis")
    # Create inputs from UTXOs
    inputs = []
    total_input = 0
    for utxo in utxos:
        source_tx = Transaction([], [TransactionOutput(P2PKH().lock(from_address), utxo["value"])])
        source_tx.txid = lambda: utxo["tx_hash"]

        inputs.append(
            TransactionInput(
                source_transaction=source_tx,
                source_output_index=utxo["tx_pos"],
                unlocking_script_template=P2PKH().unlock(private_key),
            )
        )
        total_input += utxo["value"]

        if total_input >= amount:
            break

    if total_input < amount:
        raise ValueError("Insufficient funds")

    # Create spend transaction
    spend_tx = Transaction(
        inputs,
        [
            TransactionOutput(P2PKH().lock(to_address), amount),
            TransactionOutput(P2PKH().lock(from_address), change=True),
        ],
    )

    fee_model = SatoshisPerKilobyte(1_000_000)
    spend_tx.fee(fee_model)
    spend_tx.sign()

    txid = spend_tx.txid()
    raw_tx = spend_tx.hex()
    fee = spend_tx.get_fee()
    size = spend_tx.byte_length()

    print(f"Transaction ID: {txid}")
    print(f"Raw transaction: {raw_tx}")
    print(f"Fee: {fee} satoshis")
    print(f"Size: {size} bytes")

    return spend_tx


async def fetch_utxos(address: str):
    uri = "wss://electrumx.radiant4people.com:50022/"
    async with websockets.connect(uri) as websocket:
        script = P2PKH().lock(address)
        script_bytes = script.serialize()
        script_hash = sha256(script_bytes).hex()
        reversed_script_hash = "".join(reversed([script_hash[i : i + 2] for i in range(0, len(script_hash), 2)]))
        request = {"method": "blockchain.scripthash.listunspent", "params": [reversed_script_hash], "id": 1}
        print(f"Request: {request}")
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        response_json = json.loads(response)
        return response_json.get("result", [])


async def fetch_relay_fee() -> int:
    uri = "wss://electrumx.radiant4people.com:50022/"
    async with websockets.connect(uri) as websocket:
        request = {"method": "blockchain.relayfee", "params": [], "id": 1}
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        response_json = json.loads(response)
        return int(response_json.get("result", 0) * 1e8)


async def broadcast_transaction(tx: Transaction):
    uri = "wss://electrumx.radiant4people.com:50022/"
    async with websockets.connect(uri) as websocket:
        request = {"method": "blockchain.transaction.broadcast", "params": [tx.hex()], "id": 1}
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        return response


if __name__ == "__main__":
    mnemonic: str = "stairs relief cost orbit comfort tuition canoe improve unique license average point"
    seed = seed_from_mnemonic(mnemonic, lang="en")
    master_xprv = master_xprv_from_seed(seed)
    master_xpub = master_xprv.xpub()
    bip44_keys = bip44_derive_xprvs_from_mnemonic(mnemonic, 0, 1, path=BIP44_DERIVATION_PATH, change=0)

    print("All BIP44 derived keys:")
    for i, key in enumerate(bip44_keys):
        print(f"Address {i}: {key.address()}")
        print(f"Private key {i}: {key.private_key().wif()}")

    print("Fetching UTXOs...", bip44_keys[0].address())
    utxos = asyncio.run(fetch_utxos(bip44_keys[0].address()))
    print(utxos)
    tx = asyncio.run(
        rxd_send_transaction(bip44_keys[0].private_key().wif(), "1KoRYYFuhiPecgS5zpQ8DHacrhD6eBz245", 5000000)
    )
    print(tx)
    broadcast_response = asyncio.run(broadcast_transaction(tx))
    print(broadcast_response)
