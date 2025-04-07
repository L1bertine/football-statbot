import os
import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "v3.football.api-sports.io"
}

def fetch_live_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    response = requests.get(url, headers=HEADERS)
    return response.json()['response']

def send_alert(text):
    bot.send_message(chat_id=CHAT_ID, text=text)

def simple_alert_logic():
    matches = fetch_live_matches()
    for match in matches:
        minute = match['fixture']['status']['elapsed']
        goals = match['goals']
        if not (20 <= minute <= 44): continue  # only first half
        if goals['home'] + goals['away'] != 0: continue  # skip if already a goal

        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        msg = f"⚽ [ALERT] {home} vs {away} — Minute {minute}\nNo goals yet. Consider Over 0.5 First Half Goals!"
        send_alert(msg)

simple_alert_logic()