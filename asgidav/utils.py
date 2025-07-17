def calc_content_length(full_length: int, begin: int = 0, end: int = -1) -> int:
    if begin == 0 and end == -1:
        return full_length
    if end == -1 or end >= full_length:
        end = full_length - 1
    return end - begin + 1 if end >= begin else 0
