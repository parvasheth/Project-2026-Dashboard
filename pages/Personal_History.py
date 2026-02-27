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

# --- Custom Navigation ---
st.markdown("""
<style>
div[data-testid="stColumn"] > div > div > div > div {
    gap: 0.5rem;
}
.nav-btn {
    width: 100%;
    border: 1px solid #333;
    background: #181b1f;
    color: white;
    padding: 10px;
    text-align: center;
    border-radius: 5px;
    cursor: pointer;
    text-decoration: none;
    display: block;
}
.nav-btn:hover { background: #22252b; border-color: #73bf69; }
.nav-btn.active { background: #181b1f; border-color: #73bf69; color: #73bf69; }
</style>
""", unsafe_allow_html=True)

nav1, nav2, _ = st.columns([1, 1, 4])
with nav1:
    if st.button("🏋️ Training Hub"):
        st.switch_page("dashboard.py")
with nav2:
    st.button("🧘 Personal History", disabled=True) # Current Page

# --- Data Loading ---

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
kpi_card(c2, "Act. Cal", f"{today.get('ActiveKilocalories',0):,.0f}", f"{today.get('ActiveKilocalories',0)-yesterday.get('ActiveKilocalories',0):,.0f}")
kpi_card(c3, "Sleep Score", f"{today.get('Sleep_Score',0):.0f}", f"{today.get('Sleep_Score',0)-yesterday.get('Sleep_Score',0):.0f}")
kpi_card(c4, "Body Bat.", f"{today.get('BodyBattery_Max',0):.0f} / {today.get('BodyBattery_Min',0):.0f}", None)
kpi_card(c5, "Stress", f"{today.get('Stress_Avg',0):.0f}", f"{today.get('Stress_Avg',0)-yesterday.get('Stress_Avg',0):.0f}", color="#f2cc0c")
kpi_card(c6, "RHR", f"{today.get('RHR',0):.0f}", f"{today.get('RHR',0)-yesterday.get('RHR',0):.0f}")

st.markdown("<br>", unsafe_allow_html=True)

