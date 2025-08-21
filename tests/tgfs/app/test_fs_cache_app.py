from typing import Optional
from tgfs.app.fs_cache import FSCache, gfc
from asgidav.member import Member


class MockMember(Member):
    """Mock implementation for testing"""

    def __init__(self, path: str, name: Optional[str] = None):
        super().__init__(path)
        self.name = name or path.split("/")[-1] if path != "/" else "root"

    def __str__(self):
        return f"MockMember({self.path})"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, MockMember):
            return self.path == other.path and self.name == other.name
        return False

    async def content_type(self) -> str:
        return "application/octet-stream"

    async def content_length(self) -> int:
        return 0

    async def display_name(self) -> str:
        return self.name

    async def creation_date(self) -> int:
        return 1640995200000  # 2022-01-01

    async def last_modified(self) -> int:
        return 1640995200000  # 2022-01-01

    async def remove(self) -> None:
        pass

    async def copy_to(self, destination: str) -> None:
        pass

    async def move_to(self, destination: str) -> None:
        pass


class TestFSCache:
    """Test suite for FSCache class"""

    def test_init_default(self):
        """Test FSCache initialization with default value"""
        cache = FSCache()
        assert cache._value is None
        assert isinstance(cache._cache, dict)

    def test_init_with_value(self):
        """Test FSCache initialization with a value"""
        member = MockMember("/test", "test_file")
        cache = FSCache(member)
        assert cache._value == member
        assert isinstance(cache._cache, dict)

    def test_split_path_root(self):
        """Test path splitting for root path"""
        assert FSCache.split_path("/") == [""]
        assert FSCache.split_path("") == [""]
        # Note: whitespace is preserved and creates separate path parts
        assert FSCache.split_path("  /  ") == ["", "  ", "  "]

    def test_split_path_single_level(self):
        """Test path splitting for single level paths"""
        assert FSCache.split_path("/test") == ["", "test"]
        assert FSCache.split_path("test") == ["", "test"]
        assert FSCache.split_path("/test/") == ["", "test"]
        # Whitespace creates additional path parts
        assert FSCache.split_path("  /test/  ") == ["", "  ", "test", "  "]

    def test_split_path_multi_level(self):
        """Test path splitting for multi-level paths"""
        assert FSCache.split_path("/test/file") == ["", "test", "file"]
        assert FSCache.split_path("/test/sub/file.txt") == [
            "",
            "test",
            "sub",
            "file.txt",
        ]
        assert FSCache.split_path("test/sub/file.txt") == [
            "",
            "test",
            "sub",
            "file.txt",
        ]
        assert FSCache.split_path("/test/sub/file.txt/") == [
            "",
            "test",
            "sub",
            "file.txt",
        ]

    def test_split_path_special_characters(self):
        """Test path splitting with special characters"""
        assert FSCache.split_path("/test-file_name.txt") == ["", "test-file_name.txt"]
        assert FSCache.split_path("/test/file with spaces") == [
            "",
            "test",
            "file with spaces",
        ]
        assert FSCache.split_path("/test/file@domain.com") == [
            "",
            "test",
            "file@domain.com",
        ]


class TestCacheOperations:
    """Test suite for cache operations"""

    def test_set_and_get_root(self):
        """Test setting and getting value at root"""
        cache = FSCache()
        member = MockMember("/", "root")

        cache.set("/", member)
        result = cache.get("/")

        assert result == member

    def test_set_and_get_single_level(self):
        """Test setting and getting single level path"""
        cache = FSCache()
        member = MockMember("/test", "test_file")

        cache.set("/test", member)
        result = cache.get("/test")

        assert result == member

    def test_set_and_get_multi_level(self):
        """Test setting and getting multi-level path"""
        cache = FSCache()
        member = MockMember("/test/sub/file.txt", "file.txt")

        cache.set("/test/sub/file.txt", member)
        result = cache.get("/test/sub/file.txt")

        assert result == member

    def test_get_nonexistent_path(self):
        """Test getting a non-existent path returns None"""
        cache = FSCache()
        result = cache.get("/nonexistent")
        assert result is None

    def test_get_partial_path(self):
        """Test getting a partial path that exists but has no value"""
        cache = FSCache()
        member = MockMember("/test/file.txt", "file.txt")

        cache.set("/test/file.txt", member)

        # The intermediate path "/test" should exist but have no value
        result = cache.get("/test")
        assert result is None

    def test_overwrite_existing_value(self):
        """Test overwriting an existing value"""
        cache = FSCache()
        member1 = MockMember("/test", "original")
        member2 = MockMember("/test", "updated")

        cache.set("/test", member1)
        assert cache.get("/test") == member1

        cache.set("/test", member2)
        assert cache.get("/test") == member2

    def test_set_none_value(self):
        """Test setting None value"""
        cache = FSCache()
        cache.set("/test", None)
        result = cache.get("/test")
        assert result is None


