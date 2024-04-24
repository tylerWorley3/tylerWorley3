import pandas as pd
import glob
from io import StringIO
import os
import matplotlib.pyplot as plt

#Total on time/number of cycles
#Total on time, total cycles, total active/enable
# total active has to be Ready, Pre-heat,  need to have on time coutner an off time coutner based on the time 
# Total number of cycle add each cycle, then have a total number of on time. 
# Define necessary columns

necessary_columns = [
    'DATE', 'TIME', 
    'SHELF 1 STAT', 'SHELF 1 UPR STAT', 'SHELF 1 LWR STAT',
    'SHELF 2 STAT', 'SHELF 2 UPR STAT', 'SHELF 2 LWR STAT',
    'SHELF 3 STAT', 'SHELF 3 UPR STAT', 'SHELF 3 LWR STAT',
    'SHELF 4 STAT', 'SHELF 4 UPR STAT', 'SHELF 4 LWR STAT',
    'SHELF 5 STAT', 'SHELF 5 UPR STAT', 'SHELF 5 LWR STAT',
    'SHELF 6 STAT', 'SHELF 6 UPR STAT', 'SHELF 6 LWR STAT'
]

shelf_upr_lwr_columns = [
    'SHELF 1 UPR STAT', 'SHELF 1 LWR STAT',
    'SHELF 2 UPR STAT', 'SHELF 2 LWR STAT',
    'SHELF 3 UPR STAT', 'SHELF 3 LWR STAT',
    'SHELF 4 UPR STAT', 'SHELF 4 LWR STAT',
    'SHELF 5 UPR STAT', 'SHELF 5 LWR STAT',
    'SHELF 6 UPR STAT', 'SHELF 6 LWR STAT'
]
stat_columns = [
    'SHELF 1 STAT',
    'SHELF 2 STAT',
    'SHELF 3 STAT', 
    'SHELF 4 STAT',
    'SHELF 5 STAT',
    'SHELF 6 STAT'
]
def is_structured_data_line(line):
    return any(indicator in line for indicator in ["DATE", "TIME", "UTC", "DST Enabled", "STATUS", "SHELF"])

def seems_like_report_or_empty_line(line):
    return line.count(',') > 10 and len(line.replace(',', '').strip()) < 10

def calculate_cycle_durations(df, column):  
    df_copy = df.copy()
    stripped_column = df_copy[column].str.strip()
    
    # Mark the start of a cycle as the first 'ON' in the data or an 'ON' following an 'OFF'
    is_first_on = (stripped_column == 'ON') & ((stripped_column.shift(1) != 'ON') | (stripped_column.shift(1).isna()))
    df_copy.loc[:,'ON_START'] = df_copy.loc[is_first_on, 'DATETIME']
    
    # Mark the end of a cycle as 'ON' just before an 'OFF'
    is_last_on = (stripped_column == 'ON') & (stripped_column.shift(-1) != 'ON')
    df_copy.loc[:,'ON_END'] = df_copy.loc[is_last_on, 'DATETIME']
    
    # Forward fill the start times to associate all 'ON' states with a start time
    df_copy['ON_START'] = df_copy['ON_START'].ffill()
    
    valid_cycles = df_copy[df_copy['ON_START'].notnull() & df_copy['ON_END'].notnull()].copy()
    valid_cycles.loc[:,'CYCLE_DURATION'] = (valid_cycles['ON_END'] - valid_cycles['ON_START']).dt.total_seconds() / 3600

    # Count the cycles per day
    valid_cycles['DATE'] = valid_cycles['ON_START'].dt.date

    return valid_cycles[['ON_START', 'ON_END', 'CYCLE_DURATION']]

def calculate_total_enabled_time(df, stat_columns):
    total_enabled_times = {}
    for column in stat_columns:
        enabled_time = 0
        

        for index, row in df.iterrows():
            # Handle cases where the data might be NaN or not a string
            current_status = row[column]
            if pd.notna(current_status):
                current_status = str(current_status).strip()
            else:
                continue  # Skip this iteration if the status is NaN


            if current_status in ['READY', 'PRE HEAT']:
                # Assuming the data is recorded in regular time intervals, we increment the enabled time
                enabled_time += 1  # Increment by 1 unit of time interval (e.g., 1 second)

        # Convert the total enabled time into hours assuming data is recorded every second
        total_enabled_time_in_hours = enabled_time / 3600
        total_enabled_times[column] = total_enabled_time_in_hours

    return total_enabled_times



