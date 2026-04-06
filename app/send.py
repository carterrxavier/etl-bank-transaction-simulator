import json
import os
import uuid
from pathlib import Path


class LocalObjectStore:
    """
    Tiny local stand-in for S3.

    - put(): writes JSON to disk and returns an object key
    - get(): reads JSON back from disk
    """

    def __init__(self, root_dir: str = ".local_s3"):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, obj: dict, prefix: str = "") -> str:
        key = f"{uuid.uuid4()}.json"
        path = self.root / prefix / key if prefix else (self.root / key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj) + "\n", encoding="utf-8")
        return str(Path(prefix) / key) if prefix else key

    def get(self, key: str) -> dict:
        path = self.root / key
        return json.loads(path.read_text(encoding="utf-8"))


def store() -> LocalObjectStore:
    root = os.environ.get("LOCAL_S3_DIR", ".local_s3")
    return LocalObjectStore(root_dir=root)

