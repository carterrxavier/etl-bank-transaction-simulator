from datetime import datetime
from unittest.mock import patch

import pytest

from app.generator import generate_transaction
from app.models import User


def test_generate_transaction_shape():
    user = User(7)
    user.home_lat = 40.0
    user.home_lon = -74.0
    user.avg_spending = 40.0
    with (
        patch("app.generator.random.gauss", return_value=42.0),
        patch("app.generator.random.uniform", side_effect=[0.01, -0.02]),
        patch("app.generator.random.choice", return_value="POS"),
        patch("app.generator.fake.company", return_value="Acme"),
    ):
        txn = generate_transaction(user)
    assert txn["user_id"] == 7
    assert txn["amount"] == 42.0
    assert txn["latitude"] == pytest.approx(40.01)
    assert txn["longitude"] == pytest.approx(-74.02)
    assert txn["device_id"] == user.device_id
    assert txn["transaction_type"] == "POS"
    assert txn["merchant"] == "Acme"
    datetime.fromisoformat(txn["timestamp"])
