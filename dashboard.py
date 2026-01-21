
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import datetime
import calendar

# --- Page Configuration ---
st.set_page_config(
    page_title="Parva's Project 2026",
    page_icon="🏹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS / Aesthetics (Robinhood Theme) ---
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Metrics */
    .stMetric {
        background-color: #111;
        border-radius: 8px;
        padding: 10px 15px;
        border: 1px solid #222;
        margin-bottom: 10px;
    }
    .stMetric label {
        color: #8C8C8C !important;
        font-size: 0.85rem;
    }
    .stMetric div[data-testid="stMetricValue"] {
        color: #00C805 !important; /* Robinhood Green */
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    /* Feed Card */
    .feed-card {
        background-color: #111;
        border-bottom: 1px solid #222;
        padding: 15px;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .feed-date {
        color: #8C8C8C;
        font-size: 0.8rem;
        margin-bottom: 4px;
    }
    .feed-title {
        color: #FFFFFF;
        font-size: 1.0rem;
        font-weight: 500;
    }
    .feed-stats {
        color: #00C805;
        font-size: 0.9rem;
        font-weight: 500;
        text-align: right;
    }
    .feed-substats {
        color: #8C8C8C;
        font-size: 0.8rem;
        text-align: right;
    }

    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #00C805;
    }

    /* Headers */
    h1 { color: #FFFFFF !important; font-weight: 700; font-size: 2rem; }
    h2, h3 { color: #FFFFFF !important; font-weight: 600; }
    
    /* Fire Grid */
    .fire-grid-cell {
        text-align: center;
        padding: 4px;
        font-size: 0.75rem;
        color: #444;
        border-radius: 4px;
    }
    .fire-active {
        background-color: #00C80520; /* Low opacity green bg */
        color: #FFFFFF;
        border: 1px solid #00C805;
    }
    
    /* Remove top margin for cleaner look */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Radio Button as Horizontal Pills (Approximate via Streamlit standard layout) */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        gap: 20px;
    }

    /* --- MOBILE OPTIMIZATION --- */
    @media (max-width: 640px) {
        /* 1. Reduce padding to maximize space */
        .block-container {
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
            padding-top: 0.5rem !important;
        }

        /* 2. Scale down Headers */
        h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }

        /* 3. Scale down Metrics & text */
        .stMetric { padding: 8px !important; }
        .stMetric label { font-size: 0.7rem !important; }
        .stMetric div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
        
        /* 4. Touch Targets - Make buttons taller/easier to tap */
        div[data-testid="stButton"] > button {
            min_height: 45px !important;
            font-size: 1rem !important;
            margin-bottom: 8px !important;
        }
        
        /* 5. Coach Card Adaptation */
        .coach-card {
            padding: 10px !important;
            margin-bottom: 15px !important;
        }
        .coach-header { font-size: 0.9rem !important; }
        
        /* 6. Calendar & Feed */
        .fire-grid-cell { font-size: 0.65rem !important; padding: 1px !important; }
        .feed-card { padding: 10px !important; }
        
        /* 7. Tabs - easier scrolling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding-left: 10px !important;
            padding-right: 10px !important;
            font-size: 0.8rem !important;
        }
    }
    
    /* --- BUTTON STYLING --- */
    /* Primary Buttons (Refresh, Next/Prev) */
    div[data-testid="stButton"] > button {
        background-color: #111111;
        color: #00C805;
        border: 1px solid #333333;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #00C805;
        color: #FFFFFF;
        background-color: #00C80520;
    }
    
    /* Expander Header */
    .streamlit-expanderHeader {
        background-color: #111111;
        color: #FFFFFF;
        border: 1px solid #333333;
        border-radius: 8px;
    }
    
</style>
""", unsafe_allow_html=True)

# --- Helper Functions (Global) ---
def format_duration_hm(minutes):
    """Formats minutes into Xh Ym or Zm"""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins:02d}m"

def format_duration_ms(minutes):
    """Formats minutes into M:S (for pace)"""
    mins = int(minutes)
    secs = int((minutes - mins) * 60)
    return f"{mins}:{secs:02d}"

# --- Data Loading ---
def load_data():
    try:
        # Create connection object and retrieve data
        # 'gsheets' is the name of the connection in .streamlit/secrets.toml
        # ttl=600 for 10 min cache
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Read the DataFrame
        df = conn.read()
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df['Distance (km)'] = pd.to_numeric(df['Distance (km)'], errors='coerce').fillna(0)
            df['Elevation Gain (m)'] = pd.to_numeric(df['Elevation Gain (m)'], errors='coerce').fillna(0)
            df['Duration (min)'] = pd.to_numeric(df['Duration (min)'], errors='coerce').fillna(0)
            df['Avg HR'] = pd.to_numeric(df['Avg HR'], errors='coerce').fillna(0)
            
            # Normalize 'treadmill_running' to 'running' for logic checks
            df['NormalizedType'] = df['Type'].apply(lambda x: 'running' if 'running' in str(x).lower() else str(x).lower())
            
        return df
    except Exception as e:
        st.error("Setup Required: Please configure Streamlit Secrets with your Google Sheet credentials.")
        # Only show specific error in development/debugging if needed, but keeping it clean for deploy
        # st.error(f"Details: {e}") 
        return pd.DataFrame()

df = load_data()

# --- Header ---
# --- Header ---
st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="font-size: 3rem; margin-bottom: 0; background: -webkit-linear-gradient(45deg, #ffffff, #00C805); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Parva's Project 2026
        </h1>
        <a href="https://instagram.com/the_working_athlete" target="_blank" style="color: #8C8C8C; text-decoration: none; font-size: 1.1rem; border-bottom: 1px dotted #8C8C8C;">
            @the_working_athlete
        </a>
    </div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data found. Please run the sync script.")
    st.stop()

# --- Global Physiology Calculations ---
RHR = 45
MAX_HR = 197
HR_RESERVE = MAX_HR - RHR

def calculate_trimp(duration_min, avg_hr):
    if avg_hr == 0: return 0
    hrr_factor = (avg_hr - RHR) / HR_RESERVE
    trimp = duration_min * hrr_factor * 0.64 * np.exp(1.92 * hrr_factor)
    return trimp

try:
    df_phys = df.copy().sort_values("Date")
    df_phys['TRIMP'] = df_phys.apply(lambda row: calculate_trimp(row['Duration (min)'], row['Avg HR']), axis=1)
    df_phys = df_phys.set_index('Date').resample('D')['TRIMP'].sum().reset_index()
    df_phys['CTL'] = df_phys['TRIMP'].ewm(span=42, adjust=False).mean()
    df_phys['ATL'] = df_phys['TRIMP'].ewm(span=7, adjust=False).mean()
    df_phys['TSB'] = df_phys['CTL'] - df_phys['ATL']
    
    current_metrics = df_phys.iloc[-1]
    curr_ctl = current_metrics['CTL']
    curr_atl = current_metrics['ATL']
    curr_tsb = current_metrics['TSB']
    load_ratio = curr_atl / curr_ctl if curr_ctl > 0 else 0
    
    if 0.8 <= load_ratio <= 1.3:
        status_text = "Optimal"
        status_color = "#00C805"
    elif 1.3 < load_ratio <= 1.5:
        status_text = "High"
        status_color = "#FFFF00"
    elif load_ratio > 1.5:
        status_text = "Overreach"
        status_color = "#FF0000"
    else:
        status_text = "Recovery"
        status_color = "#8C8C8C"

except Exception as e:
    curr_ctl, curr_atl, curr_tsb, load_ratio = 0, 0, 0, 0
    status_text = "N/A"
    status_color = "#8C8C8C"

st.markdown("---")

# ==========================================
# ROW 1: TRAINING STATUS
# ==========================================
st.subheader("Training Status")

# --- 1. AI Coach (Full Width) ---
import google.generativeai as genai

# Caching the expensive API call (6 hours = 21600 seconds)
@st.cache_data(ttl=21600, show_spinner="Summoning the Coach...")
def ask_gemini_coach(prompt_text):
    """
    Calls Gemini API with caching.
    Raises exception on failure so bad results aren't cached.
    """
    try:
        GENAI_API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=GENAI_API_KEY)
        
        # Try Flash models first, then standard Pro if needed
        models = ['gemini-1.5-flash', 'gemini-2.0-flash-exp', 'gemini-2.0-flash'] 
        
        for m in models:
            try:
                model = genai.GenerativeModel(m)
                response = model.generate_content(prompt_text)
                return response.text
            except Exception as e:
                # Check for rate limits specifically to fail fast if needed? 
                # Or just let the loop continue.
                continue
        
        # If we get here, all models failed
        raise Exception("All Gemini models failed to respond.")
        
    except Exception as outer_e:
        raise outer_e

try:
    with st.expander("📝 AI Coach Settings & Context", expanded=False):
        user_manual_context = st.text_area("Coach Context", placeholder="E.g. Feeling tired...", label_visibility="collapsed")
    
    # CSS for Coach Card
    st.markdown("""<style>.coach-card { border: 1px solid #7c4dff; background: linear-gradient(135deg, #0f0c29 0%, #302b63 100%); border-left: 5px solid #b388ff; padding: 15px; border-radius: 12px; margin-top: 5px; margin-bottom: 20px; color: #e0e0e0; font-size: 0.95rem; } .coach-header { font-size: 1.0rem; font-weight: 600; color: #b388ff; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }</style>""", unsafe_allow_html=True)

    project_goals = "PROJECT 2026 GOALS: 2026km Running, 26 Half Marathons, 104 Strength Sessions, 200+ Active Days."
    user_context_str = f"User: Parva. Physiology: RHR 45, MaxHR 197. User Input: {user_manual_context or 'None'}."
    metrics_context_str = f"Current Status: Date {datetime.date.today()}. CTL {curr_ctl:.1f}, ATL {curr_atl:.1f}, TSB {curr_tsb:.1f}. Workload Ratio {load_ratio:.2f} ({status_text})."
    
    prompt = f"""
    Act as an elite endurance coach for Parva. 
    CONTEXT: {project_goals}
    {user_context_str}
    {metrics_context_str}
    
    TASK: Provide a concise, motivating response (max 3-4 sentences total) structured as:
    1. ⚡ Short Term: Specific focus for today/tomorrow based on TSB/Fatigue.
    2. 🔭 Long Term: How this fits the 2026km/HM goals.
    
    Keep it punchy. If TSB is very negative, mandate rest. If TSB is high positive, push for volume.
    """

    # Logic:
    # 1. If context changed, we used to manually clear. 
    #    With st.cache_data, if 'prompt' changes (it includes context), it auto-runs.
    #    However, we need to ensure the CACHE is cleared if the user manually hits refresh.
    
    advice_text = ""
    error_display = ""
    
    try:
        advice_text = ask_gemini_coach(prompt)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Quota" in err_str:
             error_display = "Coach is resting (Rate Limit hit). Try again later."
        else:
             error_display = f"Coach Offline: {err_str}"

    if advice_text:
        st.markdown(f"""<div class="coach-card"><div class="coach-header"><span>🧙‍♂️</span> AI Coach</div><div>{advice_text}</div></div>""", unsafe_allow_html=True)
    else:
        # Fallback display
        st.markdown(f"""<div class="coach-card"><div class="coach-header"><span>🧙‍♂️</span> AI Coach</div><div>{error_display}</div></div>""", unsafe_allow_html=True)

    if st.button("Refresh Advice", key="btn_refresh_advice"):
        ask_gemini_coach.clear()
        st.rerun()

except Exception as e:
    st.caption(f"Coach Input Error: {e}")

# --- 2. Charts (Split View) ---
col_train_L, col_train_R = st.columns([2, 1])

# --- Training Left: PMC Chart ---
with col_train_L:
    st.markdown("<div style='font-size: 1rem; font-weight: 600; margin-bottom: 5px;'>Fitness, Fatigue and Form Chart</div>", unsafe_allow_html=True)
    # Reordered Tabs: 1Y First
    s1, s2, s3, s4, s5, s6 = st.tabs(["1Y", "YTD", "6M", "3M", "30D", "7D"])
    
    def plot_pmc(days_lookback=None, is_ytd=False):
        end_date = datetime.datetime.now()
        if is_ytd:
            start_date = datetime.datetime(end_date.year, 1, 1)
        else:
            start_date = end_date - datetime.timedelta(days=days_lookback)
            
        mask = (df_phys['Date'] >= start_date) & (df_phys['Date'] <= end_date)
        df_plot = df_phys.loc[mask].copy()
        
        if df_plot.empty:
            st.info("No data.")
            return

        fig_pmc = go.Figure()
        # Form
        fig_pmc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['TSB'], name='Form', fill='tozeroy', line=dict(color='rgba(255, 255, 0, 0.5)', width=0), fillcolor='rgba(255, 255, 0, 0.2)'))
        # Fitness
        fig_pmc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['CTL'], name='Fitness', line=dict(color='#00C805', width=2)))
        # Fatigue
        fig_pmc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['ATL'], name='Fatigue', line=dict(color='#FF0080', width=2)))
        
        fig_pmc.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0), height=300, showlegend=True, legend=dict(orientation="h", x=0, y=1.1, bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_pmc, use_container_width=True)

    with s1: plot_pmc(days_lookback=365)
    with s2: plot_pmc(is_ytd=True)
    with s3: plot_pmc(days_lookback=180)
    with s4: plot_pmc(days_lookback=90)
    with s5: plot_pmc(days_lookback=30)
    with s6: plot_pmc(days_lookback=7)

