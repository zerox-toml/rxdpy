from rxdpy.transaction.transaction import Transaction, TransactionInput, TransactionOutput
from rxdpy.keys import PrivateKey
from rxdpy.script.script import Script
from rxdpy.script.type import P2PKH, P2PK
from rxdpy.fee_models import SatoshisPerKilobyte
from rxdpy.constants import TRANSACTION_VERSION, TRANSACTION_LOCKTIME
from rxdpy.hd import seed_from_mnemonic, master_xprv_from_seed
from rxdpy.hd import bip44_derive_xprvs_from_mnemonic
from rxdpy.constants import BIP44_DERIVATION_PATH


def rxd_send_transaction(wif, to_address, amount):
    private_key = PrivateKey(wif)
    public_key = private_key.public_key()
    public_key_hash = public_key.address()

    # Create source transaction (UTXO)
    source_tx = Transaction([], [TransactionOutput(P2PKH().lock(public_key_hash), amount)])  # 0.1 RXD

    # Create spend transaction
    spend_tx = Transaction(
        [
            TransactionInput(
                source_transaction=source_tx,
                source_output_index=0,
                unlocking_script_template=P2PKH().unlock(private_key),
            )
        ],
        [
            # Output to recipient
            TransactionOutput(P2PKH().lock(to_address), amount),  # 0.05 RXD
            # Change output
            TransactionOutput(P2PKH().lock(public_key_hash), change=True),
        ],
    )

    # Calculate fee and adjust change output
    fee_model = SatoshisPerKilobyte(1000)  # 1000 satoshis per kilobyte
    spend_tx.fee(fee_model)

    # Sign the transaction
    spend_tx.sign()

    # Verify the transaction
    assert spend_tx.verify()

    # Get transaction details
    txid = spend_tx.txid()
    raw_tx = spend_tx.hex()
    fee = spend_tx.get_fee()
    size = spend_tx.byte_length()

    print(f"Transaction ID: {txid}")
    print(f"Raw transaction: {raw_tx}")
    print(f"Fee: {fee} satoshis")
    print(f"Size: {size} bytes")

    # Verify transaction structure
    assert spend_tx.version == TRANSACTION_VERSION
    assert spend_tx.locktime == TRANSACTION_LOCKTIME
    assert len(spend_tx.inputs) == 1
    assert len(spend_tx.outputs) == 2
    assert spend_tx.inputs[0].unlocking_script is not None
    assert spend_tx.outputs[0].satoshis == 5000000
    assert spend_tx.outputs[1].change is True


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
