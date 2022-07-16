"""
Simple Python script to render Apple Health data from Auto Exports
"""
from operator import truediv
import pandas as pd
import numpy as np
from datetime import datetime
import boto3
import os
import yaml
import flatdict

from ics import Calendar, Event


# %%
def ts_to_dt(ts):
    return datetime.fromtimestamp(ts)

def process_health_data(file):
    """
    Create [date, source] columns from files read in.
    :param file: as exported by Auto Health Export / Autosleep
    """
    df = pd.read_csv(file, sep = ',')
    print(f'Processing: {file.name}')
    if len(df.columns) > 1:
        df['creation_date'] = ts_to_dt(file.stat().st_atime)
        df['filename'] = file.name

        return df
    else:
        print(f'No data in {file.name}\r\n')

def read_raw_files(str_path):
    """
    Read all files in a directory and return a dataframe.
    :param str_path: directory path as type string
    """
    df_health = pd.DataFrame()
    df_sleep = pd.DataFrame()
    # valid_files = ['HealthAutoExport', 'AutoSleep']
    print('Reading files..')
    file_list = os.scandir(str_path)
    csv_files = [f for f in file_list if f.name.endswith('.csv')]

    for i in csv_files:
        df_tmp = process_health_data(i)
        if i.name.startswith('HealthAutoExport'):
            df_health = pd.concat([df_health, df_tmp])
        elif i.name.startswith('AutoSleep'):
            df_sleep = pd.concat([df_sleep, df_tmp])

    # ensure there is valid data
    if (len(df_health) > 0):
        if len(df_sleep) == 0:
            print('No Autosleep data found')
        return df_health, df_sleep
    else:
        print('No health data found.')
        exit

# %% [markdown]
# ### Transformations

# %% [markdown]
# Functions to cleanse the data
# - Rename columns
# - Dedupe values
# - Cleanse trim all values to closest integer except for sleep and weight
# - Create the following columns
#   - `Calories`


# %%
def update_columns(df, col_map):
    """
    Rename columns for easier reference
    Styling follows lowercase and no units with spaces being replaced by _
    """

    df.rename(columns=col_map, inplace=True)

    # fill in values
    df = df.replace(r'^\s+$', np.nan, regex=True)

    # convert column types
    df['date'] = pd.to_datetime(df['date']).dt.date
    # df['sleep_eff'] = df['sleep_eff'].fillna(0)
    # force apply float64 type for weight
    df['weight'] = df['weight'].astype(float)

    # Update column types
    df['calories'] = df['carbs'] * 4 + df['fat'] * 9 + df['protein'] * 4
    df['sleep_eff'] = df['sleep_asleep'] / df['sleep_in_bed'] * 100
    df['sleep_eff'] = df['sleep_eff'].fillna(0)
    df['sleep_eff'] = df['sleep_eff'].astype('int64')

    df['exercise'] = [1 if x > 30 else 0 for x in df['exercise_mins']]
    df['mindful'] = [1 if x > 5 else 0 for x in df['mindful_mins']]

    return df

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
                df[i] = np.floor(pd.to_numeric(df[i], errors= 'coerce')).astype('Int64')

            df[i] = df[i].fillna(0)
    return df

def dedup_df(df):
    """
    Remove duplicates ordering by 'date' and 'creation_date' and then keep only the latest
    """
    df_sort = df.sort_values(['date', 'creation_date'], ascending= True)
    df_dedup = df_sort.drop_duplicates(subset = 'date', keep = 'last')

    return df_dedup