class TestResetOperations:
    """Test suite for reset operations"""

    def test_reset_single_path(self):
        """Test resetting a single path"""
        cache = FSCache()
        member = MockMember("/test", "test_file")

        cache.set("/test", member)
        assert cache.get("/test") == member

        cache.reset("/test")
        assert cache.get("/test") is None

    def test_reset_multi_level_path(self):
        """Test resetting a multi-level path"""
        cache = FSCache()
        member = MockMember("/test/sub/file.txt", "file.txt")

        cache.set("/test/sub/file.txt", member)
        assert cache.get("/test/sub/file.txt") == member

        cache.reset("/test/sub/file.txt")
        assert cache.get("/test/sub/file.txt") is None

    def test_reset_affects_children(self):
        """Test that reset affects child paths"""
        cache = FSCache()
        member1 = MockMember("/test/file1.txt", "file1")
        member2 = MockMember("/test/file2.txt", "file2")

        cache.set("/test/file1.txt", member1)
        cache.set("/test/file2.txt", member2)

        cache.reset("/test")

        # Children should no longer be accessible
        assert cache.get("/test/file1.txt") is None
        assert cache.get("/test/file2.txt") is None

    def test_reset_nonexistent_path(self):
        """Test resetting a non-existent path doesn't cause errors"""
        cache = FSCache()
        cache.reset("/nonexistent")  # Should not raise exception

    def test_reset_parent_basic(self):
        """Test basic reset_parent functionality"""
        cache = FSCache()
        parent_member = MockMember("/test", "parent")
        child_member = MockMember("/test/child", "child")

        cache.set("/test", parent_member)
        cache.set("/test/child", child_member)

        cache.reset_parent("/test/child")

        # Parent should be reset, but root should remain
        assert cache.get("/test") is None
        assert cache.get("/test/child") is None

    def test_reset_parent_multi_level(self):
        """Test reset_parent with multi-level hierarchy"""
        cache = FSCache()
        cache.set("/", MockMember("/", "root"))
        cache.set("/test", MockMember("/test", "test"))
        cache.set("/test/sub", MockMember("/test/sub", "sub"))
        cache.set("/test/sub/file", MockMember("/test/sub/file", "file"))

        cache.reset_parent("/test/sub/file")

        # Only /test/sub should be reset
        assert cache.get("/") is not None
        assert cache.get("/test") is not None
        assert cache.get("/test/sub") is None
        assert cache.get("/test/sub/file") is None

    def test_reset_parent_root_child(self):
        """Test reset_parent for direct root children"""
        cache = FSCache()
        cache.set("/", MockMember("/", "root"))
        cache.set("/test", MockMember("/test", "test"))

        cache.reset_parent("/test")

        # Root should be reset
        assert cache.get("/") is None
        assert cache.get("/test") is None


class TestEdgeCases:
    """Test suite for edge cases"""

    def test_empty_string_path(self):
        """Test handling of empty string path"""
        cache = FSCache()
        member = MockMember("", "empty")

        cache.set("", member)
        result = cache.get("")

        assert result == member

    def test_whitespace_only_paths(self):
        """Test handling of whitespace-only paths"""
        cache = FSCache()
        member = MockMember("  ", "whitespace")

        cache.set("  ", member)
        result = cache.get("  ")

        assert result == member

    def test_consecutive_slashes(self):
        """Test handling of paths with consecutive slashes"""
        cache = FSCache()
        member = MockMember("/test//file", "file")

        # The split_path method normalizes these
        cache.set("/test//file", member)
        result = cache.get("/test//file")

        assert result == member

    def test_path_variations_equivalent(self):
        """Test that some path variations are treated equivalently"""
        cache = FSCache()
        member = MockMember("/test", "test")

        cache.set("/test", member)

        # These should all refer to the same location due to path normalization
        assert cache.get("/test") == member
        assert cache.get("test") == member  # Both become ['', 'test']
        assert cache.get("/test/") == member  # Trailing slash is stripped
        # Note: whitespace creates different path structure
        # cache.get("  /test/  ") would be ['', '  ', 'test', '  '] != ['', 'test']
        assert cache.get("  /test/  ") != member  # Different path due to whitespace

    def test_recursive_path_creation(self):
        """Test that intermediate paths are created automatically"""
        cache = FSCache()
        member = MockMember("/a/b/c/d/e", "deep_file")

        cache.set("/a/b/c/d/e", member)

        # The deep path should be accessible
        assert cache.get("/a/b/c/d/e") == member

        # Intermediate paths should exist but have no value
        assert cache.get("/a") is None
        assert cache.get("/a/b") is None
        assert cache.get("/a/b/c") is None
        assert cache.get("/a/b/c/d") is None

    def test_cache_isolation(self):
        """Test that different cache instances are isolated"""
        cache1 = FSCache()
        cache2 = FSCache()

        member1 = MockMember("/test", "cache1")
        member2 = MockMember("/test", "cache2")

        cache1.set("/test", member1)
        cache2.set("/test", member2)

        assert cache1.get("/test") == member1
        assert cache2.get("/test") == member2


