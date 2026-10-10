import os
import math
import requests
import pandas as pd
import numpy as np
from dhanhq import DhanContext, dhanhq

# Secrets / Environment Variables
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Mock Telegram]: {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def calculate_ut_bot(df, key_value=1, atr_period=10):
    """UT Bot (ATR Trailing Stop) Strategy Logic"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range & ATR Calculation
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=atr_period, adjust=False).mean()
    
    # Trailing stop logic
    src = close
    x_atr_trailing_stop = pd.Series(0.0, index=df.index)
    
    for i in range(1, len(df)):
        prev_stop = x_atr_trailing_stop.iloc[i-1]
        curr_close = src.iloc[i]
        prev_close = src.iloc[i-1]
        curr_atr = atr.iloc[i]
        loss_val = key_value * curr_atr
        
        if curr_close > prev_stop and prev_close > prev_stop:
            x_atr_trailing_stop.iloc[i] = max(prev_stop, curr_close - loss_val)
        elif curr_close < prev_stop and prev_close < prev_stop:
            x_atr_trailing_stop.iloc[i] = min(prev_stop, curr_close + loss_val)
        elif curr_close > prev_stop:
            x_atr_trailing_stop.iloc[i] = curr_close - loss_val
        else:
            x_atr_trailing_stop.iloc[i] = curr_close + loss_val

    # Signals (Buy / Sell)
    df['trailing_stop'] = x_atr_trailing_stop
    df['signal'] = 0
    df.loc[close > x_atr_trailing_stop, 'signal'] = 1   # Buy / Bullish
    df.loc[close < x_atr_trailing_stop, 'signal'] = -1  # Sell / Bearish
    
    return df

def run_bot():
    try:
        dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
        dhan = dhanhq(dhan_context)
    except Exception as e:
        print(f"Dhan Connection Error: {e}")
        return

    # Account Balance Check (Re-investing Model)
    fund_resp = dhan.get_fund_limits()
    available_capital = 50000
    if fund_resp.get("status") == "success":
        data = fund_resp.get("data", {})
        available_capital = float(data.get('availabelBalance', data.get('availableBalance', 50000)))

    # Fetching Nifty Intraday Data (Security ID 13)
    try:
        response = dhan.historical_daily_data(
            security_id="13",
            exchange_segment="IDX_I",
            instrument_type="INDEX"
        )
        if response.get("status") == "success":
            df = pd.DataFrame(response.get("data", {}))
            if df.empty:
                return
            
            df_analyzed = calculate_ut_bot(df)
            
            latest_row = df_analyzed.iloc[-1]
            prev_row = df_analyzed.iloc[-2]
            
            latest_close = float(latest_row['close'])
            current_signal = latest_row['signal']
            prev_signal = prev_row['signal']
            
            # Crossover Check
            if current_signal != prev_signal:
                atm_strike = int(round(latest_close / 50) * 50)
                
                if current_signal == 1:
                    option_symbol = f"NIFTY {atm_strike} CE"
                    lots = max(1, math.floor((available_capital * 0.20) / (120 * 75)))
                    msg = (
                        f"🟢 *UT BOT BUY SIGNAL (CALL)* 🟢\n\n"
                        f"📊 *Nifty Spot*: {latest_close}\n"
                        f"🎯 *Strike*: `{option_symbol}`\n"
                        f"📦 *Lots*: {lots} ({lots * 75} Qty)\n"
                        f"🛡️ *Initial SL*: 5% Trailing Active"
                    )
                    send_telegram_message(msg)
                    
                elif current_signal == -1:
                    option_symbol = f"NIFTY {atm_strike} PE"
                    lots = max(1, math.floor((available_capital * 0.20) / (120 * 75)))
                    msg = (
                        f"🔴 *UT BOT SELL SIGNAL (PUT)* 🔴\n\n"
                        f"📊 *Nifty Spot*: {latest_close}\n"
                        f"🎯 *Strike*: `{option_symbol}`\n"
                        f"📦 *Lots*: {lots} ({lots * 75} Qty)\n"
                        f"🛡️ *Initial SL*: 5% Trailing Active"
                    )
                    send_telegram_message(msg)
        else:
            print("Failed to fetch market data from Dhan.")
    except Exception as e:
        print(f"Error in strategy execution: {e}")

if __name__ == "__main__":
    run_bot()
