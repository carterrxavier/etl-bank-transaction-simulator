import json

import pytest

from app.send import LocalObjectStore, _s3_bucket_from_env, store


def test_local_object_store_put_get_roundtrip(tmp_path):
    s = LocalObjectStore(root_dir=str(tmp_path / "s3"))
    obj = {"a": 1, "b": "x"}
    key = s.put(obj, key="path/to/obj.json")
    assert key == "path/to/obj.json"
    assert s.get(key) == obj
    data = (tmp_path / "s3" / "path" / "to" / "obj.json").read_text(encoding="utf-8")
    assert json.loads(data.strip()) == obj


def test_store_local_default(monkeypatch, tmp_path):
    monkeypatch.delenv("OBJECT_STORE", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("LOCAL_S3_DIR", str(tmp_path / "local"))
    s = store()
    assert isinstance(s, LocalObjectStore)
    k = s.put({"x": 1}, key="k.json")
    assert s.get(k) == {"x": 1}


def test_store_s3_requires_bucket(monkeypatch):
    monkeypatch.setenv("OBJECT_STORE", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        store()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("my-bucket", "my-bucket"),
        (None, None),
    ],
)
def test_s3_bucket_from_env(monkeypatch, value, expected):
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    if value is not None:
        monkeypatch.setenv("S3_BUCKET", value)
    assert _s3_bucket_from_env() == expected