# --- Row 2: 24h Time-Series High Resolution ---
st.markdown("### 🔍 24-Hour Intraday Telemetry")
if not df_intra.empty:
    # Filter Last 24h
    latest_ts = df_intra['Timestamp'].max()
    start_24h = latest_ts - datetime.timedelta(hours=24)
    df_24h = df_intra[df_intra['Timestamp'] >= start_24h]
    
    vis1, vis2 = st.columns([1, 1], gap="large")
    
    with vis1:
        # Chart 1: Heart Rate + Stress Overlay
        df_hr = df_24h[df_24h['Type'] == 'HeartRate']
        df_stress = df_24h[df_24h['Type'] == 'Stress']
        
        fig_dual = go.Figure()
        
        # Stress (Area)
        if not df_stress.empty:
             fig_dual.add_trace(go.Scatter(
                x=df_stress['Timestamp'], y=df_stress['Value'],
                mode='lines', name='Stress Level',
                fill='tozeroy', line=dict(width=0),
                marker=dict(color='rgba(255, 165, 0, 0.3)'),
                yaxis='y2', hoverinfo='x+y'
             ))
             
        # HR (Line) - Red
        if not df_hr.empty:
            fig_dual.add_trace(go.Scatter(
                x=df_hr['Timestamp'], y=df_hr['Value'],
                mode='lines', name='Heart Rate',
                line=dict(color='#FF4560', width=2),
                hoverinfo='x+y'
            ))
            
        fig_dual.update_layout(
            template="plotly_dark", height=380,
            title=dict(text="Heart Rate & Stress Overlay", font=dict(size=18, color="#e0e0e0")),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(title="Heart Rate (bpm)", showgrid=True, gridcolor='rgba(128,128,128,0.1)', range=[40, 200]),
            yaxis2=dict(title="Stress (0-100)", overlaying='y', side='right', range=[0, 100], showgrid=False),
            margin=dict(t=50, l=10, r=10, b=30),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
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
                name='Body Battery', mode='lines',
                line=dict(color='#00E396', width=2.5),
                fill='tozeroy', fillcolor='rgba(0, 227, 150, 0.15)',
                hoverinfo='x+y'
            ))
        if not df_br.empty:
            fig_br.add_trace(go.Scatter(
                x=df_br['Timestamp'], y=df_br['Value'],
                name='Respiration (BrPM)', mode='lines',
                line=dict(color='#008FFB', width=1.5, dash='dot'),
                yaxis='y2', hoverinfo='x+y'
            ))
            
        fig_br.update_layout(
             template="plotly_dark", height=380,
             title=dict(text="Energy Drain & Recovery (Body Battery)", font=dict(size=18, color="#e0e0e0")),
             xaxis=dict(showgrid=False, title=""),
             yaxis=dict(range=[0, 100], title="Body Battery (%)", showgrid=True, gridcolor='rgba(128,128,128,0.1)'),
             yaxis2=dict(overlaying='y', side='right', title="Resp Rate (BrPM)", showgrid=False, range=[10, 25]),
             margin=dict(t=50, l=10, r=10, b=30),
             legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
             paper_bgcolor='rgba(0,0,0,0)',
             plot_bgcolor='rgba(0,0,0,0)'
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
            pivot = df_steps_i.pivot_table(index='DateStr', columns='Hour', values='Value', aggfunc='sum').fillna(0)
            
            # Custom Dark-to-Neon Green scale
            custom_scale = [
                #[0, 'rgba(0,0,0,0)'], # Transparent for 0?
                [0, '#0e1117'],       # Dark background color
                [0.1, '#0e2a17'],
                [0.5, '#00b34a'],
                [1, '#00E396']        # Neon Green
            ]
            
            fig_heat = go.Figure(go.Heatmap(
                z=pivot.values, x=pivot.columns, y=pivot.index,
                colorscale=custom_scale, showscale=False,
                xgap=2, ygap=2, hoverongaps=False,
                hovertemplate="Day: %{y}<br>Hour: %{x}:00<br>Steps: %{z:,.0f}<extra></extra>"
            ))
            fig_heat.update_layout(
                title=dict(text="Intraday Step Density", font=dict(size=18, color="#e0e0e0")),
                template="plotly_dark", height=380,
                xaxis=dict(title="Hour of Day", tickmode='linear', tick0=0, dtick=3, showgrid=False),
                yaxis=dict(title="", autorange="reversed", showgrid=False),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=50, l=10, r=10, b=30)
            )
            st.plotly_chart(fig_heat, use_container_width=True)
            
with crow2: # Sleep Architecture Timeline
    df_sleep_i = df_intra[df_intra['Type'] == 'SleepStage'].copy() if not df_intra.empty else pd.DataFrame()
    if not df_sleep_i.empty:
        stage_map = {1: "Deep", 2: "Light", 3: "REM", 4: "Awake", 0: "Unknown"}
        color_map = {"Awake": "#FF4560", "REM": "#775DD0", "Light": "#00E396", "Deep": "#008FFB", "Unknown": "gray"}
        df_sleep_i['Stage'] = df_sleep_i['Value'].map(stage_map)
        
        if 'EndTimestamp' not in df_sleep_i.columns: pass # handled by utils
             
        fig_gantt = px.timeline(
            df_sleep_i, x_start="Timestamp", x_end="EndTimestamp", y="Stage",
            color="Stage", color_discrete_map=color_map,
            category_orders={"Stage": ["Awake", "REM", "Light", "Deep", "Unknown"]},
            hover_name="Stage"
        )
        fig_gantt.update_yaxes(autorange="reversed", title="")
        fig_gantt.update_xaxes(title="Time")
        fig_gantt.update_layout(
            template="plotly_dark", height=380, 
            title=dict(text="Sleep Architecture (Hypnogram)", font=dict(size=18, color="#e0e0e0")),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=50, l=10, r=10, b=30),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", title="")
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

