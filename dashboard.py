
import streamlit as st
import pandas as pd
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
    
</style>
""", unsafe_allow_html=True)

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
st.title("Parva's Project 2026")

if df.empty:
    st.warning("No data found. Please run the sync script.")
    st.stop()

# --- Filters (Top) ---
# Using columns to put them side-by-side
f_col1, f_col2 = st.columns([1, 4])
with f_col1:
    selected_year = st.radio("Year", [2026, 2025], horizontal=True, key="year_select")
with f_col2:
    activity_filter = st.radio("Activity", ["All", "Running", "Strength Training", "Walking/Hiking", "Other"], horizontal=True, key="act_select")

# --- Filtering Logic ---
# 1. Base filter by year for the PAGE VIEW (Feed, etc)
df_year = df[df['Date'].dt.year == selected_year]

# 2. Activity Filter applying to df_year
if activity_filter == "Running":
    df_filtered = df_year[df_year['NormalizedType'] == 'running']
elif activity_filter == "Strength Training":
    df_filtered = df_year[df_year['NormalizedType'].str.contains('strength', na=False)]
elif activity_filter == "Walking/Hiking":
    df_filtered = df_year[df_year['NormalizedType'].str.contains('walking', na=False) | df_year['NormalizedType'].str.contains('hiking', na=False)]
elif activity_filter == "Other":
    # Everything NOT running, strength, walking, or hiking
    df_filtered = df_year[
        (~df_year['NormalizedType'].str.contains('running', na=False)) & 
        (~df_year['NormalizedType'].str.contains('strength', na=False)) &
        (~df_year['NormalizedType'].str.contains('walking', na=False)) &
        (~df_year['NormalizedType'].str.contains('hiking', na=False))
    ]
else:
    df_filtered = df_year

st.markdown("---")

# --- Top Section: Split View ---
col_stats, col_cal = st.columns([1, 1])

# --- LEFT: Year Stats (Dynamic) ---
with col_stats:
    title_suffix = "Progress" if selected_year == 2026 else "Totals"
    st.subheader(f"Project {selected_year} {title_suffix}")
    
    # Calculate stats for the SELECTED YEAR
    df_stats = df[df['Date'].dt.year == selected_year]
    
    # 1. Total Running Distance
    df_run = df_stats[df_stats['NormalizedType'] == 'running']
    total_run_km = df_run['Distance (km)'].sum()
    
    # 2. Half Marathons (>21.1 km)
    hm_count = len(df_run[df_run['Distance (km)'] >= 21.09])
    
    # 3. Total Active Days
    active_days = df_stats['Date'].dt.date.nunique()
    
    # 4. Strength Sessions
    df_strength = df_stats[df_stats['NormalizedType'].str.contains('strength', na=False)]
    strength_count = len(df_strength)
    
    # Targets (Only for 2026)
    is_2026 = (selected_year == 2026)
    
    target_run_km = 2026.0 if is_2026 else None
    target_hm = 26 if is_2026 else None
    target_active = 200 if is_2026 else None
    target_strength = 104 if is_2026 else None
    
    # Display Grid
    kp1, kp2 = st.columns(2)
    kp3, kp4 = st.columns(2)
    
    with kp1:
        label = f"/ {target_run_km:.0f}" if is_2026 else ""
        st.metric("Running Distance", f"{total_run_km:.1f} km", label)
        if is_2026:
            st.progress(min(total_run_km / target_run_km, 1.0))
        
    with kp2:
        label = f"/ {target_hm}" if is_2026 else ""
        st.metric("Half Marathons", f"{hm_count}", label)
        if is_2026:
            st.progress(min(hm_count / target_hm, 1.0) if target_hm > 0 else 0)
        
    with kp3:
        label = f"/ {target_active}" if is_2026 else ""
        st.metric("Active Days", f"{active_days}", label)
        if is_2026:
            st.progress(min(active_days / target_active, 1.0))
        
    with kp4:
        label = f"/ {target_strength}" if is_2026 else ""
        st.metric("Strength Sessions", f"{strength_count}", label)
        if is_2026:
            st.progress(min(strength_count / target_strength, 1.0))


# --- RIGHT: Compact Calendar ---
# --- RIGHT: Interactive Calendar ---
with col_cal:
    st.subheader("Activity Calendar")
    
    # Initialize Session State for Calendar
    if 'cal_date' not in st.session_state:
        st.session_state.cal_date = datetime.date.today()

    # Navigation Functions
    def prev_month():
        curr = st.session_state.cal_date
        first = curr.replace(day=1)
        prev = first - datetime.timedelta(days=1)
        st.session_state.cal_date = prev

    def next_month():
        curr = st.session_state.cal_date
        # Go to 28th of next month to be safe, then replace
        # Simplest: (curr.replace(day=1) + 32 days).replace(day=1)
        next_month_date = (curr.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        st.session_state.cal_date = next_month_date

    # Header Row with Buttons
    cal_col_l, cal_col_mid, cal_col_r = st.columns([1, 5, 1])
    with cal_col_l:
        st.button("◀", on_click=prev_month, key="cal_prev")
    with cal_col_mid:
        curr_date = st.session_state.cal_date
        st.markdown(f"<h3 style='text-align: center; margin: 0; padding: 0;'>{curr_date.strftime('%B %Y')}</h3>", unsafe_allow_html=True)
    with cal_col_r:
        st.button("▶", on_click=next_month, key="cal_next")

    # Filter Data for the VIEWING Month (cal_date)
    # Note: Calendar respects the global Activity Filter, but has its own Date
    view_year = curr_date.year
    view_month = curr_date.month
    
    # Filter df by Year/Month AND Activity Type
    df_cal_view = df[(df['Date'].dt.year == view_year) & (df['Date'].dt.month == view_month)]
    
    # Apply Activity Filter Logic matching top
    if activity_filter == "Running":
        df_cal_view = df_cal_view[df_cal_view['NormalizedType'] == 'running']
    elif activity_filter == "Strength Training":
        df_cal_view = df_cal_view[df_cal_view['NormalizedType'].str.contains('strength', na=False)]
    elif activity_filter == "Walking/Hiking":
        df_cal_view = df_cal_view[df_cal_view['NormalizedType'].str.contains('walking', na=False) | df_cal_view['NormalizedType'].str.contains('hiking', na=False)]
    elif activity_filter == "Other":
        df_cal_view = df_cal_view[
            (~df_cal_view['NormalizedType'].str.contains('running', na=False)) & 
            (~df_cal_view['NormalizedType'].str.contains('strength', na=False)) &
            (~df_cal_view['NormalizedType'].str.contains('walking', na=False)) &
            (~df_cal_view['NormalizedType'].str.contains('hiking', na=False))
        ]
    
    active_dates_cal = set(df_cal_view['Date'].dt.day.tolist())
    
    # Calendar Grid
    cal_obj = calendar.Calendar(firstweekday=0)
    month_days = cal_obj.monthdayscalendar(view_year, view_month)
    
    # Days Header
    cols = st.columns(7)
    day_names = ["M", "T", "W", "T", "F", "S", "S"]
    for idx, d in enumerate(day_names):
        cols[idx].markdown(f"<div style='text-align:center; color:#888; font-size:0.8rem;'>{d}</div>", unsafe_allow_html=True)
        
    # Days Grid
    for week in month_days:
        cols = st.columns(7)
        for idx, day_num in enumerate(week):
            if day_num == 0:
                cols[idx].write("")
            else:
                is_active = day_num in active_dates_cal
                # Optional: Different color for different activity types? 
                # For now, Green for active.
                css_class = "fire-grid-cell fire-active" if is_active else "fire-grid-cell"
                content = f"{day_num}"
                if is_active:
                     content += " 🔥"
                
                cols[idx].markdown(
                    f"<div class='{css_class}'>{content}</div>",
                    unsafe_allow_html=True
                )

# --- Personal Bests (Full Width) ---
st.markdown("---")
st.subheader("Personal Bests")
pb1, pb2, pb3, pb4 = st.columns(4)

with pb1: st.metric("5k", "23:15")
with pb2: st.metric("10k", "51:49")
with pb3: st.metric("Half Marathon", "1:55:37")
with pb4: st.metric("Marathon", "4:26:27")
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

st.markdown("---")

# --- MIDDLE: Summary Charts (Strava Style) ---
st.subheader("Performance Trends")

# Timeframe Tabs
t1, t2, t3, t4, t5, t6 = st.tabs(["Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last Year", "YTD"])

def render_summary_chart(days_lookback=None, is_ytd=False):
    end_date = datetime.datetime.now()
    if is_ytd:
        start_date = datetime.datetime(end_date.year, 1, 1)
    else:
        start_date = end_date - datetime.timedelta(days=days_lookback)
    
    # 1. Filter by Activity Type (Global)
    if activity_filter == "Running":
        df_trend = df[df['NormalizedType'] == 'running']
    elif activity_filter == "Strength Training":
        df_trend = df[df['NormalizedType'].str.contains('strength', na=False)]
    elif activity_filter == "Walking/Hiking":
        df_trend = df[df['NormalizedType'].str.contains('walking', na=False) | df['NormalizedType'].str.contains('hiking', na=False)]
    elif activity_filter == "Other":
        df_trend = df[
            (~df['NormalizedType'].str.contains('running', na=False)) & 
            (~df['NormalizedType'].str.contains('strength', na=False)) &
            (~df['NormalizedType'].str.contains('walking', na=False)) &
            (~df['NormalizedType'].str.contains('hiking', na=False))
        ]
    else:
        df_trend = df.copy()

    # 2. Filter by Timeframe
    mask = (df_trend['Date'] >= start_date) & (df_trend['Date'] <= end_date)
    df_trend_final = df_trend.loc[mask].copy()

    if df_trend_final.empty:
        st.info("No activities in this timeframe.")
        return

    # 3. Aggregate
    if days_lookback and days_lookback <= 14:
        freq = 'D'
    elif days_lookback and days_lookback <= 31: 
        freq = 'D'
    else:
        freq = 'W-MON'

    df_trend_final['Period'] = df_trend_final['Date'].dt.to_period(freq).apply(lambda r: r.start_time)

    # 4. Metrics
    if activity_filter in ["Running", "Walking/Hiking", "All"]:
        # Show Distance
        agg = df_trend_final.groupby('Period')['Distance (km)'].sum().reset_index()
        y_col = 'Distance (km)'
        y_title = "Distance (km)"
        bar_color = '#00C805' # Green
        line_color = '#FFFFFF' # White Trend
        
        # Tooltip format (Numeric)
        agg['Tooltip'] = agg[y_col].apply(lambda x: f"{x:.1f} km")
        total_fmt = f"{agg[y_col].sum():.1f} km"
        
    else:
        # Show Duration (Hours/Mins)
        df_trend_final['Duration (hr)'] = df_trend_final['Duration (min)'] / 60
        agg = df_trend_final.groupby('Period')['Duration (hr)'].sum().reset_index()
        y_col = 'Duration (hr)'
        y_title = "Duration (hrs)"
        # Use a muted green or white/grey for Strength/Other to avoid "Sudden Orange"
        # Keeping consistent Project 2026 Theme: Green is Good / Active.
        bar_color = '#00C805' 
        line_color = '#FFFFFF'
        
        # Tooltip format (HH:MM)
        agg['Tooltip'] = agg[y_col].apply(lambda x: format_duration_hm(x * 60))
        total_mins = agg[y_col].sum() * 60
        total_fmt = format_duration_hm(total_mins)

    # Create Combo Chart (Bar + Line)
    fig = go.Figure()
    
    # Bar Trace
    fig.add_trace(go.Bar(
        x=agg['Period'], 
        y=agg[y_col],
        name="Volume",
        marker_color=bar_color,
        opacity=0.8,
        customdata=agg['Tooltip'],
        hovertemplate="%{customdata}<extra></extra>"
    ))
    
    # Line Trace (Trend)
    fig.add_trace(go.Scatter(
        x=agg['Period'],
        y=agg[y_col],
        name="Trend",
        mode='lines+markers',
        line=dict(color=line_color, width=2),
        marker=dict(size=4, color=line_color),
        customdata=agg['Tooltip'],
        hovertemplate="%{customdata}<extra></extra>"
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=False, title=y_title),
        hovermode="x unified",
        margin=dict(l=0, r=0, t=10, b=0),
        height=250,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Total: {total_fmt}")


with t1: render_summary_chart(days_lookback=7)
with t2: render_summary_chart(days_lookback=30)
with t3: render_summary_chart(days_lookback=90)
with t4: render_summary_chart(days_lookback=180)
with t5: render_summary_chart(days_lookback=365)
with t6: render_summary_chart(is_ytd=True)

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
