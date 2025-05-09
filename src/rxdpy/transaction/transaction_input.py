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
        self.sequence: int = sequence
        self.sighash: SIGHASH = sighash

    def serialize(self) -> bytes:
        return self

    def __str__(self) -> str:
        return f"<TxInput value={self.satoshis} locking_script={self.locking_script.hex()}>"

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_hex(cls, stream: Union[str, bytes, Reader]) -> Optional["TransactionInput"]:
        return None
