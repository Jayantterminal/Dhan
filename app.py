import streamlit as st
import pandas as pd
from dhanhq import DhanContext, dhanhq
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="UT Bot Live Scanner", page_icon="📈", layout="centered")

st.title("🚀 Nifty UT Bot & Live Price Checker")

# Secrets check
try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
except Exception:
    client_id = os.environ.get("DHAN_CLIENT_ID")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN")

if st.button("🔄 Refresh Market Price & UT Bot Status", type="primary"):
    if not client_id or not access_token:
        st.error("Secrets missing in Streamlit!")
    else:
        try:
            with st.spinner("Connecting to Dhan API..."):
                dhan_context = DhanContext(client_id, access_token)
                dhan = dhanhq(dhan_context)
                
                to_date = datetime.now().strftime("%Y-%m-%d")
                from_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
                
                # Requesting Nifty Index data
                response = dhan.historical_daily_data(
                    security_id="13",
                    exchange_segment="IDX_I",
                    instrument_type="INDEX",
                    from_date=from_date,
                    to_date=to_date
                )
                
                st.write("API Raw Response:", response) # Exact response dekhne ke liye
                
                if response.get("status") == "success":
                    data_dict = response.get("data", {})
                    df = pd.DataFrame(data_dict)
                    if not df.empty:
                        latest_close = float(df['close'].iloc[-1])
                        st.metric(label="📊 Nifty Spot Price", value=latest_close)
                    else:
                        st.warning("Data received is empty.")
                else:
                    st.error(f"API Error Details: {response}")
        except Exception as e:
            st.error(f"Exception: {e}")
