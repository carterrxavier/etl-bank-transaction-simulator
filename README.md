## etl-bank-transaction-simulator

**Purpose**

This repository is a **simulation harness** for a small bank-style data pipeline: it generates **synthetic customers and transactions** (not real people or accounts), lands immutable JSON in object storage, and runs a **rules-based fraud detector** that writes separate decision records. Use it to exercise ETL, S3 eventing, Lambda, and analytics workflows without production data.

**All data is fake and for demonstration only.**

---

### Data you get

| Artifact | Location (typical) | Contents |
|----------|-------------------|----------|
| **User profiles** | **S3** default key `users/user_profiles.json` (same bucket as transactions unless `USER_PROFILES_BUCKET` is set). If the object is missing, the **first** process to load profiles **generates and uploads** it (simulation bootstrap). **Local fallback:** `app/data/user_profiles.json` when no bucket env vars are set. | `user_id`, demographics, mailing address (ZIP-aligned city/state), `home_lat` / `home_lon`, `avg_spending`, `device_id`, bank-style `segment`, etc. Count controlled by `USER_PROFILES_COUNT` (default `9999`). No balances or real PII. |
| **Transactions** | `transactions/YYYY/MM/DD/<transaction_id>.json` | One JSON object per event: `user_id`, amount, geo jitter near home, `timestamp`, merchant, `transaction_type`, `sim_anomaly_type` (injection label: usually `none`, sometimes `high_amount`, `impossible_travel`, `rapid_fire`, `new_device`). |
| **Fraud decisions** | `fraud_decisions/YYYY/MM/DD/<decision_id>.json` | One JSON object per processed transaction: `fraud_flag`, `features`, `sim_anomaly_type`, `anomaly_injected`, links back to `transaction_id` / S3 key. |

Each emitted transaction picks a **random user** from the profile pool, builds a plausible row, then **randomly** applies an anomaly (~85% are normal/`none`).

---

### How the Lambdas run (especially on a schedule)

One **container image** ([`Dockerfile`](Dockerfile)) ships both handlers; you set the handler per function in AWS:

1. **Generator (`app.generate_handler.handler`)**  
   - Intended to be invoked **periodically** (e.g. **Amazon EventBridge Scheduler** or **CloudWatch Events**).  
   - Each invocation can write **one or many** transactions (payload `count` 1–500, or equivalent in `detail`).  
   - With `OBJECT_STORE=s3` and `S3_BUCKET` (or `AWS_S3_BUCKET`) set, it **puts** objects under `transactions/...`.  
   - **IAM**: `s3:PutObject` on `transactions/*`, plus **read access** to `users/*` (profile JSON). Allow **`s3:PutObject` on `users/*`** so the function can **create** `users/user_profiles.json` if it is missing.

2. **Detector (`app.lambda_handler.handler`)**  
   - Triggered by **S3 `ObjectCreated`** on the **same bucket**, usually with prefix `transactions/`.  
   - Reads the new transaction JSON, loads the matching **customer profile** by `user_id` from S3 (same rules as the generator), runs `detect_fraud`, then **writes** a decision JSON under `fraud_decisions/...`.  
   - **IAM**: `s3:GetObject` on `transactions/*` and **`users/*`**, `s3:PutObject` on `fraud_decisions/*`, and **`s3:PutObject` on `users/*`** if profiles might be bootstrapped from this path. Plus basic CloudWatch Logs.

So the loop is: **schedule → generator Lambda → S3 transaction object → S3 event → detector Lambda → S3 fraud decision object**.

EventBridge Scheduler also needs its **execution role** plus a **resource-based policy** on the generator Lambda allowing `scheduler.amazonaws.com` (if you use that path).

---

### User profiles (S3 + optional local file)

**In AWS (recommended):** Set `S3_BUCKET` or `AWS_S3_BUCKET` (or override with `USER_PROFILES_BUCKET`). Profiles load from **`USER_PROFILES_S3_KEY`** (default `users/user_profiles.json`). If that object does not exist, the app builds profiles in memory, uploads them once, then continues. Tuning:

| Env var | Purpose |
|--------|---------|
| `USER_PROFILES_BUCKET` | Optional; if unset, uses `S3_BUCKET` / `AWS_S3_BUCKET`. |
| `USER_PROFILES_S3_KEY` | Object key (default `users/user_profiles.json`). |
| `USER_PROFILES_COUNT` | Number of synthetic users when creating the file (default `9999`). |
| `USER_PROFILES_SEED` | Reproducible seed for generation (default `42`). |

**Locally without S3:** Unset the bucket env vars. Put a JSON file at `app/data/user_profiles.json` or generate it:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_user_profiles.py --count 9999 --seed 42 --output app/data/user_profiles.json
```

That file is **gitignored** (large). Requires `zipcodes` (see `requirements.txt`).

---

### Local run (producer loop)

```bash
python3 -m pip install -r requirements.txt
```

For **local** object storage, ensure `app/data/user_profiles.json` exists (command above), **or** set `S3_BUCKET` so profiles load from `users/user_profiles.json` the same as in Lambda:

```bash
OBJECT_STORE=local python3 main.py
```

Writes under `.local_s3/`.

With real S3 (profiles + transactions use the same bucket by default):

```bash
export OBJECT_STORE=s3
export AWS_REGION=us-east-1
export S3_BUCKET=your-bucket-name
# ... AWS credentials ...

python3 main.py
```

---

### Lambda container

Build:

```bash
docker build -t etl-bank-simulator:latest .
```

Configure two functions from the same image with handlers:

- **Detector (S3 trigger):** `app.lambda_handler.handler`
- **Generator (schedule / invoke):** `app.generate_handler.handler`

---

### AWS (manual console wiring)

1. Create an S3 bucket (pick a region).  
2. Create ECR repository and push the image (no profile file in the image; profiles live in **`users/`** on S3).  
3. Create **two** Lambdas from the image (different handlers). Set **`S3_BUCKET`** (or `AWS_S3_BUCKET`) **and** **`AWS_REGION`** on both so [`app/models.py`](app/models.py) can load or bootstrap profiles.  
4. **Generator**: EventBridge Scheduler (or rule) invoking the generator on your cadence; pass `count` in the payload if you want batches.  
5. **Detector**: S3 event notification on `ObjectCreated`, prefix `transactions/`, targeting the detector function.  
6. **IAM** (typical for simulation):  
   - **Both** Lambdas: `s3:GetObject` on `arn:aws:s3:::<bucket>/users/*`  
   - **Both** Lambdas: `s3:PutObject` on `arn:aws:s3:::<bucket>/users/*` (so either can create `users/user_profiles.json` the first time)  
   - Generator: `s3:PutObject` on `transactions/*`  
   - Detector: `s3:GetObject` on `transactions/*`, `s3:PutObject` on `fraud_decisions/*`  
   - Plus basic Lambda execution / CloudWatch Logs on each function.