# --- Training Right: Gauge ---
with col_train_R:
    # 1. Gauge - Increased Height
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = load_ratio,
        title = {'text': "Workload Ratio"},
        gauge = {'axis': {'range': [0, 2]}, 'bar': {'color': status_color}, 'bgcolor': "rgba(0,0,0,0)", 'steps': [{'range': [0, 0.8], 'color': '#333'}, {'range': [0.8, 1.3], 'color': '#113311'}, {'range': [1.3, 1.5], 'color': '#333311'}, {'range': [1.5, 2.0], 'color': '#331111'}]}
    ))
    # Increased height to 280 to match PMC better
    fig_gauge.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=15, r=15, t=50, b=10), height=280)
    st.plotly_chart(fig_gauge, use_container_width=True)
    st.caption(f"Status: {status_text} | CTL: {curr_ctl:.0f} | TSB: {curr_tsb:.0f}")

st.markdown("---")

# ==========================================
# FILTERS (Moved Below Row 1)
# ==========================================
f_col1, f_col2 = st.columns([1, 4])
with f_col1:
    selected_year = st.selectbox("Year", [2026, 2025], key="year_select")
with f_col2:
    activity_filter = st.selectbox("Activity", ["All", "Running", "Strength Training", "Walking/Hiking", "Other"], key="act_select")

