import os


def generate_file_id():
    return int.from_bytes(os.urandom(8), "big")
