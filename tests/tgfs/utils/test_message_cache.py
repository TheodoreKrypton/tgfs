from tgfs.utils.message_cache import MessageCache


class TestMessageCache:
    def test_init(self):
        cache = MessageCache[str, int]()
        assert cache._lru.get_size() == 1024

    def test_get_existing_key(self):
        cache = MessageCache[str, int]()
        cache["key1"] = 100

        result = cache.get("key1")
        assert result == 100

    def test_get_nonexistent_key(self):
        cache = MessageCache[str, int]()

        result = cache.get("nonexistent")
        assert result is None

    def test_setitem_and_getitem(self):
        cache = MessageCache[str, int]()
        cache["test_key"] = 42

        assert cache["test_key"] == 42

    def test_contains(self):
        cache = MessageCache[str, int]()
        cache["exists"] = 1

        assert "exists" in cache
        assert "not_exists" not in cache

    def test_gets_multiple_keys(self):
        cache = MessageCache[str, int]()
        cache["a"] = 1
        cache["c"] = 3

        result = cache.gets(["a", "b", "c"])
        assert result == [1, None, 3]

    def test_gets_empty_list(self):
        cache = MessageCache[str, int]()

        result = cache.gets([])
        assert result == []

    def test_find_nonexistent(self):
        cache = MessageCache[str, int]()
        cache["exists1"] = 10
        cache["exists2"] = 20

        result = cache.find_nonexistent(["exists1", "missing1", "exists2", "missing2"])
        assert result == ["missing1", "missing2"]

    def test_find_nonexistent_all_exist(self):
        cache = MessageCache[str, int]()
        cache["a"] = 1
        cache["b"] = 2

        result = cache.find_nonexistent(["a", "b"])
        assert result == []

    def test_find_nonexistent_none_exist(self):
        cache = MessageCache[str, int]()

        result = cache.find_nonexistent(["missing1", "missing2"])
        assert result == ["missing1", "missing2"]

    def test_lru_behavior(self):
        cache = MessageCache[int, str]()

        # Fill cache beyond capacity would require more complex testing
        # For now, just verify basic functionality works
        for i in range(10):
            cache[i] = f"value_{i}"

        for i in range(10):
            assert cache[i] == f"value_{i}"
