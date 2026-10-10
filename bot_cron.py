import os
import datetime
import pandas as pd
import requests
from dhanhq import dhanhq

# GitHub Secrets
DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Dhan Client Init
dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

def get_nifty_historical_data():
    try:
        data = dhan.historical_daily_data(
            symbol='NIFTY',
            exchange_segment='IDX_I',
            instrument_type='INDEX',
            expiry_code=0,
            from_date=(datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d'),
            to_date=datetime.datetime.now().strftime('%Y-%m-%d')
        )
        if data.get('status') == 'success' and 'data' in data:
            return pd.DataFrame(data['data'])
    except Exception as e:
        print(f"Dhan Fetch Error: {e}")
    return None

def calculate_ut_bot(df, key_value=3, atr_period=10):
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    
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
            
    buy_signal = (src > xATRTrailingStop) & (src.shift(1) <= xATRTrailingStop.shift(1))
    sell_signal = (src < xATRTrailingStop) & (src.shift(1) >= xATRTrailingStop.shift(1))
    
    return buy_signal.iloc[-1], sell_signal.iloc[-1], src.iloc[-1], xATRTrailingStop.iloc[-1]

def place_dhan_real_order(security_id, transaction_type, symbol_name="NIFTY ATM", quantity=25):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    t_type = dhan.BUY if transaction_type == "BUY" else dhan.SELL
    
    try:
        response = dhan.place_order(
            tag='',
            transaction_type=t_type,
            exchange_segment=dhan.NSE_FNO,
            product_type=dhan.MARGIN,
            order_type=dhan.MARKET,
            validity=dhan.DAY,
            security_id=str(security_id),
            quantity=int(quantity),
            price=0
        )
        
        status = response.get('status', '')
        order_id = response.get('data', {}).get('orderId', 'N/A')
        remarks = response.get('remarks', response.get('message', 'No details'))

        if status == 'success':
            msg = f"🚀 *REAL ORDER PLACED*\n\n📊 *Symbol*: {symbol_name}\n🔄 *Type*: {transaction_type}\n📦 *Qty*: {quantity}\n🆔 *Order ID*: `{order_id}`\n⏰ *Time*: {now}"
        else:
            msg = f"⚠️ *ORDER REJECTED / FAILED*\n\n📊 *Symbol*: {symbol_name}\n🔄 *Type*: {transaction_type}\n❌ *Reason*: {remarks}\n⏰ *Time*: {now}"
            
        send_telegram_alert(msg)

    except Exception as e:
        send_telegram_alert(f"❌ *ORDER ERROR*\n`{str(e)}`\n⏰ *Time*: {now}")

def run_bot():
    df = get_nifty_historical_data()
    if df is None or df.empty:
        print("Data unavailable or token expired.")
        return
        
    buy, sell, current_price, trailing_stop = calculate_ut_bot(df, key_value=3, atr_period=10)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    print(f"[{now}] Price: {current_price} | Stop: {trailing_stop:.2f}")
    
    if buy:
        place_dhan_real_order("OPTION_SECURITY_ID", "BUY", "NIFTY CE ATM", 25)
    elif sell:
        place_dhan_real_order("OPTION_SECURITY_ID", "SELL", "NIFTY PE ATM", 25)

if __name__ == "__main__":
    run_bot()
