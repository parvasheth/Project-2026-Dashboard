
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
import pytz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

# Garmin Credentials
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")

# Google Sheets Credentials
SERVICE_ACCOUNT_FILE = os.path.join(script_dir, 'service_account.json')
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
            SERVICE_ACCOUNT_FILE, scope
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
        # Find last date. We do NOT add 1 day so we overwrite the last recorded day (usually today) with intraday updates.
        if existing_dates:
            last_date_str = max(existing_dates)
            start_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
        else:
            start_date = datetime.date(2025, 1, 1)
    except Exception:
        existing_dates = set()
        existing_data = [] # ensure empty list instead of fail
        start_date = datetime.date(2025, 1, 1)

    today = datetime.date.today()
    if start_date > today:
        start_date = today

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
            steps = summary.get("totalSteps") or 0
            active_cal = summary.get("activeKilocalories") or 0
            rhr = summary.get("restingHeartRate") or 0
            stress = summary.get("averageStressLevel") or 0
            vo2 = summary.get("vo2MaxValue") or 0
            
            # Fallback: Training Status
            if vo2 == 0:
                try:
                     logging.info(f"VO2 0 in summary, trying Training Status for {date_str}")
                     train_status = garmin_client.get_training_status(date_str)
                     # usually returns dict with 'vo2Max'
                     if train_status and isinstance(train_status, dict):
                         vo2 = train_status.get('vo2Max') or 0
                except Exception as e:
                     logging.warning(f"Training status failed: {e}")
            
            # Body Battery
            bb_max = 0
            bb_min = 0
            if bb_data:
                # Based on garminconnect returning a list of dicts per day
                if isinstance(bb_data, list) and len(bb_data) > 0:
                   first_item = bb_data[0]
                   if "bodyBatteryValuesArray" in first_item:
                       # This is the array of [timestamp, level] or similar
                       vals = [x[1] for x in first_item["bodyBatteryValuesArray"] if len(x) >= 2 and x[1] is not None]
                       if vals:
                           bb_max = max(vals)
                           bb_min = min(vals)
                   elif "value" in first_item:
                       vals = [x['value'] for x in bb_data if 'value' in x and x['value'] is not None]
                       if vals:
                           bb_max = max(vals)
                           bb_min = min(vals)

            # Sleep
            sleep_score = sleep_data.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value") or 0
            sleep_sec = sleep_data.get("dailySleepDTO", {}).get("sleepTimeSeconds") or 0
            sleep_hours = round(sleep_sec / 3600, 2)
            
            # HRV
            hrv_ms = hrv_data.get("hrvSummary", {}).get("weeklyAverage") or 0 # Fallback
            # Try to get nightly avg
            if hrv_data.get("hrvSummary", {}).get("lastNightAvg"):
                hrv_ms = hrv_data.get("hrvSummary", {}).get("lastNightAvg") or 0

            new_row = [
                date_str,
                steps,
                rhr,
                stress,
                bb_max,
                bb_min,
                sleep_score,
                sleep_hours,
                hrv_ms,
                vo2,
                active_cal
            ]

            if date_str in existing_dates:
                row_idx = next((i for i, row in enumerate(existing_data) if str(row.get("Date")).startswith(date_str)), None)
                if row_idx is not None:
                    sheet_row = row_idx + 2
                    wellness_sheet.update(range_name=f"A{sheet_row}", values=[new_row])
                    logging.info(f"Updated wellness for {date_str}")
            else:
                wellness_rows.append(new_row)
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

