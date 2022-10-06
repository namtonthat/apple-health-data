"""Process Apple Health export to create a calendar of events."""

import glob
import os
import pandas as pd

from ics import Calendar, Event

import logging
logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


#  Calendar functions
def make_event_name(event_type, description):
    """
    Creates an event name with an emoticon
    """
    emoticons = {
        'sleep'     : "💤",
        'activity'  : "🔥",
        'food'      : "🥞",
        'mindful'   : "🧘",
        'exercise'  : "🏃",
        'weight'    : "🎚️",
        'average'   : "📈"
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

def make_description(row, event_type):
    """Create a description field for the event"""

    if event_type in ('sleep', 'activity'):
        time = row['qty']
        hours = int(time)
        minutes = int((time - hours) * 60)

        value = f"{hours} hours {minutes} mins"


    # elif event_type == 'food'

    description = f"{make_event_name(event_type)} {value}"

    return description

def generate_calendar(df):
    """
    Generates a CSV and ICS from the dataframe
    :param df: cleansed dataframe from `create_description_cols`
    :param outputs: as type string - a combination of both the local and public storage
    """

    # output_csv_path = f"{output_path}/{file_name}.csv"
    # calendar_file_name = f'{file_name}.ics'
    file_name = 'apple_health'

    csv_file_name = f"{file_name}.csv"
    ics_file_name  = f"{file_name}.ics"


    LOGGER.info("Generating calendar (as .ICS)")
    c = Calendar()
    for _, row in df.iterrows():
        e = create_event(row['date'], row['name'], row['dsc'])
        c.events.add(e)

    df.to_csv(csv_file_name, index=False)

    with open(ics_file_name, 'w') as f:
        f.write(str(c))
        f.close()

    LOGGER.info("Outputing CSV and ICS to: %s", csv_file_name)
    return

def convert_kj_to_cal(row, new_name):
    """Converts kj to calories"""
    row_dict = row.to_dict()
    calorie_value = int(row['qty']/4)

    # assign new value s
    row_dict['qty'] = calorie_value
    row_dict['name'] = new_name
    row_dict['units'] = 'kcal'

    return pd.DataFrame(row_dict, index=[0])

if __name__ == "__main__":
    base_folder = os.getcwd()
    source_folder = base_folder + '/healthlake/'
    apple_health_files = glob.glob(source_folder + '*.json')

    names = [
        'carbohydrates',
        'dietary_caffeine',
        'dietary_energy',
        'dietary_sugar',
        'fiber',
        'protein',
        'sleep_analysis',
        'total_fat',
        'weight_body_mass'
    ]

    cols = [
        'qty',
        'dates',
        'name',
        'units'
    ]
    df_raw = pd.DataFrame()

    for json_file in apple_health_files:
        json_raw = pd.read_json(json_file, lines = True)
        df_raw = pd.concat([df_raw, json_raw])

    ## Start of transformations

    df_ahc = df_raw.copy()

    # define transformations to go from df_raw to df_ahc (apple-health-calendar)
    # cleaning values
    df_ahc['dates'] = pd.to_datetime(df_ahc['date']).dt.date
    df_ahc['qty'] = df_ahc['qty'].fillna(df_ahc['asleep'])

    # create calories

    active_energy_rows = df_ahc[df_ahc['name'] == 'active_energy'][cols]
    dietary_energy_rows = df_ahc[df_ahc['name'] == 'dietary_energy'][cols]

    for _, row in active_energy_rows.iterrows():
        df_row = convert_kj_to_cal(row, 'calories_burnt')
        df_ahc = pd.concat([df_ahc, df_row])

    for _, row in dietary_energy_rows.iterrows():
        df_row = convert_kj_to_cal(row, 'calories_consumed')
        df_ahc = pd.concat([df_ahc, df_row])
    # filter out values
    df_ahc = df_ahc[df_ahc['name'].isin(names)][cols].reset_index(drop = True)

    # round values
    df_ahc['qty'] = df_ahc['qty'].round(2)

