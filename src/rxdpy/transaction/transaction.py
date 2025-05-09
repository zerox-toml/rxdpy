import math
from contextlib import suppress
from typing import List, Optional, Union, Dict, Any

from ..hash import hash256
from .transaction_input import TransactionInput
from .transaction_output import TransactionOutput
from ..constants import (
    TRANSACTION_VERSION,
    TRANSACTION_LOCKTIME,
)


class InsufficientFunds(ValueError):
    pass


class Transaction:
    def __init__(self, inputs: List[TransactionInput], outputs: List[TransactionOutput]):
        self.inputs = inputs
        self.outputs = outputs
        self.version = TRANSACTION_VERSION
        self.locktime = TRANSACTION_LOCKTIME
        self.merkle_path = None
        self.kwargs = {}

    def serialize(self) -> bytes:
        return self

    def add_input(self, tx_input: TransactionInput) -> "Transaction":
        return self

    def add_inputs(self, tx_inputs: List[TransactionInput]) -> "Transaction":
        return self

    def add_output(self, tx_output: TransactionOutput) -> "Transaction":
        return self

    def add_outputs(self, tx_outputs: List[TransactionOutput]) -> "Transaction":
        return self

    def hex(self) -> str:
        return self.serialize().hex()

    raw = hex

    def hash(self) -> bytes:
        return hash256(self.serialize())

    def txid(self) -> str:
        return self.hash()[::-1].hex()

    def sign(self, bypass: bool = True) -> "Transaction":
        return self

    def total_value_in(self) -> int:
        return sum([tx_input.satoshis for tx_input in self.inputs])

    def total_value_out(self) -> int:
        return sum([tx_output.satoshis for tx_output in self.outputs])

    def get_fee(self) -> int:
        return self.total_value_in() - self.total_value_out()

    def byte_length(self) -> int:
        return len(self.serialize())
