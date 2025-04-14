import os
import time
import requests
import joblib
import numpy as np
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# API URLs
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
HEADERS = {"x-apisports-key": API_KEY}

# Load ML models
model_btts = joblib.load("btts_model.pkl")
model_home_win = joblib.load("home_win_model.pkl")
model_draw = joblib.load("draw_model.pkl")
model_over25 = joblib.load("over25_model.pkl")
model_next_goal = joblib.load("next_goal_model.pkl")

# Telegram alert sender
def send_telegram_message(message):
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(TELEGRAM_URL, data=payload)
    if not response.ok:
        logging.error(f"❌ Failed to send message: {response.text}")
    return response.ok

# API call to fetch live matches
def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        logging.error(f"Error fetching live matches: {response.status_code}")
        return []

# ML predictions using current goals
def run_match_predictions(home_goals, away_goals):
    features = np.array([[home_goals, away_goals]])
    return {
        "BTTS": model_btts.predict(features)[0],
        "Home Win": model_home_win.predict(features)[0],
        "Draw": model_draw.predict(features)[0],
        "Over 2.5": model_over25.predict(features)[0]
    }

# ML prediction for next goal
def predict_next_goal(minute, home_goals, away_goals):
    goal_diff = home_goals - away_goals
    features = np.array([[minute, goal_diff]])
    return model_next_goal.predict(features)[0]

# Main bot loop
def run_statbot():
    sent_alerts = set()

    while True:
        # Restrict bot to run between 19:45 and 22:30
        now = datetime.now().time()
        start_time = datetime.strptime("19:45", "%H:%M").time()
        end_time = datetime.strptime("22:30", "%H:%M").time()

        if not (start_time <= now <= end_time):
            logging.info("⏱ Outside match alert window. Sleeping for 5 minutes...")
            time.sleep(300)
            continue

        logging.info("🔍 Checking for live matches...")
        matches = get_live_matches()

        for match in matches:
            fixture_id = match["fixture"]["id"]
            home_team = match["teams"]["home"]["name"]
            away_team = match["teams"]["away"]["name"]
            goals = match["goals"]
            minute = match["fixture"]["status"]["elapsed"]
            home_goals = goals["home"]
            away_goals = goals["away"]
            alert_key = f"{fixture_id}_{home_goals}_{away_goals}"

            if alert_key in sent_alerts:
                continue

            preds = run_match_predictions(home_goals, away_goals)

            if preds["Over 2.5"]:
                send_telegram_message(f"🔥 {home_team} vs {away_team}: Expected Over 2.5 Goals!")
            if preds["BTTS"]:
                send_telegram_message(f"⚔️ {home_team} vs {away_team}: BTTS Likely!")
            if preds["Home Win"]:
                send_telegram_message(f"🏠 {home_team} vs {away_team}: Home Win Expected!")
            if preds["Draw"]:
                send_telegram_message(f"⚖️ {home_team} vs {away_team}: Draw is on the cards!")

            next_goal = predict_next_goal(minute, home_goals, away_goals)
            if next_goal == 1:
                send_telegram_message(f"🔮 Next Goal Prediction: {home_team} likely to score next!")
            elif next_goal == 2:
                send_telegram_message(f"🔮 Next Goal Prediction: {away_team} likely to score next!")

            sent_alerts.add(alert_key)

        time.sleep(60)

if __name__ == "__main__":
    logging.info("📦 TELEGRAM_BOT_TOKEN: ✅")
    logging.info("📦 CHAT_ID: ✅")
    send_telegram_message("✅ Statbot is live and connected to Telegram!")
    run_statbot()
    