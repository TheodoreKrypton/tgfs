"""Integration tests for :mod:`tgfs.crypto.stream` and
:mod:`tgfs.crypto.repository`.

These tests deliberately do not touch Telegram. They drive the
encryption/decryption pipeline with a fake :class:`IFileContentRepository`
that stores ciphertext in memory, which is sufficient to validate:

  * upload/download round-trip across multiple crypto-chunks
  * range requests at arbitrary plaintext offsets
  * detection of corrupted ciphertext
  * detection of a wrong master key
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from tgfs.core.repository.interface import IFileContentRepository
from tgfs.crypto.cipher import CHUNK_OVERHEAD
from tgfs.crypto.header import HEADER_SIZE, InvalidHeaderError
from tgfs.crypto.repository import EncryptingFileContentRepository
from tgfs.reqres import (
    FileContent,
    FileMessageFromBuffer,
    SentFileMessage,
    UploadableFileMessage,
)


# --- in-memory fake backend -------------------------------------------------


@dataclass
class _FakeFileVersion:
    """Stand-in for ``TGFSFileVersion`` good enough for the repository.

    Only ``id``, ``size``, ``message_ids``, and ``part_sizes`` are consulted.
    """

    id: str
    size: int
    message_ids: List[int] = field(default_factory=list)
    part_sizes: List[int] = field(default_factory=list)


class _InMemoryRepo(IFileContentRepository):
    """An ``IFileContentRepository`` that stores ciphertext in a dict.

    A "part" of the file is one message id. To make range tests interesting,
    we always store the file as a single part -- this matches small files
    in tgfs (anything < 2 GB) and exercises the chunk-level range logic in
    the encrypting wrapper.
    """

    def __init__(self, part_size: int = 10**9) -> None:
        self._files: dict[int, bytes] = {}
        self._next_msg_id = 1000
        self._part_size = part_size

    async def save(
        self, file_msg: UploadableFileMessage
    ) -> List[SentFileMessage]:
        # Read the whole ciphertext into memory in chunks, mimicking what
        # the real uploader does. We force several reads of varied size to
        # stress the wrapper's buffering.
        await file_msg.open()
        try:
            buf = bytearray()
            for read_size in (7, 4096, 8192, 1024 * 1024):
                while True:
                    piece = await file_msg.read(read_size)
                    if not piece:
                        break
                    buf += piece
                    if len(buf) >= file_msg.get_size():
                        break
                if len(buf) >= file_msg.get_size():
                    break
        finally:
            await file_msg.close()

        ciphertext = bytes(buf)
        msg_id = self._next_msg_id
        self._next_msg_id += 1
        self._files[msg_id] = ciphertext
        return [SentFileMessage(message_id=msg_id, size=len(ciphertext))]

    async def get(
        self, fv, begin: int, end: int, name: str
    ) -> FileContent:
        # Single-part files only in this fake, so use the first message id.
        # ``end`` follows the codebase-wide INCLUSIVE convention (matches the
        # real Telegram ``download_file`` API: bytes_to_read = end - begin + 1).
        ciphertext = self._files[fv.message_ids[0]]
        if end < 0:
            end = len(ciphertext) - 1
        limit = end + 1  # exclusive bound for slicing

        async def stream():
            # Emit in small, oddly-sized pieces to make sure the decrypting
            # consumer handles arbitrary boundaries.
            i = begin
            for step in (3, 17, 1024, 8192):
                if i >= limit:
                    break
                slice_end = min(i + step, limit)
                yield ciphertext[i:slice_end]
                i = slice_end
            if i < limit:
                yield ciphertext[i:limit]

        return stream()

    async def update(self, message_id: int, buffer: bytes, name: str) -> int:
        self._files[message_id] = buffer
        return message_id


def _make_repo(master_key: bytes = b"\x77" * 32, chunk_size: int = 4096):
    return EncryptingFileContentRepository(
        _InMemoryRepo(),
        master_key=master_key,
        chunk_size=chunk_size,
    )


async def _save_and_get_fv(repo, data: bytes):
    file_msg = FileMessageFromBuffer.new(buffer=data, name="test.bin")
    sent = await repo.save(file_msg)
    fv = _FakeFileVersion(
        id="v1",
        size=sum(m.size for m in sent),
        message_ids=[m.message_id for m in sent],
        part_sizes=[m.size for m in sent],
    )
    return fv


async def _collect(stream) -> bytes:
    buf = bytearray()
    async for piece in stream:
        buf += piece
    return bytes(buf)


# --- round-trip tests ------------------------------------------------------


@pytest.mark.parametrize(
    "size",
    [
        0,
        1,
        100,
        4095,
        4096,
        4097,
        4096 * 3,
        4096 * 10 + 123,
        4096 * 50 + 1,
    ],
)
async def test_full_round_trip(size: int) -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(size)
    fv = await _save_and_get_fv(repo, plaintext)

    out = await _collect(await repo.get(fv, 0, -1, "test.bin"))
    assert out == plaintext


async def test_ciphertext_size_matches_formula() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 5 + 17)
    fv = await _save_and_get_fv(repo, plaintext)
    # Ciphertext = header + 6 chunks (5 full + 1 short), each with overhead.
    expected = HEADER_SIZE + len(plaintext) + 6 * CHUNK_OVERHEAD
    assert fv.size == expected


# --- range request tests ---------------------------------------------------


async def test_range_request_within_first_chunk() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 5)
    fv = await _save_and_get_fv(repo, plaintext)
    out = await _collect(await repo.get(fv, 100, 199, "test.bin"))
    assert out == plaintext[100:200]


async def test_range_request_spanning_chunk_boundary() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 5)
    fv = await _save_and_get_fv(repo, plaintext)
    # 4090..4105 (inclusive) spans the boundary between chunk 0 and chunk 1.
    out = await _collect(await repo.get(fv, 4090, 4105, "test.bin"))
    assert out == plaintext[4090:4106]


async def test_range_request_across_many_chunks() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 10)
    fv = await _save_and_get_fv(repo, plaintext)
    # Pick a range that touches 4 chunks. ``end`` is inclusive.
    begin, slice_end = 4096 * 2 + 50, 4096 * 6 - 50
    out = await _collect(await repo.get(fv, begin, slice_end - 1, "test.bin"))
    assert out == plaintext[begin:slice_end]


async def test_range_request_to_end_of_file() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 3 + 100)
    fv = await _save_and_get_fv(repo, plaintext)
    out = await _collect(await repo.get(fv, 1234, -1, "test.bin"))
    assert out == plaintext[1234:]


async def test_range_request_last_byte() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 3 + 100)
    fv = await _save_and_get_fv(repo, plaintext)
    out = await _collect(
        await repo.get(fv, len(plaintext) - 1, len(plaintext) - 1, "test.bin")
    )
    assert out == plaintext[-1:]


# --- security tests --------------------------------------------------------


async def test_wrong_master_key_fails_header_verify() -> None:
    write_repo = _make_repo(master_key=b"\x77" * 32, chunk_size=4096)
    fv = await _save_and_get_fv(write_repo, os.urandom(8192))

    # New repo with a *different* master key, same ciphertext backend.
    read_repo = EncryptingFileContentRepository(
        write_repo._inner,
        master_key=b"\x99" * 32,
        chunk_size=4096,
    )
    with pytest.raises(Exception):  # InvalidHeaderError, but imported indirectly
        await _collect(await read_repo.get(fv, 0, -1, "test.bin"))


async def test_corrupted_ciphertext_chunk_detected() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 3)
    fv = await _save_and_get_fv(repo, plaintext)

    # Flip a byte in the middle of the first chunk's ciphertext, leaving
    # the header intact.
    inner: _InMemoryRepo = repo._inner  # type: ignore[assignment]
    msg_id = fv.message_ids[0]
    blob = bytearray(inner._files[msg_id])
    blob[HEADER_SIZE + 50] ^= 0x01
    inner._files[msg_id] = bytes(blob)

    with pytest.raises(Exception):
        await _collect(await repo.get(fv, 0, -1, "test.bin"))


async def test_empty_file_round_trip() -> None:
    repo = _make_repo(chunk_size=4096)
    fv = await _save_and_get_fv(repo, b"")
    out = await _collect(await repo.get(fv, 0, -1, "test.bin"))
    assert out == b""


# --- mixed mode: legacy plaintext + encrypted writes -----------------------


def _seed_plaintext(repo: EncryptingFileContentRepository, data: bytes) -> _FakeFileVersion:
    """Stuff a plaintext blob directly into the inner repo, as if it had
    been written before encryption was enabled."""
    inner: _InMemoryRepo = repo._inner  # type: ignore[assignment]
    msg_id = inner._next_msg_id
    inner._next_msg_id += 1
    inner._files[msg_id] = data
    return _FakeFileVersion(
        id=f"plain-{msg_id}",
        size=len(data),
        message_ids=[msg_id],
        part_sizes=[len(data)],
    )


async def test_read_plaintext_passthrough_full() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 3 + 500)
    fv = _seed_plaintext(repo, plaintext)
    out = await _collect(await repo.get(fv, 0, -1, "legacy.bin"))
    assert out == plaintext


@pytest.mark.parametrize(
    "begin,end",
    [
        (0, 0),
        (10, 199),
        (4090, 4105),  # spans a would-be chunk boundary
        (4096 * 2 + 50, 4096 * 6 - 50 - 1),
        (1234, -1),
    ],
)
async def test_read_plaintext_passthrough_ranges(begin: int, end: int) -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 10)
    fv = _seed_plaintext(repo, plaintext)
    out = await _collect(await repo.get(fv, begin, end, "legacy.bin"))
    expected = plaintext[begin:] if end < 0 else plaintext[begin:end + 1]
    assert out == expected


async def test_read_plaintext_last_byte() -> None:
    repo = _make_repo(chunk_size=4096)
    plaintext = os.urandom(4096 * 3 + 100)
    fv = _seed_plaintext(repo, plaintext)
    out = await _collect(
        await repo.get(fv, len(plaintext) - 1, len(plaintext) - 1, "legacy.bin")
    )
    assert out == plaintext[-1:]


async def test_read_plaintext_shorter_than_header() -> None:
    """A 10-byte legacy file must read back as plaintext, not error out."""
    repo = _make_repo(chunk_size=4096)
    plaintext = b"hello tgfs"
    fv = _seed_plaintext(repo, plaintext)
    out = await _collect(await repo.get(fv, 0, -1, "tiny.txt"))
    assert out == plaintext


async def test_read_plaintext_shorter_than_magic() -> None:
    """Files with <4 bytes can't even hold the magic; treat as plaintext."""
    repo = _make_repo(chunk_size=4096)
    plaintext = b"hi"
    fv = _seed_plaintext(repo, plaintext)
    out = await _collect(await repo.get(fv, 0, -1, "tiny.txt"))
    assert out == plaintext


