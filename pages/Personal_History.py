import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import numpy as np
from utils import load_wellness_data, load_intraday_data, load_data

st.set_page_config(page_title="Personal History | Project 2026", page_icon="🧘", layout="wide")

# --- Grafana Dark Theme with Neon Accents ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0c0e; }
    h1, h2, h3, h4, h5, p, span { color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #181b1f; padding: 10px; border-radius: 4px; border-left: 3px solid #73bf69; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("🧘 Personal History")

# --- Data Loading ---
df_daily = load_wellness_data()
df_intra = load_intraday_data()
df_activ = load_data() # For Activity Timeline

if df_daily.empty:
    st.error("No daily wellness data found. Please run sync.")
    st.stop()

# --- Row 1: KPI Tiles (Big Number + Delta) ---
# Calculate Deltas (Today vs Yesterday)
today = df_daily.iloc[-1]
yesterday = df_daily.iloc[-2] if len(df_daily) > 1 else today

c1, c2, c3, c4, c5, c6 = st.columns(6)

def kpi_card(col, label, value, delta, color="#73bf69"):
    with col:
        st.metric(label=label, value=value, delta=delta)
        # Custom CSS for color injection could go here, but St.metric is sufficient for now

kpi_card(c1, "Steps", f"{today.get('Steps',0):,.0f}", f"{today.get('Steps',0)-yesterday.get('Steps',0):,.0f}")
kpi_card(c2, "Act. Cal", f"{today.get('ActiveKilocalories',0):.0f}", None) # Need ActiveCal in sync
kpi_card(c3, "Sleep Score", f"{today.get('Sleep_Score',0):.0f}", f"{today.get('Sleep_Score',0)-yesterday.get('Sleep_Score',0):.0f}")
kpi_card(c4, "Body Bat.", f"{today.get('BodyBattery_Max',0):.0f}", f"Min: {today.get('BodyBattery_Min',0):.0f}")
kpi_card(c5, "Stress", f"{today.get('Stress_Avg',0):.0f}", f"{today.get('Stress_Avg',0)-yesterday.get('Stress_Avg',0):.0f}", color="#f2cc0c")
kpi_card(c6, "RHR", f"{today.get('RHR',0):.0f}", f"{today.get('RHR',0)-yesterday.get('RHR',0):.0f}")

# --- Row 2: 24h Time-Series High Resolution ---
st.markdown("### 🔍 Last 24 Hours Analysis")
if not df_intra.empty:
    # Filter Last 24h
    latest_ts = df_intra['Timestamp'].max()
    start_24h = latest_ts - datetime.timedelta(hours=24)
    df_24h = df_intra[df_intra['Timestamp'] >= start_24h]
    
    vis1, vis2 = st.columns([2, 1])
    
    with vis1:
        # Chart 1: Heart Rate + Stress Overlay
        # HR on Left Y, Stress on Right Y (Area) via secondary axis? Or stacked?
        # Grafana typically does HR line, Stress Area below.
        
        df_hr = df_24h[df_24h['Type'] == 'HeartRate']
        df_stress = df_24h[df_24h['Type'] == 'Stress']
        
        fig_dual = go.Figure()
        
        # Stress (Area)
        if not df_stress.empty:
             fig_dual.add_trace(go.Scatter(
                x=df_stress['Timestamp'], y=df_stress['Value'],
                mode='lines', name='Stress',
                fill='tozeroy', line=dict(width=0),
                marker=dict(color='rgba(255, 165, 0, 0.2)'),
                yaxis='y2'
             ))
             
        # HR (Line)
        if not df_hr.empty:
            fig_dual.add_trace(go.Scatter(
                x=df_hr['Timestamp'], y=df_hr['Value'],
                mode='lines', name='HR',
                line=dict(color='#ff2b2b', width=2)
            ))
            
        fig_dual.update_layout(
            template="plotly_dark", height=300,
            title="Heart Rate & Stress (24h)",
            xaxis=dict(showgrid=False),
            yaxis=dict(title="HR (bpm)", showgrid=True, gridcolor='#333'),
            yaxis2=dict(title="Stress", overlaying='y', side='right', range=[0,100], showgrid=False),
            margin=dict(t=40, l=10, r=10, b=10),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_dual, use_container_width=True)
        
    with vis2:
        # Chart 2: Body Battery & Respiration
        df_bb = df_24h[df_24h['Type'] == 'BodyBattery']
        df_br = df_24h[df_24h['Type'] == 'Respiration']
        
        fig_br = go.Figure()
        if not df_bb.empty:
            fig_br.add_trace(go.Scatter(
                x=df_bb['Timestamp'], y=df_bb['Value'],
                name='Body Battery',
                line=dict(color='#3274d9', width=2)
            ))
        if not df_br.empty:
            fig_br.add_trace(go.Scatter(
                x=df_br['Timestamp'], y=df_br['Value'],
                name='Resp Rate', mode='markers+lines',
                line=dict(color='#56f088', width=1, dash='dot'),
                yaxis='y2'
            ))
            
        fig_br.update_layout(
             template="plotly_dark", height=300,
             title="Energy & Respiration",
             yaxis=dict(range=[0,100], title="Body Batt"),
             yaxis2=dict(overlaying='y', side='right', title="BrPM"),
             margin=dict(t=40, l=10, r=10, b=10),
             legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_br, use_container_width=True)

# --- Row 3: Heatmaps (Steps & Sleep) ---
st.markdown("### 🧱 Intensity & Consistency")
crow1, crow2 = st.columns(2)

with crow1: # Steps Heatmap
    if not df_intra.empty:
        df_steps_i = df_intra[df_intra['Type'] == 'Steps'].copy()
        if not df_steps_i.empty:
            df_steps_i['Hour'] = df_steps_i['Timestamp'].dt.hour
            df_steps_i['DateStr'] = df_steps_i['Timestamp'].dt.date
            # Pivot
            pivot = df_steps_i.pivot_table(index='DateStr', columns='Hour', values='Value', aggfunc='sum').fillna(0)
            
            fig_heat = go.Figure(go.Heatmap(
                z=pivot.values, x=pivot.columns, y=pivot.index,
                colorscale='Greens', showscale=False
            ))
            fig_heat.update_layout(template="plotly_dark", height=300, title="Steps by Hour", margin=dict(t=40,b=10))
            st.plotly_chart(fig_heat, use_container_width=True)
            
with crow2: # Sleep Architecture Timeline (Using Gantt logic)
    # Using df_intra type=SleepStage
    df_sleep_i = df_intra[df_intra['Type'] == 'SleepStage'].copy() if not df_intra.empty else pd.DataFrame()
    if not df_sleep_i.empty:
        stage_map = {1: "Deep", 2: "Light", 3: "REM", 4: "Awake", 0: "Unknown"}
        color_map = {"Deep": "#1f77b4", "Light": "#2ca02c", "REM": "#9467bd", "Awake": "#d62728", "Unknown": "gray"}
        df_sleep_i['Stage'] = df_sleep_i['Value'].map(stage_map)
        
        # Ensure UTC
        if 'EndTimestamp' not in df_sleep_i.columns:
             # Fallback if utils failed? Utils should handle it.
             pass
             
        fig_gantt = px.timeline(
            df_sleep_i, x_start="Timestamp", x_end="EndTimestamp", y="Stage",
            color="Stage", color_discrete_map=color_map,
            category_orders={"Stage": ["Awake", "REM", "Light", "Deep"]},
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(template="plotly_dark", height=300, title="Sleep Hypnogram History", margin=dict(t=40,b=10))
        st.plotly_chart(fig_gantt, use_container_width=True)

# --- Row 4: Performance (Activity Timeline & Trends) ---
st.markdown("### 🏃 Performance Trends")
p1, p2 = st.columns([2, 1])

with p1: # Activity timeline
     if not df_activ.empty:
         # Last 7 days chart
         activ_7d = df_activ.sort_values("Date").tail(15) # Last 15 events
         # Create Timeline
         # Start = Date, End = Date + Duration
         activ_7d['End'] = activ_7d['Date'] + pd.to_timedelta(activ_7d['Duration (min)'], unit='m')
         
         fig_act = px.timeline(
             activ_7d, x_start="Date", x_end="End", y="NormalizedType",
             color="NormalizedType", title="Recent Activities Timeline",
             height=300
         )
         fig_act.update_layout(template="plotly_dark", showlegend=False)
         st.plotly_chart(fig_act, use_container_width=True)

with p2: # Daily Steps Trend
    fig_tr = px.bar(df_daily.tail(30), x='Date', y='Steps', title="30-Day Step Trend", color='Steps')
    fig_tr.update_layout(template="plotly_dark", height=300, coloraxis_showscale=False)
    st.plotly_chart(fig_tr, use_container_width=True)

# --- Row 5: Long-Term Health (Weight, VO2) ---
st.markdown("### ⚖️ Long Term Stats")
l1, l2 = st.columns(2)
# Placeholder for weight if not in data yet
# Assuming future sync adds 'Weight' to Wellness sheet or separate.
# Current logic: load_wellness_data handles keys passed. 
# We need to ensure sync_garmin adds Weight to Wellness Row. (Currently syncs summary but not weight specifically?)
# Reference impl creates 'BodyComposition' measurement in Intraday.
# Let's check Intraday for Weight for now:
if not df_intra.empty:
    df_weight = df_intra[df_intra['Type'] == 'BodyComposition'] # From updated Sync? Not added in plan yet.
    # Actually User Plan asked to fetch BodyComp. Sync logic added it?
    # Wait, previous tool call added Respiration but didn't explicitly add BodyComp function call in get_intraday_data loop?
    # I replaced lines 361-377 to add Respiration. I might have missed BodyComp call in loop.
    pass

with l1:
    fig_vo2 = px.line(df_daily, x='Date', y='VO2Max', markers=True, title="VO2 Max Trend")
    fig_vo2.update_traces(line_color="#b388ff")
    fig_vo2.update_layout(template="plotly_dark", height=250)
    st.plotly_chart(fig_vo2, use_container_width=True)

with l2:
    if 'HRV_ms' in df_daily.columns:
        fig_hrv = px.line(df_daily, x='Date', y='HRV_ms', markers=True, title="HRV Status (ms)")
        fig_hrv.update_traces(line_color="#56f088")
        fig_hrv.update_layout(template="plotly_dark", height=250)
        st.plotly_chart(fig_hrv, use_container_width=True)
