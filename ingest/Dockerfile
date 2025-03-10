# Use a Python 3.13.1 slim base image
FROM python:3.13.1-slim

# Set the Lambda task root directory
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy dependency definition
COPY pyproject.toml .

# Install uv and initialize a virtual environment, then sync dependencies
RUN pip install uv && \
  uv venv && \
  . .venv/bin/activate && \
  uv sync

# Use a build argument to specify which handler file to use (e.g., ingest_lambda.py or dbt_lambda.py)
ARG HANDLER_FILE
COPY ${HANDLER_FILE} handler.py

# Define the command to run your Lambda function; expects a function "handler" in handler.py
CMD ["handler.handler"]
