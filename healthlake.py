from datetime import datetime, date, timedelta
from io import StringIO

import arrow
import conf
import flask
import boto3
import json
import time
import csv
import sys


# initialize our app and our S3 and Athena clients
app = flask.Flask(__name__)
s3 = boto3.client("s3")
athena = boto3.client("athena")

# force the ability to parse very large CSV files
csv.field_size_limit(sys.maxsize)


#
# Utility Functions
#


def store(rows):
    """
    Store rows of health export data in our S3 bucket.
    """

    key_name = "syncs/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(row).strip() for row in rows]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


def store_workouts(workouts):
    """
    Store rows of workout data in our S3 bucket.
    """

    key_name = "workouts/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(workout).strip() for workout in workouts]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


#
# Utility Functions
#


def store(rows):
    """
    Store rows of health export data in our S3 bucket.
    """

    key_name = "syncs/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(row).strip() for row in rows]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


def store_workouts(workouts):
    """
    Store rows of workout data in our S3 bucket.
    """

    key_name = "workouts/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(workout).strip() for workout in workouts]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


def transform(data):
    """
    Flatten the nested JSON data structure from Health Export
    in order to make it easier to index and query with Athena.
    """

    rows = []
    for metric in data.get("data", {}).get("metrics", []):
        name = metric["name"]
        units = metric["units"]

        for point in metric.get("data", []):
            point["name"] = name
            point["units"] = units
            rows.append(point)

    return rows


def transform_workouts(data):
    """
    Flatten the nested JSON data structure from Health Export
    for workouts to make it easier to index and query with Athena.
    """

    workouts = []
    for raw in data.get("data", {}).get("workouts", []):
        workout = {}
        for key, val in raw.items():
            if isinstance(val, dict):
                for subkey, subval in val.items():
                    workout["_".join([key, subkey])] = subval
            else:
                workout[key] = val
        workouts.append(workout)

    return workouts


@app.route("/sync", methods=["POST"])
def sync():
    """
    Sync results from Health Export into our data lake.
    """

    # fetch the raw JSON data
    raw_data = flask.request.json

    # transform the sync data and store it
    transformed = transform(raw_data)
    store(transformed)

    # transform the workout data and store it
    workouts = transform_workouts(raw_data)
    store_workouts(workouts)

    return flask.jsonify(
        success=True, message="Successfully received and stored sync data."
    )
