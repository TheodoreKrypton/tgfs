from typing import List

from tgfs.utils.others import exclude_none, is_big_file


class TestOthers:
    def test_exclude_none_with_none_values(self):
        result = list(exclude_none([1, None, 2, None, 3]))
        assert result == [1, 2, 3]

    def test_exclude_none_with_no_none_values(self):
        result = list(exclude_none([1, 2, 3]))
        assert result == [1, 2, 3]

    def test_exclude_none_with_all_none_values(self):
        result: List = list(exclude_none([None, None, None]))
        assert result == []

    def test_exclude_none_with_empty_list(self):
        result: List = list(exclude_none([]))
        assert result == []

    def test_is_big_file_small_file(self):
        assert is_big_file(1024) is False
        assert is_big_file(10 * 1024 * 1024 - 1) is False

    def test_is_big_file_big_file(self):
        assert is_big_file(10 * 1024 * 1024) is False
        assert is_big_file(10 * 1024 * 1024 + 1) is True
        assert is_big_file(50 * 1024 * 1024) is True

    def test_is_big_file_edge_case(self):
        assert is_big_file(0) is False
        assert is_big_file(-1) is False