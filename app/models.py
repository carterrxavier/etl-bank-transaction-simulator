from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_profiles_by_id: dict[int, dict[str, Any]] | None = None


def _profiles_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "user_profiles.json"


def _load_profiles() -> dict[int, dict[str, Any]]:
    global _profiles_by_id
    if _profiles_by_id is not None:
        return _profiles_by_id
    path = _profiles_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing user profiles: {path}. Run scripts/generate_user_profiles.py"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("user_profiles.json must be a JSON array")
    _profiles_by_id = {}
    for row in raw:
        if not isinstance(row, dict) or "user_id" not in row:
            continue
        _profiles_by_id[int(row["user_id"])] = row
    return _profiles_by_id


def profile_count() -> int:
    return len(_load_profiles())


class User:
    """Synthetic customer; fields come from app/data/user_profiles.json."""

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
