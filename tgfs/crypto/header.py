"""On-disk file header format for encrypted TGFS files.

The header is the first ``HEADER_SIZE`` bytes of the encrypted payload and is
written inline at the start of the first Telegram part. Storing the header
inline (rather than only in the TGFS metadata) means a file can be decrypted
purely from its Telegram messages plus the master key, even if the TGFS
metadata channel/repository is lost or corrupted.

Wire format (big-endian, 60 bytes total):

    Offset  Size  Field
    ------  ----  --------------------------------------------------
       0      4   Magic              "TGFS"  (0x54 0x47 0x46 0x53)
       4      2   Header version     uint16, currently 1
       6      2   Algorithm id       uint16, see ``Algorithm``
       8      4   Chunk size         uint32, plaintext bytes per chunk
      12     32   File salt          random, fed to HKDF for per-file key
      44     16   Header MAC tag     truncated HMAC-SHA256(file_key, header_body)

The header MAC is computed *after* the file key is derived from the salt,
so a wrong master key or tampered header is detected before any ciphertext
chunk is decrypted.
"""

from __future__ import annotations

import enum
import hmac
import secrets
import struct
from dataclasses import dataclass
from hashlib import sha256

# Total size of the serialized header in bytes.
HEADER_SIZE = 60

# Magic bytes identifying a TGFS encrypted blob. Used to fast-fail on
# non-encrypted or corrupt input.
MAGIC = b"TGFS"

# Current header layout version. Bumping this should be accompanied by a
# migration path; the parser refuses unknown versions.
HEADER_VERSION = 1

# Default plaintext bytes per encryption chunk. Chosen as a balance between
# random-access granularity (smaller is better) and per-chunk overhead
# (larger is better). 64 KiB yields ~0.04% size overhead.
DEFAULT_CHUNK_SIZE = 64 * 1024

# Size of the random salt fed into HKDF for per-file key derivation.
FILE_SALT_SIZE = 32

# Length of the truncated HMAC tag that authenticates the header body.
HEADER_MAC_SIZE = 16


class Algorithm(enum.IntEnum):
    """Enumeration of supported AEAD algorithms.

    Only AES-256-GCM is supported in version 1. New algorithm ids must be
    added here *and* handled in :class:`tgfs.crypto.cipher.ChunkedAESGCM`.
    """

    AES_256_GCM = 1


# Pre-computed struct format for the unauthenticated portion of the header.
# Splitting the format keeps the MAC computation explicit and easy to audit.
_BODY_FORMAT = f">4sHHI{FILE_SALT_SIZE}s"
_BODY_SIZE = struct.calcsize(_BODY_FORMAT)
if _BODY_SIZE + HEADER_MAC_SIZE != HEADER_SIZE:
    raise RuntimeError("header layout mismatch")


class InvalidHeaderError(ValueError):
    """Raised when the on-disk header cannot be parsed or authenticated."""


@dataclass(frozen=True)
class FileHeader:
    """Parsed representation of an encrypted file header."""

    version: int
    algorithm: Algorithm
    chunk_size: int
    file_salt: bytes

    @classmethod
    def new(
        cls,
        algorithm: Algorithm = Algorithm.AES_256_GCM,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> "FileHeader":
        """Construct a fresh header with a cryptographically random file salt."""
        return cls(
            version=HEADER_VERSION,
            algorithm=algorithm,
            chunk_size=chunk_size,
            file_salt=secrets.token_bytes(FILE_SALT_SIZE),
        )

    def serialize(self, file_key: bytes) -> bytes:
        """Serialize the header and append a MAC computed with ``file_key``.

        The MAC binds the header to the per-file key that the body claims to
        produce. A wrong master key, corrupted salt, or tampered algorithm
        field will all cause :meth:`parse` to raise.
        """
        body = struct.pack(
            _BODY_FORMAT,
            MAGIC,
            self.version,
            int(self.algorithm),
            self.chunk_size,
            self.file_salt,
        )
        tag = hmac.new(file_key, body, sha256).digest()[:HEADER_MAC_SIZE]
        return body + tag

    @classmethod
    def parse(cls, raw: bytes) -> "FileHeader":
        """Parse a header without verifying its MAC.

        Returns a :class:`FileHeader` so the caller can derive the per-file key
        from the salt. After deriving the key, the caller MUST invoke
        :meth:`verify` to authenticate the header bytes.
        """
        if len(raw) < HEADER_SIZE:
            raise InvalidHeaderError(
                f"header too short: got {len(raw)} bytes, need {HEADER_SIZE}"
            )

        body = raw[:_BODY_SIZE]
        magic, version, algo, chunk_size, file_salt = struct.unpack(_BODY_FORMAT, body)

        if magic != MAGIC:
            raise InvalidHeaderError(f"bad magic: {magic!r}")
        if version != HEADER_VERSION:
            raise InvalidHeaderError(f"unsupported header version {version}")
        try:
            algorithm = Algorithm(algo)
        except ValueError as exc:
            raise InvalidHeaderError(f"unsupported algorithm id {algo}") from exc
        if chunk_size <= 0 or chunk_size > 16 * 1024 * 1024:
            # Reject pathological chunk sizes early; 16 MiB is a sanity ceiling.
            raise InvalidHeaderError(f"invalid chunk size {chunk_size}")

        return cls(
            version=version,
            algorithm=algorithm,
            chunk_size=chunk_size,
            file_salt=file_salt,
        )

    @staticmethod
    def verify(raw: bytes, file_key: bytes) -> None:
        """Validate the MAC of an already-parsed header.

        Raises :class:`InvalidHeaderError` if the MAC does not match. Uses
        :func:`hmac.compare_digest` to avoid timing side channels.
        """
        if len(raw) < HEADER_SIZE:
            raise InvalidHeaderError("header too short for MAC verification")
        body = raw[:_BODY_SIZE]
        tag = raw[_BODY_SIZE:HEADER_SIZE]
        expected = hmac.new(file_key, body, sha256).digest()[:HEADER_MAC_SIZE]
        if not hmac.compare_digest(tag, expected):
            raise InvalidHeaderError("header MAC verification failed")
