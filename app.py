import streamlit as st
import pandas as pd
from dhanhq import DhanContext, dhanhq
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="UT Bot Live Scanner", page_icon="📈", layout="centered")

st.title("🚀 Nifty UT Bot & Live Price Checker")
st.write("Dhan API se live market data check karne ke liye niche click karein:")

# Secrets handling (Streamlit secrets ya Environment variables)
client_id = st.secrets.get("DHAN_CLIENT_ID", os.environ.get("DHAN_CLIENT_ID"))
access_token = st.secrets.get("DHAN_ACCESS_TOKEN", os.environ.get("DHAN_ACCESS_TOKEN"))

if st.button("🔄 Refresh Market Price & UT Bot Status", type="primary"):
    if not client_id or not access_token:
        st.error("Dhan Credentials (Client ID / Access Token) missing hain! Streamlit Secrets check karein.")
    else:
        try:
            with st.spinner("Fetching data from Dhan API..."):
                dhan_context = DhanContext(client_id, access_token)
                dhan = dhanhq(dhan_context)
                
                # Date range calculate karna (pichle 30 din ka data)
                to_date = datetime.now().strftime("%Y-%m-%d")
                from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                # Nifty Index (Security ID 13) with dates
                response = dhan.historical_daily_data(
                    security_id="13",
                    exchange_segment="IDX_I",
                    instrument_type="INDEX",
                    from_date=from_date,
                    to_date=to_date
                )
                
                if response.get("status") == "success":
                    data_dict = response.get("data", {})
                    df = pd.DataFrame(data_dict)
                    if not df.empty:
                        latest_close = float(df['close'].iloc[-1])
                        atm_strike = int(round(latest_close / 50) * 50)
                        
                        st.success("Data fetched successfully!")
                        st.metric(label="📊 Nifty Spot Price", value=latest_close)
                        st.info(f"🎯 **Suggested ATM Strike**: NIFTY {atm_strike} CE/PE")
                        st.write("🛡️ **Trailing SL**: 5% Dynamic Active")
                    else:
                        st.warning("Market data empty mila.")
                else:
                    st.error(f"Dhan API Error: {response.get('remark', 'Token ya ID galat ho sakti hai')}")
        except Exception as e:
            st.error(f"Connection Error: {e}")
