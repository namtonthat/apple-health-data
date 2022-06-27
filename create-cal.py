"""
Python script to create a calendar file from Apple Health Export

"""
from ics import Calendar, Event
import boto3

def create_event(date, type, description):
    """
    Create an all day event for the given date and type
    """
    if type == 'sleep':
        emoticon = "💤 "
    if type == 'activity':
        emoticon = "🔥"
    if type == 'food':
        emoticon = "🥞"

    all_day_date = date + " 00:00:00"
    e = Event()
    e.name = emoticon + description
    e.begin = all_day_date
    e.end = all_day_date
    e.make_all_day()

    return e

def create_new_calendar(event):
    """
    Create a new calendar file with the given event(s)
    """
    c = Calendar()
    c.events.add(event)
    return c

def create_s3_bucket(s3_resource, bucket_name, aws_region):
    """
    Create a bucket if it does not exist
    :param bucket_name: name of bucket
    """
    bucket = s3_resource.Bucket(bucket_name)
    if bucket.creation_date:
        return
    else:
        location = {'LocationConstraint': aws_region}
        bucket =  s3_resource.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration=location
        )
    return

def write_event_to_file(event, filename):
    """
    Write a calendar event to a file; otherwise create a new calendar
    """
    try:
        with open(filename, 'r+') as f:
            position = f.tell()
            line = f.readline()
            while line!="END:VCALENDAR":
                position = f.tell()
                line = f.readline()
            f.seek(position, 0)

            # write the new event and close off
            f.write(str(event))
            f.write("\nEND:VCALENDAR")
            f.close()

    except FileNotFoundError:
        c = create_new_calendar(event)
        with open(filename, 'w') as f:
            f.write(str(c))
            f.close()

def send_files_to_s3(filename, date):
    """
    Send a file to S3 partitioned by date
    :param filename: name of .ics file
    :param date: date of the file
    """
    # split date
    str_date = date.split('-')
    year = str_date[0]
    month = str_date[1]
    day = str_date[2]
    bucket_name = 'apple-health-calendar'
    aws_region = 'ap-southeast-2'
    data_filename = open(filename, 'rb')

    s3 = boto3.resource('s3', region_name=aws_region)
    bucket = create_s3_bucket(s3, bucket_name, aws_region)
    # upload to S3
    bucket.put_object(Key=year+'/'+month+'/'+day+'/'+filename, Body=data_filename)

    return


if __name__ == "__main__":
    date = '2022-06-26'
    # e = create_event("2022-06-27", "sleep", "8 hrs")
    e = create_event(date, "activity", "13,042 steps")
    # e = create_event('2022-06-26', "food", "2268 calories")
    write_event_to_file(e, f"{date}.ics")
    send_files_to_s3(f"{date}.ics", date)