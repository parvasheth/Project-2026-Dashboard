
import os
import logging
import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")

if not GARMIN_EMAIL or not GARMIN_PASSWORD or not GOOGLE_SHEET_KEY:
    logging.error("Missing environment variables. Please check .env file.")
    exit(1)

def init_garmin():
    """Initialize Garmin Connect API."""
    try:
        # Tries to use saved session first
        garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        garmin.login()
        logging.info("Garmin login successful.")
        return garmin
    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
        logging.error(f"Error occurred during Garmin login: {err}")
        return None

def init_gspread():
    """Initialize Google Sheets API."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(BASE_DIR, "service_account.json"), scope
        )
        client = gspread.authorize(creds)
        logging.info("Google Sheets login successful.")
        return client.open_by_key(GOOGLE_SHEET_KEY).sheet1
    except Exception as e:
        logging.error(f"Error connecting to Google Sheets: {e}")
        return None

def get_activities(garmin_client):
    """Fetch activities from Garmin starting from Jan 1, 2025."""
    try:
        start_date = "2025-01-01"
        today = datetime.date.today().isoformat()
        
        logging.info(f"Fetching activities from {start_date} to {today}...")
        
        # garminconnect's get_activities_by_date returns list of activities
        activities = garmin_client.get_activities_by_date(start_date, today)
        
        logging.info(f"Fetched {len(activities)} activities.")
        return activities
    except Exception as e:
        logging.error(f"Error fetching activities: {e}")
        return []

def process_activities(activities):
    """Process raw Garmin activities into a clean list of dicts."""
    data = []
    for activity in activities:
        # Extract relevant fields
        activity_type = activity.get("activityType", {}).get("typeKey", "unknown")
        
        # Calculate consistent pace (min/km) from speed (m/s) if applicable
        # Speed is m/s. 1 m/s = 3.6 km/h. Pace = 60 / (speed * 3.6)
        avg_speed = activity.get("averageSpeed", 0)
        
        row = {
            "Activity ID": activity.get("activityId"),
            "Date": activity.get("startTimeLocal"),
            "Type": activity_type,
            "Distance (km)": round(activity.get("distance", 0) / 1000, 2),
            "Duration (min)": round(activity.get("duration", 0) / 60, 2),
            "Avg HR": activity.get("averageHR", 0),
            "Max HR": activity.get("maxHR", 0),
            "Elevation Gain (m)": activity.get("totalElevationGain", 0),
            "Avg Speed (m/s)": avg_speed,
            "Coordinates": f"{activity.get('startLatitude')},{activity.get('startLongitude')}" if activity.get('startLatitude') else None
        }
        data.append(row)
    return data

def sync():
    garmin_client = init_garmin()
    sheet = init_gspread()

    if not garmin_client or not sheet:
        logging.error("Initialization failed. Aborting sync.")
        return
    
    # Fetch existing IDs to avoid duplicates
    try:
        existing_data = sheet.get_all_records()
        existing_ids = set(str(row.get("Activity ID")) for row in existing_data)
    except Exception:
        existing_ids = set()
        logging.info("Sheet might be empty or unreadable.")

    activities = get_activities(garmin_client)
    if not activities:
        logging.info("No activities found.")
        return

    processed_data = process_activities(activities)
    
    new_rows = []
    for record in processed_data:
        if str(record["Activity ID"]) not in existing_ids:
            # Prepare row list in order of headers if they exist, or just keys
            # Better to rely on a fixed structure
            # If sheet is empty, write headers
            if not existing_ids and not new_rows:
                # We need to set headers first if empty
                 headers = list(record.keys())
                 sheet.append_row(headers)
            
            new_rows.append(list(record.values()))

    if new_rows:
        # Provide value_input_option to parse dates/numbers correctly if needed
        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        logging.info(f"Synced {len(new_rows)} new activities.")
    else:
        logging.info("No new activities to sync.")

def get_wellness_data(garmin_client, sheet_conn):
    """Fetch daily wellness metrics (Steps, Sleep, Stress, BB, HRV)."""
    # 1. Determine start date
    try:
        wellness_sheet = sheet_conn.worksheet("Wellness")
    except gspread.exceptions.WorksheetNotFound:
        wellness_sheet = sheet_conn.add_worksheet(title="Wellness", rows=1000, cols=15)
        wellness_sheet.append_row(["Date", "Steps", "RHR", "Stress_Avg", "BodyBattery_Max", "BodyBattery_Min", "Sleep_Score", "Sleep_Hours", "HRV_ms", "VO2Max"])

    try:
        existing_data = wellness_sheet.get_all_records()
        existing_dates = set(row.get("Date") for row in existing_data)
        # Find last date
        if existing_dates:
            last_date_str = max(existing_dates)
            start_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date() + datetime.timedelta(days=1)
        else:
            start_date = datetime.date(2025, 1, 1)
    except Exception:
        existing_dates = set()
        start_date = datetime.date(2025, 1, 1)

    today = datetime.date.today()
    if start_date > today:
        logging.info("Wellness data is up to date.")
        return

    logging.info(f"Syncing Wellness data from {start_date} to {today}...")
    
    wellness_rows = []
    current_date = start_date
    
    while current_date <= today:
        date_str = current_date.isoformat()
        try:
            # Fetch various stats
            # 1. User Summary (Steps, RHR, Stress, VO2Max)
            # Garmin API often returns list for date, but sometimes just dict. 
            # We assume garminconnect returns stats for the day.
            # Using specific methods if available or generic fetch.
            
            # steps/hr/stress comes from 'user summary' usually
            summary = garmin_client.get_user_summary(date_str)
            
            # body battery
            bb_data = garmin_client.get_body_battery(date_str)
            
            # sleep (previous night)
            sleep_data = garmin_client.get_sleep_data(date_str)
            
            # hrv (previous night)
            hrv_data = garmin_client.get_hrv_data(date_str)
            
            # Parse
            # Summary fields
            steps = summary.get("totalSteps", 0)
            rhr = summary.get("restingHeartRate", 0)
            stress = summary.get("averageStressLevel", 0)
            vo2 = summary.get("vo2Max", 0)
            
            # Body Battery
            # bb_data is usually a list of values. We want stats if available or calc.
            # garminconnect usually returns a list of dictionaries for valid timeline
            bb_max = 0
            bb_min = 0
            if bb_data:
                # Assuming bb_data structure containing 'bodyBatteryValuesArray' or similar
                # Just simplified check:
                if isinstance(bb_data, list):
                   # It might be list of dicts with 'value'
                   vals = [x['value'] for x in bb_data if 'value' in x]
                   if vals:
                       bb_max = max(vals)
                       bb_min = min(vals)
                elif isinstance(bb_data, dict):
                     # sometimes returned as dict with bodyBatteryValueDescriptorDTOList
                     vals = [x['bodyBatteryLevel'] for x in bb_data.get('bodyBatteryValuesArray', []) if 'bodyBatteryLevel' in x]
                     if vals:
                        bb_max = max(vals)
                        bb_min = min(vals)

            # Sleep
            sleep_score = sleep_data.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value", 0)
            sleep_sec = sleep_data.get("dailySleepDTO", {}).get("sleepTimeSeconds", 0)
            sleep_hours = round(sleep_sec / 3600, 2)
            
            # HRV
            hrv_ms = hrv_data.get("hrvSummary", {}).get("weeklyAverage", 0) # Fallback
            # Try to get nightly avg
            if hrv_data.get("hrvSummary", {}).get("lastNightAvg"):
                hrv_ms = hrv_data.get("hrvSummary", {}).get("lastNightAvg")

            # Append
            wellness_rows.append([
                date_str,
                steps,
                rhr,
                stress,
                bb_max,
                bb_min,
                sleep_score,
                sleep_hours,
                hrv_ms,
                vo2
            ])
            logging.info(f"Fetched wellness for {date_str}")
            
        except Exception as e:
            logging.error(f"Failed to fetch/parse wellness for {date_str}: {e}")
        
        current_date += datetime.timedelta(days=1)
        # Sleep to avoid rate limits
        import time
        time.sleep(2)

    if wellness_rows:
        wellness_sheet.append_rows(wellness_rows, value_input_option="USER_ENTERED")
        logging.info(f"Synced {len(wellness_rows)} days of wellness data.")

def sync():
    garmin_client = init_garmin()
    sheet = init_gspread() # client.open_by_key(KEY) returns Spreadsheet object, not worksheet if using open_by_key().sheet1?
    # Wait, init_gspread returns .sheet1 currently.
    # We need the SPREADSHEET object to access multiple worksheets.
    
    # Let's adjust init_gspread logic temporarily or re-open here?
    # Easier: Re-init or fix init_gspread.
    # checking init_gspread implementation in lines 46-61.
    # line 58: return client.open_by_key(GOOGLE_SHEET_KEY).sheet1
    # We need the parent spreadsheet.
    
    # RE-READ init_gspread from file:
    # It returns sheet1.
    # So 'sheet' in sync() is a Worksheet.
    # We need the Spreadsheet to add/get 'Wellness'.
    
    # Workaround: Use sheet.spreadsheet to get parent
    spreadsheet = sheet.spreadsheet
    
    if not garmin_client or not sheet:
        logging.error("Initialization failed. Aborting sync.")
        return
    
    # 1. Activities Sync (Existing Logic)
    try:
        # Fetch existing IDs to avoid duplicates
        existing_data = sheet.get_all_records()
        existing_ids = set(str(row.get("Activity ID")) for row in existing_data)
    except Exception:
        existing_ids = set()
        logging.info("Sheet might be empty or unreadable.")

    activities = get_activities(garmin_client)
    if activities:
        processed_data = process_activities(activities)
        new_rows = []
        for record in processed_data:
            if str(record["Activity ID"]) not in existing_ids:
                if not existing_ids and not new_rows:
                     headers = list(record.keys())
                     sheet.append_row(headers)
                new_rows.append(list(record.values()))

        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
            logging.info(f"Synced {len(new_rows)} new activities.")
        else:
            logging.info("No new activities to sync.")
    
    # 2. Wellness Sync (New)
    get_wellness_data(garmin_client, spreadsheet)

if __name__ == "__main__":
    sync()
