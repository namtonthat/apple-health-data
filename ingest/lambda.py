import json
import time
import boto3
import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayHttpResolver

logger = Logger()
app = APIGatewayHttpResolver()

s3_client = boto3.client("s3")
BUCKET = os.environ.get("S3_BUCKET")


def save_to_s3(event_data: dict) -> str:
    """
    Save event data to S3 and return the object key.
    """
    # Use provided timestamp if available, else current time.
    load_time = int(time.time())
    event_data["load_time"] = load_time

    # Use the integer timestamp directly in the S3 key
    key = f"landing/{load_time}.json"
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(event_data))
    return key


@app.post("/")
def ingest():
    try:
        # The JSON payload is automatically parsed by Powertools
        event_data = app.current_event.json_body
        logger.info("Received data", extra=event_data)

        key = save_to_s3(event_data)
        logger.info("Data saved to S3", extra={"key": key})
        return {"message": f"Data saved to S3 at {key}"}
    except Exception as e:
        logger.exception("Error processing event")
        return {"error": str(e)}, 500


def lambda_handler(event, context):
    # Log the entire event to see what's being received
    logger.info("Raw event received", extra={"event": event})

    return app.resolve(event, context)
