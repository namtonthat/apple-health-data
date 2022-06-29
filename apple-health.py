"""
Simple Python script to render Apple Health data from Auto Exports
"""
import pandas as pd
import numpy as np
import datetime
import boto3
import sys, getopt
import os
import yaml

from ics import Calendar, Event


# %%
def ts_to_dt(ts):
    return datetime.datetime.fromtimestamp(ts)

# %%
def process_raw_data(file):
    """
    Create [date, source] from file.
    :param file: as exported by Auto Health Export
    """
    df = pd.read_csv(file, sep = ',')
    df['creation_date'] = ts_to_dt(file.stat().st_atime)
    df['filename'] = file.name

    return df

# %%
def read_raw_files(str_path):
    """
    Read all files in a directory and return a dataframe.
    :param str_path: directory path as type string
    """
    df = pd.DataFrame()
    print('Reading files..')
    for i in os.scandir(str_path):
        if i.name.startswith('HealthAutoExport') and i.name.endswith('Data.csv'):
            print(f'Reading: {i.name}')
            df_tmp = process_raw_data(i)
            df = pd.concat([df, df_tmp])

    # concat results in weird indices
    df = df.reset_index(drop=True)
    return df

# %% [markdown]
# ### Transformations

# %% [markdown]
# Functions to cleanse the data
# - Dedupe values
# - Cleanse trim all values to closest integer except for sleep and weight
# - Create the following columns
#   - `Calories`

# %%
def create_numeric_cols(df):
    """
    Calculates the total calories from the macros
    Calculates the sleep efficiency
    """
    df['calories'] = df['carbs'] * 4 + df['fat'] * 9 + df['protein'] * 4
    df['sleep_eff'] = df['sleep_asleep'] / df['sleep_in_bed'] * 100
    df['sleep_eff'] = df['sleep_eff'].fillna(0)
    df['sleep_eff'] = df['sleep_eff'].astype(int)

    return df

# %%
def round_df(df):
    """
    Round all numerical columns to closest integer except for one d.p. cols
    Replaces all NaN with null
    """
    one_dp_cols = ['sleep_asleep', 'sleep_in_bed', 'weight']
    for i in df.columns:
        if df[i].dtypes == 'float64':
            if i in one_dp_cols:
                df[i] = df[i].round(1)
            else:
                df[i] = df[i].astype(int)

    # df = df.replace({np.nan: None})
    return df

# %%
def convert_column_types(df):
    """
    Convert certain columns to be a certain type
    """
    df['date'] = pd.to_datetime(df['date']).dt.date

    # force apply float64 type for weight
    df['weight'] = df['weight'].astype(float)

    return df

# %%
def rename_columns(df):
    """
    Rename columns for easier reference
    Styling follows lowercase and no units with spaces being replaced by _
    """
    d_col_rename = {
        'Date': 'date',
        'Carbohydrates (g)': 'carbs',
        'Protein (g)': 'protein',
        'Total Fat (g)': 'fat',
        'Sleep Analysis [In Bed] (hr)': 'sleep_in_bed',
        'Sleep Analysis [Asleep] (hr)': 'sleep_asleep',
        'Step Count (count)': 'steps',
        'Weight & Body Mass (kg) ': 'weight'
    }

    df.rename(columns=d_col_rename, inplace=True)

    # fill in values
    df = df.replace(r'^\s+$', np.nan, regex=True)

    # convert column types
    df = convert_column_types(df)
    return df

# %%
def dedup_df(df):
    """
    Remove duplicates ordering by 'date' and 'creation_date' and then keep only the latest
    """
    df_sort = df.sort_values(['date', 'creation_date'], ascending= True)
    df_dedup = df_sort.drop_duplicates(subset = 'date', keep = 'last')

    return df_dedup

# %%
def create_description_cols(df):
    """
    Create description columns for the generating events
    """
    print("Adding commas as separator")
    for i in df.columns:
        print(f"{i} : {df[i].dtypes}")
        if df[i].dtypes == 'float64':
            df[i] = df[i].apply(lambda x: f"{x:,.1f}")
        elif df[i].dtypes == 'int64':
            df[i] = df[i].apply(lambda x: f"{x:,.0f}")

    print("Creating description columns")
    df_1 = df.astype(str)

    food_macros = "(" + df_1['carbs'] + "C/" + df_1['protein'] + "P/" + df_1['fat'] + "F" + ")"
    df['food'] = df_1['calories'] + " calories " + food_macros
    df['activity'] = df_1['steps'] + " steps"

    df['sleep'] = df_1['sleep_asleep'] + " h" + " (" + df_1['sleep_eff'] + "% eff.)"
    df['sleep'] = df['sleep'].replace('nan h (0% eff.)', 'No sleep data.')

    return df

