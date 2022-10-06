"""Process Apple Health export to create a calendar of events."""

import glob
import os
import pandas as pd

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

    #

    df_ahc = df_raw.copy()

    # define transformations to go from df_raw to df_ahc (apple-health-calendar)
    # cleaning values
    df_ahc['dates'] = pd.to_datetime(df_ahc['date']).dt.date
    df_ahc['qty'] = df_ahc['qty'].fillna(df_ahc['asleep'])

    # create calories

    active_energy = df_ahc[df_ahc['name'] == 'active_energy'][cols]
    calorie_name = "calories"
    calorie_unit = 'kcal'

    for _, row in active_energy.iterrows():
        row_dict = row.to_dict()
        calorie_value = int(row['qty']/4)

        # update values
        row_dict['qty'] = calorie_value
        row_dict['units'] = calorie_unit
        row_dict['name'] = calorie_name

        calorie_row = pd.DataFrame(row_dict, index=[0])
        # append
        df_ahc = pd.concat([df_ahc, calorie_row])

    # filter out values
    df_ahc = df_ahc[df_ahc['name'].isin(names)][cols].reset_index(drop = True)
