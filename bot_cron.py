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

dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

KEY_VALUE = 3
ATR_PERIOD = 10
MAX_CAPITAL = 10000  # Max limit per trade
SELECTED_SYMBOL = "NIFTY"  # Change to "SENSEX" if needed

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

def execute_order(option_security_id, transaction_type, symbol_name, quantity):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    t_type = dhan.BUY if transaction_type == "BUY" else dhan.SELL
    
    try:
        response = dhan.place_order(
            tag='UT_BOT_CRON',
            transaction_type=t_type,
            exchange_segment=dhan.NSE_FNO,
            product_type=dhan.MARGIN,
            order_type=dhan.MARKET,
            validity=dhan.DAY,
            security_id=str(option_security_id),
            quantity=int(quantity),
            price=0
        )
        
        print(f"Order Response: {response}")
        status = response.get('status', '')
        data_resp = response.get('data', {}) if isinstance(response.get('data'), dict) else {}
        order_id = data_resp.get('orderId', 'N/A')
        remarks = response.get('remarks', response.get('message', 'No message'))

        if status == 'success':
            msg = (
                f"🚀 *AUTOMATIC ORDER PLACED*\n\n"
                f"📊 *Symbol*: {symbol_name}\n"
                f"🔄 *Type*: {transaction_type}\n"
                f"📦 *Quantity*: {quantity}\n"
                f"🆔 *Order ID*: `{order_id}`\n"
                f"⏰ *Time*: {now}"
            )
            send_telegram_alert(msg)
        else:
            msg = (
                f"⚠️ *ORDER REJECTED*\n\n"
                f"📊 *Symbol*: {symbol_name}\n"
                f"❌ *Reason*: {remarks}\n"
                f"⏰ *Time*: {now}"
            )
            send_telegram_alert(msg)

    except Exception as e:
        error_msg = f"❌ *EXECUTION ERROR*: `{str(e)}` at {now}"
        send_telegram_alert(error_msg)

def main():
    config = get_symbol_config(SELECTED_SYMBOL)
    df = get_market_data(config)
    
    if df is None or df.empty:
        print(f"{config['name']} data unavailable.")
        return
        
    buy, sell, current_price = calculate_ut_bot(df)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    diff = config["strike_diff"]
    atm_strike = int(round(current_price / diff) * diff)
    
    print(f"[{now}] {config['name']} Spot: {current_price} | ATM Calculated: {atm_strike} | Buy: {buy} | Sell: {sell}")
    
    if buy:
        print(f"Signal: BUY Triggered! Evaluating ATM CE for strike {atm_strike}")
        # Option ka live LTP fetch karke quantity calculate karne ka logic yahan integrate hoga
        # Placeholder quantity mapping based on 10k budget
        option_security_id = "YOUR_DYNAMIC_CE_ID" 
        calculated_qty = config["lot_size"] # Expiry/Budget adjustment ke sath
        execute_order(option_security_id, "BUY", f"{SELECTED_SYMBOL} {atm_strike} CE", calculated_qty)
        
    elif sell:
        print(f"Signal: SELL Triggered! Evaluating ATM PE for strike {atm_strike}")
        option_security_id = "YOUR_DYNAMIC_PE_ID"
        calculated_qty = config["lot_size"]
        execute_order(option_security_id, "BUY", f"{SELECTED_SYMBOL} {atm_strike} PE", calculated_qty)

if __name__ == "__main__":
    main()
