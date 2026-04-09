import math
from datetime import datetime, timedelta


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _parse_ts(ts) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None
    return None


def detect_fraud(transaction: dict, user) -> tuple[str, dict]:
    """
    Returns (fraud_flag, features).
    Detection uses the transaction as-stored, plus user history/state.
    """
    flag = "none"
    features: dict = {}

    amount = transaction.get("amount")
    if isinstance(amount, (int, float)):
        threshold = max(500.0, user.avg_spending * 5)
        features["amount"] = amount
        features["high_amount_threshold"] = threshold
        if amount > threshold:
            flag = "high_amount"

    txn_ts = _parse_ts(transaction.get("timestamp"))
    if txn_ts and user.last_timestamp:
        hours = abs((txn_ts - user.last_timestamp).total_seconds()) / 3600.0
        features["hours_since_last_txn"] = hours
        if hours < (1 / 60):  # < 1 minute
            flag = "rapid_fire"

    if txn_ts:
        lat = transaction.get("latitude")
        lon = transaction.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if user.last_timestamp:
                ref_lat, ref_lon = user.last_lat, user.last_lon
                ref_ts = user.last_timestamp
            else:
                # No history (e.g. stateless Lambda): assume customer was home 1h ago.
                ref_lat, ref_lon = user.home_lat, user.home_lon
                ref_ts = txn_ts - timedelta(hours=1)
            distance_km = _haversine_km(ref_lat, ref_lon, lat, lon)
            hours = abs((txn_ts - ref_ts).total_seconds()) / 3600.0
            speed_kmh = distance_km / max(hours, 0.01)
            features["distance_km"] = distance_km
            features["speed_kmh"] = speed_kmh
            if speed_kmh > 600:
                flag = "impossible_travel"

    device_id = transaction.get("device_id")
    if isinstance(device_id, str) and device_id not in user.known_devices:
        features["is_new_device"] = True
        flag = "new_device"
    else:
        features["is_new_device"] = False

    return flag, features


def update_user_state(transaction: dict, user) -> None:
    """
    Updates user history after processing a stored transaction.
    """
    ts = _parse_ts(transaction.get("timestamp")) or datetime.now()
    lat = transaction.get("latitude")
    lon = transaction.get("longitude")
    if isinstance(lat, (int, float)):
        user.last_lat = lat
    if isinstance(lon, (int, float)):
        user.last_lon = lon
    user.last_timestamp = ts

    device_id = transaction.get("device_id")
    if isinstance(device_id, str):
        user.known_devices.add(device_id)

