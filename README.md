# 🏹 Parva's Project 2026 Dashboard

> **"2026km in 2026."**  
> A personal athlete dashboard to track, analyze, and optimize the journey towards ambitious endurance goals.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![Gemini AI](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=googlebard)
![Garmin](https://img.shields.io/badge/Data-Garmin_Connect-000000?style=for-the-badge&logo=garmin)

---

## 🎯 The Mission
This dashboard tracks progress against four specific constraints for the 2026 season:
*   🏃 **2026 km** Running Volume
*   🏅 **26** Half Marathons
*   🏋️ **104** Strength Sessions (2/week)
*   🔥 **200+** Active Days

## ✨ Key Features

### 🧙‍♂️ AI Coach Integration (Gemini 2.0)
*   **Context-Aware**: Analyzes your current fatigue (TSB), recent workout history, and subjective context (e.g., "feeling tired").
*   **Goal-Oriented**: Provides advice structured around the specific "Project 2026" targets.
*   **Smart Caching**: Caches advice for 6 hours to minimize API usage, with a manual "Refresh" option for immediate feedback.
*   **Resilient**: Handles API rate limits (429) gracefully with user-friendly notifications.

### 📊 Advanced Physiology Tracking
*   **PMC Chart (Performance Management Chart)**: Visualizes Fitness (CTL), Fatigue (ATL), and Form (TSB) over time using the Banister Impulse Response model.
*   **Workload Ratio Gauge**: Real-time gauge of Acute:Chronic workload ratio to prevent injury (Green = Optimal, Red = Overreach).
*   **Dynamic Timeframes**: Interactive tabs for 1Y, YTD, 6M, 3M, 30D, and 7D views.

### 📱 Mobile-First Design
*   **Responsive Layout**: Fully optimized for mobile browsers with CSS Grid.
*   **Touch-Optimized**: Expanded button targets (>45px) and adapted font sizing.
*   **Compact Calendar**: Custom HTML/CSS Grid implementation for the activity calendar to ensure perfect alignment on small screens.

### 🔄 Automation Pipeline
*   **Garmin Sync**: Python script (`sync_garmin.py`) pulls activity data directly from Garmin Connect.
*   **Cloud Storage**: Data is serialized to Google Sheets for low-latency retrieval by the dashboard.
*   **Background Tasks**: automated via Windows Task Scheduler.

---

## 🛠️ Technical Stack
*   **Frontend**: Streamlit (Python)
*   **Visualization**: Plotly Graph Objects (Dark Mode / Robinhood Aesthetic)
*   **AI Backend**: Google Generative AI (Gemini 1.5 Flash / 2.0 Flash)
*   **Database**: Google Sheets via `st-gsheets-connection`

---

## 🚀 Setup & Installation

### 1. Credentials
Create a `.env` file in the root directory:
```bash
GARMIN_EMAIL=your_email
GARMIN_PASSWORD=your_password
GOOGLE_SHEET_KEY=your_sheet_id
```

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Sync Data
Run the sync script to backfill data from Garmin:
```bash
python sync_garmin.py
```

### 4. Launch Dashboard
```bash
streamlit run dashboard.py
```

## 🤖 Automation (Windows)
To schedule the sync script to run 5 times daily:
```powershell
schtasks /create /tn "Project2026_Sync" /tr "py C:\Path\To\sync_garmin.py" /sc daily /ri 288 /st 06:00 /du 24:00
```

---
*Built by Parva Sheth | Powered by Antigravity*
