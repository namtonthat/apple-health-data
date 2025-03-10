import os
import json
import time
import boto3
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

        # Generate a unique key (e.g., using a timestamp)
        key = f"landing/{int(time.time())}.json"
        s3_client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(event_data))

        return {"message": f"Data saved to S3 at {key}"}
    except Exception as e:
        logger.exception("Error processing event")
        return {"error": str(e)}, 500


def handler(event, context):
    return app.resolve(event, context)
