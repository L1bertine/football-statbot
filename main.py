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

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# API Setup
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
HEADERS = {"x-apisports-key": API_KEY}

# League filters
ALLOWED_LEAGUES = [2, 3, 39]  # Champions League, Europa League, Premier League
MAX_API_CALLS = 95
api_call_count = 0

# Load models
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
    try:
        response = requests.post(TELEGRAM_URL, data=payload)
        if not response.ok:
            logging.error(f"❌ Failed to send message: {response.text}")
    except Exception as e:
        logging.error(f"❌ Telegram Error: {e}")

def within_runtime_hours():
    now = datetime.now(timezone("Europe/London")).time()
    start = dtime(19, 45)
    end = dtime(22, 30)
    return start <= now <= end

def get_live_matches():
    global api_call_count
    if api_call_count >= MAX_API_CALLS:
        send_telegram_message("🧯 API call limit reached. Shutting down to avoid suspension.")
        logging.warning("API call limit reached.")
        exit()

    url = f"{API_BASE_URL}/fixtures?live=all&timezone=Europe/London"
    response = requests.get(url, headers=HEADERS)
    api_call_count += 1
    logging.debug(f"📡 API Response ({api_call_count}): {response.status_code}")

    if response.status_code == 403 or "suspended" in response.text:
        send_telegram_message("🚫 API key appears suspended. Shutting down.")
        exit()

    if response.status_code == 200:
        all_matches = response.json().get("response", [])
        return [match for match in all_matches if match.get("league", {}).get("id") in ALLOWED_LEAGUES]
    else:
        logging.error(f"❌ Error fetching matches: {response.status_code}")
        return []

def run_statbot():
    sent_alerts = set()

    # Notify on start
    if within_runtime_hours():
        send_telegram_message("✅ Statbot is live and filtering top competitions!")
    else:
        send_telegram_message("🕒 Bot started outside hours. Waiting until 19:45 UK...")

    while True:
        if not within_runtime_hours():
            logging.info("⏳ Outside active hours. Sleeping 60s...")
            time.sleep(60)
            continue

        logging.info("🔍 Checking for live filtered matches...")
        matches = get_live_matches()

        for match in matches:
            fixture = match.get("fixture", {})
            teams = match.get("teams", {})
            goals = match.get("goals", {})

            fixture_id = fixture.get("id")
            home_team = teams.get("home", {}).get("name")
            away_team = teams.get("away", {}).get("name")
            minute = fixture.get("status", {}).get("elapsed")
            home_goals = goals.get("home")
            away_goals = goals.get("away")

            if None in (fixture_id, home_team, away_team, minute, home_goals, away_goals):
                continue

            alert_key = f"{fixture_id}_{home_goals}_{away_goals}"
            if alert_key in sent_alerts:
                continue

            # Run predictions
            features_score = np.array([[home_goals, away_goals]])
            preds = {
                "BTTS": bool(model_btts.predict(features_score)[0]),
                "Home Win": bool(model_home_win.predict(features_score)[0]),
                "Draw": bool(model_draw.predict(features_score)[0]),
                "Over 2.5": bool(model_over25.predict(features_score)[0])
            }

            # Send alerts
            if preds["Over 2.5"]:
                send_telegram_message(f"🔥 {home_team} vs {away_team}: Expected Over 2.5 Goals!")
            if preds["BTTS"]:
                send_telegram_message(f"⚔️ {home_team} vs {away_team}: BTTS Likely!")
            if preds["Home Win"]:
                send_telegram_message(f"🏠 {home_team} vs {away_team}: Home Win Expected!")
            if preds["Draw"]:
                send_telegram_message(f"⚖️ {home_team} vs {away_team}: Draw is on the cards!")

            # Next goal prediction
            goal_diff = home_goals - away_goals
            next_goal = model_next_goal.predict(np.array([[minute, goal_diff]]))[0]
            if next_goal == 1:
                send_telegram_message(f"🔮 Next Goal: {home_team} likely to score next!")
            elif next_goal == 2:
                send_telegram_message(f"🔮 Next Goal: {away_team} likely to score next!")

            sent_alerts.add(alert_key)

        time.sleep(60)

if __name__ == "__main__":
    run_statbot()