import json
import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from app.send import store
from app.transaction_flow import emit_transaction_to_store, users_pool

obj_store = store()
users = users_pool()

while True:
    result = emit_transaction_to_store(obj_store, users)
    print(
        json.dumps(
            {
                "stored": True,
                "bucket": result.get("bucket"),
                "key": result["key"],
            }
        ),
        flush=True,
    )
    time.sleep(0.5)
