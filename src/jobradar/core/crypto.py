"""Encryption at rest for secrets stored in the database (`*_enc` columns; ADR-0018).

AES-256-GCM with a key from settings (`TOKEN_ENCRYPTION_KEY`, base64 of 32 random bytes; create
one with `jobradar keys generate`). Stored format: version byte, 12-byte nonce, ciphertext + tag.
Tampered or wrongly keyed data fails to decrypt instead of returning garbage.
"""

import base64
import binascii
import os
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from jobradar.core.errors import ValidationFailedError

FORMAT_VERSION: Final = 1
KEY_BYTES: Final = 32
NONCE_BYTES: Final = 12


class SecretBoxError(ValidationFailedError):
    """Missing or invalid key, or data that cannot be decrypted with it."""


def generate_key() -> str:
    """A new random key, base64-encoded for `.env`."""
    return base64.b64encode(os.urandom(KEY_BYTES)).decode("ascii")


class SecretBox:
    """Encrypts and decrypts small secrets (tokens) with one AES-256-GCM key."""

    def __init__(self, key_b64: str | None) -> None:
        """Load the key; raises SecretBoxError if it is missing or not 32 bytes."""
        if not key_b64:
            raise SecretBoxError("TOKEN_ENCRYPTION_KEY is not set (run `jobradar keys generate`)")
        try:
            key = base64.b64decode(key_b64, validate=True)
        except binascii.Error as exc:
            raise SecretBoxError("TOKEN_ENCRYPTION_KEY is not valid base64") from exc
        if len(key) != KEY_BYTES:
            raise SecretBoxError("TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with a fresh random nonce."""
        nonce = os.urandom(NONCE_BYTES)
        return bytes([FORMAT_VERSION]) + nonce + self._aead.encrypt(nonce, plaintext, None)

    def decrypt(self, blob: bytes) -> bytes:
        """Decrypt data produced by :meth:`encrypt`."""
        if len(blob) <= 1 + NONCE_BYTES or blob[0] != FORMAT_VERSION:
            raise SecretBoxError("unknown secret format")
        nonce, ciphertext = blob[1 : 1 + NONCE_BYTES], blob[1 + NONCE_BYTES :]
        try:
            return self._aead.decrypt(nonce, ciphertext, None)
        except InvalidTag as exc:
            raise SecretBoxError("secret cannot be decrypted with the configured key") from exc
