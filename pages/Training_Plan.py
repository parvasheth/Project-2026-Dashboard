import streamlit as st
import pandas as pd
import json
from utils import load_data, calculate_physiology, save_training_plan, load_training_plan
from training_engine import generate_training_plan

st.set_page_config(page_title="Elite Training Engine | Project 2026", page_icon="🧬", layout="wide")

# --- Grafana Dark Theme with Neon Accents ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0c0e; }
    h1, h2, h3, h4, h5, p, span, label { color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #181b1f; padding: 10px; border-radius: 4px; border-left: 3px solid #73bf69; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .vibe-box {
        background-color: #181b1f;
        border-left: 4px solid #775DD0;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 30px;
    }
    
    .day-card {
        background-color: #181b1f;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 10px;
        min-height: 120px;
        display: flex;
        flex-direction: column;
    }
    
    .day-title { font-weight: bold; font-size: 0.9em; margin-bottom: 5px; color: #888; }
    .day-type { font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }
    .day-dist { color: #00E396; font-size: 0.9em; margin-bottom: 5px; }
    .day-desc { font-size: 0.8em; color: #ccc; flex-grow: 1; }
    
    .type-rest { color: #888; }
    .type-easy { color: #00E396; }
    .type-interval { color: #FF4560; }
    .type-long { color: #775DD0; }
    .type-tempo { color: #f2cc0c; }
    </style>
""", unsafe_allow_html=True)

# Custom Nav
st.markdown("""
<style>
div[data-testid="stColumn"] > div > div > div > div { gap: 0.5rem; }
.nav-btn { width: 100%; border: 1px solid #333; background: #181b1f; color: white; padding: 10px; text-align: center; border-radius: 5px; cursor: pointer; text-decoration: none; display: block; }
.nav-btn:hover { background: #22252b; border-color: #73bf69; }
</style>
""", unsafe_allow_html=True)
nav1, nav2, nav3, _ = st.columns([1, 1, 1, 3])
with nav1:
    if st.button("🏋️ Training Hub"): st.switch_page("dashboard.py")
with nav2:
    if st.button("🧘 Personal History"): st.switch_page("pages/Personal_History.py")
with nav3:
    st.button("🧬 Training Plan Engine", disabled=True)

st.title("🧬 Elite Training Plan Engine")
st.markdown("Powered by AI 'Deep Vibe' Data Audit")

# --- Load Data Engine ---
def load_all_data():
    df_act = load_data()
    return df_act, calculate_physiology(df_act)

df_activ, df_phys = load_all_data()

# --- Load Current Plan State ---
current_plan_str = load_training_plan()
plan_state = None
if current_plan_str:
    try:
        plan_state = json.loads(current_plan_str)
    except:
        pass

# --- Inputs ---
with st.expander("⚙️ Configure Plan Parameters", expanded=(plan_state is None)):
    c1, c2, c3 = st.columns(3)
    with c1:
        goal_distance = st.text_input("Goal Distance / Event", value="Half Marathon (21.1km)")
    with c2:
        duration_weeks = st.number_input("Duration (Weeks)", min_value=1, max_value=24, value=12)
    with c3:
         profile_context = st.text_area("Profile Context", value="28.5 years old, 74.8kg, currently 50-55km/week. Running in AZ heat.")
         
    if st.button("🚀 Generate Adaptive Plan", use_container_width=True, type="primary"):
        with st.spinner("Analyzing TRIMP Load and historical pacing..."):
            new_plan = generate_training_plan(goal_distance, duration_weeks, profile_context, df_activ, df_phys)
            if new_plan and "plan" in new_plan:
                save_training_plan(json.dumps(new_plan))
                st.session_state['generated'] = True
                st.rerun()
            else:
                st.error("Engine failed to generate a valid plan. Check logs.")

# --- Display Plan ---
if plan_state and "plan" in plan_state:
    st.markdown(f"""
    <div class="vibe-box">
        <h4>🧠 Coach's Vibe Check</h4>
        <p>{plan_state.get('vibe_check', 'Vibe check analysis not available.')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📅 Visual Calendar View")
    
    for week in plan_state.get('plan', []):
        st.markdown(f"#### Week {week.get('week_number')} - <span style='color:#73bf69;'>{week.get('focus', '')}</span>", unsafe_allow_html=True)
        
        days = week.get('days', [])
        cols = st.columns(7)
        for i, col in enumerate(cols):
            if i < len(days):
                d = days[i]
                type_class = f"type-{str(d.get('type', '')).lower()}"
                dist_str = f"{d.get('distance_km', 0)} km" if d.get('distance_km', 0) > 0 else "Rest"
                
                with col:
                    st.markdown(f"""
                        <div class="day-card">
                            <div class="day-title">{d.get('day', '')[:3].upper()}</div>
                            <div class="day-type {type_class}">{d.get('type', '')}</div>
                            <div class="day-dist">{dist_str}</div>
                            <div class="day-desc">{d.get('description', '')}</div>
                        </div>
                    """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
elif not plan_state:
    st.info("No active training plan found. Configure parameters and generate one above.")
