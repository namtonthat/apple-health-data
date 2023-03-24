import flask
import boto3
import csv
import sys
from common_functions import transform_all_data


# initialize our app and our S3 and Athena clients
app = flask.Flask(__name__)

# force the ability to parse very large CSV files
csv.field_size_limit(sys.maxsize)


@app.route("/sync", methods=["POST"])
def sync():
    """
    Sync results from Health Export into our data lake.
    """

    # fetch the raw JSON data
    raw_data = flask.request.json

    # parse the data
    transform_all_data(raw_data)

    return flask.jsonify(success=True, message="Successfully received and stored sync data.")