# %%
def generate_calendar(df, output_path):
    """
    Generates a CSV and ICS from the dataframe
    :param df: cleansed dataframe from `create_description_cols`
    """
    print("Generating calendar")

    df_event = df[['date', 'food', 'activity', 'sleep']].melt(
        id_vars = ['date'],
        value_vars = ['food', 'activity', 'sleep'],
        var_name = 'type',
        value_name = 'description'
    )

    file_name = 'apple-health-calendar'
    output_csv_path = output_path + f'/{file_name}.csv'
    print(output_csv_path)
    df_event.to_csv(output_csv_path)

    c = Calendar()
    for _, row in df_event.iterrows():
        e = create_event(row['date'], row['type'], row['description'])
        c.events.add(e)
    calendar_file_name = file_name + '.ics'
    with open(calendar_file_name, 'w') as f:
        f.write(str(c))
        f.close()

    upload_to_s3(calendar_file_name)

    return df

# %%
def transform(df):
    """
    Round all numerical columns to closest integer except for sleep times and weight
    :param df: dataframe from the read_raw_files function
    """
    if len(df) > 0:
        df = rename_columns(df)
        df = round_df(df)
        df = dedup_df(df)
        df = create_numeric_cols(df)
        df = create_description_cols(df)

        return df

# %%
def etl_raw_data(input_path, output_path):
    """
    Perform ETL on Apple Health data
    :param input_path: directory path as type string
    :param output_path:
    """

    df = read_raw_files(input_path)
    df = transform(df)
    df = generate_calendar(df, output_path)

    return

# %%
def create_event(date, type, description):
    """
    Create an all day event for the given date and type
    :param date: date as type datetime.date
    :param type: type of event as type string
    :param description: description of event as type string
    """
    if type == 'sleep':
        emoticon = "💤"
    if type == 'activity':
        emoticon = "🔥"
    if type == 'food':
        emoticon = "🥞"

    all_day_date = str(date) + " 00:00:00"
    e = Event()
    e.name = emoticon + " " + description
    e.begin = all_day_date
    e.end = all_day_date
    e.make_all_day()

    return e


def create_s3_bucket(s3_resource, bucket_name, aws_region):
    """
    Create a bucket if it does not exist
    :param bucket_name: name of bucket
    """
    bucket = s3_resource.Bucket(bucket_name)
    if bucket.creation_date:
        print('Bucket already exists!')
    else:
        location = {'LocationConstraint': aws_region}
        bucket =  s3_resource.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration=location
        )

        print('Creating bucket')
    return bucket

def upload_to_s3(file_name):
    """
    Send a file to S3
    :param calendar_file_name: name of .ics file
    """
    # upload to S3 bucket
    # TODO: parameterise bucket name
    bucket_name = 'ntonthat-ahc'
    aws_region = 'ap-southeast-2'
    data = open(file_name, 'rb')
    print(f"Reading {file_name}")

    s3 = boto3.resource('s3', region_name=aws_region)
    bucket = create_s3_bucket(s3, bucket_name, aws_region)
    bucket.put_object(Key= file_name, Body = data, ACL='public-read')

    print(f'Uploaded {file_name} into bucket for public access')
    # TODO: print bucket name to subscribe to
    return
# %%

def get_config(config_file):
    """
    Geneerate configs are read from config.yml
    """
    config = yaml.load(open(config_file, "r"),  Loader=yaml.FullLoader)

    input_path = config['input'].get('raw_path')
    output_csv = config['output'].get('output_csv')
    output_cal =  config['output'].get('output_cal')

    paths = {
        'input_path': input_path,
        'output_csv': output_csv,
        'output_cal': output_cal
    }

    for path in paths.keys():
        if paths[path] == "":
            paths[path] = os.getcwd()

    return paths.values()

if __name__ == "__main__":
    input_path, output_csv, output_cal = get_config('config.yml')
    print(input_path, output_csv, output_cal)
    etl_raw_data(input_path = input_path, output_path = output_csv)