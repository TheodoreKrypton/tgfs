import datetime


FIRST_DAY_OF_EPOCH = datetime.datetime(
    1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
)


def ts(dt: datetime.datetime) -> int:
    return int(dt.timestamp() * 1000)
