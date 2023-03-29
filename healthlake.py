import flask
import boto3
import json
import conf
from typing import Dict, List
from datetime import datetime
import logging

# initialize app and S3 and Athena clients
app = flask.Flask(__name__)
s3 = boto3.client("s3")


def store_raw_data(data: dict) -> dict:
    """
    Store raw health export data in raw/ prefix S3 bucket.
    """
    key_name = "raw/" + datetime.utcnow().isoformat() + ".json"

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=json.dumps(data))


def store(rows: List[dict]) -> dict:
    """
    Store rows of health export data in syncs/ S3 bucket.
    """

    key_name = "syncs/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(row, default=str).strip() for row in rows]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


def store_workouts(workouts: List[dict]) -> dict:
    """
    Store rows of workout data in S3 bucket.
    """

    key_name = "workouts/" + datetime.utcnow().isoformat() + ".json"

    # athena and glue prefer a row of JSON per line
    json_rows = [json.dumps(workout).strip() for workout in workouts]
    content = "\n".join(json_rows)

    s3.put_object(Bucket=conf.bucket, Key=key_name, Body=content)


def unnest_data_points(data: Dict) -> List[Dict]:
    """
    Unnest data points from a single metric.
    Parent column fields are 'name', 'units', and 'date'.
    """
    unnest_rows = []

    # parent data point values
    prefix = data["name"]
    nested_unit = data["units"]
    date = data["date"]
    parent_data_points = ["name", "units", "date"]

    for col_name, qty in data.items():
        # filter out parent values
        if col_name not in parent_data_points:
            point = {}
            col_name = f"{prefix}_{col_name}"

            point["name"] = col_name
            point["units"] = nested_unit
            point["date"] = date
            point["qty"] = qty
            unnest_rows.append(point)

    return unnest_rows


def transform(data: dict) -> List[Dict]:
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
            has_qty = point.get("qty")
            if has_qty:
                rows.append(point)
            else:
                unnested_data_points = unnest_data_points(point)
                rows.extend(unnested_data_points)

    # add a date_updated field to each row
    for entry in rows:
        entry["date_updated"] = datetime.now()

    return rows


def transform_workouts(data: dict) -> List[Dict]:
    """
    Flatten the nested JSON data structure from Health Export
    for workouts to make it e`a`sier to index and query with Athena.
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


@app.route("/syncs", methods=["POST"])
def syncs():
    """
    Sync results from Health Export into data lake.
    """

    # fetch the raw JSON data
    raw_data = flask.request.json
    store_raw_data(raw_data)

    # transform the sync data and store it
    logging.info("transform raw data")
    transformed = transform(raw_data)
    store(transformed)

    # transform the workout data and store it
    logging.info("transform workout data")
    workouts = transform_workouts(raw_data)
    store_workouts(workouts)

    return flask.jsonify(success=True, message="Successfully received and stored sync data.")
