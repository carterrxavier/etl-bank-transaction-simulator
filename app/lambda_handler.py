import json
import os
import uuid
from datetime import datetime, timezone

from app.detector import detect_fraud, update_user_state
from app.models import User, _profiles_bucket
from app.send import S3ObjectStore


def _date_prefix(now: datetime) -> str:
    return f"{now:%Y/%m/%d}"


def _iter_s3_objects(event: dict, bucket_override: str | None) -> list[tuple[str, str]]:
    """
    Returns a list of (bucket, key) pairs from supported event shapes.

    Supported:
    - S3 notification events: event["Records"][*].s3.bucket.name / s3.object.key
    - EventBridge S3 Object Created events: event["detail"].bucket.name / event["detail"].object.key
    """
    objects: list[tuple[str, str]] = []

    records = event.get("Records")
    if isinstance(records, list) and records:
        for rec in records:
            if not isinstance(rec, dict):
                continue
            s3_info = rec.get("s3") or {}
            if not isinstance(s3_info, dict):
                continue
            bucket = bucket_override or ((s3_info.get("bucket") or {}).get("name"))
            key = (s3_info.get("object") or {}).get("key")
            if bucket and key:
                objects.append((bucket, key))
        return objects

    detail = event.get("detail")
    if isinstance(detail, dict):
        bucket = bucket_override or ((detail.get("bucket") or {}).get("name"))
        key = (detail.get("object") or {}).get("key")
        if bucket and key:
            objects.append((bucket, key))

    return objects


def handler(event, context):  # AWS Lambda entrypoint
    """
    Triggered by S3 ObjectCreated events for keys under `transactions/`.

    Supports both:
    - S3 notification payloads (event["Records"][...])
    - EventBridge S3 "Object Created" payloads (event["detail"]...)

    Downloads the transaction JSON, runs detection, and writes a fraud decision
    JSON to `fraud_decisions/YYYY/MM/DD/<decision_id>.json`.
    """
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    bucket_override = os.environ.get("S3_BUCKET") or os.environ.get("AWS_S3_BUCKET")

    objects = _iter_s3_objects(event if isinstance(event, dict) else {}, bucket_override)
    # Lambda has no .env; profile JSON loads from S3 using the same bucket as transactions.
    # If S3_BUCKET / AWS_S3_BUCKET / USER_PROFILES_BUCKET is unset, use the trigger bucket.
    if objects and not _profiles_bucket():
        os.environ["S3_BUCKET"] = objects[0][0]

    results = []

    for bucket, key in objects:
        store = S3ObjectStore(bucket=bucket, region=region)
        txn = store.get(key)

        # NOTE: Lambda is stateless; for demo we use an ephemeral per-user User object.
        # In a real system you'd pull user history from a DB/feature store.
        user_id = txn.get("user_id") or 0
        user = User(int(user_id))

        fraud_flag, features = detect_fraud(txn, user)
        update_user_state(txn, user)

        now = datetime.now(timezone.utc)
        sim_type = txn.get("sim_anomaly_type")
        decision = {
            "decision_id": str(uuid.uuid4()),
            "transaction_id": txn.get("transaction_id"),
            "transaction_key": key,
            "user_id": txn.get("user_id"),
            "sim_anomaly_type": sim_type,
            "anomaly_injected": sim_type not in (None, "none"),
            "fraud_flag": fraud_flag,
            "detector": os.environ.get("DETECTOR_NAME", "rules_v1"),
            "evaluated_at": now.isoformat(),
            "features": features,
        }

        decision_key = f"fraud_decisions/{_date_prefix(now)}/{decision['decision_id']}.json"
        store.put(decision, key=decision_key)

        results.append({"ok": True, "transaction_key": key, "decision_key": decision_key, "fraud_flag": fraud_flag})

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(results), "results": results}),
    }

