import streamlit as st
import pandas as pd
from dhanhq import DhanContext, dhanhq
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

if st.button("🔄 Check Nifty & Sensex Live Price", type="primary"):
    if not client_id or not access_token:
        st.error("Secrets missing in Streamlit!")
    else:
        try:
            with st.spinner("Fetching market data from Dhan..."):
                dhan_context = DhanContext(client_id, access_token)
                dhan = dhanhq(dhan_context)
                
                # 1. Fetch Nifty (ID: 13)
                nifty_resp = dhan.intraday_daily_charts(
                    security_id="13",
                    exchange_segment="IDX_I",
                    instrument_type="INDEX"
                )
                
                # 2. Fetch Sensex (ID: 51)
                sensex_resp = dhan.intraday_daily_charts(
                    security_id="51",
                    exchange_segment="IDX_I",
                    instrument_type="INDEX"
                )
                
                col1, col2 = st.columns(2)
                
                # Display Nifty
                with col1:
                    st.subheader("📊 Nifty Spot")
                    if nifty_resp.get("status") == "success":
                        df_nifty = pd.DataFrame(nifty_resp.get("data", {}))
                        if not df_nifty.empty:
                            nifty_price = float(df_nifty['close'].iloc[-1])
                            nifty_atm = int(round(nifty_price / 50) * 50)
                            st.metric(label="Nifty Price", value=nifty_price)
                            st.info(f"ATM: {nifty_atm} CE/PE")
                        else:
                            st.warning("Nifty data empty")
                    else:
                        st.error("Nifty Error")
                
                # Display Sensex
                with col2:
                    st.subheader("📊 Sensex Spot")
                    if sensex_resp.get("status") == "success":
                        df_sensex = pd.DataFrame(sensex_resp.get("data", {}))
                        if not df_sensex.empty:
                            sensex_price = float(df_sensex['close'].iloc[-1])
                            sensex_atm = int(round(sensex_price / 100) * 100)
                            st.metric(label="Sensex Price", value=sensex_price)
                            st.info(f"ATM: {sensex_atm} CE/PE")
                        else:
                            st.warning("Sensex data empty")
                    else:
                        st.error("Sensex Error")
                        
        except Exception as e:
            st.error(f"Exception: {e}")
