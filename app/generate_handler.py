import json

from app.send import store
from app.transaction_flow import emit_transaction_to_store, users_pool


def _parse_count(event) -> int:
    """Supports direct invoke, API Gateway-style body, or EventBridge detail."""
    if not isinstance(event, dict):
        return 1

    body = event.get("body")
    if isinstance(body, str) and body.strip():
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and "count" in parsed:
                return _clamp_count(parsed["count"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    if "count" in event:
        return _clamp_count(event.get("count"))

    detail = event.get("detail")
    if isinstance(detail, dict) and "count" in detail:
        return _clamp_count(detail.get("count"))

    return 1


def _clamp_count(raw) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, min(n, 100))


def handler(event, context):  # AWS Lambda entrypoint (generator)
    """
    Writes synthetic transactions under transactions/YYYY/MM/DD/<id>.json.

    Set OBJECT_STORE=s3 and S3_BUCKET (or AWS_S3_BUCKET) in the function config.
    Optional JSON field ``count`` (1–500) on the event, API body, or EventBridge detail.
    """
    count = _parse_count(event)
    obj_store = store()
    users = users_pool()

    results = []
    for _ in range(count):
        results.append(emit_transaction_to_store(obj_store, users))

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(results), "results": results}),
    }
