import json
import os
import uuid
from pathlib import Path
from typing import Optional


class LocalObjectStore:
    """
    Tiny local stand-in for S3.

    - put(): writes JSON to disk and returns an object key
    - get(): reads JSON back from disk
    """

    def __init__(self, root_dir: str = ".local_s3"):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, obj: dict, key: Optional[str] = None, prefix: str = "") -> str:
        """
        - If `key` is provided, writes to that relative path (S3-like key).
        - Otherwise generates a UUID filename, optionally under `prefix/`.
        """
        if key is None:
            filename = f"{uuid.uuid4()}.json"
            key = str(Path(prefix) / filename) if prefix else filename

        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj) + "\n", encoding="utf-8")
        return key

    def get(self, key: str) -> dict:
        path = self.root / key
        return json.loads(path.read_text(encoding="utf-8"))


class S3ObjectStore:
    def __init__(self, bucket: str, region: Optional[str] = None):
        import boto3

        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    def put(self, obj: dict, key: str) -> str:
        body = (json.dumps(obj) + "\n").encode("utf-8")
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return key

    def get(self, key: str) -> dict:
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        body = resp["Body"].read().decode("utf-8")
        return json.loads(body)


def _s3_bucket_from_env() -> Optional[str]:
    bucket = os.environ.get("S3_BUCKET") or os.environ.get("AWS_S3_BUCKET")
    return bucket.strip() if isinstance(bucket, str) else None


def store():
    """
    Factory that returns either a local or S3-backed object store.

    - `OBJECT_STORE=local` (default): uses `.local_s3/`
    - `OBJECT_STORE=s3`: uses S3 bucket from `S3_BUCKET` (and optional `AWS_REGION`)
    """
    mode = (os.environ.get("OBJECT_STORE") or "local").strip().lower()
    if mode == "s3":
        bucket = _s3_bucket_from_env()
        if not bucket:
            raise RuntimeError("OBJECT_STORE=s3 requires S3_BUCKET to be set")
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        return S3ObjectStore(bucket=bucket, region=region)

    root = os.environ.get("LOCAL_S3_DIR", ".local_s3")
    return LocalObjectStore(root_dir=root)