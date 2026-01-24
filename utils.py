import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
# Load environment variables
load_dotenv()
SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY") or (st.secrets["GOOGLE_SHEET_KEY"] if "GOOGLE_SHEET_KEY" in st.secrets else None)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Physiology Constants ---
RHR = 45
MAX_HR = 197
HR_RESERVE = MAX_HR - RHR

@st.cache_resource
def get_gspread_client():
    """Authenticate and return gspread client."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        
        # 1. Cloud Deployment: Check for st.secrets
        # Ensure your secrets.toml has [gcp_service_account] section
        if "gcp_service_account" in st.secrets:
            # st.secrets returns a plain dict for the section
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Fix newline issues in private_key if inherited from TOML
            if "private_key" in creds_dict:
                 creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                 
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            return client

        # 2. Local Development: Check for service_account.json
        creds_path = os.path.join(BASE_DIR, "service_account.json")
        if os.path.exists(creds_path):
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            client = gspread.authorize(creds)
            return client
            
        st.error(f"Credentials not found. Available keys in secrets: {list(st.secrets.keys())}. Setup st.secrets['gcp_service_account'] or add service_account.json locally.")
        return None
        
    except Exception as e:
        # Debugging: show keys even on unexpected error if helpful, but usually e covers it
        st.error(f"Authentication Error: {e}")
        return None

def calculate_trimp(duration_min, avg_hr):
    """Calculate TRIMP based on HR Reserve zone."""
    if avg_hr == 0: return 0
    hrr_factor = (avg_hr - RHR) / HR_RESERVE
    trimp = duration_min * hrr_factor * 0.64 * np.exp(1.92 * hrr_factor)
    return trimp

def load_data():
    """Load Activity data from Google Sheets (Sheet1)."""
    client = get_gspread_client()
    if not client or not SHEET_KEY: return pd.DataFrame()

    try:
        # Open by Key
        sh = client.open_by_key(SHEET_KEY)
        # Assuming Activities are in the first sheet or named 'Sheet1'
        # sync_garmin.py uses .sheet1 which is the first sheet
        wks = sh.sheet1
        
        data = wks.get_all_records() # Returns list of dicts
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date", ascending=True)
            
            df['Distance (km)'] = pd.to_numeric(df['Distance (km)'], errors='coerce').fillna(0)
            df['Elevation Gain (m)'] = pd.to_numeric(df['Elevation Gain (m)'], errors='coerce').fillna(0)
            df['Duration (min)'] = pd.to_numeric(df['Duration (min)'], errors='coerce').fillna(0)
            df['Avg HR'] = pd.to_numeric(df['Avg HR'], errors='coerce').fillna(0)
            
            # Normalize types
            df['NormalizedType'] = df['Type'].apply(lambda x: 'running' if 'running' in str(x).lower() else str(x).lower())
            
        return df
    except Exception as e:
        masked_key = SHEET_KEY[:5] + "..." if SHEET_KEY else "None"
        st.error(f"Error loading activity data with Key '{masked_key}': {e}")
        return pd.DataFrame()

def load_wellness_data():
    """Load Wellness data from Google Sheets (Worksheet: Wellness)."""
    client = get_gspread_client()
    if not client or not SHEET_KEY: return pd.DataFrame()

    try:
        sh = client.open_by_key(SHEET_KEY)
        try:
            wks = sh.worksheet("Wellness")
        except gspread.exceptions.WorksheetNotFound:
            st.warning("Wellness worksheet not found. Please sync data first.")
            return pd.DataFrame()
            
        data = wks.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date", ascending=True)
            # Ensure numeric
            cols = ["Steps", "RHR", "Stress_Avg", "BodyBattery_Max", "BodyBattery_Min", "Sleep_Score", "Sleep_Hours", "HRV_ms", "VO2Max"]
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Wellness data error: {e}") 
        return pd.DataFrame()

def load_intraday_data():
    """Load Intraday Wellness data from Google Sheets (Worksheet: Wellness_Intraday)."""
    client = get_gspread_client()
    if not client or not SHEET_KEY: return pd.DataFrame()

    try:
        sh = client.open_by_key(SHEET_KEY)
        try:
            wks = sh.worksheet("Wellness_Intraday")
        except gspread.exceptions.WorksheetNotFound:
            # Silent fail if not yet synced, just return empty
            return pd.DataFrame()
            
        data = wks.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Parse Dates/Timestamps
            # 'Timestamp' is ISO format
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='mixed', utc=True)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], format='mixed', utc=True)
            if 'EndTimestamp' in df.columns:
                df['EndTimestamp'] = pd.to_datetime(df['EndTimestamp'], format='mixed', utc=True)
                
            # Ensure Numeric Value
            if 'Value' in df.columns:
                 df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                 
        return df
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return pd.DataFrame()

def calculate_physiology(df):
    """Calculate CTL, ATL, TSB from activity dataframe."""
    if df.empty: return None

    df_phys = df.copy().sort_values("Date")
    df_phys['TRIMP'] = df_phys.apply(lambda row: calculate_trimp(row['Duration (min)'], row['Avg HR']), axis=1)
    
    # Resample
    df_phys = df_phys.set_index('Date').resample('D')['TRIMP'].sum()
    
    # Extend to today
    last_date = df_phys.index.max().date()
    today = datetime.date.today()
    if last_date < today:
        full_idx = pd.date_range(start=df_phys.index.min(), end=today, freq='D')
        df_phys = df_phys.reindex(full_idx, fill_value=0)
    
    df_phys = df_phys.reset_index().rename(columns={'index': 'Date'})
    
    # Calculate EWMA
    df_phys['CTL'] = df_phys['TRIMP'].ewm(span=42, adjust=False).mean()
    df_phys['ATL'] = df_phys['TRIMP'].ewm(span=7, adjust=False).mean()
    df_phys['TSB'] = df_phys['CTL'] - df_phys['ATL']
    
    return df_phys