# --- Filtering Logic ---
# 1. Base filter by year
df_year = df[df['Date'].dt.year == selected_year]

# 2. Activity Filter
if activity_filter == "Running":
    df_filtered = df_year[df_year['NormalizedType'] == 'running']
elif activity_filter == "Strength Training":
    df_filtered = df_year[df_year['NormalizedType'].str.contains('strength', na=False)]
elif activity_filter == "Walking/Hiking":
    df_filtered = df_year[df_year['NormalizedType'].str.contains('walking', na=False) | df_year['NormalizedType'].str.contains('hiking', na=False)]
elif activity_filter == "Other":
    df_filtered = df_year[
        (~df_year['NormalizedType'].str.contains('running', na=False)) & 
        (~df_year['NormalizedType'].str.contains('strength', na=False)) &
        (~df_year['NormalizedType'].str.contains('walking', na=False)) &
        (~df_year['NormalizedType'].str.contains('hiking', na=False))
    ]
else:
    df_filtered = df_year

# ==========================================
# ROW 2: PROGRESS (LEFT) | TRENDS (RIGHT)
# ==========================================
col_row2_L, col_row2_R = st.columns([1, 1])

# --- LEFT: Project Stats ---
with col_row2_L:
    title_suffix = "Progress" if selected_year == 2026 else "Totals"
    st.subheader(f"Project {selected_year} {title_suffix}")
    
    df_stats = df[df['Date'].dt.year == selected_year]
    total_run_km = df_stats[df_stats['NormalizedType'] == 'running']['Distance (km)'].sum()
    hm_count = len(df_stats[(df_stats['NormalizedType'] == 'running') & (df_stats['Distance (km)'] >= 21.09)])
    active_days = df_stats['Date'].dt.date.nunique()
    strength_count = len(df_stats[df_stats['NormalizedType'].str.contains('strength', na=False)])
    
    is_2026 = (selected_year == 2026)
    target_run_km = 2026.0 if is_2026 else None
    target_hm = 26 if is_2026 else None
    target_active = 200 if is_2026 else None
    target_strength = 104 if is_2026 else None
    
    kp1, kp2 = st.columns(2); kp3, kp4 = st.columns(2)
    with kp1:
        st.metric("Running Distance", f"{total_run_km:.1f} km", f"/ {target_run_km:.0f}" if is_2026 else "")
        if is_2026: st.progress(min(total_run_km / target_run_km, 1.0))
    with kp2:
        st.metric("Half Marathons", f"{hm_count}", f"/ {target_hm}" if is_2026 else "")
        if is_2026: st.progress(min(hm_count / target_hm, 1.0) if target_hm > 0 else 0)
    with kp3:
        st.metric("Active Days", f"{active_days}", f"/ {target_active}" if is_2026 else "")
        if is_2026: st.progress(min(active_days / target_active, 1.0))
    with kp4:
        st.metric("Strength Sessions", f"{strength_count}", f"/ {target_strength}" if is_2026 else "")
        if is_2026: st.progress(min(strength_count / target_strength, 1.0))

