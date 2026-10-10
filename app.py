import streamlit as st
from dhanhq import DhanContext, dhanhq
import os

st.set_page_config(page_title="UT Bot Live Scanner", page_icon="📈", layout="centered")

st.title("🚀 Nifty Live Price Checker")

# Secrets check
try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
except Exception:
    client_id = os.environ.get("DHAN_CLIENT_ID")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN")

if st.button("🔄 Check Live Nifty Price", type="primary"):
    if not client_id or not access_token:
        st.error("Secrets missing in Streamlit!")
    else:
        try:
            with st.spinner("Fetching live price from Dhan..."):
                dhan_context = DhanContext(client_id, access_token)
                dhan = dhanhq(dhan_context)
                
                # Using LTP API which is available in Free Plan
                response = dhan.ltp(
                    security_list=[
                        {"exchange_segment": "IDX_I", "security_id": "13"}
                    ]
                )
                
                if response.get("status") == "success":
                    data = response.get("data", {})
                    # Extracting Nifty LTP
                    nifty_price = data.get("13", {}).get("last_price") or data.get("IX", {}).get("13", {}).get("last_price")
                    
                    if nifty_price:
                        atm_strike = int(round(float(nifty_price) / 50) * 50)
                        st.success("Live price fetched successfully!")
                        st.metric(label="📊 Nifty Spot Price", value=nifty_price)
                        st.info(f"🎯 **Suggested ATM Strike**: NIFTY {atm_strike} CE/PE")
                    else:
                        st.warning(f"Response data format check: {response}")
                else:
                    st.error(f"API Error: {response}")
        except Exception as e:
            st.error(f"Exception: {e}")
