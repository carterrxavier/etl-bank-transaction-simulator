FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .
RUN pip install -r requirements.txt -t .

COPY app/ app/

# Override handler per function in AWS (same image):
#   Detector (S3 trigger): app.lambda_handler.handler
#   Generator (schedule / invoke): app.generate_handler.handler
CMD ["app.lambda_handler.handler"]

