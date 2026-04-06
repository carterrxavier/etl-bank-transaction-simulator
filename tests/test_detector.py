from datetime import datetime, timedelta

import pytest

from app.detector import detect_fraud, update_user_state
from app.models import User


def test_detect_high_amount():
    user = User(1)
    user.avg_spending = 50.0
    flag, features = detect_fraud({"amount": 600.0}, user)
    assert flag == "high_amount"
    assert features["amount"] == 600.0
    assert features["high_amount_threshold"] == 500.0


def test_detect_rapid_fire():
    user = User(1)
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    user.last_timestamp = t0
    txn = {
        "amount": 10.0,
        "latitude": user.home_lat,
        "longitude": user.home_lon,
        "device_id": user.device_id,
        "timestamp": (t0 + timedelta(seconds=30)).isoformat(),
    }
    flag, features = detect_fraud(txn, user)
    assert flag == "rapid_fire"
    assert features["hours_since_last_txn"] == pytest.approx(30 / 3600.0)


def test_detect_impossible_travel():
    user = User(1)
    user.last_lat = 0.0
    user.last_lon = 0.0
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    user.last_timestamp = t0
    txn = {
        "amount": 10.0,
        "latitude": 0.0,
        "longitude": 10.0,
        "device_id": user.device_id,
        "timestamp": (t0 + timedelta(hours=1)).isoformat(),
    }
    flag, features = detect_fraud(txn, user)
    assert flag == "impossible_travel"
    assert features["speed_kmh"] > 600


def test_detect_new_device():
    user = User(1)
    flag, features = detect_fraud({"amount": 10.0, "device_id": "unknown-device"}, user)
    assert flag == "new_device"
    assert features["is_new_device"] is True


def test_update_user_state():
    user = User(1)
    ts = datetime(2024, 6, 1, 10, 0, 0)
    update_user_state(
        {
            "timestamp": ts.isoformat(),
            "latitude": 12.5,
            "longitude": -45.0,
            "device_id": "new-phone",
        },
        user,
    )
    assert user.last_lat == 12.5
    assert user.last_lon == -45.0
    assert user.last_timestamp == ts
    assert "new-phone" in user.known_devices
