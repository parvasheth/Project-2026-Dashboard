# Project 2026 Dashboard

## Setup
1. **Environment Variables**:
   - Copy `.env.template` to `.env`.
   - Fill in `GARMIN_EMAIL`, `GARMIN_PASSWORD`.
   - Create a Google Sheet and copy its ID to `GOOGLE_SHEET_KEY`.
   - Share the Google Sheet with the `client_email` found in `service_account.json` (Editor access).

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initial Sync**:
   ```bash
   python sync_garmin.py
   ```
   *Note: First run might trigger an MFA prompt if Garmin detects a new login.*

4. **Run Dashboard**:
   ```bash
   streamlit run dashboard.py
   ```

## Automation (Windows Task Scheduler)
To run the sync script 5 times daily (every ~4.8 hours), run this command in **Command Prompt (Admin)** or PowerShell:

```powershell
schtasks /create /tn "Project2026_Sync" /tr "py c:\Users\parva\OneDrive\Documents\Antigravity\Project2026_Dashboard\sync_garmin.py" /sc daily /ri 288 /st 06:00 /du 24:00
```
*Note: Make sure 'py' or 'python' is in your system PATH. If not, use the full path to python.exe.*
*Flag `/ri 288` runs it every 288 minutes (approx 4.8 hours).*

## Aesthetics
- **Theme**: "Volcanic" (Pitch Black, Red/Gold/Blue).
- **Interactive**: Lightning borders on KPIs, Fire color scale on charts.
