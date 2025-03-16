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


@app.post("/")
def ingest():
    try:
        # The JSON payload is automatically parsed by Powertools
        event_data = app.current_event.json_body
        logger.info("Received data", extra=event_data)

        load_date = int(time.time())
        event_data["load_date"] = load_date
        key = f"landing/{load_date}.json"
        s3_client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(event_data))

        return {"message": f"Data saved to S3 at {key}"}
    except Exception as e:
        logger.exception("Error processing event")
        return {"error": str(e)}, 500


def lambda_handler(event, context):
    # Log the entire event to see what's being received
    logger.info("Raw event received", extra={"event": event})

    return app.resolve(event, context)
