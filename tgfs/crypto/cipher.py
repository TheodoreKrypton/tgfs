"""Chunked authenticated stream cipher (AES-256-GCM).

Plaintext is split into fixed-size chunks (see :data:`FileHeader.chunk_size`),
and each chunk is encrypted independently with a fresh deterministic nonce
plus a 16-byte GCM auth tag. The on-wire layout for a single chunk is:

    [ nonce (12 bytes) | ciphertext (<= chunk_size bytes) | tag (16 bytes) ]

Deriving the nonce from the chunk index (rather than randomly) lets us
seek to any chunk without scanning earlier ones, while still guaranteeing
nonce uniqueness for the same key (which is a hard GCM requirement).

The per-chunk auth tag means tampering with any chunk is detected on
decryption, and a corrupt or truncated chunk cannot silently produce wrong
plaintext for the rest of the file.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# AES-GCM standard nonce and tag sizes.
NONCE_SIZE = 12
TAG_SIZE = 16

# Per-chunk overhead in bytes: nonce + tag.
CHUNK_OVERHEAD = NONCE_SIZE + TAG_SIZE


class CipherError(Exception):
    """Raised on any encrypt/decrypt failure (wrong key, tampered data, etc.)."""


def chunk_nonce(file_salt: bytes, chunk_index: int) -> bytes:
    """Construct the deterministic GCM nonce for ``chunk_index``.

    Layout (12 bytes):
        [ first 4 bytes of file_salt | uint64 BE chunk_index ]

    Mixing in the file salt prevents the same chunk index from producing
    identical nonces across different files that happen to share a key
    (e.g. via key rotation accidents). The chunk index is big-endian so
    debugging traces are easier to read.
    """
    if chunk_index < 0 or chunk_index > 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"chunk index out of range: {chunk_index}")
    return file_salt[:4] + struct.pack(">Q", chunk_index)


@dataclass
class ChunkedAESGCM:
    """Stateless chunked AES-256-GCM helper bound to a single per-file key.

    The class is intentionally side-effect-free: callers drive the chunking
    themselves via :meth:`encrypt_chunk` / :meth:`decrypt_chunk` so we don't
    have to thread an internal buffer through async streams.
    """

    file_key: bytes
    file_salt: bytes
    chunk_size: int

    def __post_init__(self) -> None:
        if len(self.file_key) != 32:
            raise ValueError(f"file key must be 32 bytes, got {len(self.file_key)}")
        if len(self.file_salt) < 4:
            # We only consume the first 4 bytes for the nonce, but reject
            # obviously bogus salts early.
            raise ValueError("file salt too short")
        if self.chunk_size <= 0:
            raise ValueError(f"chunk size must be positive, got {self.chunk_size}")
        # Cache the AESGCM instance; it is cheap but reusing it avoids a
        # subtle hot-loop allocation pattern.
        self._aead = AESGCM(self.file_key)

    @staticmethod
    def ciphertext_chunk_size(plaintext_chunk_size: int) -> int:
        """Return on-wire size of one full plaintext chunk."""
        return plaintext_chunk_size + CHUNK_OVERHEAD

    def encrypt_chunk(self, plaintext: bytes, chunk_index: int) -> bytes:
        """Encrypt one plaintext chunk and return ``nonce || ciphertext || tag``.

        ``plaintext`` must not exceed :attr:`chunk_size` -- callers are
        responsible for splitting at chunk boundaries.
        """
        if len(plaintext) > self.chunk_size:
            raise ValueError(
                f"chunk too large: {len(plaintext)} > {self.chunk_size}"
            )
        nonce = chunk_nonce(self.file_salt, chunk_index)
        # AESGCM.encrypt returns ciphertext || tag concatenated.
        ct_and_tag = self._aead.encrypt(nonce, plaintext, associated_data=None)
        return nonce + ct_and_tag

    def decrypt_chunk(self, blob: bytes, chunk_index: int) -> bytes:
        """Decrypt one ``nonce || ciphertext || tag`` blob.

        Verifies that the nonce embedded in ``blob`` matches the deterministic
        nonce expected for ``chunk_index`` -- this catches chunk-reordering
        attacks that the GCM tag alone would not detect.
        """
        if len(blob) < CHUNK_OVERHEAD:
            raise CipherError(f"chunk blob too short: {len(blob)} bytes")

        nonce = blob[:NONCE_SIZE]
        ct_and_tag = blob[NONCE_SIZE:]

        expected_nonce = chunk_nonce(self.file_salt, chunk_index)
        if nonce != expected_nonce:
            # Either we are reading the wrong chunk or someone reordered the
            # ciphertext. Both are fatal.
            raise CipherError(
                f"nonce mismatch at chunk {chunk_index}: "
                f"got {nonce.hex()}, expected {expected_nonce.hex()}"
            )

        try:
            return self._aead.decrypt(nonce, ct_and_tag, associated_data=None)
        except InvalidTag as exc:
            raise CipherError(
                f"authentication failed at chunk {chunk_index}"
            ) from exc


def ciphertext_size_for_plaintext(plaintext_size: int, chunk_size: int) -> int:
    """Compute the total ciphertext payload size for a given plaintext size.

    This does NOT include the file header -- :data:`FileHeader.HEADER_SIZE`
    must be added separately. Used by the upload wrapper to declare the
    correct file size up-front to Telegram.
    """
    if plaintext_size < 0:
        raise ValueError(f"plaintext size negative: {plaintext_size}")
    if plaintext_size == 0:
        return 0
    full_chunks, remainder = divmod(plaintext_size, chunk_size)
    n_chunks = full_chunks + (1 if remainder else 0)
    return plaintext_size + n_chunks * CHUNK_OVERHEAD


def plaintext_offset_to_chunk(offset: int, chunk_size: int) -> tuple[int, int]:
    """Map a plaintext byte offset to ``(chunk_index, offset_within_chunk)``."""
    if offset < 0:
        raise ValueError(f"offset negative: {offset}")
    return divmod(offset, chunk_size)


def chunk_to_ciphertext_offset(chunk_index: int, chunk_size: int) -> int:
    """Return the ciphertext byte offset where ``chunk_index`` begins.

    The caller must add :data:`tgfs.crypto.header.HEADER_SIZE` if the
    on-wire stream is being addressed (the header is prepended once).
    """
    if chunk_index < 0:
        raise ValueError(f"chunk index negative: {chunk_index}")
    return chunk_index * (chunk_size + CHUNK_OVERHEAD)
