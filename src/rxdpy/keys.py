import tempfile
import hashlib
import hmac
from base64 import b64encode, b64decode
from typing import Optional, Union, Callable, Tuple

from coincurve import PrivateKey as CcPrivateKey, PublicKey as CcPublicKey

from .aes_cbc import aes_decrypt_with_iv
from .aes_cbc import aes_encrypt_with_iv
from .base58 import base58check_encode
from .constants import Network, NETWORK_ADDRESS_PREFIX_DICT, NETWORK_WIF_PREFIX_DICT, PUBLIC_KEY_COMPRESSED_PREFIX_LIST
from .curve import Point
from .curve import curve, curve_multiply as curve_multiply, curve_add as curve_add
from .hash import hash160, hash256, hmac_sha256
from .utils import decode_wif, text_digest, stringify_ecdsa_recoverable, unstringify_ecdsa_recoverable
from .utils import deserialize_ecdsa_recoverable, serialize_ecdsa_der


class PublicKey:

    def __init__(self, public_key: Union[str, bytes, Point, CcPublicKey]):
        """
        create public key from serialized hex string or bytes, or curve point, or CoinCurve public key
        """
        self.compressed: bool = True  # use compressed format public key by default
        if isinstance(public_key, Point):
            # from curve point
            self.key: CcPublicKey = CcPublicKey.from_point(public_key.x, public_key.y)
        elif isinstance(public_key, CcPublicKey):
            # from CoinCurve public key
            self.key: CcPublicKey = public_key
        else:
            if isinstance(public_key, str):
                # from serialized public key in hex string
                pk: bytes = bytes.fromhex(public_key)
            elif isinstance(public_key, bytes):
                # from serialized public key in bytes
                pk: bytes = public_key
            else:
                raise TypeError('unsupported public key type')
            # here we have serialized public key in bytes
            self.key: CcPublicKey = CcPublicKey(pk)
            self.compressed: bool = pk[:1] in PUBLIC_KEY_COMPRESSED_PREFIX_LIST

    def point(self) -> Point:
        return Point(*self.key.point())

    def serialize(self, compressed: Optional[bool] = None) -> bytes:
        compressed = self.compressed if compressed is None else compressed
        return self.key.format(compressed)

    def hex(self, compressed: Optional[bool] = None) -> str:
        return self.serialize(compressed).hex()

    def hash160(self, compressed: Optional[bool] = None) -> bytes:
        """
        :returns: public key hash corresponding to this public key
        """
        return hash160(self.serialize(compressed))

    hash = hash160

    def address(self, compressed: Optional[bool] = None, network: Network = Network.MAINNET) -> str:
        """
        :returns: P2PKH address corresponding to this public key
        """
        return base58check_encode(NETWORK_ADDRESS_PREFIX_DICT.get(network) + self.hash160(compressed))

    def verify(self, signature: bytes, message: bytes, hasher: Optional[Callable[[bytes], bytes]] = hash256) -> bool:
        """
        verify serialized ECDSA signature in bitcoin strict DER (low-s) format
        """
        return self.key.verify(signature, message, hasher)

    def verify_recoverable(
            self,
            signature: bytes,
            message: bytes,
            hasher: Optional[Callable[[bytes], bytes]] = hash256
    ) -> bool:
        """
        verify serialized recoverable ECDSA signature in format "r (32 bytes) + s (32 bytes) + recovery_id (1 byte)"
        """
        r, s, _ = deserialize_ecdsa_recoverable(signature)
        der = serialize_ecdsa_der((r, s))
        return self.verify(der, message, hasher) and self == recover_public_key(signature, message, hasher)

    def derive_shared_secret(self, key: 'PrivateKey') -> bytes:
        return PublicKey(self.key.multiply(key.serialize())).serialize()

    def encrypt(self, message: bytes) -> bytes:
        """
        Electrum ECIES (aka BIE1) encryption
        """
        # generate an ephemeral EC private key in order to derive shared secret (ECDH key)
        ephemeral_private_key = PrivateKey()
        # derive ECDH key
        ecdh_key: bytes = self.derive_shared_secret(ephemeral_private_key)
        # SHA512(ECDH_KEY), then we have
        # key_e and iv used in AES, key_m used in HMAC.SHA256
        key: bytes = hashlib.sha512(ecdh_key).digest()
        iv, key_e, key_m = key[0:16], key[16:32], key[32:]
        # make AES encryption
        cipher: bytes = aes_encrypt_with_iv(key_e, iv, message)
        # encrypted = magic_bytes (4 bytes) + ephemeral_public_key (33 bytes) + cipher (16 bytes at least)
        encrypted: bytes = 'BIE1'.encode('utf-8') + ephemeral_private_key.public_key().serialize() + cipher
        # mac = HMAC_SHA256(encrypted), 32 bytes
        mac: bytes = hmac.new(key_m, encrypted, hashlib.sha256).digest()
        # give out encrypted + mac
        return encrypted + mac

    def encrypt_text(self, text: str) -> str:
        """
        :returns: BIE1 encrypted text, base64 encoded
        """
        message: bytes = text.encode('utf-8')
        return b64encode(self.encrypt(message)).decode('ascii')

    def derive_child(self, private_key: 'PrivateKey', invoice_number: str) -> 'PublicKey':
        """
        derive a child key with BRC-42
        :param private_key: the private key of the other party
        :param invoice_number: the invoice number used to derive the child key
        :return: the derived child key
        """
        shared_key = self.derive_shared_secret(private_key)
        hashing = hmac_sha256(shared_key, invoice_number.encode('utf-8'))
        point = curve_multiply(int.from_bytes(hashing, 'big'), curve.g)
        final_point = curve_add(self.point(), point)
        return PublicKey(final_point)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, PublicKey):
            return self.key == o.key
        return super().__eq__(o)  # pragma: no cover

    def __str__(self) -> str:  # pragma: no cover
        return f'<PublicKey hex={self.hex()}>'

    def __repr__(self) -> str:  # pragma: no cover
        return self.__str__()


