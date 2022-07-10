"""
Simple Python script to render Apple Health data from Auto Exports
"""
import pandas as pd
import numpy as np
from datetime import datetime
import boto3
import os
import yaml

from ics import Calendar, Event


# %%
def ts_to_dt(ts):
    return datetime.fromtimestamp(ts)

def process_health_data(file):
    """
    Create [date, source] from file.
    :param file: as exported by Auto Health Export
    """
    df = pd.read_csv(file, sep = ',')
    print(f'Processing: {file.name}')
    df['creation_date'] = ts_to_dt(file.stat().st_atime)
    df['filename'] = file.name

    return df

def read_raw_files(str_path):
    """
    Read all files in a directory and return a dataframe.
    :param str_path: directory path as type string
    """
    df_health = pd.DataFrame()
    df_sleep = pd.DataFrame()
    # valid_files = ['HealthAutoExport', 'AutoSleep']
    print('Reading files..')
    for i in os.scandir(str_path):
        if i.name.endswith('.csv'):
            df_tmp = process_health_data(i)
            if i.name.startswith('HealthAutoExport'):
                df_health = pd.concat([df_health, df_tmp])
            elif i.name.startswith('AutoSleep'):
                df_sleep = pd.concat([df_sleep, df_tmp])

    # concat results in weird indices
    df_health = df_health.reset_index(drop=True)
    return df_health, df_sleep


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
    print("Creating description columns for calendar events")
    for i in df.columns:
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
def transform(df):
    """
    Round all numerical columns to closest integer except for sleep times and weight
    :param df: dataframe from the read_raw_files function
    """
    # Fix up df_health
    if len(df) > 0:
        df = rename_columns(df)
        df = round_df(df)
        df = dedup_df(df)
        df = create_numeric_cols(df)
        df = create_description_cols(df)

        return df


def convert_autosleep_time(time, is_24h=False):
    """
    Converts time as from a string, stripping the date and adding the AM / PM
    """
    time_dt = time.split(" ")[-1][:5]

    if is_24h:
        time_dt = datetime.strptime(time_dt, "%H:%M")
        time_dt = time_dt.strftime("%-I:%M %p")
    else:
        hours = int(time_dt.split(":")[0])
        min = int(time_dt.split(":")[1])
        time_dt = str(hours) + " h " + str(min) + " m"

    return time_dt

def etl_autosleep_data(df_sleep):
    """
    Cleans autosleep data into correct formatting
    """
    # Create a copy for non destructive debugging
    df = df_sleep.copy()

    #  Clean up the time columns with either 12 h format (AM / PM) or with hours and minutes
    time_dict = {
        '24h': ['bedtime', 'waketime'],
        'hrs': ['asleep', 'deep']
    }
    for time_type, time_cols in time_dict.items():
        is_24h = 0
        for time_col in time_cols:
            if time_type == '24h': is_24h = 1
            df[time_col] = df[time_col].apply(lambda x: convert_autosleep_time(x, is_24h))

    # Collect the date
    df['date'] = df['ISO8601'].apply(lambda x: datetime.strptime(x.split("T")[0], '%Y-%m-%d').date())

    df['sleep'] = df.agg(lambda x: f"{x['asleep']} [{x['deep']} / {int(x['efficiency'])}%]\r\n(🌒 {x['bedtime']} /🌞 {x['waketime']})", axis = 1)

    # Remove duplicates
    df = df.drop_duplicates(subset = ['date'], keep = 'last').sort_values(by = ['date']).reset_index(drop = True)

    return df

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

def generate_calendar(df, output_path):
    """
    Generates a CSV and ICS from the dataframe
    :param df: cleansed dataframe from `create_description_cols`
    :param output_path: as type string - a combination of both the local and public storage
    """
    output_csv = output_path[0]
    output_cal = output_path[1]
    file_name = 'apple-health-calendar'

    output_csv_path = output_csv + f'/{file_name}.csv'
    calendar_file_name = file_name + '.ics'

    print("Generating calendar (as CSV)")
    df_event = df[['date', 'food', 'activity', 'sleep']].melt(
        id_vars = ['date'],
        value_vars = ['food', 'activity', 'sleep'],
        var_name = 'type',
        value_name = 'description'
    )

    print("Generating calendar (as .ICS)")
    c = Calendar()
    for _, row in df_event.iterrows():
        e = create_event(row['date'], row['type'], row['description'])
        c.events.add(e)

    df_event.to_csv(output_csv_path)

    with open(calendar_file_name, 'w') as f:
        f.write(str(c))
        f.close()

    print(f"Outputing csv and cal to: {output_csv_path}")

    if output_cal.startswith("s3://"):
        upload_to_s3(calendar_file_name, output_cal)

    return

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

def upload_to_s3(file_name, output_cal):
    """
    Send a file to S3
    :param calendar_file_name: name of .ics file
    :param output_cal: location of public storage for calendar to resdie in
    """
    print(f'Attempting to upload into public location: {output_cal}')
    # upload to S3 bucket
    bucket_name = output_cal.split('s3://')[1]
    # TODO: parameterise aws_region
    aws_region = 'ap-southeast-2'
    data = open(file_name, 'rb')
    print(f"Reading {file_name}")

    s3 = boto3.resource('s3', region_name=aws_region)
    bucket = create_s3_bucket(s3, bucket_name, aws_region)
    bucket.put_object(Key= file_name, Body = data, ACL='public-read')

    print(f'Uploaded {file_name} for public read access')
    print(f'Subscribe to {output_cal}/{file_name} for calendar events')

    return
# %%

def get_config(config_file):
    """
    Geneerate configs are read from config.yml
    If no values defined, return as current working directory
    """
    config = yaml.load(open(config_file, "r"),  Loader=yaml.FullLoader)
    # TODO: iterate over variables quicker
    input_path = config['input'].get('raw_path')
    output_local = config['output'].get('output_local')
    output_cal =  config['output'].get('output_cal')

    paths = {
        'input_path': input_path,
        'output_local': output_local,
        'output_cal': output_cal
    }

    for path in paths.keys():
        if paths[path] == "":
            paths[path] = os.getcwd()

    return paths.values()

if __name__ == "__main__":
    # TODO: simplify input and output paths
    input_path, output_local, output_cal = get_config('config.yml')
    print(input_path, output_local, output_cal)

    # TODO: create weight list
    df_health, df_sleep = read_raw_files(input_path)
    df = transform(df_health)

    # Fix up df_sleep
    if len(df_sleep) > 0:
        df_health_sleep = etl_autosleep_data(df_sleep)
        df_merge = pd.merge(df, df_health_sleep,  on = 'date', how= 'left')[['date', 'food', 'activity', 'sleep_x', 'sleep_y']]
        df_merge['sleep'] = df_merge['sleep_y'].mask(pd.isnull, df_merge['sleep_x'])
        df = df_merge[['date', 'food', 'activity', 'sleep']]

    df = generate_calendar(df, output_path = [output_local, output_cal])