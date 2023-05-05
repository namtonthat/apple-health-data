import polars as pl
from smart_open import open
import json
import yaml
import logging
import s3fs
from typing import List

# personal = boto3.Session(profile_name="personal")
bucket = "ntonthat-apple-heatlh-data"
prefix = "raw/"
fs = s3fs.S3FileSystem()


def get_file_list(bucket: str, prefix: str) -> List[str]:
    """
    Returns a list of files located in the specified S3 bucket and prefix.

    Parameters:
        - bucket (str): The name of the S3 bucket to list files from.
        - prefix (str): The prefix for the S3 object keys to include in the list.

    Returns:
        - List[str]: A list of S3 object keys (i.e., file paths) that match the specified prefix.
    """
    url = f"s3://{bucket}/{prefix}/"
    file_list = fs.ls(url)

    return file_list


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


def create_view(data: pl.DataFrame, view_name: str, view_values: List[str]) -> pl.DataFrame:
    """
    Creates a new view DataFrame from the specified data, with rows filtered by a list of values.

    Parameters:
        - data (pl.DataFrame): The input DataFrame to create the view from.
        - view_name (str): The name to use for the new view.
        - view_values (List[str]): A list of values to use for filtering the rows.

    Returns:
        - pl.DataFrame: The resulting view DataFrame with columns following the VIEW_SCHEMA.

    VIEW_SCHEMA:
    - "date" (str): The date the record was created.
    - "source" (str): The source of the record.
    - "qty" (float): The quantity value of the record.
    - "name" (str): The name of the record.
    - "units" (str): The unit of measurement for the record.
    - "date_updated" (str): The date the record was last updated.
    - "mapped_name" (str): The mapped name value for the record.
    - "mapped_event" (str): The mapped event value for the record.
    """
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


if __name__ == "__main__":
    # convert contents to native python string
    latest_file = get_file_list(bucket, prefix)[-1]

    try:
        with open(f"s3://{latest_file}", "rb") as f:
            json_data = f.read().decode("utf-8")
        source_data = []

        for line in json_data.splitlines():
            source_data.append(json.loads(line))
        logging.info("Converting to dataframe")

        df = pl.from_records(source_data, infer_schema_length=None)

        logging.info("cleansing data")
        cleansed_df = (
            df.with_columns(pl.col("qty").cast(pl.Utf8).alias("qty"))
            .with_columns(pl.col("date").str.strptime(pl.Date, "%Y-%m-%d %H:%M:%S %z"))
            .with_columns(pl.col("name").map_dict(NAME_MAPPING).alias("mapped_name"))
            .with_columns(pl.col("name").map_dict(EVENT_MAPPING).alias("mapped_event"))
        )

        for event_name, event_cols in events.items():
            logging.info("creating view %s", event_name)
            create_view(data=cleansed_df, view_name=event_name, view_values=event_cols)

    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                prefix, bucket
            )
        )
        raise e
