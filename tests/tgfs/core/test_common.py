import pytest
import datetime


class TestValidateName:
    def test_validate_name_valid(self):
        from tgfs.core.model.common import validate_name
        validate_name("valid_name")
        validate_name("valid-name123")
        validate_name("ValidName")
        
    def test_validate_name_starts_with_dash(self):
        from tgfs.core.model.common import validate_name
        from tgfs.errors import InvalidName
        with pytest.raises(InvalidName):
            validate_name("-invalid")
            
    def test_validate_name_contains_slash(self):
        from tgfs.core.model.common import validate_name
        from tgfs.errors import InvalidName
        with pytest.raises(InvalidName):
            validate_name("invalid/name")
        with pytest.raises(InvalidName):
            validate_name("path/to/file")


class TestTimestamp:
    def test_ts_epoch(self):
        from tgfs.core.model.common import ts, FIRST_DAY_OF_EPOCH
        result = ts(FIRST_DAY_OF_EPOCH)
        assert result == 0
        
    def test_ts_conversion(self):
        from tgfs.core.model.common import ts
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        result = ts(dt)
        expected = int(dt.timestamp() * 1000)
        assert result == expected
        
    def test_ts_with_microseconds(self):
        from tgfs.core.model.common import ts
        dt = datetime.datetime(2023, 1, 1, 12, 0, 0, 123000, tzinfo=datetime.timezone.utc)
        result = ts(dt)
        expected = int(dt.timestamp() * 1000)
        assert result == expected
