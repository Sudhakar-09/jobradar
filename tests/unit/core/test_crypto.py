import base64

import pytest

from jobradar.core.crypto import SecretBox, SecretBoxError, generate_key


def test_round_trip_and_fresh_nonce() -> None:
    box = SecretBox(generate_key())

    first, second = box.encrypt(b"refresh-token"), box.encrypt(b"refresh-token")

    assert first != second
    assert b"refresh-token" not in first
    assert box.decrypt(first) == box.decrypt(second) == b"refresh-token"


def test_tampered_data_is_rejected() -> None:
    box = SecretBox(generate_key())
    sealed = bytearray(box.encrypt(b"secret"))
    sealed[-1] ^= 0x01

    with pytest.raises(SecretBoxError, match="cannot be decrypted"):
        box.decrypt(bytes(sealed))


def test_another_key_cannot_decrypt() -> None:
    sealed = SecretBox(generate_key()).encrypt(b"secret")

    with pytest.raises(SecretBoxError):
        SecretBox(generate_key()).decrypt(sealed)


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (None, "not set"),
        ("", "not set"),
        ("not base64!!", "not valid base64"),
        (base64.b64encode(b"short").decode(), "32 bytes"),
    ],
)
def test_bad_keys_are_rejected(key: str | None, message: str) -> None:
    with pytest.raises(SecretBoxError, match=message):
        SecretBox(key)


def test_unknown_format_is_rejected() -> None:
    with pytest.raises(SecretBoxError, match="unknown secret format"):
        SecretBox(generate_key()).decrypt(b"\x02" + b"0" * 40)


def test_generated_key_is_32_bytes() -> None:
    assert len(base64.b64decode(generate_key())) == 32
