from tgfs.app.webdav.cache import FSCache


class TestFSCache:
    def test_split_path(self):
        assert FSCache.split_path("/") == [""]
        assert FSCache.split_path("/test/") == ["", "test"]

    def test_get_set(self, mocker):
        cache = FSCache()

        cache.set("/", mocker.Mock(path="/"))
        value = cache.get("/")
        assert value and value.path == "/"

        value = cache.get("/test")
        assert value is None

        cache.set("/test", mocker.Mock(path="/test"))
        value = cache.get("/test")
        assert value and value.path == "/test"

    def test_reset(self, mocker):
        cache = FSCache()

        cache.set("/", mocker.Mock(path="/"))
        cache.set("/test", mocker.Mock(path="/test"))
        cache.set("/test/child", mocker.Mock(path="/test/child"))

        cache.reset("/test")
        assert cache.get("/") is not None
        assert cache.get("/test") is None
        assert cache.get("/test/child") is None

    def test_reset_parent(self, mocker):
        cache = FSCache()

        cache.set("/", mocker.Mock(path="/"))
        cache.set("/test", mocker.Mock(path="/test"))
        cache.set("/test/child", mocker.Mock(path="/test/child"))

        cache.reset_parent("/test/child")
        assert cache.get("/") is not None
        assert cache.get("/test") is None
        assert cache.get("/test/child") is None
