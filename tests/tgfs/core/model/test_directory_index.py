"""Regression coverage for the wide-directory listing bottleneck.

Listing a directory with N children through WebDAV resolves every child by
name (``Folder.member`` -> ``Ops.stat_file`` -> ``DirectoryApi.get_fr`` ->
``TGFSDirectory.find_files([name])``).  A linear scan over ``self.files``
makes that N lookups x N entries = O(N^2) entries visited, which is what made
wide directories unusable.

These tests pin the required *complexity*, not just the result: the number of
entries a lookup has to visit must stay proportional to the number of names
asked for, not to the width of the directory.  They also pin that whatever
makes lookups fast cannot go stale, because a fast-but-wrong cache is worse
than a slow scan.

The work is measured with ``CountingList``, a drop-in ``list`` that records
how many of its entries a caller actually pulled out of it.  That is a
black-box measure: it is independent of how the lookup is implemented, and
any implementation that visits fewer entries is genuinely doing less work.
"""

import pytest

from tgfs.core.model.directory import TGFSDirectory, TGFSFileRef
from tgfs.errors import FileOrDirectoryDoesNotExist


class CountingList(list):
    """A ``list`` that records how many entries callers iterate over.

    ``scanned`` counts entries actually yielded since the last ``reset``.
    One full pass over a directory of N entries costs N; an indexed lookup
    costs a small constant no matter how wide the directory is.
    """

    def __init__(self, iterable=()) -> None:
        super().__init__(iterable)
        self.scanned = 0

    def __iter__(self):
        for item in super().__iter__():
            self.scanned += 1
            yield item

    def reset(self) -> None:
        self.scanned = 0


def build_wide_dir(size: int) -> TGFSDirectory:
    """A directory of `size` files whose entry list counts what is visited."""
    root = TGFSDirectory.root_dir()
    root.files = CountingList(
        TGFSFileRef(message_id=1_000 + i, name=f"child-{i:05d}.txt", location=root)
        for i in range(size)
    )
    return root


def build_wide_subdirs(size: int) -> TGFSDirectory:
    root = TGFSDirectory.root_dir()
    root.children = CountingList(
        TGFSDirectory(name=f"dir-{i:05d}", parent=root) for i in range(size)
    )
    return root


class TestFindFilesIsSublinearInDirectoryWidth:
    """The core complexity contract: lookups must not depend on directory width."""

    def test_named_lookup_does_not_visit_every_entry(self):
        size = 5_000
        root = build_wide_dir(size)

        # Warm the structure up first: building an internal index on first
        # use is allowed, repeating that build on every lookup is not.
        assert root.find_files(["child-00000.txt"])
        root.files.reset()

        found = root.find_files(["child-04999.txt"])

        assert [f.name for f in found] == ["child-04999.txt"]
        assert root.files.scanned < size // 100, (
            f"resolving one name in a {size}-entry directory visited "
            f"{root.files.scanned} entries; expected a constant-time lookup, "
            f"not a linear scan"
        )

    def test_a_wider_directory_costs_the_same_per_lookup(self):
        """Doubling the width must not increase the per-lookup cost.

        This is the direct O(N^2) -> O(N) assertion.  A linear scan makes the
        entries-visited-per-lookup grow with the directory width; an index
        keeps it flat.
        """
        small = build_wide_dir(2_000)
        large = build_wide_dir(16_000)

        assert small.find_files(["child-00001.txt"])
        assert large.find_files(["child-00001.txt"])
        small.files.reset()
        large.files.reset()

        assert small.find_files(["child-00001.txt"])
        assert large.find_files(["child-00001.txt"])

        assert large.files.scanned <= small.files.scanned + 1, (
            f"an 8x wider directory visited {large.files.scanned} entries per "
            f"lookup vs {small.files.scanned} for the narrow one, so lookups "
            f"still scale with directory width"
        )

    def test_resolving_every_child_stays_linear(self):
        """The hot path: resolving each child of a wide directory, in order.

        This is exactly what a depth-1 PROPFIND does.  A linear scan makes it
        N*N entries visited, which is the reported production bottleneck.
        """
        size = 2_000
        root = build_wide_dir(size)

        assert root.find_files(["child-00000.txt"])
        root.files.reset()

        for i in range(size):
            assert root.find_files([f"child-{i:05d}.txt"])

        assert root.files.scanned < 10 * size, (
            f"resolving all {size} children visited {root.files.scanned} entries "
            f"({root.files.scanned / size:.1f} per lookup); a per-lookup linear "
            f"scan costs {size} each, i.e. {size * size} total"
        )

    def test_multi_name_lookup_is_not_quadratic_either(self):
        size = 4_000
        root = build_wide_dir(size)
        names = [f"child-{i:05d}.txt" for i in range(0, size, 400)]

        assert root.find_files(names[:1])
        root.files.reset()

        found = root.find_files(names)

        assert [f.name for f in found] == names
        assert root.files.scanned < 10 * len(names), (
            f"looking up {len(names)} names visited {root.files.scanned} entries"
        )


