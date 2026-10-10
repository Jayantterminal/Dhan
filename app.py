import streamlit as st
import pandas as pd
import requests
import time
import os

st.set_page_config(
    page_title="UT Bot Paper Trading Engine",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 UT Bot Automated Paper Trading Engine")
st.caption("Test UT Bot signals with dynamic 5% Trailing Stop-Loss and Instant Telegram Alerts.")

# Load Secrets / Environment Variables
try:
    default_client_id = st.secrets.get("DHAN_CLIENT_ID", "")
    default_access_token = st.secrets.get("DHAN_ACCESS_TOKEN", "")
    default_tg_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
    default_tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
except Exception:
    default_client_id = os.environ.get("DHAN_CLIENT_ID", "")
    default_access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
    default_tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    default_tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

# Sidebar Controls
st.sidebar.header("🔑 Dhan Credentials")
client_id = st.sidebar.text_input("Client ID", value=default_client_id)
access_token = st.sidebar.text_input("Access Token", value=default_access_token, type="password")

st.sidebar.divider()
st.sidebar.header("📲 Telegram Alerts")
telegram_bot_token = st.sidebar.text_input("Telegram Bot Token", value=default_tg_token, type="password")
telegram_chat_id = st.sidebar.text_input("Telegram Chat ID", value=default_tg_chat_id)

st.sidebar.divider()
st.sidebar.header("⚙️ Fixed Strategy Parameters")
st.sidebar.info("📌 **Trading Index**: Automatic (NIFTY / SENSEX)\n📌 **Position Size**: Fixed 1 Lot\n📌 **Trailing SL**: 5.0%")

trailing_sl_pct = 5.0

# Session States
if "trade_active" not in st.session_state:
    st.session_state.trade_active = False
if "trade_details" not in st.session_state:
    st.session_state.trade_details = {}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

# Telegram Notification Helper
def send_telegram_msg(message):
    if telegram_bot_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass

# API Helper
def fetch_index_price(security_id, token):
    if not token:
        return None
    url = "https://api.dhan.co/charts/intraday"
    headers = {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "security_id": security_id,
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200 and response.text.strip():
            res_json = response.json()
            if res_json.get("status") == "success":
                data = res_json.get("data", {})
                df = pd.DataFrame(data)
                if not df.empty and 'close' in df.columns:
                    return float(df['close'].iloc[-1])
    except Exception:
        pass
    return None

# Fetch NIFTY as primary display
spot_price = fetch_index_price("13", access_token)
display_spot = spot_price if spot_price else 25000.0  # Fallback for testing

col1, col2, col3 = st.columns(3)

with col1:
    if spot_price:
        st.metric(label="📊 Current NIFTY Spot", value=f"₹{spot_price:,.2f}")
    else:
        st.metric(label="📊 Current NIFTY Spot (Simulated)", value=f"₹{display_spot:,.2f}")

with col2:
    atm_strike = int(round(display_spot / 50) * 50)
    st.metric(label="🎯 ATM Strike", value=f"NIFTY {atm_strike}")

with col3:
    status_label = "🟢 Active Trade" if st.session_state.trade_active else "⚪ Waiting for Signal"
    st.metric(label="Status", value=status_label)

st.divider()

# Simulation Controls
st.subheader("⚡ Signal Engine & Simulation Controls")
sim_c1, sim_c2, sim_c3 = st.columns(3)

sim_premium = 120.0  # Simulated Option Premium
fixed_qty = 25       # Fixed 1 Lot Nifty (25 Qty)

with sim_c1:
    if st.button("🚀 Simulate BUY Signal (CE)", use_container_width=True, disabled=st.session_state.trade_active):
        atm = int(round(display_spot / 50) * 50)
        st.session_state.trade_active = True
        st.session_state.trade_details = {
            "type": "BUY (CE)",
            "symbol": f"NIFTY {atm} CE",
            "entry_spot": display_spot,
            "entry_price": sim_premium,
            "high_watermark": sim_premium,
            "stop_loss": sim_premium * (1 - trailing_sl_pct / 100.0),
            "qty": fixed_qty,
            "capital_used": sim_premium * fixed_qty,
            "entry_time": time.strftime("%H:%M:%S")
        }
        # Telegram Alert
        msg = (
            f"🚀 *UT BOT SIGNAL ALERT*\n\n"
            f"📈 *Symbol*: NIFTY {atm} CE\n"
            f"💰 *Entry Premium*: ₹{sim_premium:.2f}\n"
            f"📊 *Lot*: 1 Lot ({fixed_qty} Qty)\n"
            f"💵 *Total Capital*: ₹{(sim_premium * fixed_qty):,.2f}\n"
            f"🛑 *Trailing SL (5%)*: ₹{(sim_premium * (1 - trailing_sl_pct / 100.0)):.2f}\n"
            f"⏰ *Time*: {time.strftime('%H:%M:%S')}"
        )
        send_telegram_msg(msg)
        st.rerun()

with sim_c2:
    if st.button("🔻 Simulate SELL Signal (PE)", use_container_width=True, disabled=st.session_state.trade_active):
        atm = int(round(display_spot / 50) * 50)
        st.session_state.trade_active = True
        st.session_state.trade_details = {
            "type": "BUY (PE)",
            "symbol": f"NIFTY {atm} PE",
            "entry_spot": display_spot,
            "entry_price": sim_premium,
            "high_watermark": sim_premium,
            "stop_loss": sim_premium * (1 - trailing_sl_pct / 100.0),
            "qty": fixed_qty,
            "capital_used": sim_premium * fixed_qty,
            "entry_time": time.strftime("%H:%M:%S")
        }
        # Telegram Alert
        msg = (
            f"🔻 *UT BOT SIGNAL ALERT*\n\n"
            f"📉 *Symbol*: NIFTY {atm} PE\n"
            f"💰 *Entry Premium*: ₹{sim_premium:.2f}\n"
            f"📊 *Lot*: 1 Lot ({fixed_qty} Qty)\n"
            f"💵 *Total Capital*: ₹{(sim_premium * fixed_qty):,.2f}\n"
            f"🛑 *Trailing SL (5%)*: ₹{(sim_premium * (1 - trailing_sl_pct / 100.0)):.2f}\n"
            f"⏰ *Time*: {time.strftime('%H:%M:%S')}"
        )
        send_telegram_msg(msg)
        st.rerun()

with sim_c3:
    if st.button("🛑 Force Exit Trade", use_container_width=True, disabled=not st.session_state.trade_active):
        if st.session_state.trade_active:
            trade = st.session_state.trade_details
            trade["exit_price"] = trade["high_watermark"]
            trade["exit_time"] = time.strftime("%H:%M:%S")
            trade["pnl"] = (trade["exit_price"] - trade["entry_price"]) * trade["qty"]
            trade["reason"] = "Manual Exit"
            st.session_state.trade_history.append(trade)
            
            # Telegram Alert
            msg = (
                f"🛑 *TRADE EXIT ALERT*\n\n"
                f"📊 *Symbol*: {trade['symbol']}\n"
                f"💵 *Exit Premium*: ₹{trade['exit_price']:.2f}\n"
                f"💵 *P&L*: ₹{trade['pnl']:,.2f}\n"
                f"📝 *Reason*: Manual Exit / Trailing SL Hit\n"
                f"⏰ *Time*: {time.strftime('%H:%M:%S')}"
            )
            send_telegram_msg(msg)
            
            st.session_state.trade_active = False
            st.session_state.trade_details = {}
            st.rerun()

st.divider()

# Active Trade Monitor View
if st.session_state.trade_active:
    trade = st.session_state.trade_details
    st.subheader(f"📈 Active Paper Trade: {trade['symbol']} (1 Lot | ₹{trade['capital_used']:,.2f} Capital)")
    
    current_premium = trade["high_watermark"]
    unrealized_pnl = (current_premium - trade["entry_price"]) * trade["qty"]
    
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("Entry Premium", f"₹{trade['entry_price']:.2f}")
    p_col2.metric("Current Premium", f"₹{current_premium:.2f}")
    p_col3.metric("Trailing Stop Loss (5%)", f"₹{trade['stop_loss']:.2f}")
    p_col4.metric("Unrealized P&L", f"₹{unrealized_pnl:,.2f}", delta=f"{unrealized_pnl:.2f}")

# Trade History Log
st.subheader("📜 Paper Trade Logs & History")
if st.session_state.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_history)
    st.dataframe(df_history[["entry_time", "exit_time", "symbol", "type", "qty", "capital_used", "entry_price", "exit_price", "pnl", "reason"]], use_container_width=True)
else:
    st.info("Abhi tak koi paper trade execute nahi hua hai.")
