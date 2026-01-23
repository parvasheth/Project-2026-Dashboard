import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import numpy as np
from utils import load_wellness_data, load_intraday_data

# Page Config
st.set_page_config(page_title="Personal History | Project 2026", page_icon="🧘", layout="wide")

# Styling: Grafana Dark Mode Override
st.markdown("""
    <style>
    .stApp { background-color: #0b0c0e; } /* Grafana Dark */
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    h1, h2, h3, h4, h5 { color: #e9ecef; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #181b1f; padding: 15px; border-radius: 5px; border: 1px solid #2c3235; }
    </style>
""", unsafe_allow_html=True)

st.title("🧘 Personal History & Wellness")

# --- Helper Functions ---
def create_gauge(value, title, min_val, max_val, color_ranges):
    """Create a Grafana-style Arc Gauge."""
    steps = []
    # color_ranges = [(value, color), (value, color)...]
    # Simple gradient approach or fixed steps
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 14, 'color': "gray"}},
        number = {'font': {'size': 24, 'color': "white"}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "gray"},
            'bar': {'color': "rgba(0,0,0,0)"}, # Invisible bar, we use steps/thresholds typically or needle
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': [
                {'range': [min_val, value], 'color': color_ranges} 
            ],
            'threshold': {
                'line': {'color': "white", 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(paper_bgcolor = "rgba(0,0,0,0)", font = {'color': "white", 'family': "Arial"}, height=150, margin=dict(l=20,r=20,t=30,b=20))
    return fig

def create_radial_gauge(value, title, min_val, max_val, color):
    """Create a circular progress gauge."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14, 'color': "#c7d0d9"}},
        number = {'font': {'size': 20, 'color': "white"}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'visible': False},
            'bar': {'color': color},
            'bgcolor': "#22252b",
            'borderwidth': 0,
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=140, margin=dict(t=30, b=10, l=20, r=20))
    return fig

# --- Load Data ---
df_wellness = load_wellness_data()
df_intra = load_intraday_data()

if df_wellness.empty:
    st.error("No wellness data found. Run `sync_garmin.py`.")
    st.stop()

# --- Top Filters ---
col_filter, _ = st.columns([1, 4])
with col_filter:
    days_lookback = st.selectbox("Timeframe", [7, 30, 90], index=0)

# Filter Wellness
end_date = df_wellness['Date'].max()
start_date = end_date - datetime.timedelta(days=days_lookback)
df_w_filt = df_wellness[(df_wellness['Date'] >= start_date) & (df_wellness['Date'] <= end_date)]

# --- Row 1: KPI Gauges (Grafana Style) ---
st.markdown("### 🚦 Current Status")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

# Latest Values
latest = df_wellness.iloc[-1]
with kpi1:
    st.plotly_chart(create_radial_gauge(
        latest.get('Sleep_Score', 0), "Sleep Score", 0, 100, "#73bf69"
    ), use_container_width=True)
with kpi2:
    st.plotly_chart(create_radial_gauge(
        latest.get('BodyBattery_Max', 0), "Body Battery (Max)", 0, 100, "#56a2f5"
    ), use_container_width=True)
with kpi3:
    st.plotly_chart(create_radial_gauge(
        latest.get('Stress_Avg', 0), "Avg Stress", 0, 100, "#f2cc0c"
    ), use_container_width=True)
with kpi4:
    steps_val = latest.get('Steps', 0)
    st.plotly_chart(create_radial_gauge(
        steps_val, "Daily Steps", 0, 10000, "#FF4B4B" if steps_val < 5000 else "#73bf69"
    ), use_container_width=True)

# --- Row 2: Intraday HR & Stress (The "Deep Dive") ---
st.markdown("### ❤️ Heart Rate & Stress Dynamics")

# Filter Intraday for last 3 days max (visual clutter reduction)
if not df_intra.empty:
    recent_params = df_intra['Date'].max() - datetime.timedelta(days=2) # Last 3 days
    df_i_filt = df_intra[df_intra['Date'] >= recent_params]
    
    # 2A. Heart Rate Line (Gradient)
    df_hr = df_i_filt[df_i_filt['Type'] == 'HeartRate']
    if not df_hr.empty:
        fig_hr = go.Figure()
        fig_hr.add_trace(go.Scatter(
            x=df_hr['Timestamp'], 
            y=df_hr['Value'],
            mode='lines',
            name='Heart Rate',
            line=dict(color='#ff3333', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(255, 51, 51, 0.1)'
        ))
        fig_hr.update_layout(
            title="Intraday Heart Rate (bpm)",
            template="plotly_dark",
            height=300,
            yaxis=dict(range=[40, 180]),
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_hr, use_container_width=True)

    # 2B. Stress & Body Battery Overlay
    col_stress, col_bb = st.columns([1, 1]) # Split or Combined? User wants Grafana which usually stacks them.
    # Let's stack them visually in one big chart? Reference image has them separate often.
    # Let's do Overlay for compactness.
    
    df_stress = df_i_filt[df_i_filt['Type'] == 'Stress']
    df_bb = df_i_filt[df_i_filt['Type'] == 'BodyBattery']
    
    fig_combo = go.Figure()
    if not df_stress.empty:
        fig_combo.add_trace(go.Scatter(
            x=df_stress['Timestamp'], y=df_stress['Value'],
            mode='lines', name='Stress',
            line=dict(color='#f2994a', width=1),
            fill='tozeroy', fillcolor='rgba(242, 153, 74, 0.2)'
        ))
    if not df_bb.empty:
        fig_combo.add_trace(go.Scatter(
            x=df_bb['Timestamp'], y=df_bb['Value'],
            mode='lines', name='Body Battery',
            line=dict(color='#2d9cdb', width=2),
        ))
    
    fig_combo.update_layout(
        title="Stress vs Body Battery Charge/Drain",
        template="plotly_dark",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_combo, use_container_width=True)

    # --- Row 3: Sleep Architecture ---
    st.markdown("### 💤 Sleep Hypnogram")
    
    df_sleep = df_i_filt[df_i_filt['Type'] == 'SleepStage'].copy()
    if not df_sleep.empty:
        stage_map = {1: "Deep", 2: "Light", 3: "REM", 4: "Awake", 0: "Unknown"}
        color_map = {"Deep": "#005f99", "Light": "#2c8c4c", "REM": "#8c56b5", "Awake": "#d62728", "Unknown": "gray"}
        df_sleep['Stage'] = df_sleep['Value'].map(stage_map)
        
        fig_sleep = px.timeline(
            df_sleep, x_start="Timestamp", x_end="EndTimestamp", y="Stage",
            color="Stage", color_discrete_map=color_map,
            category_orders={"Stage": ["Awake", "REM", "Light", "Deep"]},
        )
        fig_sleep.update_yaxes(autorange="reversed")
        fig_sleep.update_layout(
            template="plotly_dark",
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_sleep, use_container_width=True)

    # --- Row 4: Steps Heatmap ---
    st.markdown("### 👣 Hourly Activity Heatmap")
    
    df_steps = df_i_filt[df_i_filt['Type'] == 'Steps'].copy()
    if not df_steps.empty:
        # Prepare Heatmap Data: Index=Date, Col=Hour, Value=Steps
        df_steps['Hour'] = df_steps['Timestamp'].dt.hour
        df_steps['DateStr'] = df_steps['Timestamp'].dt.date
        
        pivot_steps = df_steps.pivot_table(index='DateStr', columns='Hour', values='Value', aggfunc='sum').fillna(0)
        
        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot_steps.values,
            x=pivot_steps.columns,
            y=pivot_steps.index,
            colorscale='Greens',
            xgap=1, ygap=1
        ))
        fig_heat.update_layout(
            title="Steps per Hour",
            template="plotly_dark",
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("Intraday data missing. Run `sync_garmin.py`.")
