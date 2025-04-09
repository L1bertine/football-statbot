import os
import requests
import time
import joblib
import numpy as np
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Logging config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# API config
API_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Load ML models
model_btts = joblib.load("btts_model.pkl")
model_home_win = joblib.load("home_win_model.pkl")
model_draw = joblib.load("draw_model.pkl")
model_over25 = joblib.load("over25_model.pkl")
model_next_goal = joblib.load("next_goal_model.pkl")

# Send Telegram message
def send_telegram_message(message):
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(TELEGRAM_URL, data=payload)
    if response.ok:
        logging.info(f"📤 Sent: {message}")
    else:
        logging.error(f"❌ Failed to send message: {response.text}")
    return response.ok

# Get live matches
def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        logging.error(f"❌ Error fetching live matches: {response.status_code}")
        return []

# Run standard match predictions
def run_match_predictions(home_goals, away_goals):
    features = np.array([[home_goals, away_goals]])
    return {
        "BTTS": model_btts.predict(features)[0],
        "Home Win": model_home_win.predict(features)[0],
        "Draw": model_draw.predict(features)[0],
        "Over 2.5": model_over25.predict(features)[0]
    }

# Predict next goal
def predict_next_goal(minute, home_goals, away_goals):
    goal_diff = home_goals - away_goals
    features = np.array([[minute, goal_diff]])
    return model_next_goal.predict(features)[0]

# Main bot loop
def run_statbot():
    sent_alerts = set()
    while True:
        logging.info("🔍 Checking for live matches...")
        matches = get_live_matches()

        for match in matches:
            fixture_id = match["fixture"]["id"]
            home = match["teams"]["home"]["name"]
            away = match["teams"]["away"]["name"]
            goals = match["goals"]
            minute = match["fixture"]["status"]["elapsed"]

            home_goals = goals["home"]
            away_goals = goals["away"]
            alert_key = f"{fixture_id}_{home_goals}_{away_goals}"

            if alert_key in sent_alerts:
                continue

            preds = run_match_predictions(home_goals, away_goals)

            if preds["Over 2.5"]:
                send_telegram_message(f"🔥 {home} vs {away}: Expected Over 2.5 Goals!")
            if preds["BTTS"]:
                send_telegram_message(f"⚔️ {home} vs {away}: BTTS Likely!")
            if preds["Home Win"]:
                send_telegram_message(f"🏠 {home} vs {away}: Home Win Expected!")
            if preds["Draw"]:
                send_telegram_message(f"⚖️ {home} vs {away}: Draw is on the cards!")

            next_goal = predict_next_goal(minute, home_goals, away_goals)
            if next_goal == 1:
                send_telegram_message(f"🔮 Next Goal Prediction: {home} likely to score next!")
            elif next_goal == 2:
                send_telegram_message(f"🔮 Next Goal Prediction: {away} likely to score next!")

            sent_alerts.add(alert_key)

        time.sleep(60)

# Startup block
if __name__ == "__main__":
    print("📦 TELEGRAM_BOT_TOKEN:", TELEGRAM_BOT_TOKEN)
    print("📦 CHAT_ID:", CHAT_ID)

    test_message = "✅ TEST message from bot - running live on Railway"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": test_message}
    response = requests.post(url, data=payload)
    print("🔁 Telegram test response:", response.status_code, response.text)

    run_statbot()