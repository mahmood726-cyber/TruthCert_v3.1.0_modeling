import hashlib
from pathlib import Path
from typing import Iterable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def hash_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def hash_doc_list(doc_hashes: Iterable[str]) -> str:
    joined = "".join(list(doc_hashes))
    return sha256_text(joined)