async def test_overwrite_plaintext_produces_ciphertext() -> None:
    """Writing a new file under an encryption-enabled wrapper always
    encrypts -- regardless of whether prior files in the repo are plaintext."""
    repo = _make_repo(chunk_size=4096)
    # Seed a plaintext file so the inner repo holds a mix.
    _seed_plaintext(repo, b"old content from before encryption was enabled")

    # New write through the wrapper.
    new_plaintext = os.urandom(8192)
    new_fv = await _save_and_get_fv(repo, new_plaintext)
    inner: _InMemoryRepo = repo._inner  # type: ignore[assignment]
    stored = inner._files[new_fv.message_ids[0]]
    assert stored[:4] == b"TGFS", "new write must start with TGFS magic"
    assert stored != new_plaintext

    # And it round-trips through the wrapper.
    out = await _collect(await repo.get(new_fv, 0, -1, "new.bin"))
    assert out == new_plaintext


async def test_plaintext_with_accidental_tgfs_prefix_fails_loudly() -> None:
    """A plaintext file that happens to start with ``TGFS`` and looks like a
    header parse target must NOT be silently treated as plaintext: the MAC
    will fail and we must surface the error so a real key mismatch is never
    masked.
    """
    repo = _make_repo(chunk_size=4096)
    # Construct a 60-byte blob whose magic + version + algorithm + chunk_size
    # parse OK, but the MAC is garbage. parse() succeeds; verify() raises.
    import struct as _struct

    body = _struct.pack(">4sHHI32s", b"TGFS", 1, 1, 4096, b"\x00" * 32)
    fake = body + b"\xff" * 16  # wrong MAC
    fv = _seed_plaintext(repo, fake + b"some more data")
    with pytest.raises(InvalidHeaderError):
        await _collect(await repo.get(fv, 0, -1, "ambiguous.bin"))


async def test_plaintext_with_tgfs_prefix_short_fails_loudly() -> None:
    """Magic match but truncated below HEADER_SIZE: surface as error."""
    repo = _make_repo(chunk_size=4096)
    fv = _seed_plaintext(repo, b"TGFS" + b"\x00" * 10)  # 14 bytes total
    with pytest.raises(InvalidHeaderError):
        await _collect(await repo.get(fv, 0, -1, "short.bin"))


async def test_detection_cached_across_calls() -> None:
    """A second read of the same plaintext file must not re-probe the inner."""
    repo = _make_repo(chunk_size=4096)
    fv = _seed_plaintext(repo, os.urandom(1024))

    # First read populates the cache.
    await _collect(await repo.get(fv, 0, -1, "legacy.bin"))

    hit, entry = repo._cache.lookup(fv.id)
    assert hit and entry is None  # cached as plaintext
