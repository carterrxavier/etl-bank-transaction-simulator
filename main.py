import json
import random
import time
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from app.models import User
from app.generator import generate_transaction
from app.injector import inject_anomaly
from app.send import store


users = [User(i) for i in range(1, 10000)]
obj_store = store()


def _date_prefix(now: datetime) -> str:
    return f"{now:%Y/%m/%d}"

while True:
    user = random.choice(users)
    txn = generate_transaction(user)  # event is created
    txn, _ = inject_anomaly(txn, user)  # anomalies injected (no detection here)

    now = datetime.now(timezone.utc)
    txn_id = txn.get("transaction_id", "unknown")
    key = f"transactions/{_date_prefix(now)}/{txn_id}.json"
    obj_store.put(txn, key=key)

    print(json.dumps({"stored": True, "bucket": getattr(obj_store, "bucket", None), "key": key}), flush=True)
    time.sleep(.5)
    