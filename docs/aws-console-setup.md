## Manual AWS Console setup (S3 → Lambda container)

### 1) Create the S3 bucket
- Create a bucket in your desired region (example: `us-east-1`).
- You can leave versioning off for the demo (optional).

### 2) Create an ECR repository (for the Lambda container)
- ECR → Create repository (example name: `etl-fraud-detector`).

### 3) Build and push the image
From your repo root:

```bash
docker build -f Dockerfile.lambda -t etl-fraud-detector:latest .
```

Authenticate Docker to ECR and push (replace region/account/repo):

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com

docker tag etl-fraud-detector:latest <account_id>.dkr.ecr.us-east-1.amazonaws.com/etl-fraud-detector:latest
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/etl-fraud-detector:latest
```

### 4) Create the Lambda function from the container image
- Lambda → Create function → Container image
- Select the ECR image/tag you pushed.
- Set **Timeout** to something like 10–30 seconds for the demo.
- Ensure the handler is the image CMD (already set in `Dockerfile.lambda` as `app.lambda_handler.handler`).

### 5) IAM permissions for the Lambda role (minimum)
Attach a policy allowing:
- `s3:GetObject` on `arn:aws:s3:::<bucket>/transactions/*`
- `s3:PutObject` on `arn:aws:s3:::<bucket>/fraud_decisions/*`
- CloudWatch Logs (basic Lambda execution role)

Example policy (replace `<bucket>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadTransactions",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::<bucket>/transactions/*"]
    },
    {
      "Sid": "WriteFraudDecisions",
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::<bucket>/fraud_decisions/*"]
    }
  ]
}
```

### 6) Add the S3 event trigger
- S3 → your bucket → Properties → Event notifications → Create event notification
- Events: **All object create events** (ObjectCreated)
- Prefix: `transactions/`
- Destination: **Lambda function** (pick the function you created)

### 7) Test end-to-end
1. Run the producer locally with env credentials:

```bash
export OBJECT_STORE=s3
export AWS_REGION=us-east-1
export S3_BUCKET=<bucket>
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

python3 main.py
```

2. Watch S3:
- New objects appear under `transactions/YYYY/MM/DD/…`
- Lambda should write decisions under `fraud_decisions/YYYY/MM/DD/…`

3. Troubleshooting:
- CloudWatch Logs for Lambda are the first place to look.
- If triggers don’t fire, re-check the S3 event notification prefix and Lambda permissions.

