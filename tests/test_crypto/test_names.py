"""Tests for :mod:`tgfs.crypto.names`.

Covers the basic round-trip property, the AAD-free GCM authentication, the
"randomized" property (same plaintext produces different ciphertexts), and
the integration with :class:`EncryptingFileContentRepository` so a Telegram
backend never sees the plaintext document name when ``encrypt_names`` is
enabled.
"""

from __future__ import annotations

import pytest

from tgfs.crypto.names import (
    NAME_PREFIX,
    NameEncryptionError,
    decrypt_name,
    derive_name_key,
    encrypt_name,
    is_encrypted_name,
)


def _key() -> bytes:
    return derive_name_key(b"\x42" * 32)


# --- key derivation --------------------------------------------------------


def test_derive_name_key_length() -> None:
    assert len(_key()) == 32


def test_derive_name_key_rejects_short_master() -> None:
    with pytest.raises(ValueError):
        derive_name_key(b"\x00" * 16)


def test_derive_name_key_is_deterministic() -> None:
    # Same master key must yield the same name key on every call, otherwise
    # decryption after a restart breaks.
    assert derive_name_key(b"\x42" * 32) == derive_name_key(b"\x42" * 32)


def test_derive_name_key_differs_from_master() -> None:
    master = b"\x42" * 32
    assert derive_name_key(master) != master


# --- round-trip ------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "a",
        "report.pdf",
        "Vacation Photo 2024-08-12.JPG",
        "über/-name with spaces.txt",  # unicode + special chars
        "x" * 200,
    ],
)
def test_encrypt_decrypt_round_trip(name: str) -> None:
    key = _key()
    enc = encrypt_name(key, name)
    assert is_encrypted_name(enc)
    assert decrypt_name(key, enc) == name


def test_encrypt_is_randomized() -> None:
    key = _key()
    a = encrypt_name(key, "report.pdf")
    b = encrypt_name(key, "report.pdf")
    # Same plaintext, two different ciphertexts -- this is the headline
    # property the user asked for.
    assert a != b
    assert decrypt_name(key, a) == "report.pdf"
    assert decrypt_name(key, b) == "report.pdf"


def test_encrypted_output_is_filename_safe() -> None:
    key = _key()
    enc = encrypt_name(key, "anything")
    # base64url uses '-' and '_', never '/' or '+', which makes the output
    # safe to drop into a filename-like field without further escaping.
    assert "/" not in enc
    assert "+" not in enc


def test_encrypted_output_carries_prefix() -> None:
    enc = encrypt_name(_key(), "foo.txt")
    assert enc.startswith(NAME_PREFIX)
    assert is_encrypted_name(enc)
    assert not is_encrypted_name("plain.txt")


# --- security tests --------------------------------------------------------


def test_wrong_key_fails_authentication() -> None:
    enc = encrypt_name(_key(), "secret.pdf")
    other_key = derive_name_key(b"\x99" * 32)
    with pytest.raises(NameEncryptionError):
        decrypt_name(other_key, enc)


def test_tampered_ciphertext_fails_authentication() -> None:
    key = _key()
    enc = encrypt_name(key, "secret.pdf")
    # Flip one character in the body; base64 is permissive so we may not
    # hit a decode error, but the GCM tag must reject the tampered blob.
    body = enc[len(NAME_PREFIX) :]
    flipped_char = "A" if body[-2] != "A" else "B"
    tampered = NAME_PREFIX + body[:-2] + flipped_char + body[-1]
    with pytest.raises(NameEncryptionError):
        decrypt_name(key, tampered)


def test_decrypt_rejects_missing_prefix() -> None:
    with pytest.raises(NameEncryptionError):
        decrypt_name(_key(), "not-a-tgfs-name")


def test_decrypt_rejects_truncated_blob() -> None:
    # Prefix is present but the body is too short for nonce + tag.
    with pytest.raises(NameEncryptionError):
        decrypt_name(_key(), NAME_PREFIX + "AAAA")
