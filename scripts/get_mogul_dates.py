from argparse import ArgumentParser
from bs4 import BeautifulSoup
import datetime as dt
from datetime import timedelta
import os.path
import pickle
import re
import requests

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_URL = 'https://www.chillfactore.com/plan-your-visit/events'
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_raw_data():
    # get raw scraped data
    response = requests.get(
        BASE_URL,
        timeout=5
    )

    return BeautifulSoup(response.content, 'html.parser')


def extract_dates(soup):
    dates_with_moguls = list()

    day_match_re = r'(?<=data-day=")(.*)(?=" data-month)'
    month_match_re = r'(?<=data-month=")(.*)(?=")'

    year = '2024'

    for i in soup.find_all(['figure']):
        if not 'alt="Moguls"' in str(i):
            continue
        # strip out date info
        _i = str(i)
        day = re.search(day_match_re, _i).group(0)
        month = re.search(month_match_re, _i).group(0)
        
        # format
        date = '-'.join([year, month, day])
        date = dt.datetime.strptime(date, '%Y-%b-%d').date()
        
        dates_with_moguls.append(date)
    return dates_with_moguls


def get_creds():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_new_calendar(service):
    new_calendar = {
        'summary': 'Dates of moguls',
        'timeZone': 'Europe/London',

    }
    
    return service.calendars().insert(body=new_calendar).execute()


def add_events_to_calender(service, created_calendar, dates_with_moguls):
    tz = 'Europe/London'

    for date in dates_with_moguls:

        start_date = dt.datetime(
            date.year,
            date.month,
            date.day,
            8
        ).isoformat()

        end_date = dt.datetime(
            date.year,
            date.month,
            date.day,
            23 
        ).isoformat()

        event = {
            'summary': 'Moguls',
            # 'location': '',
            # 'description': '',
            'start': {
                'dateTime': start_date,
                'timeZone': tz,
            },
            'end': {
                'dateTime': end_date,
                'timeZone': tz,
            },
        }

        service.events().insert(calendarId=created_calendar['id'], body=event).execute()


def main():

    # === scrape dates ===
    raw_data = get_raw_data()

    # find dates with moguls events
    dates_with_moguls = extract_dates(raw_data)

    print(f'Dates with moguls: {dates_with_moguls}')

    # === add to google calendar ===

    # get credentials and build service
    creds = get_creds()
    service = build('calendar', 'v3', credentials=creds)

    # create a new calendar
    created_calendar = create_new_calendar(service)
    print(f"Created calendar: {created_calendar['id']}")

    # insert moguls events
    add_events_to_calender(service, created_calendar, dates_with_moguls)


if __name__ == '__main__':

    main()

