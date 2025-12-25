import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Deprecia - VIN Lookup & Depreciation", page_icon="🚗")
st.title("🚗 Deprecia – VIN Lookup & Car Depreciation")
st.markdown("""
Enter a **VIN** to auto-fill real vehicle details, or select manually.  
See instant drive-off loss and 5-year depreciation forecast.
""")

# NHTSA API base
BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

# --- VIN Decode Function ---
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
            "series": info.get("Series", ""),
            "body": info.get("Body Class", ""),
            "engine": info.get("Engine Model", ""),
            "drive": info.get("Drive Type", ""),
            "fuel": info.get("Fuel Type - Primary", "")
        }
    except:
        return None

# --- Dropdown Data Functions (fallback or manual) ---
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

# VIN Lookup First
vin = st.sidebar.text_input("Enter VIN (17 characters)", placeholder="e.g., 5YJ3E1EA0JF000123")
decoded = None
if vin:
    with st.spinner("Decoding VIN..."):
        decoded = decode_vin(vin.strip())
    if decoded and decoded["year"]:
        st.sidebar.success(f"✅ Found: {decoded['year']} {decoded['make']} {decoded['model']}")
    else:
        st.sidebar.error("Invalid or unrecognized VIN. Use manual selection below.")

# Manual selection (pre-filled if VIN decoded)
make_options = [""] + get_makes()
selected_make = decoded["make"] if decoded else st.sidebar.selectbox("Make (Manual)", make_options, index=make_options.index(decoded["make"]) if decoded and decoded["make"] in make_options else 0)

models = get_models(selected_make) if selected_make else []
selected_model = decoded["model"] if decoded else st.sidebar.selectbox("Model (Manual)", [""] + models, index=models.index(decoded["model"]) if decoded and decoded["model"] in models else 0)

# Year from VIN or manual guess
year_options = [decoded["year"]] if decoded and decoded["year"] else [""] + [str(y) for y in range(2025, 2010, -1)]
year = st.sidebar.selectbox("Year", year_options, index=0 if decoded else None)

# Purchase price
default_price = 45000  # reasonable default
purchase_price = st.sidebar.number_input("Purchase Price ($)", min_value=5000, max_value=500000, value=default_price, step=1000)

if st.sidebar.button("Calculate Depreciation"):
    if not year or not selected_make or not selected_model:
        st.error("Please enter a valid VIN or complete manual selection.")
    else:
        full_name = f"{year} {selected_make} {selected_model}"
        if decoded:
            trim_info = decoded.get("trim") or decoded.get("series", "")
            if trim_info:
                full_name += f" {trim_info}"

        st.success(f"### Vehicle: {full_name}")

        # Show extra specs if from VIN
        if decoded:
            specs = []
            if decoded.get("body"): specs.append(f"Body: {decoded['body']}")
            if decoded.get("engine"): specs.append(f"Engine: {decoded['engine']}")
            if decoded.get("drive"): specs.append(f"Drive: {decoded['drive']}")
            if decoded.get("fuel"): specs.append(f"Fuel: {decoded['fuel']}")
            if specs:
                st.write(" | ".join(specs))

        # Depreciation Model
        def calculate_depreciation(price, years=5):
            rates = [0.25, 0.18, 0.16, 0.14, 0.12]  # Year 1-5
            values = [price]
            for r in rates:
                values.append(values[-1] * (1 - r))
            return values

        values = calculate_depreciation(purchase_price)
        drive_off_loss = purchase_price * 0.12
        first_year_loss = purchase_price - values[1]

        st.warning(f"🚨 **Immediate Drive-Off Loss:** ~${drive_off_loss:,.0f} (12%)")
        st.info(f"**Total First-Year Loss:** ~${first_year_loss:,.0f}")

        # Forecast Table
        forecast_years = [int(year)] + [int(year) + i for i in range(1, 6)]
        df = pd.DataFrame({
            "Year": forecast_years,
            "Estimated Value ($)": [round(v) for v in values]
        })
        df["Loss That Year ($)"] = df["Estimated Value ($)"].diff().fillna(0) * -1

        st.subheader("5-Year Depreciation Forecast")
        st.dataframe(df.style.format({
            "Estimated Value ($)": "${:,.0f}",
            "Loss That Year ($)": "${:,.0f}"
        }))

        # Chart
        st.subheader("Value Over Time")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["Year"], df["Estimated Value ($)"], marker="o", color="#e74c3c", linewidth=3)
        ax.fill_between(df["Year"], df["Estimated Value ($)"], purchase_price, alpha=0.2, color="#e74c3c")
        ax.set_title(f"{full_name} – Projected Value")
        ax.set_ylabel("Value ($)")
        ax.set_xlabel("Year")
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        st.pyplot(fig)

        total_remaining = values[-1]
        total_loss = purchase_price - total_remaining
        st.markdown(f"""
        ### Summary
        - After 5 years: **~${total_remaining:,.0f}** remaining ({(total_remaining/purchase_price)*100:.1f}% of original)
        - Total depreciation: **${total_loss:,.0f}**
        """)

        st.info("💡 VIN decoding powered by official NHTSA vPIC API (free). Depreciation based on industry averages.")

# Footer
st.markdown("---")
st.markdown("Deprecia Demo | VIN Lookup + Depreciation | Data: NHTSA vPIC API")