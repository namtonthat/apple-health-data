# NOTE: Use a AWS's Python 3.13 to work with lambdas
FROM public.ecr.aws/lambda/python:3.13

# Set the Lambda task root directory
ENV LAMBDA_TASK_ROOT=/var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy dependency definition
COPY pyproject.toml .

# Install uv and initialize a virtual environment, then sync dependencies
RUN pip install uv && \
  uv venv --python 3.13.1 && \
  . .venv/bin/activate && \
  uv sync

# Copy DBT project and Lambda handler code
COPY dbt/ /var/dbt_project/

# Use a build argument to specify which handler file to use (e.g., ingest_lambda.py or dbt_lambda.py)
COPY dbt_lambda.py handler.py

# Define the command to run your Lambda function; expects a function "handler" in handler.py
CMD ["handler.handler"]

