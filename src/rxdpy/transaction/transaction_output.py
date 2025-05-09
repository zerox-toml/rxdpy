from typing import Optional, Union

from ..script import Script
from ..utils import Reader


class TransactionOutput:
    def __init__(self, locking_script: Script, satoshis: int = None, change: bool = False):
        self.satoshis = satoshis
        self.locking_script = locking_script
        self.change = change

    def serialize(self) -> bytes:
        return self

    def __str__(self) -> str:
        return f"<TxOutput value={self.satoshis} locking_script={self.locking_script.hex()}>"

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_hex(cls, stream: Union[str, bytes, Reader]) -> Optional["TransactionOutput"]:
        return None
