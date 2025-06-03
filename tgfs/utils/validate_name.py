from tgfs.errors.path import InvalidName


def validate_name(name: str) -> None:
    if name[0] == "-" or "/" in name:
        raise InvalidName(name)
