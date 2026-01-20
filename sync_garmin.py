
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
load_dotenv()

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
            "service_account.json", scope
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

if __name__ == "__main__":
    sync()