class PrivateKey:

    def __init__(
            self,
            private_key: Union[str, int, bytes, CcPrivateKey, None] = None,
            network: Optional[Network] = None
    ):
        """
        create private key from WIF (str), or int, or bytes, or CoinCurve private key
        random a new private key if None
        """
        self.network: Network = network or Network.MAINNET
        self.compressed: bool = True  # use compressed WIF by default
        if private_key is None:
            # create a new private key
            self.key: CcPrivateKey = CcPrivateKey()
        elif isinstance(private_key, CcPrivateKey):
            # from CoinCurve private key
            self.key: CcPrivateKey = private_key
        else:
            if isinstance(private_key, str):
                # from wif
                private_key_bytes, self.compressed, self.network = decode_wif(private_key)
                self.key: CcPrivateKey = CcPrivateKey(private_key_bytes)
            elif isinstance(private_key, int):
                # from private key as int
                self.key: CcPrivateKey = CcPrivateKey.from_int(private_key)
            elif isinstance(private_key, bytes):
                # from private key integer in bytes
                self.key: CcPrivateKey = CcPrivateKey(private_key)
            else:
                raise TypeError('unsupported private key type')

    def public_key(self) -> PublicKey:
        return PublicKey(self.key.public_key.format(self.compressed))

    def address(self, compressed: Optional[bool] = None, network: Optional[Network] = None) -> str:
        """
        :returns: P2PKH address corresponding to this private key
        """
        compressed = self.compressed if compressed is None else compressed
        network = network or self.network
        return self.public_key().address(compressed, network)

    def wif(self, compressed: Optional[bool] = None, network: Optional[Network] = None) -> str:
        compressed = self.compressed if compressed is None else compressed
        network = network or self.network
        key_bytes = self.serialize()
        compressed_bytes = b'\x01' if compressed else b''
        return base58check_encode(NETWORK_WIF_PREFIX_DICT.get(network) + key_bytes + compressed_bytes)

    def int(self) -> int:
        return self.key.to_int()

    def serialize(self) -> bytes:
        return self.key.secret

    def hex(self) -> str:
        return self.serialize().hex()

    def der(self) -> bytes:  # pragma: no cover
        return self.key.to_der()

    def pem(self) -> bytes:  # pragma: no cover
        return self.key.to_pem()

    def sign(self, message: bytes, hasher: Optional[Callable[[bytes], bytes]] = hash256, k: Optional[int] = None) -> bytes:
        """
        :returns: ECDSA signature in bitcoin strict DER (low-s) format
        """
        if k:
            return self._sign_custom_k(message, hasher, k)
        return self.key.sign(message, hasher)
    
    def _sign_custom_k(self, message: bytes, hasher: Callable[[bytes], bytes], k: int) -> bytes:
        # TODO: This could be done using self.key.sign() but the interface needs a custom k value function to be injected into te C binary
        #       of libsecp256k1, since the default one does some transformations to the value.
        #       See https://github.com/rustyrussell/secp256k1-py/blob/5bad581d959d722bf6c2df5eaa996fd4c24096aa/tests/test_custom_nonce.py#L51ffi%20=%20FFI()
        #           https://github.com/bitcoin-core/secp256k1/blob/master/src/secp256k1.c#L518

        z = int.from_bytes(hasher(message), 'big')

        # Ensure k is valid
        k = k % curve.n
        if k == 0:
            raise ValueError("Invalid nonce k")

        # Compute R = k * G and obtain its x-coordinate (r)
        R = curve_multiply(k, curve.g)
        if R is None:
            raise ValueError("Invalid R value")
        r = R.x

        # Compute s = k^(-1) * (z + r * d) mod n
        d = int.from_bytes(self.serialize(), 'big')
        s = (pow(k, -1, curve.n) * (z + r * d)) % curve.n
        if s == 0:
            raise ValueError("Invalid s value")

        # Ensure the signature is canonical (low S value)
        if s > curve.n // 2:
            s = curve.n - s

        # Convert r and s to bytes
        r_bytes = r.to_bytes(32, 'big')
        s_bytes = s.to_bytes(32, 'big')

        # Add prefix if the MSB is set
        if r_bytes[0] & 0x80:
            r_bytes = b'\x00' + r_bytes
        if s_bytes[0] & 0x80:
            s_bytes = b'\x00' + s_bytes

        # Serialize the signature in DER format
        signature = b'\x30' + (4 + len(r_bytes) + len(s_bytes)).to_bytes(1, 'big') + \
                    b'\x02' + len(r_bytes).to_bytes(1, 'big') + r_bytes + \
                    b'\x02' + len(s_bytes).to_bytes(1, 'big') + s_bytes

        return signature

    def verify(self, signature: bytes, message: bytes, hasher: Optional[Callable[[bytes], bytes]] = hash256) -> bool:
        """
        verify ECDSA signature in bitcoin strict DER (low-s) format
        """
        return self.public_key().verify(signature, message, hasher)

    def sign_recoverable(self, message: bytes, hasher: Optional[Callable[[bytes], bytes]] = hash256) -> bytes:
        """
        :returns: serialized recoverable ECDSA signature (aka compact signature) in format
                    r (32 bytes) + s (32 bytes) + recovery_id (1 byte)
        """
        return self.key.sign_recoverable(message, hasher)

    def verify_recoverable(
            self,
            signature: bytes,
            message: bytes,
            hasher: Optional[Callable[[bytes], bytes]] = hash256
    ) -> bool:
        """
        verify serialized recoverable ECDSA signature in format "r (32 bytes) + s (32 bytes) + recovery_id (1 byte)"
        """
        return self.public_key().verify_recoverable(signature, message, hasher)

    def sign_text(self, text: str) -> Tuple[str, str]:
        """sign arbitrary text with bitcoin private key
        :returns: (p2pkh_address, stringified_recoverable_ecdsa_signature)
        This function follows Bitcoin Signed Message Format.
        For BRC-77, use signed_message.py instead.
        """
        message: bytes = text_digest(text)
        return self.address(), stringify_ecdsa_recoverable(self.sign_recoverable(message), self.compressed)

    def derive_shared_secret(self, key: PublicKey) -> bytes:
        return PublicKey(key.key.multiply(self.serialize())).serialize()

    def decrypt(self, message: bytes) -> bytes:
        """
        Electrum ECIES (aka BIE1) decryption
        """
        assert len(message) >= 85, 'invalid encrypted length'
        encrypted, mac = message[:-32], message[-32:]
        # encrypted = magic_bytes (4 bytes) + ephemeral_public_key (33 bytes) + cipher_text (16 bytes at least)
        magic_bytes, ephemeral_public_key, cipher = encrypted[:4], PublicKey(encrypted[4:37]), encrypted[37:]
        assert magic_bytes.decode('utf-8') == 'BIE1', 'invalid magic bytes'
        # restore ECDH key
        ecdh_key = self.derive_shared_secret(ephemeral_public_key)
        # restore iv, key_e, key_m
        key = hashlib.sha512(ecdh_key).digest()
        iv, key_e, key_m = key[0:16], key[16:32], key[32:]
        # verify mac
        assert hmac.new(key_m, encrypted, hashlib.sha256).digest().hex() == mac.hex(), 'incorrect hmac checksum'
        # make the AES decryption
        return aes_decrypt_with_iv(key_e, iv, cipher)

    def decrypt_text(self, text: str) -> str:
        """
        decrypt BIE1 encrypted, base64 encoded text
        """
        message: bytes = b64decode(text)
        return self.decrypt(message).decode('utf-8')

    def encrypt(self, message: bytes) -> bytes:  # pragma: no cover
        """
        Electrum ECIES (aka BIE1) encryption
        """
        return self.public_key().encrypt(message)

    def encrypt_text(self, text: str) -> str:  # pragma: no cover
        """
        :returns: BIE1 encrypted text, base64 encoded
        """
        return self.public_key().encrypt_text(text)

    def derive_child(self, public_key: PublicKey, invoice_number: str) -> 'PrivateKey':
        """
        derive a child key with BRC-42
        :param public_key: the public key of the other party
        :param invoice_number: the invoice number used to derive the child key
        :return: the derived child key
        """
        shared_key = self.derive_shared_secret(public_key)
        hashing = hmac_sha256(shared_key, invoice_number.encode('utf-8'))
        return PrivateKey((self.int() + int.from_bytes(hashing, 'big')) % curve.n)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, PrivateKey):
            return self.key == o.key
        return super().__eq__(o)  # pragma: no cover

    def __str__(self) -> str:  # pragma: no cover
        return f'<PrivateKey wif={self.wif()} int={self.int()}>'

    def __repr__(self) -> str:  # pragma: no cover
        return self.__str__()

    @classmethod
    def from_hex(cls, octets: Union[str, bytes]) -> 'PrivateKey':
        b: bytes = octets if isinstance(octets, bytes) else bytes.fromhex(octets)
        return PrivateKey(CcPrivateKey(b))

    @classmethod
    def from_der(cls, octets: Union[str, bytes]) -> 'PrivateKey':  # pragma: no cover
        b: bytes = octets if isinstance(octets, bytes) else bytes.fromhex(octets)
        return PrivateKey(CcPrivateKey.from_der(b))

    @classmethod
    def from_pem(cls, octets: Union[str, bytes]) -> 'PrivateKey':  # pragma: no cover
        b: bytes = octets if isinstance(octets, bytes) else bytes.fromhex(octets)
        return PrivateKey(CcPrivateKey.from_pem(b))


def verify_signed_text(
        text: str,
        address: str,
        signature: str,
        hasher: Optional[Callable[[bytes], bytes]] = hash256
) -> bool:
    """
    verify signed arbitrary text
    """
    serialized_recoverable, compressed = unstringify_ecdsa_recoverable(signature)
    r, s, _ = deserialize_ecdsa_recoverable(serialized_recoverable)
    message: bytes = text_digest(text)
    public_key: PublicKey = recover_public_key(serialized_recoverable, message, hasher)
    der: bytes = serialize_ecdsa_der((r, s))
    return public_key.verify(der, message, hasher) and public_key.address(compressed=compressed) == address


def recover_public_key(
        signature: bytes,
        message: bytes,
        hasher: Optional[Callable[[bytes], bytes]] = hash256
) -> PublicKey:
    """
    recover public key from serialized recoverable ECDSA signature in format
      "r (32 bytes) + s (32 bytes) + recovery_id (1 byte)"
    """
    return PublicKey(CcPublicKey.from_signature_and_message(signature, message, hasher))
