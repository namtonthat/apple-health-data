"""Process Apple Health export to create a calendar of events."""

import glob
import os
import pandas as pd


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

