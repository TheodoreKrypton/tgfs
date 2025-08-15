from asgidav.app import split_path, extract_path_from_destination


class TestAppHelpers:
    def test_split_path_root(self):
        parent, name = split_path("/")
        assert parent == "/"
        assert name == ""

    def test_split_path_single_level(self):
        parent, name = split_path("/test")
        assert parent == "/"
        assert name == "test"

    def test_split_path_multiple_levels(self):
        parent, name = split_path("/path/to/file.txt")
        assert parent == "path/to"
        assert name == "file.txt"

    def test_split_path_trailing_slash(self):
        parent, name = split_path("/path/to/folder/")
        assert parent == "path/to"
        assert name == "folder"

    def test_extract_path_from_destination_http(self):
        url = "http://example.com/webdav/path/to/file.txt"
        result = extract_path_from_destination(url)
        assert result == "/webdav/path/to/file.txt"

    def test_extract_path_from_destination_https(self):
        url = "https://example.com/webdav/path/to/file.txt"
        result = extract_path_from_destination(url)
        assert result == "/webdav/path/to/file.txt"

    def test_extract_path_from_destination_path_only(self):
        path = "/webdav/path/to/file.txt"
        result = extract_path_from_destination(path)
        assert result == "/webdav/path/to/file.txt"

    def test_extract_path_from_destination_encoded(self):
        path = "/webdav/path%20with%20spaces/file.txt"
        result = extract_path_from_destination(path)
        assert result == "/webdav/path with spaces/file.txt"
