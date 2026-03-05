import json
import re
import datetime
import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Failed to configure Gemini: {e}")

def _prepare_training_data(df_activ, df_phys):
    """
    Condense the last 6 months of running history to feed into Gemini.
    """
    if df_activ.empty:
        return "{}"
        
    six_months_ago = datetime.date.today() - datetime.timedelta(days=180)
    df_recent = df_activ[df_activ['Date'].dt.date >= six_months_ago].copy()
    
    # Filter to runs only
    df_runs = df_recent[df_recent['NormalizedType'].isin(['running', 'trail_running', 'treadmill_running'])].copy()
    if df_runs.empty:
        return '{"message": "No running data in the last 6 months."}'
        
    df_runs['DateStr'] = df_runs['Date'].dt.strftime('%Y-%m-%d')
    
    # Extract key metrics
    df_runs['Pace (min/km)'] = (df_runs['Duration (min)'] / df_runs['Distance (km)']).round(2).fillna(0)
    export_cols = ['DateStr', 'NormalizedType', 'Distance (km)', 'Duration (min)', 'Pace (min/km)', 'Avg HR', 'Elevation Gain (m)', 'TRIMP', 'Max Temp']
    # Ensure all columns exist to prevent KeyError
    for c in export_cols:
        if c not in df_runs.columns:
            df_runs[c] = 0
            
    runs_list = df_runs[export_cols].fillna(0).to_dict(orient='records')
    
    # Condense physiology (last 30 days of TRIMP/CTL)
    phys_summary = []
    if df_phys is not None and not df_phys.empty:
         thirty_days = datetime.date.today() - datetime.timedelta(days=30)
         df_phys_recent = df_phys[df_phys['Date'].dt.date >= thirty_days]
         for _, row in df_phys_recent.iterrows():
             phys_summary.append({
                 "Date": row['Date'].strftime('%Y-%m-%d'),
                 "TRIMP": round(row['TRIMP'], 1),
                 "CTL": round(row['CTL'], 1),
                 "TSB": round(row['TSB'], 1)
             })
             
    data = {
        "runs": runs_list,
        "physiology_30d": phys_summary
    }
    
    return json.dumps(data)

def generate_training_plan(goal_distance, duration_weeks, profile_context, df_activ, df_phys):
    """
    Generates a structured JSON training plan using Gemini Flash.
    Returns:
       dict: {
           "vibe_check": "String summary...",
           "plan": [
               {
                   "week_number": 1,
                   "focus": "Aerobic Base",
                   "days": [
                       {"day": "Monday", "type": "Rest", "distance_km": 0, "description": "Rest day"}
                   ]
               }
           ]
       }
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
    except:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    system_prompt = f"""
    You are an Elite Running Coach and Sports Data Scientist specializing in Periodization and Exercise Physiology.
    Your goal is to build a highly personalized, adaptive training plan engine that deeply analyzes the user's running history and generates a structured plan.
    
    ### USER PARAMETERS
    - Goal: {goal_distance}
    - Duration: {duration_weeks} weeks
    - Profile: {profile_context}
    
    ### DATA AUDIT PROTOCOL
    I am providing you a JSON string containing the user's running history (last 6 months) and physiology TRIMP/CTL load (last 30 days).
    Perform a 'Deep Vibe Analysis' looking at their historical distance, pacing dynamics (minutes per km), elevation, heart rate, temperature (Max Temp in Celsius), and training load (TRIMP/CTL). 
    Ensure the new plan avoids the 'Injury Red Zone' based on their current load, and adjusts paces if they are running in high heat.
    
    ### PLAN GENERATION LOGIC
    - Periodization: Use a 3-week build / 1-week recover cycle.
    - Workout Variety: Every week must include 1 Interval Session (Speed), 1 Tempo/Threshold Run, 1 Recovery Run, and 1 Progressive or Easy Long Run.
    - Elevation Target: Include 1 'Hill Repeat' session every two weeks if the goal dictates.
    
    ### OUTPUT REQUIREMENTS
    You MUST output STRICT valid JSON matching the following schema EXACTLY. DO NOT wrap with markdown code blocks like ```json. Output raw JSON only.
    {{
        "vibe_check": "A fun, highly analytical Elite Coach summary of their 'Running Identity' today (e.g. 'Endurance-heavy, Speed-limited') and thoughts on the upcoming plan.",
        "plan": [
            {{
                "week_number": 1,
                "focus": "Aerobic Base",
                "days": [
                    {{"day": "Monday", "type": "Rest", "distance_km": 0.0, "description": "Total rest or light stretching."}},
                    {{"day": "Tuesday", "type": "Easy", "distance_km": 6.0, "description": "Easy zone 2 running."}},
                    {{"day": "Wednesday", "type": "Interval", "distance_km": 8.0, "description": "Warmup, 6x400m hard, Cooldown."}},
                     ... all 7 days ...
                ]
            }}
            ... all {duration_weeks} weeks ...
        ]
    }}
    """
    
    historical_data_json = _prepare_training_data(df_activ, df_phys)
    
    user_prompt = f"Here is my historical running data:\n{historical_data_json}\n\nGenerate my JSON training plan."
    
    try:
        response = model.generate_content([system_prompt, user_prompt])
        text = response.text
        
        # Strip potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
             text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        
        plan_dict = json.loads(text)
        return plan_dict
    except Exception as e:
        print(f"Error generating plan: {e}")
        return None
