## etl-bank-transaction-simulator

**Purpose**

This repository is a **simulation harness** for a small bank-style data pipeline: it generates **synthetic customers and transactions** (not real people or accounts), lands immutable JSON in object storage, and runs a **rules-based fraud detector** that writes separate decision records. Use it to exercise ETL, S3 eventing, Lambda, and analytics workflows without production data.

**All data is fake and for demonstration only.**

---

### Data you get

| Artifact | Location (typical) | Contents |
|----------|-------------------|----------|
| **User profiles** | Bundled at runtime from `app/data/user_profiles.json` (generate locally; see below) | ~9,999 rows: `user_id`, demographics, mailing address (ZIP-aligned city/state), `home_lat` / `home_lon`, `avg_spending`, `device_id`, bank-style `segment`, etc. No balances or real PII. |
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
   - **IAM**: the function role needs `s3:PutObject` on `transactions/*` (and any prefix you use).

2. **Detector (`app.lambda_handler.handler`)**  
   - Triggered by **S3 `ObjectCreated`** on the **same bucket**, usually with prefix `transactions/`.  
   - Reads the new transaction JSON, loads the matching **customer profile** by `user_id`, runs `detect_fraud`, then **writes** a decision JSON under `fraud_decisions/...`.  
   - **IAM**: `s3:GetObject` on `transactions/*`, `s3:PutObject` on `fraud_decisions/*`, plus basic CloudWatch Logs.

So the loop is: **schedule → generator Lambda → S3 transaction object → S3 event → detector Lambda → S3 fraud decision object**.

EventBridge Scheduler also needs its **execution role** plus a **resource-based policy** on the generator Lambda allowing `scheduler.amazonaws.com` (if you use that path).

---

### User profiles (local generation)

`app/data/user_profiles.json` is **not committed** (size / GitHub limits). For local runs, Docker builds, or to upload to S3 (e.g. Snowflake), generate it once:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_user_profiles.py --count 9999 --seed 42 --output app/data/user_profiles.json
```

- Adjust `--count` / `--seed` as needed; the app loads whatever profiles exist in that file.  
- Requires the `zipcodes` dependency (listed in `requirements.txt`).

---

### Local run (producer loop)

```bash
python3 -m pip install -r requirements.txt
```

Ensure `app/data/user_profiles.json` exists (command above), then:

```bash
OBJECT_STORE=local python3 main.py
```

Writes under `.local_s3/`.

With real S3:

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
2. Generate `user_profiles.json` and include it under `app/data/` in the image (already covered by `COPY app/ app/` in the Dockerfile) **or** mount/supply via your build pipeline.  
3. Create ECR repository and push the image.  
4. Create **two** Lambdas from the image (different handlers).  
5. **Generator**: EventBridge Scheduler (or rule) invoking the generator on your cadence; pass `count` in the payload if you want batches.  
6. **Detector**: S3 event notification on `ObjectCreated`, prefix `transactions/`, targeting the detector function.  
7. **IAM** (minimum):  
   - Generator: `s3:PutObject` on `transactions/*`  
   - Detector: `s3:GetObject` on `transactions/*`, `s3:PutObject` on `fraud_decisions/*`, plus the basic Lambda execution / logging role.