# --- Row 4: Performance ---
st.markdown("### 🏃 Performance Trends")
p1, p2 = st.columns([2, 1], gap="large")

with p1: # Activity timeline
     if not df_activ.empty:
         activ_7d = df_activ.sort_values("Date").tail(15)
         activ_7d['End'] = activ_7d['Date'] + pd.to_timedelta(activ_7d['Duration (min)'], unit='m')
         
         fig_act = px.timeline(
             activ_7d, x_start="Date", x_end="End", y="NormalizedType",
             color="NormalizedType",
             height=350, color_discrete_sequence=px.colors.qualitative.Prism,
             hover_name="Title", hover_data={"NormalizedType": False, "Date": "|%b %d, %H:%M", "Distance (km)": ':.2f'}
         )
         fig_act.update_layout(
             title=dict(text="Recent Activities Timeline", font=dict(size=18, color="#e0e0e0")),
             template="plotly_dark", showlegend=False,
             yaxis=dict(title="", categoryorder="category descending"), xaxis=dict(title="Date & Time"),
             paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
             margin=dict(t=50, l=10, r=10, b=10)
         )
         st.plotly_chart(fig_act, use_container_width=True)

with p2: # Daily Steps Trend
    fig_tr = px.bar(df_daily.tail(30), x='Date', y='Steps')
    fig_tr.update_traces(
        marker_color='#00E396', marker_line_width=0, opacity=0.8,
        hovertemplate="Date: %{x}<br>Steps: %{y:,.0f}<extra></extra>"
    )
    fig_tr.update_layout(
        title=dict(text="30-Day Step Trend", font=dict(size=18, color="#e0e0e0")),
        template="plotly_dark", height=350, coloraxis_showscale=False,
        yaxis=dict(title="Total Steps", showgrid=True, gridcolor='rgba(128,128,128,0.1)'),
        xaxis=dict(title=""),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, l=10, r=10, b=10)
    )
    st.plotly_chart(fig_tr, use_container_width=True)

# --- Row 5: Long-Term Stats ---
st.markdown("### ⚖️ Long Term Stats")
l1, l2 = st.columns(2, gap="large")

with l1:
    fig_vo2 = px.line(df_daily, x='Date', y='VO2Max', markers=True)
    fig_vo2.update_traces(
        line_color="#775DD0", marker=dict(size=6, color="#775DD0", line=dict(width=2, color="#0b0c0e")),
        hovertemplate="Date: %{x}<br>VO2 Max: %{y:.1f}<extra></extra>"
    )
    fig_vo2.update_layout(
        title=dict(text="VO2 Max Trend", font=dict(size=18, color="#e0e0e0")),
        template="plotly_dark", height=320,
        yaxis=dict(title="VO2 Max", showgrid=True, gridcolor='rgba(128,128,128,0.1)'),
        xaxis=dict(title=""),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, l=10, r=10, b=10)
    )
    st.plotly_chart(fig_vo2, use_container_width=True)

with l2:
    if 'HRV_ms' in df_daily.columns:
        fig_hrv = px.line(df_daily, x='Date', y='HRV_ms', markers=True)
        fig_hrv.update_traces(
            line_color="#008FFB", marker=dict(size=6, color="#008FFB", line=dict(width=2, color="#0b0c0e")),
            hovertemplate="Date: %{x}<br>HRV: %{y:.0f} ms<extra></extra>"
        )
        fig_hrv.update_layout(
            title=dict(text="HRV Status (ms)", font=dict(size=18, color="#e0e0e0")),
            template="plotly_dark", height=320,
            yaxis=dict(title="Average HRV (ms)", showgrid=True, gridcolor='rgba(128,128,128,0.1)'),
            xaxis=dict(title=""),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=50, l=10, r=10, b=10)
        )
        st.plotly_chart(fig_hrv, use_container_width=True)
