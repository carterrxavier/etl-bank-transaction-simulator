## etl-bank-transaction-simulator

### What this does
- **Producer** generates synthetic transactions and writes immutable JSON objects to S3 under `transactions/YYYY/MM/DD/<transaction_id>.json`.
- **Detector** runs in an **AWS Lambda container image** triggered by S3 `ObjectCreated` events, reads the transaction, and writes a separate **fraud decision event** to `fraud_decisions/YYYY/MM/DD/<decision_id>.json`.

### Local run (producer)
Install deps:

```bash
python3 -m pip install -r requirements.txt
```

Run with local storage (writes under `.local_s3/`):

```bash
OBJECT_STORE=local python3 main.py
```

Run with real S3 (requires env credentials):

```bash
export OBJECT_STORE=s3
export AWS_REGION=us-east-1
export S3_BUCKET=your-bucket-name
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

python3 main.py
```

### Lambda container (detector)
Build container:

```bash
docker build -f Dockerfile.lambda -t etl-fraud-detector:latest .
```

Handler entrypoint is `app.lambda_handler.handler`.

### AWS (manual console wiring)
1. **Create an S3 bucket** (pick a region).\n+2. **Create ECR repository** and push the detector image.\n+3. **Create Lambda** from the ECR image.\n+4. **Add S3 event notification** on `ObjectCreated` with prefix `transactions/` targeting the Lambda.\n+5. **Lambda IAM role permissions** (minimum):\n+   - `s3:GetObject` on `arn:aws:s3:::<bucket>/transactions/*`\n+   - `s3:PutObject` on `arn:aws:s3:::<bucket>/fraud_decisions/*`\n+   - CloudWatch Logs permissions (basic execution role)\n+