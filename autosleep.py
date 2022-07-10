import pandas as pd

def process_health_data(file_name):
    """
    Create [date, source] from file.
    :param file: as exported by Auto Health Export
    """
    df = pd.read_csv(file, sep = ',')
    print(f'Processing: {file_name}')
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
    df = df.reset_index(drop=True)
    return df