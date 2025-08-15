import datetime


class TestTimestamp:
    def test_ts_epoch(self):
        from tgfs.utils.time import ts, FIRST_DAY_OF_EPOCH

        result = ts(FIRST_DAY_OF_EPOCH)
        assert result == 0

    def test_ts_conversion(self):
        from tgfs.utils.time import ts

        dt = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        result = ts(dt)
        expected = int(dt.timestamp() * 1000)
        assert result == expected

    def test_ts_with_microseconds(self):
        from tgfs.utils.time import ts

        dt = datetime.datetime(
            2023, 1, 1, 12, 0, 0, 123000, tzinfo=datetime.timezone.utc
        )
        result = ts(dt)
        expected = int(dt.timestamp() * 1000)
        assert result == expected
