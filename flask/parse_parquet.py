import logging
import pandas as pd
import boto3
import json
import urllib.parse
import io
import tempfile

s3 = boto3.client("s3")


def run(event, context):
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    key = urllib.parse.unquote_plus(
        event.get("Records")[0].get("s3").get("object").get("key"), encoding="utf-8"
    )
    # personal = boto3.Session(profile_name='personal')
    # s3 = personal.resource('s3')

    # convert contents to native python string
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response["ContentType"])
        json_data = response.get("Body").read().decode("utf-8")
    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                key, bucket
            )
        )
        raise e

    source_data = []

    for line in json_data.splitlines():
        source_data.append(json.loads(line))

    logging.info("Converting to dataframe")
    df = pd.DataFrame.from_records(source_data)

    # force conversion types
    df["qty"] = df["qty"].astype(str)
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    logging.info("Converting to parquet")

    # write to parquet
    file_name = key.split("/")[-1].split(".")[0]
    with tempfile.NamedTemporaryFile() as tmp:
        df.to_parquet(tmp.name, compression="gzip", engine="fastparquet")
        with open(tmp.name, "rb") as fh:
            parquet_buffer = io.BytesIO(fh.read())

    response = s3.put_object(
        Bucket=bucket,
        Key=f"parquets/{file_name}.parquet",
        Body=parquet_buffer.getvalue(),
    )

    return
