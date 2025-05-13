from contextlib import suppress
from io import BytesIO
from typing import Optional, Union

from ..constants import SIGHASH
from ..constants import TRANSACTION_SEQUENCE
from ..script.script import Script
from ..script.unlocking_template import UnlockingScriptTemplate
from ..utils import Reader


class TransactionInput:

    def __init__(
            self,
            source_transaction=None,
            source_txid: Optional[str] = None,
            source_output_index: int = 0,
            unlocking_script: Optional[Script] = None,
            unlocking_script_template: UnlockingScriptTemplate = None,
            sequence: int = TRANSACTION_SEQUENCE,
            sighash: SIGHASH = SIGHASH.ALL_FORKID,
    ):
        utxo = None
        if source_transaction:
            utxo = source_transaction.outputs[source_output_index]

        self.source_txid = source_txid
        if source_transaction and not source_txid:
            self.source_txid = source_transaction.txid()

        self.source_output_index: int = source_output_index
        self.satoshis: int = utxo.satoshis if utxo else None
        self.locking_script: Script = utxo.locking_script if utxo else None
        self.source_transaction = source_transaction
        self.unlocking_script: Script = unlocking_script
        self.unlocking_script_template = unlocking_script_template
        self.sequence: int = sequence
        self.sighash: SIGHASH = sighash

    def serialize(self) -> bytes:
        stream = BytesIO()
        stream.write(bytes.fromhex(self.source_txid)[::-1])
        stream.write(self.source_output_index.to_bytes(4, "little"))
        stream.write(
            self.unlocking_script.byte_length_varint()
            if self.unlocking_script
            else b"\x00"
        )
        stream.write(
            self.unlocking_script.serialize() if self.unlocking_script else b""
        )
        stream.write(self.sequence.to_bytes(4, "little"))
        return stream.getvalue()

    def __str__(self) -> str:  # pragma: no cover
        return (f"<TransactionInput outpoint={self.source_txid}:{self.source_output_index} "
                f"value={self.satoshis} locking_script={self.locking_script}>")

    def __repr__(self) -> str:  # pragma: no cover
        return self.__str__()

    @classmethod
    def from_hex(cls, stream: Union[str, bytes, Reader]) -> Optional["TransactionInput"]:
        with suppress(Exception):
            stream = (
                stream
                if isinstance(stream, Reader)
                else Reader(
                    stream if isinstance(stream, bytes) else bytes.fromhex(stream)
                )
            )
            txid = stream.read_bytes(32)[::-1]
            assert len(txid) == 32
            vout = stream.read_int(4)
            assert vout is not None
            script_length = stream.read_var_int_num()
            assert script_length is not None
            unlocking_script_bytes = stream.read_bytes(script_length)
            sequence = stream.read_int(4)
            assert sequence is not None

            return TransactionInput(
                source_txid=txid.hex(),
                source_output_index=vout,
                unlocking_script=Script(unlocking_script_bytes),
                sequence=sequence,
            )

        return None
