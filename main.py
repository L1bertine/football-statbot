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

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# API setup
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
HEADERS = {"x-apisports-key": API_KEY}

# Load ML models
try:
    model_btts = joblib.load("btts_model.pkl")
    model_home_win = joblib.load("home_win_model.pkl")
    model_draw = joblib.load("draw_model.pkl")
    model_over25 = joblib.load("over25_model.pkl")
    model_next_goal = joblib.load("next_goal_model.pkl")
except Exception as e:
    logging.error(f"❌ Failed to load ML models: {e}")
    raise

def send_telegram_message(message):
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(TELEGRAM_URL, data=payload)
    if not response.ok:
        logging.error(f"❌ Failed to send message: {response.text}")
    return response.ok

def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all&timezone=Europe/London"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        logging.error(f"❌ Error fetching live matches: {response.status_code}")
        return []

def within_runtime_hours():
    now = datetime.now(timezone("Europe/London")).time()
    start_time = dtime(19, 45)
    end_time = dtime(22, 30)
    return start_time <= now <= end_time

def run_statbot():
    sent_alerts = set()

    if within_runtime_hours():
        send_telegram_message("✅ Statbot is live and monitoring!")
    else:
        logging.info("⏳ Waiting for 19:45 UK time to start...")
        send_telegram_message("🕒 Statbot running but waiting for 19:45 UK time to activate alerts.")

    while True:
        if not within_runtime_hours():
            logging.info("⏰ Outside permitted hours (19:45–22:30 UK) — sleeping...")
            time.sleep(60)
            continue

        logging.info("🔍 Checking for live matches...")
        matches = get_live_matches()

        for match in matches:
            fixture_id = match["fixture"]["id"]
            home_team = match["teams"]["home"]["name"]
            away_team = match["teams"]["away"]["name"]
            minute = match["fixture"]["status"]["elapsed"]
            home_goals = match["goals"]["home"]
            away_goals = match["goals"]["away"]

            if None in (fixture_id, home_team, away_team, minute, home_goals, away_goals):
                continue

            alert_key = f"{fixture_id}_{home_goals}_{away_goals}"
            if alert_key in sent_alerts:
                continue

            features = np.array([[home_goals, away_goals]])
            preds = {
                "BTTS": bool(model_btts.predict(features)[0]),
                "Home Win": bool(model_home_win.predict(features)[0]),
                "Draw": bool(model_draw.predict(features)[0]),
                "Over 2.5": bool(model_over25.predict(features)[0])
            }

            if preds["Over 2.5"]:
                send_telegram_message(f"🔥 {home_team} vs {away_team}: Over 2.5 Goals expected")
            if preds["BTTS"]:
                send_telegram_message(f"⚔️ {home_team} vs {away_team}: BTTS Likely")
            if preds["Home Win"]:
                send_telegram_message(f"🏠 {home_team} likely to win vs {away_team}")
            if preds["Draw"]:
                send_telegram_message(f"⚖️ {home_team} vs {away_team}: Draw looking likely")

            # Next Goal Prediction
            goal_diff = home_goals - away_goals
            next_goal = model_next_goal.predict(np.array([[minute, goal_diff]]))[0]
            if next_goal == 1:
                send_telegram_message(f"🔮 Next Goal Prediction: {home_team} likely to score next!")
            elif next_goal == 2:
                send_telegram_message(f"🔮 Next Goal Prediction: {away_team} likely to score next!")

            sent_alerts.add(alert_key)

        time.sleep(60)

if __name__ == "__main__":
    run_statbot()