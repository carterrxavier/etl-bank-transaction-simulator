import json
import random
import time

from app.models import User
from app.generator import generate_transaction
from app.anamolies import inject_anamoly


users = [User(i) for i in range(1, 10000)]

while True:
    user = random.choice(users)
    txn = generate_transaction(user)
    txn, anamoly_type = inject_anamoly(txn, user)
    print(json.dumps(txn), flush=True)
    time.sleep(.5)
    