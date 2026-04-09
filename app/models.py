from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_profiles_by_id: dict[int, dict[str, Any]] | None = None


def _profiles_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "user_profiles.json"


def _profiles_bucket() -> str | None:
    b = (
        os.environ.get("USER_PROFILES_BUCKET")
        or os.environ.get("S3_BUCKET")
        or os.environ.get("AWS_S3_BUCKET")
    )
    if not b or not str(b).strip():
        return None
    return str(b).strip()


def _profiles_s3_key() -> str:
    k = os.environ.get("USER_PROFILES_S3_KEY") or "users/user_profiles.json"
    return str(k).strip().lstrip("/")


def _aws_region() -> str | None:
    r = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return r.strip() if r else None


def _index_raw_profiles(raw: list | object) -> dict[int, dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("user_profiles.json must be a JSON array")
    out: dict[int, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict) or "user_id" not in row:
            continue
        out[int(row["user_id"])] = row
    return out


def _load_profiles_from_local_file() -> dict[int, dict[str, Any]]:
    path = _profiles_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing user profiles: {path}. Set S3 bucket env for auto-load, or run "
            "scripts/generate_user_profiles.py"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _index_raw_profiles(raw)


def _load_or_create_profiles_s3() -> dict[int, dict[str, Any]]:
    import boto3
    from botocore.exceptions import ClientError

    bucket = _profiles_bucket()
    assert bucket  # caller checks
    key = _profiles_s3_key()
    s3 = boto3.client("s3", region_name=_aws_region())

    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        raw = json.loads(resp["Body"].read().decode("utf-8"))
        return _index_raw_profiles(raw)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("NoSuchKey", "404"):
            raise

    count = int(os.environ.get("USER_PROFILES_COUNT", "99999"))
    seed = int(os.environ.get("USER_PROFILES_SEED", "42"))

    from app.user_profiles_dataset import build_profiles

    profiles_list = build_profiles(count, seed)
    body = (json.dumps(profiles_list) + "\n").encode("utf-8")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return _index_raw_profiles(profiles_list)


def _load_profiles() -> dict[int, dict[str, Any]]:
    global _profiles_by_id
    if _profiles_by_id is not None:
        return _profiles_by_id

    if _profiles_bucket():
        _profiles_by_id = _load_or_create_profiles_s3()
    else:
        _profiles_by_id = _load_profiles_from_local_file()
    return _profiles_by_id


def profile_count() -> int:
    return len(_load_profiles())


class User:
    """Synthetic customer; profiles from S3 (``users/…``) or local ``app/data/user_profiles.json``."""

    def __init__(self, user_id: int):
        profiles = _load_profiles()
        uid = int(user_id)
        if uid not in profiles:
            raise KeyError(f"Unknown user_id {uid!r}; valid range 1..{profile_count()}")

        p = profiles[uid]
        self.user_id = uid
        self.full_name = p.get("full_name", "")
        self.date_of_birth = p.get("date_of_birth")
        self.phone = p.get("phone")
        self.email = p.get("email")
        self.address_line1 = p.get("address_line1", "")
        self.address_line2 = p.get("address_line2")
        self.city = p.get("city", "")
        self.state = p.get("state", "")
        self.postal_code = p.get("postal_code", "")
        self.country = p.get("country", "")
        self.customer_since = p.get("customer_since")
        self.segment = p.get("segment", "retail")

        self.home_lat = float(p["home_lat"])
        self.home_lon = float(p["home_lon"])
        self.avg_spending = float(p["avg_spending"])
        self.device_id = str(p["device_id"])
        self.known_devices = {self.device_id}

        self.last_lat = self.home_lat
        self.last_lon = self.home_lon
        self.last_timestamp = None
