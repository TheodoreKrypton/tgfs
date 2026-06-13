"""Filename and directory-name obfuscation for TGFS.

When the optional ``encrypt_names`` flag is set, the document name that
TGFS hands to Telegram on every upload is replaced with a self-tagged,
base64url-encoded AES-256-GCM ciphertext blob. The plaintext name is
still kept inside the TGFS metadata.json (which is itself encrypted at
rest), so user-facing paths (WebDAV, the manager UI, file refs) keep
working unchanged -- only the Telegram-channel view loses access to the
original names.

Wire format::

    "TGFS1_" || base64url( nonce(12) || ciphertext || tag(16) )

A random nonce per call means the same plaintext name produces a
different ciphertext on every upload, so a passive Telegram observer
cannot tell whether two parts share an original filename.
"""

from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Distinct HKDF info so the name-encryption key cannot collide with any
# per-file key derived for content encryption.
_HKDF_INFO = b"tgfs-name-key-v1"

# Prefix tagging a Telegram document name as TGFS-encrypted. Includes a
# trailing underscore so the chunked uploader's "[partN]" prefix and the
# encrypted body remain easy to distinguish in logs.
NAME_PREFIX = "TGFS1_"

# AES-GCM standard nonce size.
NAME_NONCE_SIZE = 12

# AES-GCM auth tag size.
NAME_TAG_SIZE = 16


class NameEncryptionError(ValueError):
    """Raised when an encrypted filename cannot be decoded or authenticated."""


def derive_name_key(master_key: bytes) -> bytes:
    """Derive a dedicated 32-byte AES-256 key for filename encryption.

    Domain-separated from the per-file content keys via a distinct HKDF
    ``info`` string, so a compromise of one key class does not weaken
    the other.
    """
    if len(master_key) != 32:
        raise ValueError(f"master key must be 32 bytes, got {len(master_key)}")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"",
        info=_HKDF_INFO,
    )
    return hkdf.derive(master_key)


def is_encrypted_name(name: str) -> bool:
    """Return whether ``name`` carries the TGFS encrypted-name prefix."""
    return name.startswith(NAME_PREFIX)


def encrypt_name(name_key: bytes, plaintext: str) -> str:
    """Return a base64url-encoded ciphertext of ``plaintext``.

    The output is filename-safe (no ``/`` or ``+``), prefixed with
    :data:`NAME_PREFIX`, and bounded in length by
    ``ceil(4/3 * (12 + len(plaintext.encode('utf-8')) + 16)) +
    len(NAME_PREFIX)`` characters.
    """
    nonce = secrets.token_bytes(NAME_NONCE_SIZE)
    aead = AESGCM(name_key)
    ct = aead.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    blob = nonce + ct
    return NAME_PREFIX + base64.urlsafe_b64encode(blob).rstrip(b"=").decode("ascii")


def decrypt_name(name_key: bytes, encrypted: str) -> str:
    """Reverse :func:`encrypt_name`.

    Provided so that an operator who needs to identify a Telegram message
    by its original filename -- e.g. during disaster recovery from the
    channel alone -- can run a one-off decryption with the master key.
    The normal TGFS data path never needs to decrypt filenames because
    the plaintext is already kept in the metadata blob.
    """
    if not encrypted.startswith(NAME_PREFIX):
        raise NameEncryptionError("not a TGFS-encrypted name")
    body = encrypted[len(NAME_PREFIX) :]
    # urlsafe_b64decode needs proper padding; encrypt_name strips it for
    # compactness, so re-pad here.
    body += "=" * (-len(body) % 4)
    try:
        blob = base64.urlsafe_b64decode(body.encode("ascii"))
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise NameEncryptionError(f"invalid base64 in encrypted name: {exc}") from exc
    if len(blob) < NAME_NONCE_SIZE + NAME_TAG_SIZE:
        raise NameEncryptionError("encrypted name too short")
    nonce, ct = blob[:NAME_NONCE_SIZE], blob[NAME_NONCE_SIZE:]
    aead = AESGCM(name_key)
    try:
        plain = aead.decrypt(nonce, ct, associated_data=None)
    except Exception as exc:
        raise NameEncryptionError("name authentication failed") from exc
    return plain.decode("utf-8")