class TestIndexOfChildDirectories:
    """Directory lookups ride the same path and get the same treatment."""

    def test_named_dir_lookup_does_not_visit_every_entry(self):
        size = 5_000
        root = build_wide_subdirs(size)

        assert root.find_dirs(["dir-00000"])
        root.children.reset()

        found = root.find_dirs(["dir-04999"])

        assert [d.name for d in found] == ["dir-04999"]
        assert root.children.scanned < size // 100, (
            f"resolving one directory name in a {size}-entry directory visited "
            f"{root.children.scanned} entries"
        )

    def test_resolving_every_child_dir_stays_linear(self):
        size = 2_000
        root = build_wide_subdirs(size)

        assert root.find_dirs(["dir-00000"])
        root.children.reset()

        for i in range(size):
            assert root.find_dirs([f"dir-{i:05d}"])

        assert root.children.scanned < 10 * size, (
            f"resolving all {size} child directories visited "
            f"{root.children.scanned} entries"
        )


class TestIndexStaysCorrectAfterMutation:
    """A cached index is only safe if mutation keeps it honest."""

    def test_file_added_after_first_lookup_is_findable(self):
        root = TGFSDirectory.root_dir()
        first = root.create_file_ref("first.txt", 1)
        assert root.find_files(["first.txt"]) == [first]

        second = root.create_file_ref("second.txt", 2)

        assert root.find_files(["second.txt"]) == [second]

    def test_file_added_after_a_failed_lookup_is_findable(self):
        root = TGFSDirectory.root_dir()

        assert root.find_files(["later.txt"]) == []
        later = root.create_file_ref("later.txt", 1)

        assert root.find_files(["later.txt"]) == [later]

    def test_removed_file_is_no_longer_returned(self):
        root = TGFSDirectory.root_dir()
        victim = root.create_file_ref("victim.txt", 1)
        root.create_file_ref("keeper.txt", 2)

        assert root.find_files(["victim.txt"]) == [victim]
        root.delete_file_ref(victim)

        assert root.find_files(["victim.txt"]) == []

    def test_removed_file_does_not_shadow_a_later_duplicate(self):
        """Deleting the indexed entry must not hide an identical remaining one.

        The model tolerates duplicate names (see the GitHub metadata loader).
        Returning nothing for a name that is still present would be a silent
        data-loss bug.
        """
        root = TGFSDirectory.root_dir()
        first = TGFSFileRef(message_id=1, name="dup.txt", location=root)
        second = TGFSFileRef(message_id=2, name="dup.txt", location=root)
        root.files.append(first)
        root.files.append(second)

        assert root.find_files(["dup.txt"]) == [first, second]
        root.delete_file_ref(first)
        assert root.find_files(["dup.txt"]) == [second]

        root.delete_file_ref(second)
        assert root.find_files(["dup.txt"]) == []

    def test_file_ref_delete_keeps_the_index_consistent(self):
        root = TGFSDirectory.root_dir()
        victim = root.create_file_ref("victim.txt", 1)

        assert root.find_files(["victim.txt"]) == [victim]
        victim.delete()

        with pytest.raises(FileOrDirectoryDoesNotExist):
            root.find_file("victim.txt")

    def test_replacement_of_a_removed_file_is_findable(self):
        root = TGFSDirectory.root_dir()
        old = root.create_file_ref("reused.txt", 1)

        assert root.find_files(["reused.txt"]) == [old]
        root.delete_file_ref(old)
        new = root.create_file_ref("reused.txt", 2)

        assert root.find_files(["reused.txt"]) == [new]

    def test_dir_added_after_first_lookup_is_findable(self):
        root = TGFSDirectory.root_dir()
        assert root.find_dirs(["a"]) == []

        root.create_dir("a", None)

        assert [d.name for d in root.find_dirs(["a"])] == ["a"]

    def test_removed_dir_is_no_longer_returned(self):
        root = TGFSDirectory.root_dir()
        child = root.create_dir("child", None)

        assert root.find_dirs(["child"]) == [child]
        child.delete()

        assert root.find_dirs(["child"]) == []

    def test_root_delete_clears_the_index(self):
        root = TGFSDirectory.root_dir()
        root.create_dir("child", None)
        root.create_file_ref("file.txt", 1)

        assert root.find_dirs(["child"])
        assert root.find_files(["file.txt"])

        root.delete()

        assert root.find_dirs(["child"]) == []
        assert root.find_files(["file.txt"]) == []