# --- RIGHT: Trends ---
with col_row2_R:
    st.subheader("Performance Trends")
    # Reordered Tabs: 1Y First
    t1, t2, t3, t4, t5, t6 = st.tabs(["1Y", "YTD", "6M", "3M", "30D", "7D"])

    def format_duration_hm(minutes):
        if minutes < 60: return f"{int(minutes)}m"
        hours = int(minutes // 60); mins = int(minutes % 60)
        return f"{hours}h {mins:02d}m"

    def render_summary_chart(days_lookback=None, is_ytd=False):
        end_date = datetime.datetime.now()
        start_date = datetime.datetime(end_date.year, 1, 1) if is_ytd else end_date - datetime.timedelta(days=days_lookback)
        
        # Filter Logic based on Global 'activity_filter'
        if activity_filter == "Running": df_trend = df[df['NormalizedType'] == 'running']
        elif activity_filter == "Strength Training": df_trend = df[df['NormalizedType'].str.contains('strength', na=False)]
        elif activity_filter == "Walking/Hiking": df_trend = df[df['NormalizedType'].str.contains('walking', na=False) | df['NormalizedType'].str.contains('hiking', na=False)]
        elif activity_filter == "Other": df_trend = df[(~df['NormalizedType'].str.contains('running', na=False)) & (~df['NormalizedType'].str.contains('strength', na=False)) & (~df['NormalizedType'].str.contains('walking', na=False)) & (~df['NormalizedType'].str.contains('hiking', na=False))]
        else: df_trend = df.copy()

        mask = (df_trend['Date'] >= start_date) & (df_trend['Date'] <= end_date)
        df_trend_final = df_trend.loc[mask].copy()

        if df_trend_final.empty: st.info("No activities."); return

        freq = 'D' if (days_lookback and days_lookback <= 31) else 'W-MON'
        df_trend_final['Period'] = df_trend_final['Date'].dt.to_period(freq).apply(lambda r: r.start_time)

        if activity_filter in ["Running", "Walking/Hiking", "All"]:
            agg = df_trend_final.groupby('Period')['Distance (km)'].sum().reset_index()
            y_col = 'Distance (km)'; y_title = "Distance"; bar_color = '#00C805'
            agg['Tooltip'] = agg[y_col].apply(lambda x: f"{x:.1f} km")
            total_fmt = f"{agg[y_col].sum():.1f} km"
        else:
            df_trend_final['Duration (hr)'] = df_trend_final['Duration (min)'] / 60
            agg = df_trend_final.groupby('Period')['Duration (hr)'].sum().reset_index()
            y_col = 'Duration (hr)'; y_title = "Hours"; bar_color = '#00C805'
            agg['Tooltip'] = agg[y_col].apply(lambda x: format_duration_hm(x * 60))
            total_fmt = format_duration_hm(agg[y_col].sum() * 60)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=agg['Period'], y=agg[y_col], name="Vol", marker_color=bar_color, opacity=0.8, customdata=agg['Tooltip'], hovertemplate="%{customdata}<extra></extra>"))
        fig.add_trace(go.Scatter(x=agg['Period'], y=agg[y_col], name="Trend", mode='lines+markers', line=dict(color='#FFFFFF', width=2), marker=dict(size=4, color='#FFFFFF'), customdata=agg['Tooltip'], hovertemplate="%{customdata}<extra></extra>"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=False, title=y_title), hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), height=250, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Total: {total_fmt}")

    with t1: render_summary_chart(days_lookback=365)
    with t2: render_summary_chart(is_ytd=True)
    with t3: render_summary_chart(days_lookback=180)
    with t4: render_summary_chart(days_lookback=90)
    with t5: render_summary_chart(days_lookback=30)
    with t6: render_summary_chart(days_lookback=7)

