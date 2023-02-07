import boto3
import urllib
import logging

s3 = boto3.resource("s3")


def run(event, context):
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    key = urllib.parse.unquote_plus(
        event.get("Records")[0].get("s3").get("object").get("key"), encoding="utf-8"
    )
    file = key.split("/")[-1]
    public_bucket = "ntonthat-public-data"
    public_key = f"apple-health-calendar/{file}"

    copy_source = {"Bucket": bucket, "Key": key}

    logging.info(
        "Copying files to public bucket %s",
    )
    s3.meta.client.copy(copy_source, public_bucket, public_key, {"ACL": "public-read"})

    # s3.Object(public_bucket, public_key).Acl().put(ACL="public-read")
