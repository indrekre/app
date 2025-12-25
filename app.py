import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np  # Required for pmt and financial calcs

st.set_page_config(page_title="Deprecia - Smart Financing & Depreciation", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation Transparency")
st.markdown("""
Enter a VIN or select a vehicle to see depreciation, then explore smarter financing options to minimize value loss.
""")

# NHTSA API
BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

@st.cache_data(ttl=3600)
def decode_vin(vin):
    if not vin or len(vin) != 17:
        return None
    url = f"{BASE_URL}/decodevin/{vin.upper()}?format=json"
    try:
        data = requests.get(url).json()['Results']
        info = {item['Variable']: item['Value'] for item in data if item['Value']}
        return {
            "make": info.get("Make", "").title(),
            "model": info.get("Model", "").title(),
            "year": info.get("Model Year", ""),
            "trim": info.get("Trim", ""),
            "fuel": info.get("Fuel Type - Primary", "")
        }
    except:
        return None

@st.cache_data(ttl=3600)
def get_makes():
    url = f"{BASE_URL}/getallmakes?format=json"
    try:
        data = requests.get(url).json()['Results']
        makes = [m['Make_Name'].title() for m in data if m['VehicleType_Name'] == 'Passenger Car']
        return sorted(set(makes))
    except:
        return ["Toyota", "Honda", "Ford", "Chevrolet", "BMW", "Tesla"]

@st.cache_data(ttl=3600)
def get_models(make):
    if not make:
        return []
    url = f"{BASE_URL}/GetModelsForMake/{make.upper()}?format=json"
    try:
        return sorted(set(m['Model_Name'].title() for m in requests.get(url).json()['Results']))
    except:
        return []

# Sidebar
st.sidebar.header("Vehicle Selection")
vin = st.sidebar.text_input("Enter VIN (17 chars)")
decoded = None
if vin:
    with st.spinner("Decoding VIN..."):
        decoded = decode_vin(vin.strip())
    if decoded and decoded["year"]:
        st.sidebar.success(f"✅ {decoded['year']} {decoded['make']} {decoded['model']}")
    else:
        st.sidebar.warning("Invalid VIN – use manual selection.")

make_options = [""] + get_makes()
selected_make = decoded["make"] if decoded else st.sidebar.selectbox("Make", make_options)

models = get_models(selected_make) if selected_make else []
selected_model = decoded["model"] if decoded else st.sidebar.selectbox("Model", [""] + models)

year = st.sidebar.selectbox("Year", [decoded["year"]] if decoded and decoded["year"] else [""] + [str(y) for y in range(2025, 2010, -1)])

purchase_price = st.sidebar.number_input("Purchase Price ($)", min_value=10000, max_value=300000, value=45000, step=1000)
annual_miles = st.sidebar.number_input("Annual Miles", value=12000, step=1000)

# Low-dep models
low_dep_models = ["Toyota Tacoma", "Toyota 4Runner", "Toyota Corolla Cross", "Honda Civic", "Honda CR-V", "Porsche 911", "Jeep Wrangler", "Subaru Crosstrek", "Lexus RX", "Toyota RAV4 Prime"]

if st.sidebar.button("Calculate"):
    if not year or not selected
