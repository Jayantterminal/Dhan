import os
import requests
import pandas as pd
import datetime

# Fetch Credentials from Secrets
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

def get_nifty_spot():
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
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", {})
            df = pd.DataFrame(data)
            if not df.empty and 'close' in df.columns:
                return float(df['close'].iloc[-1])
    except Exception as e:
        print(f"Dhan Fetch Error: {e}")
    return None

def place_dhan_real_order(security_id, transaction_type, symbol_name="NIFTY OPTION", quantity=25):
    """
    Dhan API v2 Order Placement Endpoint with Telegram Status Notification
    """
    url = f"{BASE_URL}/orders"
    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "dhanClientId": DHAN_CLIENT_ID,
        "transactionType": transaction_type,
        "exchangeSegment": "NSE_FNO",
        "productType": "MARGIN",
        "orderType": "MARKET",
        "validity": "DAY",
        "securityId": str(security_id),
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
        print(f"Order Response: {res_data}")

        # Check Order Status Response
        order_status = res_data.get("orderStatus", "")
        order_id = res_data.get("orderId", "N/A")
        remarks = res_data.get("remarks", res_data.get("message", "No description"))

        if res.status_code == 200 and order_status in ["SUCCESS", "PENDING", "TRADED"]:
            msg = (
                f"🚀 *REAL ORDER PLACED*\n\n"
                f"📊 *Symbol*: {symbol_name}\n"
                f"🔄 *Type*: {transaction_type}\n"
                f"📦 *Qty*: {quantity} (1 Lot)\n"
                f"🆔 *Order ID*: `{order_id}`\n"
                f"⏰ *Time*: {now}"
            )
            send_telegram_alert(msg)
            return True
        else:
            # Order Failed / Rejected Alert (e.g. Insufficient Funds)
            msg = (
                f"⚠️ *ORDER REJECTED / FAILED*\n\n"
                f"📊 *Symbol*: {symbol_name}\n"
                f"🔄 *Type*: {transaction_type}\n"
                f"❌ *Reason*: {remarks}\n"
                f"⏰ *Time*: {now}\n\n"
                f"_Signal generate hua tha, par account issue/balance ki wajeh se order execute nahi hua._"
            )
            send_telegram_alert(msg)
            return False

    except Exception as e:
        error_msg = (
            f"❌ *ORDER EXECUTION ERROR*\n\n"
            f"Error details: `{str(e)}`\n"
            f"⏰ *Time*: {now}"
        )
        send_telegram_alert(error_msg)
        return False

def check_signal_and_execute():
    spot = get_nifty_spot()
    if not spot:
        print("Market Offline / Token Missing")
        return
    
    atm = int(round(spot / 50) * 50)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    print(f"[{now}] Live NIFTY Spot: {spot} | ATM Strike: {atm}")

if __name__ == "__main__":
    check_signal_and_execute()