def calculate_heater_stats(df, column, day_count):
    df_copy = df.copy()
    stripped_column = df_copy[column].str.strip()

    # Mark the start of a cycle as the first 'ON' in the data or an 'ON' following an 'OFF'
    is_first_on = (stripped_column == 'ON') & ((stripped_column.shift(1) != 'ON') | (stripped_column.shift(1).isna()))
    df_copy.loc[:,'ON_START'] = df_copy.loc[is_first_on, 'DATETIME']
    
    # Mark the end of a cycle as 'ON' just before an 'OFF'
    is_last_on = (stripped_column == 'ON') & (stripped_column.shift(-1) != 'ON')
    df_copy.loc[:,'ON_END'] = df_copy.loc[is_last_on, 'DATETIME']
    
    df_copy['ON_START'] = df_copy['ON_START'].ffill()
    
    # Ensure that complete_cycles is a copy, not a view
    complete_cycles = df_copy.loc[df_copy['ON_START'].notnull() & df_copy['ON_END'].notnull()].copy()

    # Calculate the cycle duration in seconds
    complete_cycles['CYCLE_DURATION'] = (complete_cycles['ON_END'] - complete_cycles['ON_START']).dt.total_seconds() / 3600

    total_on_time = complete_cycles['CYCLE_DURATION'].sum()
    total_cycles = complete_cycles['ON_START'].nunique()

    if day_count == 1:
        daily_total_on_time = total_on_time
    else:
        daily_total_on_time = total_on_time / day_count

    daily_active_time = daily_total_on_time / total_cycles if total_cycles > 0 else 0

    return daily_total_on_time, total_cycles, daily_active_time

directory_path = input("Enter the directory path containing the CSV files: ")
output_file_path = 'cleaned_structured_data.csv'
print("1")
day_count = 0

all_data = []
for file_path in glob.glob(directory_path + '/*.csv'):
    print("2")
    # Check file size before processing
    if os.path.getsize(file_path) < 15000000:  # 15,000 KB 
        print("3")
        continue
    day_count += 1
    with open(file_path, 'r') as file:
        print("4")
        lines = file.readlines()

    filtered_lines = [line for line in lines if is_structured_data_line(line) and not seems_like_report_or_empty_line(line)]
    print("5")
    if filtered_lines:
        print("6")
        df = pd.read_csv(StringIO(''.join(filtered_lines)), on_bad_lines='skip', low_memory=False)
        all_data.append(df)

if all_data:
    print("7")
    df_cleaned = pd.concat(all_data, ignore_index=True)
    df_cleaned.columns = df_cleaned.columns.str.strip()
    df_cleaned['DATETIME'] = pd.to_datetime(df_cleaned['DATE'] + ' ' + df_cleaned['TIME'], errors='coerce')
    df_cleaned.sort_values('DATETIME', inplace=True)

    # Convert the 'DATETIME' column to datetime type
    df_cleaned['DATETIME'] = pd.to_datetime(df_cleaned['DATETIME'])

    # Ensure the data is sorted by date
    df_cleaned = df_cleaned.sort_values('DATETIME')

    # Calculate the time difference between consecutive rows
    df_cleaned['TIME_DIFF'] = df_cleaned['DATETIME'].diff().shift(-1)

    # Set a threshold to identify significant gaps, for example, 5 minutes
    gap_threshold = pd.Timedelta(seconds=2)

    # Filter out the gaps that are considered as system off time
    operating_periods = df_cleaned[df_cleaned['TIME_DIFF'] <= gap_threshold]['TIME_DIFF']

    # Convert time difference to hours and sum to get the total operating hours
    total_operating_hours = operating_periods.dt.total_seconds().sum() / 3600
    if day_count > 1 : 
        # This tells us how long the cabinet was on per day. 
        average_total_operating_hours = total_operating_hours / 24
    else:
        average_total_operating_hours = total_operating_hours
    print(f"Total operating hours: {total_operating_hours}")
    total_enabled_times = calculate_total_enabled_time(df_cleaned, stat_columns)
    for shelf, time in total_enabled_times.items():
        enabled_time_ratio = time / total_operating_hours
        print(f"{shelf}: {enabled_time_ratio} hours")


    for col in shelf_upr_lwr_columns[0:]:  # Starting from the 3rd column to skip 'DATE' and 'TIME'
        if col in df_cleaned.columns:
            cycle_durations = calculate_cycle_durations(df_cleaned, col)
            total_on_time, total_cycles, total_active_time = calculate_heater_stats(df_cleaned, col, average_total_operating_hours)
        
            if not cycle_durations.empty:
                daily_average = cycle_durations['CYCLE_DURATION'].sum()
                print(f"{col} daily average:")
                print(f"Daily Average: Total cycles: {total_cycles / average_total_operating_hours}")
                print(f"Daily Average: Total heat ON time : {daily_average / average_total_operating_hours} hours")
                print("\n")
                



            

