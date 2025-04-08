import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
        print("❌ Failed to send message:", response.text)
    return response.ok

# Get live matches
def get_live_matches():
    url = f"{API_BASE_URL}/fixtures?live=all"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"❌ Error fetching live matches: {response.status_code}")
        return []

# Get detailed statistics for a match
def get_match_statistics(fixture_id):
    url = f"{API_BASE_URL}/fixtures/statistics?fixture={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("response", [])
    else:
        print(f"❌ Error fetching stats for fixture {fixture_id}: {response.status_code}")
        return []

# Analyze match and make prediction
def analyze_match(match):
    fixture_id = match["fixture"]["id"]
    stats = get_match_statistics(fixture_id)

    teams = match["teams"]
    score = match["goals"]
    home = teams["home"]["name"]
    away = teams["away"]["name"]
    home_goals = score["home"]
    away_goals = score["away"]

    prediction = None

    # If no stats returned
    if not stats:
        return None

    try:
        home_stats = next(team for team in stats if team["team"]["name"] == home)["statistics"]
        away_stats = next(team for team in stats if team["team"]["name"] == away)["statistics"]

        def get_stat(stats_list, stat_type):
            for stat in stats_list:
                if stat["type"] == stat_type:
                    return stat["value"] or 0
            return 0

        # Extract relevant stats
        home_shots = get_stat(home_stats, "Shots on Goal")
        away_shots = get_stat(away_stats, "Shots on Goal")
        home_possession = float(str(get_stat(home_stats, "Ball Possession")).replace('%','') or 0)
        away_possession = float(str(get_stat(away_stats, "Ball Possession")).replace('%','') or 0)
        home_corners = get_stat(home_stats, "Corner Kicks")
        away_corners = get_stat(away_stats, "Corner Kicks")

        # Smart logic
        if abs(home_goals - away_goals) == 0 and max(home_shots, away_shots) >= 8:
            prediction = f"⚠️ {home} vs {away} is tied {home_goals}-{away_goals}, but high intensity with {home_shots + away_shots} shots on goal!"
        elif home_possession > 65 and home_shots > 6:
            prediction = f"🔥 {home} is dominating with {home_possession}% possession and {home_shots} shots on goal!"
        elif away_possession > 65 and away_shots > 6:
            prediction = f"🔥 {away} is controlling the match with {away_possession}% possession and {away_shots} shots on goal!"
        elif home_corners >= 6:
            prediction = f"🚩 {home} has earned {home_corners} corners already – applying serious pressure!"
        elif away_corners >= 6:
            prediction = f"🚩 {away} has earned {away_corners} corners already – pressure mounting!"

        # Fallback: simple score line
        if not prediction:
            if home_goals > away_goals:
                prediction = f"🔥 {home} is leading {away} {home_goals}-{away_goals}"
            elif away_goals > home_goals:
                prediction = f"🔥 {away} is leading {home} {away_goals}-{home_goals}"
            else:
                prediction = f"⚖️ {home} vs {away} is level at {home_goals}-{away_goals}"

        return prediction

    except Exception as e:
        print(f"❌ Error analyzing match: {e}")
        return None

# Main bot loop
def run_statbot():
    sent_alerts = set()

    send_telegram_message("📡 Football StatBot is now live and scanning matches!")

    while True:
        print("🔍 Checking for live matches...")
        live_matches = get_live_matches()

        for match in live_matches:
            fixture_id = match["fixture"]["id"]
            if fixture_id in sent_alerts:
                continue

            prediction = analyze_match(match)

            if prediction:
                print(f"📤 Sending: {prediction}")
                send_telegram_message(prediction)
                sent_alerts.add(fixture_id)

        time.sleep(60)  # Re-check every 60 seconds

if __name__ == "__main__":
    run_statbot()