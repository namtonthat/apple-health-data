# NOTE: Use a AWS's Python 3.13 to work with lambdas
FROM public.ecr.aws/lambda/python:3.13

# Copy dependency definition
COPY pyproject.toml ${LAMBDA_TASK_ROOT}

# Install uv and use it to sync dependencies
RUN pip3 install uv
RUN uv pip install --system -r pyproject.toml

COPY ingest/lambda.py ${LAMBDA_TASK_ROOT}/lambda_function.py

CMD ["lambda_function.lambda_handler"]
