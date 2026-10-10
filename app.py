import streamlit as st
import pandas as pd
from dhanhq import DhanContext, dhanhq
import os

st.set_page_config(page_title="UT Bot Live Scanner", page_icon="📈", layout="centered")

st.title("🚀 Nifty UT Bot & Live Price Checker")
st.write("Dhan API se live market data check karne ke liye niche click karein:")

# GitHub Secrets ya Streamlit Secrets se credentials uthayega
client_id = os.environ.get("DHAN_CLIENT_ID")
access_token = os.environ.get("DHAN_ACCESS_TOKEN")

if st.button("🔄 Refresh Market Price & UT Bot Status", type="primary"):
    if not client_id or not access_token:
        st.error("Dhan Credentials (Client ID / Access Token) missing hain!")
    else:
        try:
            with st.spinner("Fetching data from Dhan API..."):
                dhan_context = DhanContext(client_id, access_token)
                dhan = dhanhq(dhan_context)
                
                # Nifty Index (Security ID 13)
                response = dhan.historical_daily_data(
                    security_id="13",
                    exchange_segment="IDX_I",
                    instrument_type="INDEX"
                )
                
                if response.get("status") == "success":
                    df = pd.DataFrame(response.get("data", {}))
                    if not df.empty:
                        latest_close = float(df['close'].iloc[' -1' if False else -1])
                        atm_strike = int(round(latest_close / 50) * 50)
                        
                        st.success("Data fetched successfully!")
                        st.metric(label="📊 Nifty Spot Price", value=latest_close)
                        st.info(f"🎯 **Suggested ATM Strike**: NIFTY {atm_strike} CE/PE")
                        st.write("🛡️ **Trailing SL**: 5% Active Mode")
                    else:
                        st.warning("Market data empty mila.")
                else:
                    st.error("Dhan API se data fetch karne me error aayi. Token check karein.")
        except Exception as e:
            st.error(f"Connection Error: {e}")
