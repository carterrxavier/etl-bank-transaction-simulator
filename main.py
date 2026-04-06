import json
import random
import time
import uuid
from datetime import datetime

from app.models import User
from app.generator import generate_transaction
from app.injector import inject_anomaly
from app.detector import detect_fraud, update_user_state
from app.send import store


users = [User(i) for i in range(1, 10000)]
s3 = store()

while True:
    user = random.choice(users)
    txn = generate_transaction(user)                 # event is created
    txn, _ = inject_anomaly(txn, user)               # anomalies injected (no flags)

    txn_key = s3.put(txn, prefix="transactions")     # stored (S3 stand-in)
    stored_txn = s3.get(txn_key)                     # retrieved for evaluation

    fraud_flag, features = detect_fraud(stored_txn, user)  # detection step
    decision = {
        "decision_id": str(uuid.uuid4()),
        "transaction_id": stored_txn.get("transaction_id"),
        "transaction_key": txn_key,
        "user_id": stored_txn.get("user_id"),
        "fraud_flag": fraud_flag,
        "detector": "rules_v1",
        "evaluated_at": datetime.now().isoformat(),
        "features": features,
    }
    _ = s3.put(decision, prefix="fraud_decisions")

    update_user_state(stored_txn, user)              # update state after processing

    print(json.dumps(stored_txn), flush=True)
    print(json.dumps(decision), flush=True)
    time.sleep(.1)
    