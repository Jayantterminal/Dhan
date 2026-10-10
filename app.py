import streamlit as st
import pandas as pd
import requests
import os

st.set_page_config(page_title="Nifty & Sensex Live Checker", page_icon="📈", layout="centered")

st.title("🚀 Nifty & Sensex Live Price Checker")

# Secrets check
try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
except Exception:
    client_id = os.environ.get("DHAN_CLIENT_ID")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN")

def fetch_index_price(security_id, client_id, access_token):
    url = "https://api.co.dhan.co/charts/intraday"
    headers = {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }
    payload = {
        "security_id": security_id,
        "exchange_segment": "IDX_I",
        "instrument_type": "INDEX"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()
        
        # Debug info dikhane ke liye
        st.write(f"API Response ({security_id}):", res_json)
        
        if res_json.get("status") == "success":
            data = res_json.get("data", {})
            df = pd.DataFrame(data)
            if not df.empty and 'close' in df.columns:
                return float(df['close'].iloc[-1])
    except Exception as e:
        st.error(f"Error: {e}")
    return None

if st.button("🔄 Check Nifty & Sensex Live Price", type="primary"):
    if not client_id or not access_token:
        st.error("Secrets missing in Streamlit!")
    else:
        with st.spinner("Fetching market data..."):
            nifty_price = fetch_index_price("13", client_id, access_token)
            sensex_price = fetch_index_price("51", client_id, access_token)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Nifty Spot")
                if nifty_price:
                    nifty_atm = int(round(nifty_price / 50) * 50)
                    st.metric(label="Nifty Price", value=nifty_price)
                    st.info(f"ATM: {nifty_atm} CE/PE")
                else:
                    st.warning("Market band hone ki wajah se data nahi mila.")
            
            with col2:
                st.subheader("📊 Sensex Spot")
                if sensex_price:
                    sensex_atm = int(round(sensex_price / 100) * 100)
                    st.metric(label="Sensex Price", value=sensex_price)
                    st.info(f"ATM: {sensex_atm} CE/PE")
                else:
                    st.warning("Market band hone ki wajah se data nahi mila.")
