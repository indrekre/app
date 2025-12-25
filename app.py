import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Deprecia - Smart Financing", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation")

# Front Page Sample Test Section
st.markdown("### Quick Sample Test: 2023 Porsche Taycan Base (High Depreciation EV Example)")
st.markdown("""
**Scenario**: Dealer asks 72,000€ for a used 2023 Taycan base. Market value ~65,000-75,000€ (avg 70,000€). Expected resale in 2-3 years: 55,000-60,000€.  
This hits hard due to fast EV depreciation – load and see why leasing may be wiser!
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.image("https://media.ed.edmunds-media.com/porsche/taycan/2023/fe/2023_porsche_taycan_f34_fe_315221_1600.jpg", caption="2023 Porsche Taycan Base")
with col2:
    st.image("https://platform.cstatic-images.com/in/v2/stock_photos/ebee8062-c9f0-465c-a2a6-82d6c66c02ce/aeadf38d-55ff-4e4e-814a-dbfe7dc658f1.png", caption="Taycan Specs View")
with col3:
    st.image("https://cka-dash.s3.amazonaws.com/008-0723-CPO835/model1.png", caption="Taycan Profile")

if st.button("Load Porsche Taycan 2023 Sample Test"):
    st.session_state.vin = "WP0AA2Y1XPSA12345"  # Sample VIN
    st.session_state.vehicle_type = "Used (2+ years old)"
    st.session_state.make = "Porsche"
    st.session_state.model = "Taycan"
    st.session_state.year = "2023"
    st.session_state.purchase_price = 72000
    st.session_state.fair_market_value = 70000
    st.session_state.annual_miles = 10000
    st.success("Sample loaded! Scroll to sidebar and click Calculate.")

BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

# ... (rest of the code unchanged – VIN decode, makes/models, sidebar with session_state defaults, calculation logic, etc.)

# In sidebar, use session_state for defaults
vin = st.sidebar.text_input("Enter VIN (17 chars)", value=st.session_state.get('vin', ''), help="Optional")
vehicle_type = st.sidebar.selectbox("New or Used?", ["New", "Used (2+ years old)"], index=["New", "Used (2+ years old)"].index(st.session_state.get('vehicle_type', "New")))
make = st.sidebar.selectbox("Make", [""] + get_makes(), index=get_makes().index(st.session_state.get('make', "")) if 'make' in st.session_state else 0)
# ... similarly for model, year, etc. (add session_state defaults for all)

# Full code too long – add the session_state lines to your existing sidebar inputs for persistence.

st.markdown("Deprecia – With Porsche Taycan Sample Test on Front Page")
