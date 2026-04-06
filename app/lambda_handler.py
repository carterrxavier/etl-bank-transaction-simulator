import json
import os
import uuid
from datetime import datetime, timezone

from app.detector import detect_fraud, update_user_state
from app.models import User
from app.send import S3ObjectStore


def _date_prefix(now: datetime) -> str:
    return f"{now:%Y/%m/%d}"


def handler(event, context):  # AWS Lambda entrypoint
    """
    Triggered by S3 ObjectCreated events for keys under `transactions/`.

    Downloads the transaction JSON, runs detection, and writes a fraud decision
    JSON to `fraud_decisions/YYYY/MM/DD/<decision_id>.json`.
    """
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    bucket_override = os.environ.get("S3_BUCKET") or os.environ.get("AWS_S3_BUCKET")

    records = event.get("Records") or []
    results = []

    for rec in records:
        s3_info = (rec.get("s3") or {})
        bucket = bucket_override or (s3_info.get("bucket") or {}).get("name")
        key = (s3_info.get("object") or {}).get("key")

        if not bucket or not key:
            results.append({"ok": False, "error": "missing_bucket_or_key"})
            continue

        store = S3ObjectStore(bucket=bucket, region=region)
        txn = store.get(key)

        # NOTE: Lambda is stateless; for demo we use an ephemeral per-user User object.
        # In a real system you'd pull user history from a DB/feature store.
        user_id = txn.get("user_id") or 0
        user = User(int(user_id))

        fraud_flag, features = detect_fraud(txn, user)
        update_user_state(txn, user)

        now = datetime.now(timezone.utc)
        decision = {
            "decision_id": str(uuid.uuid4()),
            "transaction_id": txn.get("transaction_id"),
            "transaction_key": key,
            "user_id": txn.get("user_id"),
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

