import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SHEET_ID = os.getenv("GOOGLE_SHEET_KEY")
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}" if SHEET_ID else None

# --- Physiology Constants ---
RHR = 45
MAX_HR = 197
HR_RESERVE = MAX_HR - RHR

def calculate_trimp(duration_min, avg_hr):
    """Calculate TRIMP based on HR Reserve zone."""
    if avg_hr == 0: return 0
    hrr_factor = (avg_hr - RHR) / HR_RESERVE
    trimp = duration_min * hrr_factor * 0.64 * np.exp(1.92 * hrr_factor)
    return trimp

def load_data():
    """Load Activity data from Google Sheets."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 for instant updates
        
        if not SHEET_URL:
            st.error("Missing GOOGLE_SHEET_KEY in .env file.")
            return pd.DataFrame()

        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
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
        st.error(f"Error loading activity data: {e}")
        return pd.DataFrame()

def load_wellness_data():
    """Load Wellness data from Google Sheets (Worksheet: Wellness)."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        if not SHEET_URL:
             # Already handled/shown in load_data usually, but good to be safe
             return pd.DataFrame()

        # Read specifically the Wellness worksheet
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Wellness", ttl=0)
        
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
        # It's possible the worksheet doesn't exist yet if sync hasn't run
        st.warning(f"Wellness data error: {e}") 
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
