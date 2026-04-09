import random
from datetime import datetime, timezone

from app.detector import update_user_state
from app.generator import generate_transaction
from app.injector import inject_anomaly
from app.models import User, profile_count


def _date_prefix(now: datetime) -> str:
    return f"{now:%Y/%m/%d}"


_users_cache: list | None = None


def users_pool(size: int | None = None) -> list:
    """
    Lazily built pool of users backed by app/data/user_profiles.json (ids 1..N).

    If ``size`` is given, returns the first ``min(size, N)`` users (shared instances).
    """
    global _users_cache
    cap = profile_count()
    if _users_cache is None:
        _users_cache = [User(i) for i in range(1, cap + 1)]
    if size is None:
        return _users_cache
    n = max(1, min(int(size), cap))
    return _users_cache[:n]


def emit_transaction_to_store(obj_store, users: list | None = None) -> dict:
    """
    Generate one transaction, optionally inject a simulated anomaly, write to object store.

    Returns metadata including the storage key (S3 key or local path).
    """
    pool = users if users is not None else users_pool()
    user = random.choice(pool)
    txn = generate_transaction(user)
    txn, _ = inject_anomaly(txn, user)
    update_user_state(txn, user)

    now = datetime.now(timezone.utc)
    txn_id = txn.get("transaction_id", "unknown")
    key = f"transactions/{_date_prefix(now)}/{txn_id}.json"
    obj_store.put(txn, key=key)

    return {
        "key": key,
        "transaction_id": txn.get("transaction_id"),
        "bucket": getattr(obj_store, "bucket", None),
    }
