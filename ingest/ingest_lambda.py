import json
import os
import boto3
import time

s3 = boto3.client("s3")
BUCKET = os.environ["S3_BUCKET"]


def handler(event, context):
    # Attempt to parse the incoming JSON (assuming a Lambda Function URL POST event)
    try:
        # event["body"] holds the JSON payload as a string
        data = json.loads(event.get("body", "{}"))
    except Exception as e:
        return {"statusCode": 400, "body": "Invalid JSON: " + str(e)}

    # Create a unique filename (e.g., using a timestamp)
    filename = f"landing/data_{int(time.time())}.json"

    # Write the JSON data to the S3 bucket under the landing/ prefix
    s3.put_object(Bucket=BUCKET, Key=filename, Body=json.dumps(data))
    return {"statusCode": 200, "body": "Data stored successfully"}