class TestGlobalCache:
    """Test suite for global cache dictionary"""

    def test_global_cache_exists(self):
        """Test that global cache dictionary exists"""
        assert isinstance(gfc, dict)

    def test_global_cache_initially_empty(self):
        """Test that global cache starts empty"""
        # Clear any existing state
        gfc.clear()
        assert len(gfc) == 0

    def test_global_cache_can_store_caches(self):
        """Test that global cache can store FSCache instances"""
        gfc.clear()

        cache = FSCache()
        gfc["test_key"] = cache

        assert "test_key" in gfc
        assert gfc["test_key"] == cache

    def test_global_cache_multiple_entries(self):
        """Test global cache with multiple entries"""
        gfc.clear()

        cache1 = FSCache()
        cache2 = FSCache()

        gfc["cache1"] = cache1
        gfc["cache2"] = cache2

        assert len(gfc) == 2
        assert gfc["cache1"] == cache1
        assert gfc["cache2"] == cache2


class TestIntegrationScenarios:
    """Integration tests combining multiple operations"""

    def test_complex_file_system_simulation(self):
        """Test a complex file system simulation"""
        cache = FSCache()

        # Create a file system structure
        cache.set("/", MockMember("/", "root"))
        cache.set("/docs", MockMember("/docs", "docs"))
        cache.set("/docs/readme.txt", MockMember("/docs/readme.txt", "readme.txt"))
        cache.set("/docs/manual.pdf", MockMember("/docs/manual.pdf", "manual.pdf"))
        cache.set("/src", MockMember("/src", "src"))
        cache.set("/src/main.py", MockMember("/src/main.py", "main.py"))
        cache.set("/src/utils", MockMember("/src/utils", "utils"))
        cache.set(
            "/src/utils/helper.py", MockMember("/src/utils/helper.py", "helper.py")
        )

        # Test retrieval
        root_member = cache.get("/")
        assert isinstance(root_member, MockMember) and root_member.name == "root"

        readme_member = cache.get("/docs/readme.txt")
        assert (
            isinstance(readme_member, MockMember) and readme_member.name == "readme.txt"
        )

        helper_member = cache.get("/src/utils/helper.py")
        assert (
            isinstance(helper_member, MockMember) and helper_member.name == "helper.py"
        )

        # Test reset operations
        cache.reset("/docs")
        assert cache.get("/docs") is None
        assert cache.get("/docs/readme.txt") is None
        assert cache.get("/docs/manual.pdf") is None

        # Other paths should remain
        assert cache.get("/") is not None
        assert cache.get("/src") is not None
        assert cache.get("/src/utils/helper.py") is not None

    def test_cache_update_workflow(self):
        """Test a typical cache update workflow"""
        cache = FSCache()

        # Initial setup
        original_file = MockMember("/test/file.txt", "original")
        cache.set("/test/file.txt", original_file)

        # Verify initial state
        assert cache.get("/test/file.txt") == original_file

        # Update the file
        updated_file = MockMember("/test/file.txt", "updated")
        cache.set("/test/file.txt", updated_file)

        # Verify update
        assert cache.get("/test/file.txt") == updated_file

        # Reset parent (simulating directory invalidation)
        cache.reset_parent("/test/file.txt")

        # Both parent and file should be gone
        assert cache.get("/test") is None
        assert cache.get("/test/file.txt") is None

    def test_concurrent_path_access(self):
        """Test concurrent access to overlapping paths"""
        cache = FSCache()

        # Set up overlapping paths
        cache.set("/test", MockMember("/test", "test_dir"))
        cache.set("/test/file1", MockMember("/test/file1", "file1"))
        cache.set("/test/file2", MockMember("/test/file2", "file2"))
        cache.set("/test/subdir", MockMember("/test/subdir", "subdir"))
        cache.set("/test/subdir/file3", MockMember("/test/subdir/file3", "file3"))

        # Verify all paths are accessible
        test_member = cache.get("/test")
        assert isinstance(test_member, MockMember) and test_member.name == "test_dir"

        file1_member = cache.get("/test/file1")
        assert isinstance(file1_member, MockMember) and file1_member.name == "file1"

        file2_member = cache.get("/test/file2")
        assert isinstance(file2_member, MockMember) and file2_member.name == "file2"

        subdir_member = cache.get("/test/subdir")
        assert isinstance(subdir_member, MockMember) and subdir_member.name == "subdir"

        file3_member = cache.get("/test/subdir/file3")
        assert isinstance(file3_member, MockMember) and file3_member.name == "file3"

        # Reset a sub-path and verify isolation
        cache.reset("/test/subdir")

        # Subdir and its children should be gone
        assert cache.get("/test/subdir") is None
        assert cache.get("/test/subdir/file3") is None

        # Other paths should remain
        remaining_test_member = cache.get("/test")
        assert (
            isinstance(remaining_test_member, MockMember)
            and remaining_test_member.name == "test_dir"
        )

        remaining_file1_member = cache.get("/test/file1")
        assert (
            isinstance(remaining_file1_member, MockMember)
            and remaining_file1_member.name == "file1"
        )

        remaining_file2_member = cache.get("/test/file2")
        assert (
            isinstance(remaining_file2_member, MockMember)
            and remaining_file2_member.name == "file2"
        )