class TestPreservedSemantics:
    """The optimisation must not change any observable behaviour."""

    def test_empty_names_still_returns_every_entry(self):
        root = TGFSDirectory.root_dir()
        a = root.create_file_ref("a.txt", 1)
        b = root.create_file_ref("b.txt", 2)

        assert root.find_files() == [a, b]
        assert root.find_files([]) == [a, b]

    def test_no_names_argument_returns_the_live_list(self):
        root = TGFSDirectory.root_dir()
        a = root.create_file_ref("a.txt", 1)

        assert root.find_files() is root.files
        assert root.find_files() == [a]

    def test_results_follow_directory_order_not_lookup_order(self):
        root = TGFSDirectory.root_dir()
        a = root.create_file_ref("a.txt", 1)
        b = root.create_file_ref("b.txt", 2)
        c = root.create_file_ref("c.txt", 3)

        assert root.find_files(["c.txt", "a.txt"]) == [a, c]
        assert root.find_files(["b.txt", "c.txt", "a.txt"]) == [a, b, c]

    def test_duplicate_query_names_do_not_duplicate_results(self):
        root = TGFSDirectory.root_dir()
        a = root.create_file_ref("a.txt", 1)

        assert root.find_files(["a.txt", "a.txt"]) == [a]

    def test_unknown_names_return_nothing(self):
        root = TGFSDirectory.root_dir()
        a = root.create_file_ref("a.txt", 1)

        assert root.find_files(["missing.txt"]) == []
        assert root.find_files(["a.txt", "missing.txt"]) == [a]

    def test_duplicate_entry_names_are_all_returned(self):
        root = TGFSDirectory.root_dir()
        first = TGFSFileRef(message_id=1, name="dup.txt", location=root)
        second = TGFSFileRef(message_id=2, name="dup.txt", location=root)
        root.files.append(first)
        root.files.append(second)

        assert root.find_files(["dup.txt"]) == [first, second]

    def test_find_file_returns_the_first_match(self):
        root = TGFSDirectory.root_dir()
        first = TGFSFileRef(message_id=1, name="dup.txt", location=root)
        second = TGFSFileRef(message_id=2, name="dup.txt", location=root)
        root.files.append(first)
        root.files.append(second)

        assert root.find_file("dup.txt") is first

    def test_non_string_names_do_not_crash_the_lookup(self):
        """Lookups are not always fed clean strings by every caller."""
        root = TGFSDirectory.root_dir()
        root.create_file_ref("a.txt", 1)

        assert root.find_files([1]) == []

    def test_directories_and_files_are_indexed_independently(self):
        root = TGFSDirectory.root_dir()
        root.create_file_ref("shared", 1)
        root.create_dir("shared", None)

        assert len(root.find_files(["shared"])) == 1
        assert len(root.find_dirs(["shared"])) == 1
