TELEGRAM_BOT_TOKEN = "7966578270:AAFXhwzTZceaxy07iZ0tRmyp33xh1gJuV_E"

def get_updates():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    print(response.json())
    get_updates()
