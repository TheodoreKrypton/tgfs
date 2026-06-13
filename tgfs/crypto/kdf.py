"""Key derivation for TGFS encryption.

The key hierarchy is:

    passphrase   --Argon2id-->   master_key (32 bytes)
    master_key   --HKDF-SHA256(salt=file_salt, info=...)-->   file_key (32 bytes)

Why two stages?
  * Argon2id is intentionally slow and memory-hard so brute-forcing a weak
    passphrase is expensive. It runs only once at startup.
  * HKDF is fast and gives us a fresh, independent per-file key, so that
    leaking one file's key cannot be used to decrypt other files.

The master salt is stored in the TGFS config (or a sibling file). It is not
secret -- losing it just means re-deriving the master key with the same salt
is impossible, so the salt should be backed up alongside the metadata.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)

# Argon2id parameters. These are deliberately on the conservative side; the
# KDF only runs once per process startup so the cost is amortized. Tune via
# config if startup latency becomes a problem on weak hardware.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 64 * 1024  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32  # bytes -> matches AES-256 key size

# HKDF info string. Embedding a version tag here means we can rotate the
# derivation scheme by bumping the info string without changing the salt.
_HKDF_INFO = b"tgfs-file-key-v1"

# Size of the master salt. 16 bytes is the Argon2 recommendation.
MASTER_SALT_SIZE = 16


@dataclass(frozen=True)
class MasterKey:
    """Wrapper around a derived master key.

    Holding the master key in a dataclass (rather than a bare ``bytes``) makes
    it harder to accidentally log or serialize. The :meth:`__repr__` is also
    overridden so the secret never appears in tracebacks.
    """

    key: bytes
    salt: bytes

    def __repr__(self) -> str:  # pragma: no cover -- trivial
        return f"MasterKey(salt={self.salt.hex()[:8]}..., key=<redacted>)"


def derive_master_key(
    passphrase: str,
    salt: Optional[bytes] = None,
    *,
    time_cost: int = ARGON2_TIME_COST,
    memory_cost: int = ARGON2_MEMORY_COST_KIB,
    parallelism: int = ARGON2_PARALLELISM,
) -> MasterKey:
    """Derive the master key from a passphrase via Argon2id.

    If ``salt`` is ``None`` a fresh random salt is generated -- callers MUST
    persist the returned :attr:`MasterKey.salt` so the same key can be
    re-derived next time.
    """
    # argon2-cffi is imported lazily so the rest of the crypto module can be
    # exercised in unit tests without pulling the native dependency.
    from argon2.low_level import Type, hash_secret_raw

    if salt is None:
        salt = secrets.token_bytes(MASTER_SALT_SIZE)
    elif len(salt) < 8:
        # Argon2 requires at least 8 bytes; we recommend MASTER_SALT_SIZE.
        raise ValueError(f"master salt too short: {len(salt)} bytes")

    logger.info(
        "Deriving master key (argon2id, t=%d, m=%d KiB, p=%d)",
        time_cost,
        memory_cost,
        parallelism,
    )
    key = hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )
    return MasterKey(key=key, salt=salt)


def derive_file_key(master_key: bytes, file_salt: bytes) -> bytes:
    """Derive a per-file key from the master key using HKDF-SHA256.

    ``file_salt`` should be the 32-byte value stored in the file header.
    The output is suitable as an AES-256 key.
    """
    if len(master_key) != 32:
        raise ValueError(f"master key must be 32 bytes, got {len(master_key)}")
    if len(file_salt) < 16:
        # We don't require the full 32 here so the function can also be used
        # for KAT vectors with shorter salts in tests.
        raise ValueError(f"file salt too short: {len(file_salt)} bytes")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=file_salt,
        info=_HKDF_INFO,
    )
    return hkdf.derive(master_key)


def fingerprint(master_key: bytes) -> str:
    """Return a short, non-secret fingerprint of the master key.

    Useful for logging which key a TGFS instance is operating under without
    revealing the key itself. Returns the first 8 hex chars of SHA-256 over
    a domain-separated digest.
    """
    return sha256(b"tgfs-master-fingerprint\x00" + master_key).hexdigest()[:8]
