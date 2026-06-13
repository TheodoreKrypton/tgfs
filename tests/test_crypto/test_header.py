"""Unit tests for :mod:`tgfs.crypto.header`."""

from __future__ import annotations

import pytest

from tgfs.crypto.header import (
    HEADER_SIZE,
    Algorithm,
    FileHeader,
    InvalidHeaderError,
)


def _file_key() -> bytes:
    return b"\x42" * 32


class TestFileHeaderRoundTrip:
    def test_default_construction(self) -> None:
        header = FileHeader.new()
        assert header.algorithm == Algorithm.AES_256_GCM
        assert header.chunk_size == 64 * 1024
        assert len(header.file_salt) == 32

    def test_serialize_size(self) -> None:
        header = FileHeader.new()
        raw = header.serialize(_file_key())
        assert len(raw) == HEADER_SIZE

    def test_parse_round_trip(self) -> None:
        header = FileHeader.new(chunk_size=8192)
        raw = header.serialize(_file_key())
        parsed = FileHeader.parse(raw)
        assert parsed == header
        FileHeader.verify(raw, _file_key())

    def test_parse_rejects_short_buffer(self) -> None:
        with pytest.raises(InvalidHeaderError):
            FileHeader.parse(b"\x00" * (HEADER_SIZE - 1))

    def test_parse_rejects_bad_magic(self) -> None:
        header = FileHeader.new()
        raw = bytearray(header.serialize(_file_key()))
        raw[0:4] = b"XXXX"
        with pytest.raises(InvalidHeaderError, match="magic"):
            FileHeader.parse(bytes(raw))

    def test_parse_rejects_unknown_version(self) -> None:
        header = FileHeader.new()
        raw = bytearray(header.serialize(_file_key()))
        # Bytes 4-5 are the version (big-endian).
        raw[4] = 0xFF
        raw[5] = 0xFF
        with pytest.raises(InvalidHeaderError, match="version"):
            FileHeader.parse(bytes(raw))

    def test_parse_rejects_unknown_algorithm(self) -> None:
        header = FileHeader.new()
        raw = bytearray(header.serialize(_file_key()))
        # Bytes 6-7 are the algorithm id.
        raw[6] = 0x00
        raw[7] = 0xEE
        with pytest.raises(InvalidHeaderError, match="algorithm"):
            FileHeader.parse(bytes(raw))

    def test_parse_rejects_zero_chunk_size(self) -> None:
        header = FileHeader.new()
        raw = bytearray(header.serialize(_file_key()))
        # Bytes 8-11 are the chunk size.
        raw[8:12] = b"\x00\x00\x00\x00"
        with pytest.raises(InvalidHeaderError, match="chunk size"):
            FileHeader.parse(bytes(raw))


class TestFileHeaderMAC:
    def test_verify_passes_with_correct_key(self) -> None:
        header = FileHeader.new()
        raw = header.serialize(_file_key())
        FileHeader.verify(raw, _file_key())

    def test_verify_fails_with_wrong_key(self) -> None:
        header = FileHeader.new()
        raw = header.serialize(_file_key())
        with pytest.raises(InvalidHeaderError, match="MAC"):
            FileHeader.verify(raw, b"\x99" * 32)

    def test_verify_fails_after_tamper(self) -> None:
        header = FileHeader.new()
        raw = bytearray(header.serialize(_file_key()))
        # Flip a byte inside the salt -- valid struct-wise, but MAC fails.
        raw[20] ^= 0x01
        # The struct still parses; MAC verification is the safety net.
        FileHeader.parse(bytes(raw))
        with pytest.raises(InvalidHeaderError, match="MAC"):
            FileHeader.verify(bytes(raw), _file_key())

    def test_distinct_salts_produce_distinct_serializations(self) -> None:
        a = FileHeader.new()
        b = FileHeader.new()
        # Collision is astronomically unlikely with 32-byte random salts.
        assert a.serialize(_file_key()) != b.serialize(_file_key())
