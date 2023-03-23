import polars as pl
from smart_open import open
import urllib.parse
import boto3
import json
import yaml
import logging

personal = boto3.Session(profile_name="personal")


# functions
def make_dict_from_column_mapping(column_mapping, key):
    """
    Make a dictionary from a column mapping and a key.
    """
    dict_ = {
        column_name: column_mapping.get(column_name).get(key)
        for column_name in column_mapping.keys()
    }

    return dict_


def create_view(data: pl.DataFrame, view_name: str, view_values: str) -> pl.DataFrame:
    view_df = data.filter(pl.col("name").is_in(view_values)).select(VIEW_SCHEMA)
    view_df.write_parquet(f"outputs/parquets/{view_name}.parquet", compression="snappy")

    return view_df


# global variables
COLUMN_MAPPING = yaml.SafeLoader(open("config/column_mapping.yaml")).get_data()

NAME_MAPPING = make_dict_from_column_mapping(COLUMN_MAPPING, "name")
EVENT_MAPPING = make_dict_from_column_mapping(COLUMN_MAPPING, "event")
events = yaml.SafeLoader(open("config/events.yaml")).get_data()

# schema values
SCHEMA = [
    "date",
    "source",
    "qty",
    "name",
    "units",
    "date_updated",
]

NEW_COLUMNS = [
    "mapped_name",
    "mapped_event",
]
VIEW_SCHEMA = SCHEMA + NEW_COLUMNS


def run(event, context):
    bucket = event.get("Records")[0].get("s3").get("bucket").get("name")
    key = urllib.parse.unquote_plus(
        event.get("Records")[0].get("s3").get("object").get("key"), encoding="utf-8"
    )
    url = f"s3://{bucket}/{key}"

    # convert contents to native python string
    try:
        with open(url, "rb", transport_params={"client": personal.client("s3")}) as f:
            json_data = f.read().decode("utf-8")

        # logging.info("Converting to dataframe")
        source_data = []

        for line in json_data.splitlines():
            source_data.append(json.loads(line))
        logging.info("Converting to dataframe")

        df = pl.from_records(source_data, infer_schema_length=None)
        cleansed_df = (
            df.with_columns(pl.col("qty").cast(pl.Utf8).alias("qty"))
            .with_columns(pl.col("date").str.strptime(pl.Date, "%Y-%m-%d %H:%M:%S %z"))
            .with_columns(pl.col("name").map_dict(NAME_MAPPING).alias("mapped_name"))
            .with_columns(pl.col("name").map_dict(EVENT_MAPPING).alias("mapped_event"))
        )

        for event_name, event_cols in events.items():
            create_view(data=cleansed_df, view_name=event_name, view_values=event_cols)

    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                key, bucket
            )
        )
        raise e
