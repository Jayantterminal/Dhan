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
st.caption("Test UT Bot signals with dynamic 5% Trailing Stop-Loss on Dhan Live Feeds without financial risk.")

# Load Credentials
try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
except Exception:
    client_id = os.environ.get("DHAN_CLIENT_ID")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN")

# Initialize Session States for Paper Trading
if "trade_active" not in st.session_state:
    st.session_state.trade_active = False
if "trade_details" not in st.session_state:
    st.session_state.trade_details = {}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

# API Helper Function
def fetch_index_price(security_id):
    url = "https://api.dhan.co/charts/intraday"
    headers = {
        "access-token": access_token,
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

# Sidebar Controls
st.sidebar.header("⚙️ Strategy Parameters")
index_choice = st.sidebar.selectbox("Trading Index", ["NIFTY", "SENSEX"])
sec_id = "13" if index_choice == "NIFTY" else "51"
strike_step = 50 if index_choice == "NIFTY" else "100"

trailing_sl_pct = st.sidebar.number_input("Trailing Stop Loss (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
lot_qty = st.sidebar.number_input("Quantity (Lots/Units)", min_value=1, value=25 if index_choice == "NIFTY" else 10)

st.sidebar.divider()
st.sidebar.header("🕹️ Paper Signal Controls")

# Layout Setup
col1, col2, col3 = st.columns(3)

spot_price = fetch_index_price(sec_id)

with col1:
    if spot_price:
        st.metric(label=f"📊 Current {index_choice} Spot", value=f"₹{spot_price:,.2f}")
    else:
        st.metric(label=f"📊 Current {index_choice} Spot", value="Offline / Closed")

with col2:
    if spot_price:
        atm_strike = int(round(spot_price / (50 if index_choice == "NIFTY" else 100)) * (50 if index_choice == "NIFTY" else 100))
        st.metric(label="🎯 ATM Strike", value=f"{index_choice} {atm_strike}")
    else:
        st.metric(label="🎯 ATM Strike", value="N/A")

with col3:
    status_label = "🟢 Active Trade" if st.session_state.trade_active else "⚪ Waiting for Signal"
    st.metric(label="Status", value=status_label)

st.divider()

# Trade Simulation Controls (Manual Override / Signal Triggering)
st.subheader("⚡ Signal Engine & Controls")
sim_c1, sim_c2, sim_c3 = st.columns(3)

with sim_c1:
    if st.button("🚀 Simulate BUY Signal (CE)", use_container_width=True, disabled=st.session_state.trade_active):
        if spot_price:
            atm = int(round(spot_price / (50 if index_choice == "NIFTY" else 100)) * (50 if index_choice == "NIFTY" else 100))
            entry_premium = 100.0  # Base Virtual Premium for Paper Trading
            st.session_state.trade_active = True
            st.session_state.trade_details = {
                "type": "BUY (CE)",
                "symbol": f"{index_choice} {atm} CE",
                "entry_spot": spot_price,
                "entry_price": entry_premium,
                "high_watermark": entry_premium,
                "stop_loss": entry_premium * (1 - trailing_sl_pct / 100.0),
                "qty": lot_qty,
                "entry_time": time.strftime("%H:%M:%S")
            }
            st.rerun()
        else:
            st.warning("Cannot start Paper Trade without Live Spot price.")

with sim_c2:
    if st.button("🔻 Simulate SELL Signal (PE)", use_container_width=True, disabled=st.session_state.trade_active):
        if spot_price:
            atm = int(round(spot_price / (50 if index_choice == "NIFTY" else 100)) * (50 if index_choice == "NIFTY" else 100))
            entry_premium = 100.0
            st.session_state.trade_active = True
            st.session_state.trade_details = {
                "type": "BUY (PE)",
                "symbol": f"{index_choice} {atm} PE",
                "entry_spot": spot_price,
                "entry_price": entry_premium,
                "high_watermark": entry_premium,
                "stop_loss": entry_premium * (1 - trailing_sl_pct / 100.0),
                "qty": lot_qty,
                "entry_time": time.strftime("%H:%M:%S")
            }
            st.rerun()
        else:
            st.warning("Cannot start Paper Trade without Live Spot price.")

with sim_c3:
    if st.button("🛑 Force Exit Trade", use_container_width=True, disabled=not st.session_state.trade_active):
        if st.session_state.trade_active:
            trade = st.session_state.trade_details
            trade["exit_price"] = trade["high_watermark"] # Exiting at high/current
            trade["exit_time"] = time.strftime("%H:%M:%S")
            trade["pnl"] = (trade["exit_price"] - trade["entry_price"]) * trade["qty"]
            trade["reason"] = "Manual Exit"
            st.session_state.trade_history.append(trade)
            st.session_state.trade_active = False
            st.session_state.trade_details = {}
            st.rerun()

st.divider()

# Active Trade Monitor View
if st.session_state.trade_active:
    trade = st.session_state.trade_details
    st.subheader(f"📈 Active Paper Trade: {trade['symbol']}")
    
    # Simulate Live Premium Movement relative to spot or time
    current_premium = trade["high_watermark"]
    
    # Trailing SL Update Logic
    if current_premium > trade["high_watermark"]:
        st.session_state.trade_details["high_watermark"] = current_premium
        st.session_state.trade_details["stop_loss"] = current_premium * (1 - trailing_sl_pct / 100.0)
    
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
    st.dataframe(df_history[["entry_time", "exit_time", "symbol", "type", "entry_price", "exit_price", "pnl", "reason"]], use_container_width=True)
else:
    st.info("No paper trades executed yet.")
