from pathlib import Path


def get_file_payload(path: str) -> str:
    return Path("data/" + path).read_text()