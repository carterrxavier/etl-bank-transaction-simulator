"""Build synthetic user profile rows (shared by scripts and S3 bootstrap in models)."""

from __future__ import annotations

import random
import uuid
from datetime import date

import zipcodes
from faker import Faker

_zip_by_code: dict[str, dict] | None = None
_all_zip_rows: list[dict] | None = None


def _zip_index() -> dict[str, dict]:
    global _zip_by_code
    if _zip_by_code is None:
        _zip_by_code = {z["zip_code"]: z for z in zipcodes.list_all()}
    return _zip_by_code


def _all_rows() -> list[dict]:
    global _all_zip_rows
    if _all_zip_rows is None:
        _all_zip_rows = list(_zip_index().values())
    return _all_zip_rows


def _pick_zip_row(rng: random.Random, fake: Faker) -> dict:
    idx = _zip_index()
    for _ in range(30):
        raw = fake.postcode()
        if not raw:
            continue
        code = raw.split("-")[0]
        if len(code) == 5 and code.isdigit() and code in idx:
            return idx[code]
    return rng.choice(_all_rows())


def _home_lat_lon_from_row(row: dict, rng: random.Random) -> tuple[float, float]:
    lat = float(row["lat"])
    lon = float(row["long"])
    jitter = 0.02
    return (
        round(lat + rng.uniform(-jitter, jitter), 6),
        round(lon + rng.uniform(-jitter, jitter), 6),
    )


def _profile_row(user_id: int, seed: int) -> dict:
    rng = random.Random(seed + user_id)
    fake = Faker("en_US")
    fake.seed_instance(seed + user_id)

    zrow = _pick_zip_row(rng, fake)
    postal = zrow["zip_code"]
    city = zrow["city"]
    state = zrow["state"]
    country = "US"

    street = fake.street_address()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90)
    customer_since = fake.date_between(start_date="-12y", end_date=date.today())

    home_lat, home_lon = _home_lat_lon_from_row(zrow, rng)
    avg_spending = round(rng.uniform(20.0, 200.0), 2)
    device_uuid = uuid.UUID(int=rng.getrandbits(128))

    line2 = fake.secondary_address() if rng.random() < 0.25 else None

    segment = rng.choices(
        ["retail", "preferred", "private_banking"],
        weights=[0.82, 0.15, 0.03],
        k=1,
    )[0]

    return {
        "user_id": user_id,
        "full_name": fake.name(),
        "date_of_birth": dob.isoformat(),
        "phone": fake.phone_number(),
        "email": fake.email(),
        "address_line1": street,
        "address_line2": line2,
        "city": city,
        "state": state,
        "postal_code": postal,
        "country": country,
        "customer_since": customer_since.isoformat(),
        "segment": segment,
        "home_lat": home_lat,
        "home_lon": home_lon,
        "avg_spending": avg_spending,
        "device_id": str(device_uuid),
    }


def build_profiles(count: int, seed: int) -> list[dict]:
    """Return ``count`` profile dicts with ``user_id`` 1..count."""
    if count < 1:
        raise ValueError("count must be >= 1")
    return [_profile_row(i, seed) for i in range(1, count + 1)]
