import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from utils import load_wellness_data

# Page Config
st.set_page_config(page_title="Personal History | Project 2026", page_icon="🧘", layout="wide")

# Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stat-card { background-color: #262730; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .stat-value { font-size: 2rem; font-weight: bold; color: #b388ff; }
    .stat-label { font-size: 1rem; color: #a0a0a0; }
    </style>
""", unsafe_allow_html=True)

st.title("🧘 Personal History & Wellness")

# Load Data
df_wellness = load_wellness_data()

if df_wellness.empty:
    st.info("No wellness data found. Please ensure `sync_garmin.py` has run successfully.")
    st.stop()

# Date Range Picker
col_ctrl1, col_ctrl2 = st.columns([1, 3])
with col_ctrl1:
    time_range = st.selectbox("Time Range", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"], index=1)

# Filter Data
end_date = df_wellness['Date'].max()
if time_range == "Last 7 Days": start_date = end_date - datetime.timedelta(days=7)
elif time_range == "Last 30 Days": start_date = end_date - datetime.timedelta(days=30)
elif time_range == "Last 90 Days": start_date = end_date - datetime.timedelta(days=90)
else: start_date = df_wellness['Date'].min()

mask = (df_wellness['Date'] >= start_date) & (df_wellness['Date'] <= end_date)
df_filtered = df_wellness.loc[mask]

# --- Row 1: Stat Cards ---
st.markdown("### Snapshot")
c1, c2, c3, c4 = st.columns(4)

# Calculate Averages/Latest
avg_sleep_score = df_filtered['Sleep_Score'].mean()
avg_stress = df_filtered['Stress_Avg'].mean()
avg_steps = df_filtered['Steps'].mean()
latest_vo2 = df_wellness['VO2Max'].iloc[-1] if 'VO2Max' in df_wellness.columns and not df_wellness['VO2Max'].eq(0).all() else 0

with c1: st.metric("Sleep Quality (Avg)", f"{avg_sleep_score:.0f}", delta=None)
with c2: st.metric("Stress Level (Avg)", f"{avg_stress:.0f}", delta=None, delta_color="inverse")
with c3: st.metric("Daily Steps (Avg)", f"{avg_steps:,.0f}")
with c4: st.metric("VO2 Max", f"{latest_vo2:.0f}" if latest_vo2 > 0 else "N/A")

st.markdown("---")

# --- Row 2: Deep Health Visualizations ---

# 1. Body Battery vs Stress (Dual Axis)
st.subheader("🔋 Body Battery & Stress")
fig_bb = go.Figure()

# Stress Area (Background)
fig_bb.add_trace(go.Scatter(
    x=df_filtered['Date'], y=df_filtered['Stress_Avg'],
    name="Avg Stress",
    fill='tozeroy',
    line=dict(color='rgba(255, 100, 100, 0.5)', width=1),
    fillcolor='rgba(255, 100, 100, 0.2)'
))

# Body Battery Range (High/Low) - Candlestick-like or Range area?
# Let's use lines for Max and Min
fig_bb.add_trace(go.Scatter(
    x=df_filtered['Date'], y=df_filtered['BodyBattery_Max'],
    name="Body Battery Max",
    line=dict(color='#00C805', width=2)
))
fig_bb.add_trace(go.Scatter(
    x=df_filtered['Date'], y=df_filtered['BodyBattery_Min'],
    name="Body Battery Min",
    line=dict(color='#006402', width=1, dash='dot')
))

fig_bb.update_layout(
    template="plotly_dark",
    height=350,
    legend=dict(orientation="h", y=1.1, x=0),
    yaxis=dict(title="Score (0-100)", range=[0, 100]),
    margin=dict(l=20, r=20, t=40, b=20)
)
st.plotly_chart(fig_bb, use_container_width=True)

# 2. Sleep Timeline & Score
c_sleep_L, c_sleep_R = st.columns([2, 1])

with c_sleep_L:
    st.subheader("💤 Sleep Duration & Consistency")
    # Bar Chart for Sleep Hours, Color by Score
    fig_sleep = px.bar(
        df_filtered, x='Date', y='Sleep_Hours',
        color='Sleep_Score',
        color_continuous_scale='RdYlGn',
        range_color=[50, 90],
        title="Sleep Duration (hrs) colored by Score"
    )
    fig_sleep.add_hline(y=8, line_dash="drive", line_color="green", annotation_text="Goal (8h)")
    fig_sleep.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig_sleep, use_container_width=True)

with c_sleep_R:
    st.subheader("Daily Steps")
    fig_steps = px.bar(
        df_filtered, x='Date', y='Steps',
        color='Steps',
        color_continuous_scale='Blues',
        title="Step Count"
    )
    fig_steps.update_layout(template="plotly_dark", height=300, showlegend=False)
    st.plotly_chart(fig_steps, use_container_width=True)