st.markdown("---")

# ==========================================
# ROW 3: PERSONAL BESTS (LEFT) | CALENDAR (RIGHT)
# ==========================================
col_row3_L, col_row3_R = st.columns([1, 1])

# --- LEFT: Personal Bests ---
with col_row3_L:
    st.subheader("Personal Bests")
    # Using 2x2 Grid since we are in a half-width column
    pb_r1_c1, pb_r1_c2 = st.columns(2)
    pb_r2_c1, pb_r2_c2 = st.columns(2)
    
    with pb_r1_c1: st.metric("5k", "23:15")
    with pb_r1_c2: st.metric("10k", "51:49")
    with pb_r2_c1: st.metric("Half Marathon", "1:55:37")
    with pb_r2_c2: st.metric("Marathon", "4:26:27")

# --- RIGHT: Activity Calendar ---
with col_row3_R:
    st.subheader("Activity Calendar")
    if 'cal_date' not in st.session_state: st.session_state.cal_date = datetime.date.today()
    
    def prev_month(): st.session_state.cal_date = (st.session_state.cal_date.replace(day=1) - datetime.timedelta(days=1))
    def next_month(): st.session_state.cal_date = (st.session_state.cal_date.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    
    cc1, cc2, cc3 = st.columns([1, 5, 1])
    with cc1: st.button("◀", on_click=prev_month, key="cal_prev")
    with cc2: st.markdown(f"<h3 style='text-align: center; margin: 0;'>{st.session_state.cal_date.strftime('%B %Y')}</h3>", unsafe_allow_html=True)
    with cc3: st.button("▶", on_click=next_month, key="cal_next")
    
    view_year = st.session_state.cal_date.year; view_month = st.session_state.cal_date.month
    df_cal = df[(df['Date'].dt.year == view_year) & (df['Date'].dt.month == view_month)]
    
    # Apply global activity filter to calendar
    if activity_filter == "Running": df_cal = df_cal[df_cal['NormalizedType'] == 'running']
    elif activity_filter == "Strength Training": df_cal = df_cal[df_cal['NormalizedType'].str.contains('strength', na=False)]
    elif activity_filter == "Walking/Hiking": df_cal = df_cal[df_cal['NormalizedType'].str.contains('walking', na=False) | df_cal['NormalizedType'].str.contains('hiking', na=False)]
    elif activity_filter == "Other": df_cal = df_cal[(~df_cal['NormalizedType'].str.contains('running', na=False)) & (~df_cal['NormalizedType'].str.contains('strength', na=False)) & (~df_cal['NormalizedType'].str.contains('walking', na=False)) & (~df_cal['NormalizedType'].str.contains('hiking', na=False))]
    
    active_dates = set(df_cal['Date'].dt.day.tolist())
    cal_obj = calendar.Calendar(firstweekday=0)
    month_days = cal_obj.monthdayscalendar(view_year, view_month)
    
    # CSS Grid Style (Injected locally for scoping)
    st.markdown("""
    <style>
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
        margin-top: 10px;
    }
    .cal-header {
        text-align: center;
        color: #888;
        font-size: 0.8rem;
        padding-bottom: 4px;
    }
    .cal-cell {
        text-align: center;
        padding: 8px;
        border-radius: 6px;
        background-color: #1a1a1a;
        color: #555;
        font-size: 0.9rem;
    }
    .cal-cell.active {
        background-color: #00C80530;
        color: #ffffff;
        border: 1px solid #00C805;
        font-weight: bold;
    }
    .cal-cell.empty {
        background-color: transparent;
    }
    
    @media (max-width: 640px) {
        .calendar-grid { gap: 2px; }
        .cal-cell { padding: 4px; font-size: 0.75rem; min-height: 30px; display: flex; align-items: center; justify-content: center; }
    }
    </style>
    """, unsafe_allow_html=True)

    # HTML Generator
    html_content = '<div class="calendar-grid">'
    
    # Headers
    for d in ["M", "T", "W", "T", "F", "S", "S"]:
        html_content += f'<div class="cal-header">{d}</div>'
        
    # Days
    for week in month_days:
        for day in week:
            if day == 0:
                html_content += '<div class="cal-cell empty"></div>'
            else:
                is_active = day in active_dates
                css_class = "cal-cell active" if is_active else "cal-cell"
                # Add fire icon only if active
                content = f"{day}{' 🔥' if is_active else ''}"
                # On mobile, the fire icon might force stacking if not careful. 
                # Let's keep it simply "Day" and maybe a color dot? 
                # Preserving the fire for now but CSS handles wrapping if needed.
                html_content += f'<div class="{css_class}">{content}</div>'
    
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

st.markdown("---")

# --- BOTTOM: Activity Feed ---
st.subheader("Activity Feed")

# Sort Controls
s_col1, s_col2 = st.columns([1, 4])
with s_col1:
    sort_option = st.selectbox("Sort By", ["Date", "Distance", "Duration"])
with s_col2:
    sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True, label_visibility="collapsed")

