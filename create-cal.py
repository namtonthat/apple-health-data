"""
Python script to create a calendar file from Apple Health Export

"""
from ics import Calendar, Event

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

if __name__ == "__main__":

    e = create_event("2022-06-26", "sleep", "8 hrs")
    e = create_event('2022-06-26', "activity", "11,041 steps")
    e = create_event('2022-06-26', "food", "2268 calories")
    write_event_to_file(e, "my.ics")

