import os
import datetime
import pandas as pd
import numpy as np
import requests
from dhanhq import dhanhq

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

def main():
    try:
        if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
            print("Error: Dhan Credentials missing in Environment Variables / Secrets.")
            return

        dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        
        # Fetching Nifty Intraday Data
        response = dhan.intraday_daily_data(
            security_id='13',
            exchange_segment='IDX_I',
            instrument_type='INDEX'
        )
        
        if response and response.get('status') == 'success':
            print("Successfully connected and fetched market data from Dhan!")
        else:
            print(f"Dhan Response Warning: {response}")

    except Exception as e:
        print(f"Execution Exception: {str(e)}")

if __name__ == "__main__":
    main()
