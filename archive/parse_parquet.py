"""
Parse the json extracts from Apple Health Data as a parquet
"""

import logging
import pandas as pd
import boto3
import json
import urllib.parse
import io
import tempfile
import s3fs
import fastparquet as fp
import numpy as np
import conf
from datetime import datetime

s3 = boto3.client("s3")
# personal = boto3.Session(profile_name="personal")
# s3 = personal.client("s3")


def parse_automated_exports(response_data: str):
    """Parse the automated json extracts from Apple Health Data"""
    source_data = []

    for line in response_data.splitlines():
        source_data.append(json.loads(line))

    logging.info("Converting to dataframe")
    df = pd.DataFrame.from_records(source_data)

    return df


def create_latest_health_dataset(bucket):
    """Parse all parquest files and return unique data for all metrics"""
    # Read the parquet file
    s3fileSystem = s3fs.S3FileSystem()
    fs = s3fs.core.S3FileSystem()

    bucket_uri = f"s3://{bucket}/parquets/*.parquet"
    all_paths_from_s3 = fs.glob(path=bucket_uri)
    df = pd.DataFrame()
    for s3_file in all_paths_from_s3:
        fp_obj = fp.ParquetFile(s3_file, open_with=s3fileSystem.open)
        # convert to pandas dataframe
        df_s3_file = fp_obj.to_pandas()
        df = pd.concat([df, df_s3_file])

    df["date"] = df["date"].astype("str")
    df["date"] = [f[:10] for f in df["date"]]
    cte_latest_data = df.groupby(["date", "name"]).agg({"date_updated": np.max})
    df_latest = df.merge(
        cte_latest_data, on=["date", "name", "date_updated"], how="inner"
    )

    return df_latest


def run(event, context):
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    key = urllib.parse.unquote_plus(
        event.get("Records")[0].get("s3").get("object").get("key"), encoding="utf-8"
    )

    # convert contents to native python string
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        json_data = response.get("Body").read().decode("utf-8")
    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                key, bucket
            )
        )
        raise e

    try:
        df = parse_automated_exports(json_data)
        print(df.head())
        # force conversion types
        logging.info("forcing type conversions for `qty` and `date` columns")
        df["qty"] = df["qty"].astype(str)
        df["date"] = df["date"].apply(
            lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S %z").strftime("%Y-%m-%d")
        )

        df_cols = ["date", "source", "qty", "name", "units", "date_updated"]
        df_parquet = df[df_cols]
    except json.JSONDecodeError as e:
        logging.error("Error parsing json")
        raise e

    logging.info("Converting to parquet")

    # write to parquet
    file_name = key.split("/")[-1].split(".")[0]
    with tempfile.NamedTemporaryFile() as tmp:
        df_parquet.to_parquet(tmp.name, engine="fastparquet")
        with open(tmp.name, "rb") as fh:
            parquet_buffer = io.BytesIO(fh.read())

    response = s3.put_object(
        Bucket=bucket,
        Key=f"parquets/{file_name}.parquet",
        Body=parquet_buffer.getvalue(),
    )

    df_parquet.to_parquet(
        f"s3://{bucket}/parquets/{file_name}.parquet", engine="fastparquet"
    )

    logging.info("Creating latest dataset")
    df_latest = create_latest_health_dataset(bucket)[df_cols]

    logging.info("Writing latest data into a single parquet file")
    with tempfile.NamedTemporaryFile() as tmp:
        df_latest.to_parquet(tmp.name, engine="fastparquet", index=False)
        with open(tmp.name, "rb") as fh:
            parquet_buffer = io.BytesIO(fh.read())

    s3.put_object(
        Bucket=bucket,
        Key=f"outputs/{conf.parquet_file_name}.parquet",
        Body=parquet_buffer.getvalue(),
        ACL="public-read",
    )

    return
