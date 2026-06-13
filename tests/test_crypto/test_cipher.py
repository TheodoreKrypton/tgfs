"""Unit tests for :mod:`tgfs.crypto.cipher`."""

from __future__ import annotations

import os

import pytest

from tgfs.crypto.cipher import (
    CHUNK_OVERHEAD,
    NONCE_SIZE,
    TAG_SIZE,
    ChunkedAESGCM,
    CipherError,
    chunk_nonce,
    chunk_to_ciphertext_offset,
    ciphertext_size_for_plaintext,
    plaintext_offset_to_chunk,
)


def _make_cipher(chunk_size: int = 64 * 1024) -> ChunkedAESGCM:
    """Build a cipher with a fixed key/salt for deterministic tests."""
    return ChunkedAESGCM(
        file_key=b"\x01" * 32,
        file_salt=b"\xaa" * 32,
        chunk_size=chunk_size,
    )


class TestChunkNonce:
    def test_first_four_bytes_come_from_salt(self) -> None:
        nonce = chunk_nonce(b"abcdEFGHIJKLMNOP", 0)
        assert nonce[:4] == b"abcd"

    def test_chunk_index_is_big_endian(self) -> None:
        nonce = chunk_nonce(b"\x00" * 32, 1)
        assert nonce[4:] == b"\x00\x00\x00\x00\x00\x00\x00\x01"

    def test_negative_index_rejected(self) -> None:
        with pytest.raises(ValueError):
            chunk_nonce(b"\x00" * 32, -1)

    def test_huge_index_rejected(self) -> None:
        with pytest.raises(ValueError):
            chunk_nonce(b"\x00" * 32, 2**65)

    def test_size_is_12_bytes(self) -> None:
        assert len(chunk_nonce(b"\x00" * 32, 42)) == NONCE_SIZE


class TestChunkedAESGCMRoundTrip:
    def test_empty_chunk(self) -> None:
        cipher = _make_cipher()
        blob = cipher.encrypt_chunk(b"", 0)
        # Empty plaintext still produces nonce + tag.
        assert len(blob) == NONCE_SIZE + TAG_SIZE
        assert cipher.decrypt_chunk(blob, 0) == b""

    def test_short_chunk(self) -> None:
        cipher = _make_cipher()
        plaintext = b"hello, world"
        blob = cipher.encrypt_chunk(plaintext, 5)
        assert len(blob) == NONCE_SIZE + len(plaintext) + TAG_SIZE
        assert cipher.decrypt_chunk(blob, 5) == plaintext

    def test_full_chunk(self) -> None:
        cipher = _make_cipher(chunk_size=128)
        plaintext = os.urandom(128)
        blob = cipher.encrypt_chunk(plaintext, 0)
        assert cipher.decrypt_chunk(blob, 0) == plaintext

    def test_overlong_plaintext_rejected(self) -> None:
        cipher = _make_cipher(chunk_size=16)
        with pytest.raises(ValueError):
            cipher.encrypt_chunk(b"a" * 17, 0)

    def test_short_key_rejected(self) -> None:
        with pytest.raises(ValueError):
            ChunkedAESGCM(file_key=b"x" * 16, file_salt=b"y" * 32, chunk_size=64)


class TestChunkedAESGCMTampering:
    """Verify that any tampering is detected on decrypt."""

    def _setup(self) -> tuple[ChunkedAESGCM, bytes]:
        cipher = _make_cipher()
        return cipher, cipher.encrypt_chunk(b"some plaintext", 7)

    def test_flipped_byte_in_ciphertext_detected(self) -> None:
        cipher, blob = self._setup()
        # Flip a byte in the ciphertext (after the nonce, before the tag).
        tampered = bytearray(blob)
        tampered[NONCE_SIZE + 3] ^= 0x01
        with pytest.raises(CipherError):
            cipher.decrypt_chunk(bytes(tampered), 7)

    def test_flipped_byte_in_tag_detected(self) -> None:
        cipher, blob = self._setup()
        tampered = bytearray(blob)
        tampered[-1] ^= 0x80
        with pytest.raises(CipherError):
            cipher.decrypt_chunk(bytes(tampered), 7)

    def test_wrong_chunk_index_detected(self) -> None:
        cipher, blob = self._setup()
        # Decrypting as chunk 8 instead of 7 must fail because the nonce
        # was bound to index 7 via the salt-derived nonce.
        with pytest.raises(CipherError):
            cipher.decrypt_chunk(blob, 8)

    def test_swapped_nonce_detected(self) -> None:
        cipher = _make_cipher()
        a = cipher.encrypt_chunk(b"chunk-a", 0)
        b = cipher.encrypt_chunk(b"chunk-b", 1)
        # Move chunk-b's nonce in front of chunk-a's ciphertext+tag.
        forged = b[:NONCE_SIZE] + a[NONCE_SIZE:]
        with pytest.raises(CipherError):
            cipher.decrypt_chunk(forged, 1)

    def test_too_short_blob_detected(self) -> None:
        cipher = _make_cipher()
        with pytest.raises(CipherError):
            cipher.decrypt_chunk(b"x" * (CHUNK_OVERHEAD - 1), 0)


class TestSizeArithmetic:
    @pytest.mark.parametrize(
        "plaintext_size, chunk_size, expected",
        [
            (0, 64 * 1024, 0),
            (1, 64 * 1024, 1 + CHUNK_OVERHEAD),
            (64 * 1024, 64 * 1024, 64 * 1024 + CHUNK_OVERHEAD),
            (64 * 1024 + 1, 64 * 1024, 64 * 1024 + 1 + 2 * CHUNK_OVERHEAD),
            (10 * 64 * 1024, 64 * 1024, 10 * 64 * 1024 + 10 * CHUNK_OVERHEAD),
        ],
    )
    def test_ciphertext_size_for_plaintext(
        self, plaintext_size: int, chunk_size: int, expected: int
    ) -> None:
        assert (
            ciphertext_size_for_plaintext(plaintext_size, chunk_size) == expected
        )

    def test_offset_to_chunk_round_trip(self) -> None:
        for offset in (0, 1, 64 * 1024 - 1, 64 * 1024, 64 * 1024 + 5):
            chunk_index, in_chunk = plaintext_offset_to_chunk(offset, 64 * 1024)
            reconstructed = chunk_index * 64 * 1024 + in_chunk
            assert reconstructed == offset

    def test_chunk_to_ciphertext_offset_first_chunk(self) -> None:
        assert chunk_to_ciphertext_offset(0, 64 * 1024) == 0

    def test_chunk_to_ciphertext_offset_second_chunk(self) -> None:
        assert chunk_to_ciphertext_offset(1, 64 * 1024) == 64 * 1024 + CHUNK_OVERHEAD
