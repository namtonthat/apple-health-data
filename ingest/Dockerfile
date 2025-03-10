# Use a Python 3.13.1 slim base image
FROM python:3.13.1-slim

# Set the Lambda task root directory
WORKDIR /var/task

# Copy dependency definition
COPY pyproject.toml .

# Install uv and initialize a virtual environment, then sync dependencies
RUN pip install uv && \
  uv pip install -r pyproject.toml

# Use a build argument to specify which handler file to use (e.g., ingest_lambda.py or dbt_lambda.py)
COPY ingest/lambda.py handler.py

CMD ["handler.handler"]
