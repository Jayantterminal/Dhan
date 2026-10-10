import os
import datetime
import pandas as pd
import numpy as np
import requests
from dhanhq import dhanhq

# ==========================================
# CONFIGURATION & CREDENTIALS
# ==========================================
DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Initialize Dhan API safely
dhan = None
if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN:
    try:
        dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
    except Exception as e:
        print(f"Dhan Initialization Error: {e}")

KEY_VALUE = 3
ATR_PERIOD = 10
MAX_CAPITAL = 10000  # ₹10,000 limit
SELECTED_SYMBOL = "NIFTY"

def get_symbol_config(symbol):
    if symbol == "SENSEX":
        return {
            "security_id": "51",
            "exchange_segment": "IDX_I",
            "instrument_type": "INDEX",
            "name": "BSE SENSEX",
            "strike_diff": 100,
            "lot_size": 10
        }
    else:
        return {
            "security_id": "13",
            "exchange_segment": "IDX_I",
            "instrument_type": "INDEX",
            "name": "NIFTY 50",
            "strike_diff": 50,
            "lot_size": 25
        }

def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

def get_market_data(config):
    if not dhan:
        print("Dhan client not initialized.")
        return None
    try:
        response = dhan.intraday_daily_data(
            security_id=config["security_id"],
            exchange_segment=config["exchange_segment"],
            instrument_type=config["instrument_type"]
        )
        if response and response.get('status') == 'success' and 'data' in response:
            df = pd.DataFrame(response['data'])
            if not df.empty and all(k in df.columns for k in ['high', 'low', 'close']):
                return df
    except Exception as e:
        print(f"Dhan Data Fetch Error: {e}")
    return None

def calculate_ut_bot(df):
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/ATR_PERIOD, adjust=False).mean()
    
    nLoss = KEY_VALUE * atr
    src = close
    
    xATRTrailingStop = pd.Series(0.0, index=df.index)
    
    for i in range(1, len(df)):
        prev_stop = xATRTrailingStop.iloc[i-1]
        curr_src = src.iloc[i]
        prev_src = src.iloc[i-1]
        curr_loss = nLoss.iloc[i]
        
        if curr_src > prev_stop and prev_src > prev_stop:
            xATRTrailingStop.iloc[i] = max(prev_stop, curr_src - curr_loss)
        elif curr_src < prev_stop and curr_src < prev_stop:
            xATRTrailingStop.iloc[i] = min(prev_stop, curr_src + curr_loss)
        elif curr_src > prev_stop:
            xATRTrailingStop.iloc[i] = curr_src - curr_loss
        else:
            xATRTrailingStop.iloc[i] = curr_src + curr_loss
            
    buy_signal = (src > xATRTrailingStop) & (src.shift(1) <= xATRTrailingStop.shift(1))
    sell_signal = (src < xATRTrailingStop) & (src.shift(1) >= xATRTrailingStop.shift(1))
    
    return buy_signal.iloc[-1], sell_signal.iloc[-1], src.iloc[-1]

def main():
    config = get_symbol_config(SELECTED_SYMBOL)
    df = get_market_data(config)
    
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    if df is None or df.empty:
        print(f"[{now}] Market closed or Data unavailable for {config['name']}.")
        return
        
    buy, sell, current_price = calculate_ut_bot(df)
    
    diff = config["strike_diff"]
    atm_strike = int(round(current_price / diff) * diff)
    
    print(f"[{now}] {config['name']} Spot: {current_price} | ATM: {atm_strike} | Buy: {buy} | Sell: {sell}")

if __name__ == "__main__":
    main()
