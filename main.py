import os
import time
import requests
import joblib
import numpy as np
import logging
from datetime import datetime, time as dtime
from pytz import timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# API URLs
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
HEADERS = {"x-apisports-key": API_KEY}

# Load models
try:
    model_btts = joblib.load("btts_model.pkl")
    model_home_win = joblib.load("home_win_model.pkl")
    model_draw = joblib.load("draw_model.pkl")
    model_over25 = joblib.load("over25_model.pkl")
    model_next_goal = joblib.load("next_goal_model.pkl")
except Exception as e:
    logging.error(f"❌ Failed to load model(s): {e}")
    raise

# Send Telegram message
def send_telegram_message(msg):
    payload = {"chat_id": CHAT_ID, "text": msg}
    response = requests.post(TELEGRAM_URL, data=payload)
    if not response.ok:
        logging.error(f"❌ Telegram error: {response.status_code} | {response.text}")
    return response.ok

# Check if time is between 19:45 and 22:30 (London time)
def within_runtime_hours():
    now = datetime.now(timezone("Europe/London")).time()
    return dtime(19, 45) <= now <= dtime(22, 30)

# Get live fixtures
def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all&timezone=Europe/London"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json().get("response", [])
        else:
            logging.error(f"⚠️ API error: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"❌ Exception fetching matches: {e}")
        return []

# Main loop
def run_statbot():
    sent_alerts = set()

    # Startup message
    if within_runtime_hours():
        send_telegram_message("✅ Statbot is live and connected to Telegram!")
    else:
        send_telegram_message("🕒 Bot started outside run hours (19:45–22:30 UK). Waiting...")

    while True:
        if not within_runtime_hours():
            logging.info("🕒 Outside run hours. Sleeping 60s...")
            time.sleep(60)
            continue

        logging.info("🔍 Checking for live matches...")
        matches = get_live_matches()

        for match in matches:
            fixture = match.get("fixture", {})
            teams = match.get("teams", {})
            goals = match.get("goals", {})

            fixture_id = fixture.get("id")
            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")
            minute = fixture.get("status", {}).get("elapsed")
            home_goals = goals.get("home")
            away_goals = goals.get("away")

            # Skip incomplete
            if None in (fixture_id, home, away, minute, home_goals, away_goals):
                logging.debug(f"⛔ Incomplete data for fixture {fixture_id}")
                continue

            alert_key = f"{fixture_id}_{home_goals}_{away_goals}"
            if alert_key in sent_alerts:
                continue

            # Prediction inputs
            score_features = np.array([[home_goals, away_goals]])
            next_goal_features = np.array([[minute, home_goals - away_goals]])

            # Run predictions
            try:
                preds = {
                    "BTTS": model_btts.predict(score_features)[0],
                    "Home Win": model_home_win.predict(score_features)[0],
                    "Draw": model_draw.predict(score_features)[0],
                    "Over 2.5": model_over25.predict(score_features)[0],
                }
                next_goal = model_next_goal.predict(next_goal_features)[0]
            except Exception as e:
                logging.error(f"❌ Prediction error: {e}")
                continue

            # Send alerts
            if preds["Over 2.5"]:
                send_telegram_message(f"🔥 {home} vs {away}: Over 2.5 Goals Expected")
            if preds["BTTS"]:
                send_telegram_message(f"⚔️ {home} vs {away}: BTTS Likely")
            if preds["Home Win"]:
                send_telegram_message(f"🏠 {home} vs {away}: Home Win Expected")
            if preds["Draw"]:
                send_telegram_message(f"⚖️ {home} vs {away}: Possible Draw")

            if next_goal == 1:
                send_telegram_message(f"🔮 Next Goal: {home} likely to score next")
            elif next_goal == 2:
                send_telegram_message(f"🔮 Next Goal: {away} likely to score next")

            sent_alerts.add(alert_key)

        time.sleep(60)

if __name__ == "__main__":
    run_statbot()