def get_intraday_data(garmin_client, start_date, days=3):
    """Fetch intraday data (HR, Stress, Sleep Stages) for the last N days."""
    intraday_data = []
    
    # Calculate date range (Today back to N days ago)
    end_date = datetime.date.today()
    start = end_date - datetime.timedelta(days=days)
    
    current = end_date
    while current >= start:
        date_str = current.isoformat()
        try:
            logging.info(f"Fetching Intraday: {date_str}...")
            
            # 1. Heart Rate (Values are [timestamp_ms, value])
            hr_data = garmin_client.get_heart_rates(date_str)
            hr_values = hr_data.get('heartRateValues', [])
            if hr_values:
                for entry in hr_values:
                    if entry[1]: # Scan for valid HR
                        # Timestamp is GMT ms
                        ts = datetime.datetime.fromtimestamp(entry[0]/1000, pytz.utc)
                        intraday_data.append({
                            "Type": "HeartRate",
                            "Date": date_str,
                            "Timestamp": ts.isoformat(),
                            "Value": entry[1]
                        })

            # 2. Stress & Body Battery
            stress_data = garmin_client.get_stress_data(date_str)
            stress_values = stress_data.get('stressValuesArray', [])
            bb_values = stress_data.get('bodyBatteryValuesArray', [])
            
            # Stress: [timestamp, level]
            for entry in stress_values:
                if entry[1] is not None and entry[1] >= 0:
                    ts = datetime.datetime.fromtimestamp(entry[0]/1000, pytz.utc)
                    intraday_data.append({
                        "Type": "Stress",
                        "Date": date_str,
                        "Timestamp": ts.isoformat(),
                        "Value": entry[1]
                    })
            
            # Body Battery
            for entry in bb_values:
                 if len(entry) > 0:
                     ts = datetime.datetime.fromtimestamp(entry[0]/1000, pytz.utc)
                     val = entry[-1] # Level is usually last
                     if val is not None:
                        intraday_data.append({
                            "Type": "BodyBattery",
                            "Date": date_str,
                            "Timestamp": ts.isoformat(),
                            "Value": val
                        })

            # 3. Sleep Levels (Hypnogram)
            sleep_data = garmin_client.get_sleep_data(date_str)
            sleep_levels = sleep_data.get('dailySleepDTO', {}).get('sleepLevels', [])
            # Actually get_sleep_data returns the full object. 'dailySleepDTO' might not be top level in some versions.
            # Using logic from reference: all_sleep_data.get("sleepLevels")
            if not sleep_levels:
                sleep_levels = sleep_data.get('sleepLevels', [])
                
            for entry in sleep_levels:
                # {startGMT, endGMT, activityLevel}
                # activityLevel: 0=Unknown, 1=Deep, 2=Light, 3=REM, 4=Awake
                if 'startGMT' in entry and 'endGMT' in entry:
                     # Formats are like "2025-01-23T05:00:00.000"
                     intraday_data.append({
                         "Type": "SleepStage",
                         "Date": date_str,
                         # Use Start Time as Timestamp
                         "Timestamp": entry['startGMT'], 
                         "EndTimestamp": entry['endGMT'],
                         "Value": entry.get('activityLevel')
                     })

            # 4. Steps Intraday (15-min or 1-min intervals)
            # garmin_connect.get_steps_data(date) returns list of dicts: {startGMT, endGMT, steps}
            steps_data = garmin_client.get_steps_data(date_str)
            if steps_data:
                for entry in steps_data:
                    # Filter out zero steps to save space? Keep them for heatmap continuity.
                    if 'steps' in entry and entry['steps'] > 0:
                         intraday_data.append({
                             "Type": "Steps",
                             "Date": date_str,
                             "Timestamp": entry['startGMT'], # Start time
                             "Value": entry['steps']
                         })

            # 5. Respiration Intraday
            # garmin_connect.get_respiration_data(date) -> dict with 'respirationValuesArray'
            respiration_data = garmin_client.get_respiration_data(date_str)
            if respiration_data:
                resp_values = respiration_data.get('respirationValuesArray', [])
                for entry in resp_values:
                    # [timestamp_GMT_ms, value]
                    if entry[1]:
                        ts = datetime.datetime.fromtimestamp(entry[0]/1000, pytz.utc)
                        intraday_data.append({
                            "Type": "Respiration",
                            "Date": date_str,
                            "Timestamp": ts.isoformat(),
                            "Value": entry[1]
                        })

            # 6. Body Composition (Weight)
            weight_data = garmin_client.get_weigh_ins(date_str, date_str)
            if weight_data:
                daily_summaries = weight_data.get('dailyWeightSummaries', [])
                if daily_summaries:
                    # Usually just one summary per day
                    summary = daily_summaries[0]
                    all_metrics = summary.get('allWeightMetrics', [])
                    for metric in all_metrics:
                         if 'weight' in metric and metric['weight']:
                             ts = datetime.datetime.fromtimestamp(metric['timestampGMT']/1000, pytz.utc)
                             intraday_data.append({
                                 "Type": "BodyComposition",
                                 "Date": date_str,
                                 "Timestamp": ts.isoformat(),
                                 "Value": metric['weight'] / 1000.0, # g to kg
                             })

        except Exception as e:
            logging.error(f"Failed Intraday for {date_str}: {e}")
        
        current -= datetime.timedelta(days=1)
        
    return intraday_data

def sync_wellness_intraday(garmin_client, spreadsheet):
    """Sync last 3 days of Intraday data to 'Wellness_Intraday' sheet."""
    try:
        data = get_intraday_data(garmin_client, datetime.date.today(), days=3)
        if not data:
            return
            
        df = pd.DataFrame(data)
        df = df.where(pd.notnull(df), "") # Replace NaNs with empty string for JSON compliance
        
        try:
            wks = spreadsheet.worksheet("Wellness_Intraday")
            wks.clear()
        except gspread.exceptions.WorksheetNotFound:
            wks = spreadsheet.add_worksheet("Wellness_Intraday", rows=10000, cols=10)
            
        # Write headers and data
        wks.update(range_name='A1', values=[df.columns.values.tolist()] + df.values.tolist())
        logging.info(f"Synced {len(df)} rows to Wellness_Intraday")
        
    except Exception as e:
        logging.error(f"Wellness Intraday Sync failed: {e}")

def sync():
    garmin_client = init_garmin()
    sheet = init_gspread() # Returns Worksheet
    spreadsheet = sheet.spreadsheet # Get Spreadsheet
    
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
    
    # 2. Daily Wellness Sync
    get_wellness_data(garmin_client, spreadsheet)

    # 3. Intraday Wellness Sync
    sync_wellness_intraday(garmin_client, spreadsheet)

if __name__ == "__main__":
    sync()
