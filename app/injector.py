import random

from faker import Faker

fake = Faker()


def inject_anomaly(transaction: dict, user) -> tuple[dict, str]:
    """
    Mutates the transaction payload to simulate anomalous behavior.
    Does NOT set any fraud flags; detection should happen in a separate step.
    """
    anomaly_type = random.choices(
        ["none", "high_amount", "impossible_travel", "rapid_fire", "new_device"],
        weights=[0.85, 0.05, 0.03, 0.04, 0.03],
        k=1,
    )[0]

    if anomaly_type == "high_amount":
        if "amount" in transaction and isinstance(transaction["amount"], (int, float)):
            transaction["amount"] = round(transaction["amount"] * 10, 2)

    elif anomaly_type == "impossible_travel" and user.last_timestamp:
        # Intentionally far away to induce "impossible travel" in detection.
        transaction["latitude"] = random.uniform(35, 40)
        transaction["longitude"] = random.uniform(130, 140)

    elif anomaly_type == "new_device":
        transaction["device_id"] = fake.uuid4()

    # rapid_fire is about *timing* between events; we keep payload unchanged.

    # Simulation-only label so you can compare injected vs detected downstream.
    transaction["sim_anomaly_type"] = anomaly_type
    return transaction, anomaly_type

