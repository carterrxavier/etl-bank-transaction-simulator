from datetime import datetime
import random
from faker import Faker
import uuid

fake = Faker()

def generate_transaction(user):
    amount = round(max(0.01, random.gauss(user.avg_spending, 15)), 2)
    return {
        "transaction_id": str(uuid.uuid4()),
        "user_id": user.user_id,
        "latitude": user.home_lat + random.uniform(-0.05, 0.05),
        "longitude": user.home_lon + random.uniform(-0.05, 0.05),
        "amount": amount,
        "avg_spending": round(user.avg_spending, 2),
        "device_id": user.device_id,
        "timestamp": datetime.now().isoformat(), # in UTC
        "merchant": fake.company(),
        "transaction_type": random.choice(['POS', 'ATM', 'Online']),
    }