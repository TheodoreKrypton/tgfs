"""Streaming wrapper that turns a plaintext ``UploadableFileMessage`` into
a ciphertext ``UploadableFileMessage`` consumable by the existing TGFS
uploader.

The wrapper exposes the same ``read(length)`` interface as the underlying
plaintext message but emits encrypted bytes:

    [file_header (60 B)] [chunk_0] [chunk_1] ... [chunk_N]

where each ``chunk_i`` is ``nonce || ciphertext || tag``. The upload size
declared to Telegram is computed up-front via
:func:`ciphertext_size_for_plaintext` so the FileUploader can plan its parts
exactly as it does for plaintext files.

The wrapper does its own internal chunking and buffering -- the FileUploader
reads in ~512 KiB Telegram-chunks while we encrypt in (typically) 64 KiB
crypto-chunks, so we keep a small ``_pending`` buffer to span the two.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tgfs.crypto.cipher import (
    ChunkedAESGCM,
    ciphertext_size_for_plaintext,
)
from tgfs.crypto.header import HEADER_SIZE, FileHeader
from tgfs.reqres import FileTags, UploadableFileMessage

logger = logging.getLogger(__name__)


@dataclass
class EncryptingFileMessage(UploadableFileMessage):
    """An ``UploadableFileMessage`` that encrypts a wrapped plaintext source.

    The wrapped ``inner`` message is read on demand; we never load the whole
    plaintext into memory. ``size`` on this object reflects the *ciphertext*
    size including the header, which is what the uploader uses to compute
    Telegram parts and progress.
    """

    inner: UploadableFileMessage = field(init=False)
    cipher: ChunkedAESGCM = field(init=False)
    header_bytes: bytes = field(init=False)

    # Internal streaming state. ``_pending`` is the unconsumed tail of the
    # most recently produced ciphertext chunk (or the header). ``_chunk_index``
    # is the index of the *next* plaintext chunk to encrypt.
    _pending: bytes = field(default=b"", init=False, repr=False)
    _chunk_index: int = field(default=0, init=False, repr=False)
    _plaintext_read: int = field(default=0, init=False, repr=False)
    _header_emitted: bool = field(default=False, init=False, repr=False)

    @classmethod
    def wrap(
        cls,
        inner: UploadableFileMessage,
        file_key: bytes,
        header: FileHeader,
    ) -> "EncryptingFileMessage":
        """Build an ``EncryptingFileMessage`` around ``inner``.

        ``file_key`` must already be derived from the master key + header
        salt by the caller. ``header`` provides the chunk size and the salt
        used for nonce construction.
        """
        cipher = ChunkedAESGCM(
            file_key=file_key,
            file_salt=header.file_salt,
            chunk_size=header.chunk_size,
        )
        header_bytes = header.serialize(file_key)
        if len(header_bytes) != HEADER_SIZE:
            raise RuntimeError("serialized header has unexpected size")

        plaintext_size = inner.get_size()
        ciphertext_size = HEADER_SIZE + ciphertext_size_for_plaintext(
            plaintext_size, header.chunk_size
        )

        msg = cls(
            name=inner.name,
            size=ciphertext_size,
            caption=inner.caption,
            tags=FileTags(),
            _offset=0,
            _read_size=0,
            task_tracker=inner.task_tracker,
        )
        # Initialize the non-dataclass-init fields after construction.
        msg.inner = inner
        msg.cipher = cipher
        msg.header_bytes = header_bytes
        return msg

    # -- UploadableFileMessage protocol ------------------------------------

    def _get_size(self) -> int:
        # ``size`` is set explicitly in ``wrap`` and never falls back here,
        # but the protocol requires this method to exist.
        return self.size

    async def open(self) -> None:
        await self.inner.open()
        # Prepend the header to the pending buffer; it is emitted before any
        # ciphertext chunk.
        if not self._header_emitted:
            self._pending = self.header_bytes
            self._header_emitted = True

    async def close(self) -> None:
        await self.inner.close()

    async def read(self, length: int) -> bytes:
        """Return up to ``length`` ciphertext bytes.

        The contract matches ``FileMessageFromPath.read``: the uploader
        already constrains the request to the remaining file size, so we
        do not need to track an end-of-stream sentinel beyond producing
        whatever the cipher emits.
        """
        out = bytearray()
        while len(out) < length:
            # Drain pending bytes first.
            if self._pending:
                take = min(length - len(out), len(self._pending))
                out += self._pending[:take]
                self._pending = self._pending[take:]
                continue

            # Refill the pending buffer with the next encrypted chunk.
            plaintext_chunk = await self._read_plaintext_chunk()
            if not plaintext_chunk:
                # End of plaintext -- nothing more to emit.
                break

            encrypted = self.cipher.encrypt_chunk(plaintext_chunk, self._chunk_index)
            self._chunk_index += 1
            self._pending = encrypted

        return bytes(out)

    async def _read_plaintext_chunk(self) -> bytes:
        """Read exactly one plaintext crypto-chunk from the inner message.

        Loops in case the inner ``read`` returns short, which is allowed by
        the protocol (FileMessageFromStream in particular may do so).
        """
        target = self.cipher.chunk_size
        buf = bytearray()
        remaining_plaintext = self.inner.get_size() - self._plaintext_read
        if remaining_plaintext <= 0:
            return b""

        want = min(target, remaining_plaintext)
        while len(buf) < want:
            piece = await self.inner.read(want - len(buf))
            if not piece:
                # Inner stream ended earlier than its declared size -- treat
                # what we have as the final (possibly short) chunk.
                break
            buf += piece

        self._plaintext_read += len(buf)
        return bytes(buf)


def encrypted_size_for(plaintext_size: int, chunk_size: int) -> int:
    """Public helper returning the on-wire size (header + chunks)."""
    return HEADER_SIZE + ciphertext_size_for_plaintext(plaintext_size, chunk_size)
