import logging
import pandas as pd
import boto3
import json


def get_s3_keys(bucket):
    """Get a list of keys in an S3 bucket."""
    keys = []
    personal = boto3.Session(profile_name='personal')
    s3 = personal.client('s3')
    resp = s3.list_objects(Bucket=bucket)
    for obj in resp['Contents']:
        keys.append(obj['Key'])
    return keys


def load_json_from_s3(bucket, key):
    """Parse a json file from s3 and return the contents"""
    # personal = boto3.Session(profile_name='personal')
    # s3 = personal.resource('s3')

    obj = s3.Object(bucket, key)
    body = obj.get()['Body']
    body = body.read().decode('utf-8')
    return body


def read_s3_trigger(trigger_event):
    """Read the s3 event trigger and return the bucket and key"""
    logging.info('Reading s3 event trigger')
    s3_event = json.loads(open(f'{trigger_event}', 'r').read())

    s3_key = s3_event.get("Records")[0].get('s3').get('object').get('key')
    s3_bucket = s3_event.get("Records")[0].get('s3').get('bucket').get('name')

    return s3_bucket, s3_key


def run(event):
    s3 = boto3.resource('s3')
    # personal = boto3.Session(profile_name='personal')
    # s3 = personal.resource('s3')
    bucket, key = read_s3_trigger(event)

    # convert contents to native python string
    json_data = load_json_from_s3(bucket, key)

    source_data = []

    for line in json_data.splitlines():
        source_data.append(json.loads(line))

    logging.info('Converting to dataframe')
    df = pd.DataFrame.from_records(source_data)

    # force conversion types
    df['qty'] = df['qty'].astype(str)
    df['date'] = pd.to_datetime(df['date']).dt.date

    logging.info('Converting to parquet')

    # write to parquet
    file_name = key.split('/')[-1].split('.')[0]
    parquet_file_name = f'outputs/parquets/{file_name}.parquet'
    df.to_parquet(f'{parquet_file_name}')

    s3.meta.client.upload_file(f'{parquet_file_name}', bucket, f'parquets/{parquet_file_name}')

    return