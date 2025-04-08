import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Debug log to confirm environment variables are loaded
print("\U0001F527 Debug - API_KEY Loaded:", "Yes" if API_KEY else "No")
print("\U0001F527 Debug - TELEGRAM_BOT_TOKEN Loaded:", "Yes" if TELEGRAM_BOT_TOKEN else "No")
print("\U0001F527 Debug - CHAT_ID Loaded:", CHAT_ID if CHAT_ID else "No")

# Base URLs
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

HEADERS = {
    "x-apisports-key": API_KEY
}

# Send message to Telegram
def send_telegram_message(message):
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(TELEGRAM_URL, data=payload)

    if not response.ok:
        print("❌ Failed to send message:", response.json())
    else:
        print("✅ Telegram message sent:", message)

    return response.ok

# Get live matches
def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"Error fetching live matches: {response.status_code}")
        return []

# Analyze match and make prediction
def analyze_match(match):
    teams = match["teams"]
    score = match["goals"]
    stats = match.get("statistics", [])

    home = teams["home"]["name"]
    away = teams["away"]["name"]
    home_goals = score["home"]
    away_goals = score["away"]

    # Placeholder for deeper stat analysis
    prediction = None
    if abs(home_goals - away_goals) == 0:
        prediction = f"⚖️ {home} vs {away} is level at {home_goals}-{away_goals}"
    elif home_goals > away_goals:
        prediction = f"🔥 {home} is leading {away} {home_goals}-{away_goals}"
    else:
        prediction = f"🔥 {away} is leading {home} {away_goals}-{home_goals}"

    # Add intelligence: send if match is in second half or intense stats
    minute = match.get("fixture", {}).get("status", {}).get("elapsed", 0)
    if minute >= 45:
        prediction += f" ⏱️ ({minute} mins)"

    return prediction

# Main polling loop
def run_statbot():
    sent_alerts = set()

    while True:
        print("\U0001F50D Checking for live matches...")
        live_matches = get_live_matches()

        for match in live_matches:
            fixture_id = match["fixture"]["id"]
            prediction = analyze_match(match)

            if prediction and fixture_id not in sent_alerts:
                print(f"\U0001F4E4 Sending: {prediction}")
                send_telegram_message(prediction)
                sent_alerts.add(fixture_id)

        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    run_statbot()
