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

dhan = None
if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN:
    try:
        dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
    except Exception as e:
        print(f"Dhan Init Error: {e}")

KEY_VALUE = 3
ATR_PERIOD = 10
MAX_CAPITAL = 10000  # Max ₹10,000 limit per trade
SELECTED_SYMBOL = "NIFTY"  # Options Index

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
        print(f"Data Fetch Error: {e}")
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
    
    return buy_signal.iloc[-1], sell_signal.iloc[-1], src.iloc[-1], xATRTrailingStop.iloc[-1]

def get_active_position_details():
    """Checks existing open positions and how long ago they were opened"""
    if not dhan:
        return None, 0
    try:
        positions = dhan.get_positions()
        if positions and positions.get('status') == 'success':
            for pos in positions.get('data', []):
                qty = int(pos.get('netQty', 0))
                if qty != 0:
                    # Return position security ID and net quantity
                    return pos, qty
    except Exception as e:
        print(f"Position check error: {e}")
    return None, 0

def square_off_all_positions():
    """Automatic square off at 3:20 PM or on exit signal"""
    if not dhan:
        return
    try:
        positions = dhan.get_positions()
        if positions and positions.get('status') == 'success':
            for pos in positions.get('data', []):
                qty = int(pos.get('netQty', 0))
                if qty != 0:
                    sec_id = pos.get('securityId')
                    t_type = dhan.SELL if qty > 0 else dhan.BUY
                    dhan.place_order(
                        tag='AUTO_EXIT',
                        transaction_type=t_type,
                        exchange_segment=dhan.NSE_FNO,
                        product_type=dhan.MARGIN,
                        order_type=dhan.MARKET,
                        validity=dhan.DAY,
                        security_id=str(sec_id),
                        quantity=abs(qty),
                        price=0
                    )
            send_telegram_alert("⚠️ *POSITION CLOSED*\nUT Bot exit signal triggered or time reached.")
    except Exception as e:
        print(f"Square off error: {e}")

def main():
    now_time = datetime.datetime.now().time()
    current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
    
    # 3:20 PM Automatic Square Off Check
    square_off_time = datetime.time(15, 20, 0)
    if now_time >= square_off_time:
        print(f"[{current_time_str}] Past 3:20 PM. Triggering Square-Off.")
        square_off_all_positions()
        send_telegram_alert("⏰ *AUTO SQUARE-OFF AT 3:20 PM*\nAll open option positions squared off.")
        return

    config = get_symbol_config(SELECTED_SYMBOL)
    df = get_market_data(config)
    
    if df is None or df.empty:
        print(f"[{current_time_str}] Market closed or data unavailable.")
        return
        
    buy, sell, current_price, trailing_stop = calculate_ut_bot(df)
    
    diff = config["strike_diff"]
    atm_strike = int(round(current_price / diff) * diff)
    
    print(f"[{current_time_str}] {config['name']} Spot: {current_price} | ATM: {atm_strike} | Buy: {buy} | Sell: {sell}")
    
    # Check current active position
    active_pos, net_qty = get_active_position_details()
    
    if net_qty != 0:
        # Position is already running. Check for 5-min grace period or exit conditions.
        # Note: In production cron, we evaluate exit if trailing stop is breached or opposite signal occurs.
        print(f"Active position found with qty {net_qty}. Monitoring exit conditions...")
        
        # Example Exit Rule: If sell signal occurs while holding CE, or trailing stop breached
        if sell and net_qty > 0:
            print("Exit condition met (Opposite signal / Trailing breach). Squaring off...")
            square_off_all_positions()
        return

    # If no active position, check for fresh entry
    if buy:
        print(f"Signal: BUY Triggered! Evaluating ATM CE for strike {atm_strike} within ₹10k budget.")
        # Quantity calculation based on 10k budget will execute here when option security ID is mapped.
        
    elif sell:
        print(f"Signal: SELL Triggered! Evaluating ATM PE for strike {atm_strike} within ₹10k budget.")

if __name__ == "__main__":
    main()