# %%
def create_description_cols(df, is_autosleep=False):
    """
    Create description columns for the generating events
    Converts events into boolean
    """
    print("Creating description columns for calendar events")
    # cleansing Autosleep data
    if is_autosleep:
        print("Updating sleep statistics")
        df['dsc_sleep'] =  df.agg(lambda x:
            f"Deep sleep: {x['deep']} \r\n"
            f"Sleep efficiency: {int(x['efficiency'])}% \r\n"
            f"Bedtime: 🌒 {x['bedtime']} \r\n"
            f"Wakeup time: 🌞 {x['waketime']}",
            axis=1
        )

        df['sleep'] = df.agg(lambda x: f"{x['asleep']}", axis = 1)
        print(df.head())
        return df
    # cleansing Apple Health Data
    else:
        for i in df.columns:
            if df[i].dtypes == 'float64':
                df[i] = df[i].apply(lambda x: f"{x:,.1f}")
            elif df[i].dtypes in ('int64', 'Int64'):
                df[i] = df[i].map('{:,.0f}'.format)

        # Create columns descriptions for event description
        df['dsc_food'] = [f"{a}C / {b}P / {c}F" for a,b,c in zip(df['carbs'], df['protein'], df['fat'])]

        df['dsc_activity'] = df.agg(lambda x:
            f"{x['exercise_mins']} mins of exercise and "
            f"{x['mindful_mins']} mindful mins",
            axis=1
        )

        df['dsc_sleep'] = df.agg(lambda x:
            f"{x['sleep_asleep']} hrs asleep and "
            f"{x['sleep_in_bed']} hrs in bed",
            axis=1
        )

        # Create basic column descriptions for event names
        df['food'] = [f"{a} calories" for a in df['calories']]
        df['activity'] = [f"{a} steps" for a in df['steps']]
        df['sleep'] = [f"{a} h ({b} % eff.)" for a,b in zip(df['sleep_asleep'], df['sleep_eff'])]

        # Cleanse data
        df['sleep'] = df['sleep'].replace('nan h (0% eff.)', 'No sleep data.')

        return df

def convert_autosleep_time(time, is_24h=False):
    """
    Converts time from a string; stripping the date and adding the AM / PM / hours and minutes
    """
    time_dt = time.split(" ")[-1][:5]

    if is_24h:
        time_dt = datetime.strptime(time_dt, "%H:%M")
        time_dt = time_dt.strftime("%-I:%M %p")
    else:
        hours = int(time_dt.split(":")[0])
        min = int(time_dt.split(":")[1])
        time_dt = f"{hours} h {min} m"

    return time_dt

def etl_autosleep_data(df):
    """
    Cleans autosleep data into correct formatting
    """
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

    df = create_description_cols(df, is_autosleep=True)

    # Remove duplicates
    df = dedup_df(df)

    return df


def make_event_name(event_type, description):
    """
    Creates an event name with an emoticon
    """
    emoticons = {
        'sleep'     : "💤",
        'activity'  : "🔥",
        'food'      : "🥞",
        'mindful'   : "🧘",
        'exercise'  : "🏃"
    }

    emoticon = emoticons.get(event_type)

    # case statement to catch events that were not completed
    if description == 1:
        description = ""

    event_name = f"{emoticon} {description}"
    return event_name

# %%
def create_event(date, event_name, description: None):
    """
    Create an all day event for the given date and type
    :param date: date as type datetime.date
    :param event_name: name of event as string
    """
    all_day_date = f"{date} 00:00:00"
    e = Event()
    e.name = event_name
    e.description = description
    e.begin = all_day_date
    e.end = all_day_date
    e.make_all_day()

    return e

def create_events_df(df):
    """
    Unpivot dataframe and updates descriptions with emoticons
    """
    print("Generating calendar (as .CSV)")
    df_events = df[['date', 'food','sleep','activity', 'exercise', 'mindful']].melt(
        id_vars = ['date'],
        value_vars = ['food', 'sleep', 'activity', 'exercise', 'mindful'],
        var_name = 'event_type',
        value_name = 'event_name'
    )

    df_events_dsc = df[['date', 'dsc_food', 'dsc_sleep','dsc_activity']].melt(
        id_vars = ['date'],
        value_vars = ['dsc_food', 'dsc_sleep','dsc_activity'],
        var_name = 'event_type',
        value_name = 'dsc'
    )

    # TODO: make this into a function to speed up
    df_events_dsc['event_type'] = [x.split('dsc_')[-1] for x in df_events_dsc['event_type']]

    df_events['event_name'] = [make_event_name(a,b) for a,b in zip(df_events['event_type'], df_events['event_name'])]

    df_events = join_events(df_events, list_events=['activity', 'mindful', 'exercise'])

    # merge description into the events if available
    df_events = pd.merge(df_events, df_events_dsc, on = ['date','event_type'], how = 'left')

    return df_events


