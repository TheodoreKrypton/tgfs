"""End-to-end proof that listing a wide directory is not quadratic.

This drives the real WebDAV layer -- `tgfs.app.webdav` `Folder`/`Resource`,
`Ops`, `DirectoryApi` -- over the in-memory fixture in
`wide_listing_fixture`, and counts both

* how many times a child name is resolved (`ScanCounter.calls`), and
* how many directory entries are actually visited (`CountingList.scanned`).

The second number is the one that matters: before the fix, every per-child
resolution walked the whole entry list, so listing N children visited N*N
entries.  `ScanCounter.scanned` is deliberately *not* used as the pass/fail
signal here, because it charges a flat `len(dir.files)` per call and cannot
distinguish a real scan from an indexed lookup.

Behaviour is pinned too: every child must still resolve, and an entry added
after a listing must not be hidden by a stale snapshot.
"""

import pytest

from tests.tgfs.app.webdav.wide_listing_fixture import (
    ScanCounter,
    install_find_files_probe,
    make_cold_client,
)
from tests.tgfs.core.model.test_directory_index import CountingList
from tgfs.app.fs_cache import FSCache, gfc
from tgfs.app.webdav.folder import Folder
from tgfs.core.model import TGFSFileRef


@pytest.fixture(name="counter")
def counter_fixture():
    counter = ScanCounter()
    restore = install_find_files_probe(counter)
    try:
        yield counter
    finally:
        restore()


@pytest.fixture(name="client_for")
def client_for_fixture():
    """Build a cold fixture client, registered with the global FS cache.

    `Resource` looks its client up in `tgfs.app.fs_cache.gfc`, which the
    server normally populates; the fixture stands up a bare client, so the
    registration is done here.
    """

    built = []

    async def build(size: int, instrument: bool = True):
        client, bot, repo = await make_cold_client(size)
        gfc.setdefault(client.name, FSCache())
        built.append(client.name)

        root = client.dir_api.root
        if instrument:
            root.files = CountingList(root.files)
        return client, bot, repo

    yield build

    for name in built:
        gfc.pop(name, None)


def instrumented_root(client) -> CountingList:
    """Swap the root's entry list for one that counts visits; return it."""
    root = client.dir_api.root
    if not isinstance(root.files, CountingList):
        root.files = CountingList(root.files)
    return root.files


async def resolve_all_children(client, size: int):
    """Resolve every child of the root directory, as a depth-1 PROPFIND does.

    `Folder.member` is the per-child step a PROPFIND repeats for each entry;
    each call builds a `Resource`, which stats the file and therefore
    resolves its name in the parent directory.
    """
    folder = Folder("/", client)
    return [await folder.member(f"child-{i:05d}.txt") for i in range(size)]


class TestListingCostIsLinearInDirectoryWidth:
    """The production bottleneck, measured on the real request path."""

    @pytest.mark.asyncio
    async def test_listing_a_wide_directory_is_not_quadratic(
        self, counter, client_for
    ):
        size = 200
        client, _bot, _repo = await client_for(size)
        root = instrumented_root(client)

        # Warm up: building the index on first use is allowed, rebuilding it
        # on every lookup is not.
        Folder("/", client)
        root.reset()
        counter.reset()

        await resolve_all_children(client, size)

        assert counter.calls == size
        # A per-child linear scan visits size entries per call, i.e. size*size
        # for the whole listing; an index keeps this at O(size).
        assert root.scanned < 4 * size, (
            f"resolving {size} children visited {root.scanned} entries "
            f"({root.scanned / size:.1f} per child); a per-child scan "
            f"would visit {size * size}"
        )

    @pytest.mark.asyncio
    async def test_cost_per_child_does_not_grow_with_directory_width(
        self, counter, client_for
    ):
        """Quadrupling the width must not increase the cost per child."""
        small_size = 50
        large_size = 200

        small_client, _bot, _repo = await client_for(small_size)
        small_root = instrumented_root(small_client)
        Folder("/", small_client)
        small_root.reset()
        await resolve_all_children(small_client, small_size)
        small_per_child = small_root.scanned / small_size
        counter.reset()

        large_client, _bot, _repo = await client_for(large_size)
        large_root = instrumented_root(large_client)
        Folder("/", large_client)
        large_root.reset()
        await resolve_all_children(large_client, large_size)
        large_per_child = large_root.scanned / large_size

        assert large_per_child <= small_per_child + 2, (
            f"resolving visited {large_per_child:.1f} entries per child at "
            f"{large_size} children vs {small_per_child:.1f} at {small_size}: "
            f"lookups still scale with directory width"
        )


class TestListingStillResolvesEveryChild:
    """The optimisation must not drop entries or serve stale ones."""

    @pytest.mark.asyncio
    async def test_every_child_is_resolved(self, counter, client_for):
        size = 50
        client, _bot, _repo = await client_for(size)

        members = await resolve_all_children(client, size)

        assert all(member is not None for member in members)
        assert len(members) == size

    @pytest.mark.asyncio
    async def test_a_child_added_after_a_listing_is_visible(self, counter, client_for):
        """The fast lookup path must not serve a stale snapshot."""
        size = 10
        client, _bot, _repo = await client_for(size)
        await resolve_all_children(client, size)

        root = client.dir_api.root
        root.files.append(
            TGFSFileRef(message_id=9_999_999, name="late.txt", location=root)
        )

        # A fresh Folder snapshots the directory, so this covers the lookup
        # performed while building it as well as `member`.
        assert await Folder("/", client).member("late.txt") is not None
