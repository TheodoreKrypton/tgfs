"""Deterministic, network-free fixture for reproducing the wide-directory
WebDAV PROPFIND bottleneck.

The fixture stands up the *real* production stack -- `asgidav` PROPFIND
handling, `tgfs.app.webdav.Folder`/`Resource`, `Ops`, `DirectoryApi`,
`FileApi`, `FileDescApi`, the `MessageBroker` and `TGMsgFDRepository` --
on top of an in-memory metadata repository and a fake TDLib client.
Nothing touches the network, Telegram, or GitHub.

The instrumentation is deliberately attached to `TGFSDirectory.find_files`
(see `tgfs/core/model/directory.py`), because that is the primitive every
per-child resolution funnels through:

    propfind_stream / _child_response_elements
      -> Folder.member(name)                    (tgfs/app/webdav/folder.py)
      -> Resource(...)                          (tgfs/app/webdav/resource.py)
      -> Ops.stat_file(path)                    (tgfs/core/ops.py)
      -> Ops.cd(dirname) + DirectoryApi.get_fr  (tgfs/core/ops.py)
      -> TGFSDirectory.find_files([name])       <-- linear scan, per child

Each entry visited this way is O(len(dir.files)), so listing N children
costs O(N^2) elementary comparisons. `find_files` is called with a *single*
name during a listing, which makes it an unambiguous probe: the number of
calls counts per-child resolutions, and the number of elements scanned
counts the quadratic work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from tgfs.core.api import DirectoryApi, FileApi, FileDescApi, MessageApi, MetaDataApi
from tgfs.core.client import Client
from tgfs.core.model import (
    TGFSDirectory,
    TGFSFileDesc,
    TGFSFileRef,
    TGFSFileVersion,
    TGFSMetadata,
)
from tgfs.core.repository.impl.fd.tg_msg import TGMsgFDRepository
from tgfs.core.repository.interface import IMetaDataRepository
from tgfs.reqres import (
    Document,
    GetMeResp,
    GetMessagesReq,
    GetMessagesResp,
    MessageResp,
)
from tgfs.telegram.interface import ITDLibClient, TDLibApi


# --------------------------------------------------------------------------
# Instrumentation
# --------------------------------------------------------------------------


@dataclass
class ScanCounter:
    """Counts the elementary work done by `TGFSDirectory.find_files`.

    `calls`       -- how many times a directory was searched by name.
                     During a flat depth-1 listing this is the number of
                     per-child resolutions performed.
    `scanned`     -- how many candidate entries were compared in total.
                     This is the quadratic work: searching one name in a
                     directory of N files costs N comparisons.
    `by_dir_size` -- {directory_size: number_of_searches}, used to show the
                     cost is proportional to the *width* of the directory.
    """

    calls: int = 0
    scanned: int = 0
    by_dir_size: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.by_dir_size is None:
            self.by_dir_size = {}

    def record(self, dir_size: int) -> None:
        self.calls += 1
        self.scanned += dir_size
        self.by_dir_size[dir_size] = self.by_dir_size.get(dir_size, 0) + 1

    def reset(self) -> None:
        self.calls = 0
        self.scanned = 0
        self.by_dir_size = {}


def install_find_files_probe(counter: ScanCounter):
    """Monkeypatch `TGFSDirectory.find_files` to count elementary work.

    Returns a callable that restores the original method.
    """
    original = TGFSDirectory.find_files

    def probed(self: TGFSDirectory, names=()):  # type: ignore[no-untyped-def]
        result = original(self, names)
        # Only count lookups by name; `find_files()` with no args just
        # returns the list and is not part of the per-child resolution path.
        if names:
            counter.record(len(self.files))
        return result

    TGFSDirectory.find_files = probed  # type: ignore[method-assign]

    def restore() -> None:
        TGFSDirectory.find_files = original  # type: ignore[method-assign]

    return restore


# --------------------------------------------------------------------------
# Fake Telegram transport (in-memory, no network)
# --------------------------------------------------------------------------


class FakeTDLibClient(ITDLibClient):
    """An in-memory stand-in for a Telegram client.

    Serves file-descriptor messages (JSON documents) that were pre-loaded
    into `messages`. Records how many messages were actually fetched so a
    test can prove the listing performs per-child descriptor round trips.
    """

    def __init__(self, messages: dict[int, MessageResp], name: str = "fake-bot"):
        super().__init__()
        self._messages = messages
        self._name = name
        self.fetch_count = 0

    async def get_messages(self, req: GetMessagesReq) -> GetMessagesResp:
        self.fetch_count += len(req.message_ids)
        return [self._messages.get(mid) for mid in req.message_ids]

    async def send_text(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def edit_message_text(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def search_messages(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not search")

    async def get_pinned_messages(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not read pins")

    async def pin_message(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def save_big_file_part(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def save_file_part(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def send_big_file(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def send_small_file(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def edit_message_media(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not write")

    async def download_file(self, req):  # type: ignore[no-untyped-def]
        raise AssertionError("listing must not download")

    async def resolve_channel_id(self, channel_id: str) -> int:
        return int(channel_id)

    async def _get_me(self) -> GetMeResp:
        return GetMeResp(is_premium=False, name=self._name)


# --------------------------------------------------------------------------
# In-memory metadata repository
# --------------------------------------------------------------------------


class InMemoryMetadataRepository(IMetaDataRepository):
    """Serves a pre-built `TGFSMetadata` tree; `push` is a no-op recorder."""

    def __init__(self, metadata: TGFSMetadata):
        super().__init__()
        self._metadata = metadata
        self.pushes = 0

    async def get(self) -> TGFSMetadata:
        return self._metadata

    async def push(self) -> None:
        self.pushes += 1


# --------------------------------------------------------------------------
# Fixture construction
# --------------------------------------------------------------------------


def build_file_desc(name: str, message_id: int, size: int) -> TGFSFileDesc:
    """A one-version file descriptor whose single part is `message_id`."""
    version = TGFSFileVersion(
        id="v1",
        updated_at=__import__("datetime").datetime(
            2024, 1, 1, tzinfo=__import__("datetime").timezone.utc
        ),
        _size=size,
        message_ids=[message_id],
        part_sizes=[size],
    )
    return TGFSFileDesc(
        name=name,
        latest_version_id="v1",
        versions={"v1": version},
    )


async def make_client(
    channel_id: int,
    num_children: int,
    client_name: str = "notes",
) -> tuple[Client, FakeTDLibClient, InMemoryMetadataRepository]:
    """Build a real `Client` with `num_children` files directly under root.

    Each file `child-00000.txt` .. `child-<N-1>.txt` gets:
      * a `TGFSFileRef` in the root directory (message_id = fd message id)
      * a file-descriptor message in the fake Telegram channel
      * a document message for the file's content part
    """
    root = TGFSDirectory.root_dir()

    fd_messages: dict[int, MessageResp] = {}
    doc_messages: dict[int, MessageResp] = {}

    for i in range(num_children):
        name = f"child-{i:05d}.txt"

        # The file-descriptor message id and the content message id are
        # distinct, exactly as in production.
        fd_msg_id = 1_000_000 + i
        doc_msg_id = 2_000_000 + i

        fd = build_file_desc(name, doc_msg_id, size=1024)
        fd_messages[fd_msg_id] = MessageResp(
            message_id=fd_msg_id,
            text=json.dumps(fd.to_dict()),
            document=None,
        )
        doc_messages[doc_msg_id] = MessageResp(
            message_id=doc_msg_id,
            text="",
            document=Document(
                size=1024,
                id=doc_msg_id,
                access_hash=0,
                file_reference=b"",
                mime_type="text/plain",
            ),
        )

        root.files.append(
            TGFSFileRef(message_id=fd_msg_id, name=name, location=root)
        )

    all_messages = {**fd_messages, **doc_messages}

    bot = FakeTDLibClient(all_messages)
    tdlib = TDLibApi(bots=[bot], account=None)

    message_api = MessageApi(tdlib, channel_id)
    fd_repo = TGMsgFDRepository(message_api)

    metadata_repo = InMemoryMetadataRepository(TGFSMetadata(dir=root))
    metadata_api = MetaDataApi(metadata_repo)
    # `Client.create` does this; without it `DirectoryApi.root` raises.
    await metadata_api.init()
    fd_api = FileDescApi(fd_repo, None)  # type: ignore[arg-type]

    file_api = FileApi(metadata_api, fd_api)
    dir_api = DirectoryApi(metadata_api)

    client = Client(
        name=client_name,
        message_api=message_api,
        file_api=file_api,
        dir_api=dir_api,
    )
    return client, bot, metadata_repo


async def make_cold_client(num_children: int, channel_id: int = 114514):
    """Build a client and clear every message cache so no lookup is served
    from memory. This isolates the *work performed*, not the cache state."""
    from tgfs.utils.message_cache import global_message_cache

    global_message_cache.clear()

    client, bot, repo = await make_client(channel_id, num_children)
    global_message_cache.clear()
    return client, bot, repo
