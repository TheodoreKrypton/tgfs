import datetime

from tgfs.errors.path import InvalidName

FIRST_DAY_OF_EPOCH = datetime.datetime(
    1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
)


def validate_name(name: str) -> None:
    if name[0] == "-" or "/" in name:
        raise InvalidName(name)


def ts(dt: datetime.datetime) -> int:
    return int(dt.timestamp() * 1000)
