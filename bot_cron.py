import os
import requests
import pandas as pd
import datetime

# Fetch Credentials from Secrets / Environment Variables
DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

def get_nifty_spot():
    url = "https://api.dhan.co/charts/intraday"
    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "security_id": "13",
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", {})
            df = pd.DataFrame(data)
            if not df.empty and 'close' in df.columns:
                return float(df['close'].iloc[-1])
    except Exception as e:
        print(f"Dhan Fetch Error: {e}")
    return None

def check_signal_and_alert():
    spot = get_nifty_spot()
    if not spot:
        print("Market Offline ya Token Missing")
        return
    
    atm = int(round(spot / 50) * 50)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Example UT Bot Signal Logic Trigger (Yahan aapka candle indicator check hoga)
    # Testing ke liye alert log:
    print(f"[{now}] NIFTY Spot: {spot} | ATM: {atm}")

if __name__ == "__main__":
    check_signal_and_alert()
