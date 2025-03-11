import json
import subprocess
from aws_lambda_powertools import Logger, Tracer
import polars as pl
import boto3
import io

logger = Logger()
tracer = Tracer()


def read_s3_json(bucket: str, key: str) -> pl.DataFrame:
    """
    Reads a newline-delimited JSON (NDJSON) file from S3 and returns a Polars DataFrame.

    Args:
        bucket (str): The name of the S3 bucket.
        key (str): The S3 object key (path to the JSON file).

    Returns:
        pl.DataFrame: A DataFrame containing the JSON data.
    """
    # Initialize the S3 client (make sure your AWS credentials are set up)
    s3 = boto3.client("s3")

    # Retrieve the S3 object
    response = s3.get_object(Bucket=bucket, Key=key)

    # Read the file content from the response body and decode it
    content = response["Body"].read().decode("utf-8")

    # Use StringIO to allow Polars to read from the string as a file-like object
    json_stream = io.StringIO(content)

    # Read the NDJSON file into a Polars DataFrame
    df = pl.read_ndjson(json_stream)

    return df


def handler(event, context):
    # Log the incoming S3 event
    logger.info("Received S3 event", extra=event)
    # s3_landing_file = read_s3_json(event.s3.bbucket.name, event.object.key)

    dbt_project_path = "/var/dbt_project"

    try:
        result = subprocess.run(
            ["dbt", "run"], cwd=dbt_project_path, capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("DBT job succeeded", extra={"output": result.stdout})
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "DBT job executed", "output": result.stdout}
                ),
            }
        else:
            logger.error("DBT job failed", extra={"error": result.stderr})
            return {"statusCode": 500, "body": json.dumps({"error": result.stderr})}
    except Exception as e:
        logger.exception("Exception when executing DBT job")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