def join_events(df, list_events):
    """
    Joins multiple events into a single entry
    """
    print(f"Combining {list_events} into a single event")

    # Filter out events to join
    df_list_events = df.query(f'event_type in @list_events').sort_values(by= ['date', 'event_type'], ascending=True)
    df_list_events.fillna('', inplace=True)

    # join events together
    df_list_events['event_name'] = df_list_events.groupby('date')['event_name'].transform(lambda x: ' '.join(x))

    # cleanse trailing
    df_list_events['event_name'] = [x.strip() for x in df_list_events['event_name']]

    # Keep only the last events - as descriptions are duplicated
    df_list_events.drop_duplicates(subset = ['date', 'event_name'], keep = 'first', inplace = True)
    df_list_events.reset_index(drop=True, inplace=True)

    # merge back with original data
    df_events = pd.concat([df.query('event_type not in @list_events'), df_list_events])

    return df_events

def generate_calendar(df, outputs, aws_region: None):
    """
    Generates a CSV and ICS from the dataframe
    :param df: cleansed dataframe from `create_description_cols`
    :param outputs: as type string - a combination of both the local and public storage
    :param aws_region: as type string - the AWS S3 bucket region for uploading the ICS
    """
    output_path, output_cal, file_name = outputs

    output_csv_path = f"{output_path}/{file_name}.csv"
    calendar_file_name = f'{file_name}.ics'

    df_event = create_events_df(df)

    print("Generating calendar (as .ICS)")
    c = Calendar()
    for _, row in df_event.iterrows():
        e = create_event(row['date'], row['event_name'], row['dsc'])
        c.events.add(e)

    df_event.to_csv(output_csv_path)

    with open(calendar_file_name, 'w') as f:
        f.write(str(c))
        f.close()

    print(f"Outputing CSV and ICS to: {output_csv_path}")

    if output_cal.startswith("s3://") and region is not None:
        upload_to_s3(calendar_file_name, output_cal, region)

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

def upload_to_s3(file_name, output_cal, aws_region):
    """
    Send a file to S3
    :param calendar_file_name: name of .ICS file
    :param output_cal: location of public storage for calendar to reside in
    """
    print(f'Attempting to upload into public location: {output_cal}')
    bucket_name = output_cal.split('s3://')[1]

    data = open(file_name, 'rb')
    print(f"Reading {file_name}")

    s3 = boto3.resource('s3', region_name=aws_region)
    bucket = create_s3_bucket(s3, bucket_name, aws_region)
    bucket.put_object(Key= file_name, Body = data, ACL='public-read')

    print(f'Uploaded {file_name} for public read access')
    print(f'Subscribe to https://{bucket_name}.s3.{aws_region}.amazonaws.com/{file_name} for calendar events')

    return
# %%

def get_config(config_file):
    """
    Generate configs are read from config.yml
    If no values defined, return as current working directory
    """
    config = yaml.load(open(config_file, "r"),  Loader=yaml.FullLoader)
    config = flatdict.FlatDict(config, delimiter = '.')
    for k, v in config.items():
        if not k.startswith('type'):
            if v == "": config[k] = os.getcwd()

    return config

if __name__ == "__main__":
    # TODO: create function to calculate percentage of how close you are to your goal
    # TODO: refactor code so that the columns are parameterise - based on what they want to see in each event
    # TODO: create weekly summary statistics for Sunday
    # TODO: add in dropbox functionality
    # TODO: add serverless framework
    config = get_config('config.yml')
    input_path = config.get('input.raw_path')
    output_path = config.get('output.raw_path')
    output_cal = config.get('output.calendar_path')
    output_file_name = config.get('output.file_name')
    region = config.get('type.region')
    col_map = config.get('col_map')

    df, df_sleep = read_raw_files(input_path)

    df = update_columns(df, col_map)
    df = round_df(df)
    df = dedup_df(df)
    df = create_description_cols(df)
    df = df.reset_index(drop=True)

    # If Autosleep data is available, use that instead of Apple Health sleep data
    if len(df_sleep) > 0:
        df_health_sleep = etl_autosleep_data(df_sleep)
        df_merge = pd.merge(df, df_health_sleep[['date', 'dsc_sleep', 'sleep']],  on = 'date', how= 'left')

        # Take autosleep first but if not, take Apple Health
        df_merge['sleep'] = df_merge['sleep_y'].mask(pd.isnull, df_merge['sleep_x'])
        df_merge['dsc_sleep'] = df_merge['dsc_sleep_y'].mask(pd.isnull, df_merge['dsc_sleep_x'])

        # duplicated dataframe because if it doesn't exist, df_merge doesn't exist
        df = df_merge.copy()

    # Upload into S3 / public access bucket
    df = generate_calendar(df, outputs = [output_path, output_cal, output_file_name], aws_region = region)