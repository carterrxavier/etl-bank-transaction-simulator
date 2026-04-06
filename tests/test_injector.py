import app.injector as inj


def test_inject_high_amount(monkeypatch):
    user = type("U", (), {"last_timestamp": None})()
    txn = {"amount": 12.34}
    monkeypatch.setattr(inj.random, "choices", lambda *a, **k: ["high_amount"])
    out, kind = inj.inject_anomaly(txn, user)
    assert kind == "high_amount"
    assert out["amount"] == 123.4
    assert out["sim_anomaly_type"] == "high_amount"


def test_inject_new_device(monkeypatch):
    user = type("U", (), {"last_timestamp": None})()
    txn = {"amount": 1.0, "device_id": "old"}
    fake_uuid = "00000000-0000-0000-0000-000000000001"
    monkeypatch.setattr(inj.random, "choices", lambda *a, **k: ["new_device"])
    monkeypatch.setattr(inj.fake, "uuid4", lambda: fake_uuid)
    out, kind = inj.inject_anomaly(txn, user)
    assert kind == "new_device"
    assert out["device_id"] == fake_uuid


def test_inject_impossible_travel(monkeypatch):
    from datetime import datetime

    user = type("U", (), {"last_timestamp": datetime(2024, 1, 1)})()
    txn = {"amount": 5.0, "latitude": 1.0, "longitude": 1.0}
    monkeypatch.setattr(inj.random, "choices", lambda *a, **k: ["impossible_travel"])
    monkeypatch.setattr(inj.random, "uniform", lambda a, b: (a + b) / 2)
    out, kind = inj.inject_anomaly(txn, user)
    assert kind == "impossible_travel"
    assert out["latitude"] == 37.5
    assert out["longitude"] == 135.0
