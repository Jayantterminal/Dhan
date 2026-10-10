import os
import requests
import pandas as pd
import datetime
import numpy as np

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BASE_URL = "https://api.dhan.co"

def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

def get_nifty_historical_data():
    # 5-minute interval data for UT Bot logic
    url = f"{BASE_URL}/charts/intraday"
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
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("data", {})
            df = pd.DataFrame(data)
            if not df.empty and all(k in df.columns for k in ['high', 'low', 'close']):
                return df
    except Exception as e:
        print(f"Dhan Chart Fetch Error: {e}")
    return None

def calculate_ut_bot(df, key_value=3, atr_period=10):
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    
    # True Range & ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    nLoss = key_value * atr
    src = close
    
    xATRTrailingStop = pd.Series(0.0, index=df.index)
    
    for i in range(1, len(df)):
        prev_stop = xATRTrailingStop.iloc[i-1]
        curr_src = src.iloc[i]
        prev_src = src.iloc[i-1]
        curr_loss = nLoss.iloc[i]
        
        if curr_src > prev_stop and prev_src > prev_stop:
            xATRTrailingStop.iloc[i] = max(prev_stop, curr_src - curr_loss)
        elif curr_src < prev_stop and prev_src < prev_stop:
            xATRTrailingStop.iloc[i] = min(prev_stop, curr_src + curr_loss)
        elif curr_src > prev_stop:
            xATRTrailingStop.iloc[i] = curr_src - curr_loss
        else:
            xATRTrailingStop.iloc[i] = curr_src + curr_loss
            
    # Crossover Signals
    buy_signal = (src > xATRTrailingStop) & (src.shift(1) <= xATRTrailingStop.shift(1))
    sell_signal = (src < xATRTrailingStop) & (src.shift(1) >= xATRTrailingStop.shift(1))
    
    return buy_signal.iloc[-1], sell_signal.iloc[-1], src.iloc[-1], xATRTrailingStop.iloc[-1]

def place_dhan_real_order(transaction_type, symbol_name="NIFTY ATM OPTION", quantity=25):
    url = f"{BASE_URL}/orders"
    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    # Note: Real execution ke liye securityId yahan ATM option contract ki deni hogi
    payload = {
        "dhanClientId": DHAN_CLIENT_ID,
        "transactionType": transaction_type,
        "exchangeSegment": "NSE_FNO",
        "productType": "MARGIN",
        "orderType": "MARKET",
        "validity": "DAY",
        "securityId": "YOUR_OPTION_SECURITY_ID", # Option contract security ID
        "quantity": int(quantity),
        "disclosedQuantity": 0,
        "price": 0,
        "triggerPrice": 0,
        "afterMarketOrder": False
    }
    
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res_data = res.json()
        order_status = res_data.get("orderStatus", "")
        order_id = res_data.get("orderId", "N/A")
        remarks = res_data.get("remarks", res_data.get("message", "No description"))

        if res.status_code == 200 and order_status in ["SUCCESS", "PENDING", "TRADED"]:
            msg = f"🚀 *REAL ORDER PLACED*\n\n📊 Symbol: {symbol_name}\n🔄 Type: {transaction_type}\n📦 Qty: {quantity}\n🆔 Order ID: `{order_id}`\n⏰ Time: {now}"
            send_telegram_alert(msg)
        else:
            msg = f"⚠️ *ORDER REJECTED / FAILED*\n\n📊 Symbol: {symbol_name}\n🔄 Type: {transaction_type}\n❌ Reason: {remarks}\n⏰ Time: {now}"
            send_telegram_alert(msg)
    except Exception as e:
        send_telegram_alert(f"❌ *ORDER ERROR*\n`{str(e)}`")

def run_bot():
    df = get_nifty_historical_data()
    if df is None or df.empty:
        print("Data fetch nahi ho paya.")
        return
        
    buy, sell, current_price, trailing_stop = calculate_ut_bot(df, key_value=3, atr_period=10)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    print(f"[{now}] Price: {current_price} | Stop: {trailing_stop:.2f} | Buy: {buy} | Sell: {sell}")
    
    if buy:
        print("UT Bot BUY Signal Triggered!")
        place_dhan_real_order("BUY", "NIFTY ATM", 25)
    elif sell:
        print("UT Bot SELL Signal Triggered!")
        place_dhan_real_order("SELL", "NIFTY ATM", 25)

if __name__ == "__main__":
    run_bot()