st.caption(f"Showing {len(df_filtered)} activities")

# Sorting Logic
ascending = True if sort_order == "Ascending" else False

if sort_option == "Date":
    sort_col = "Date"
elif sort_option == "Distance":
    sort_col = "Distance (km)"
elif sort_option == "Duration":
    sort_col = "Duration (min)"

df_feed = df_filtered.sort_values(sort_col, ascending=ascending)

for index, row in df_feed.iterrows():
    # Parse Data
    act_date = row['Date'].strftime('%b %d, %Y')
    act_type = row['Type'].replace('_', ' ').title()
    norm_type = row['NormalizedType']
    
    # Stats Logic
    main_stat = ""
    sub_stat = ""
    
    # Running (and Treadmill)
    if 'running' in norm_type:
        dist = row['Distance (km)']
        dur = row['Duration (min)']
        hr = row['Avg HR']
        
        # Pace (min/km)
        pace = dur / dist if dist > 0 else 0
        pace_fmt = format_duration_ms(pace)
        
        main_stat = f"{dist} km"
        sub_stat = f"{pace_fmt} /km • {int(hr)} bpm"
        
    # Strength
    elif 'strength' in norm_type:
        dur = row['Duration (min)']
        hr = row['Avg HR']
        
        main_stat = format_duration_hm(dur)
        sub_stat = f"Avg HR: {int(hr)} bpm"
        
    # Others (Hiking/Walking/etc)
    else:
        dist = row['Distance (km)']
        dur = row['Duration (min)']
        
        if dist > 0:
            main_stat = f"{dist} km"
            sub_stat = format_duration_hm(dur)
        else:
            main_stat = format_duration_hm(dur)
            sub_stat = ""

    # Render Card
    st.markdown(
        f"""
        <div class="feed-card">
            <div>
                <div class="feed-date">{act_date}</div>
                <div class="feed-title">{act_type}</div>
            </div>
            <div>
                <div class="feed-stats">{main_stat}</div>
                <div class="feed-substats">{sub_stat}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
