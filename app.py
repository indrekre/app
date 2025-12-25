import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

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

# Low-dep recommender
low_dep_models = ["Toyota Tacoma", "Toyota 4Runner", "Toyota Corolla Cross", "Honda Civic", "Honda CR-V", "Porsche 911", "Jeep Wrangler", "Subaru Crosstrek", "Lexus RX", "Toyota RAV4 Prime"]

if st.sidebar.button("Calculate"):
    if not year or not selected_make or not selected_model:
        st.error("Complete vehicle selection.")
    else:
        full_name = f"{year} {selected_make} {selected_model}"
        st.success(f"### Vehicle: {full_name}")

        # Depreciation (adjust for high miles)
        base_rates = [0.25, 0.18, 0.16, 0.14, 0.12]
        if annual_miles > 15000:
            base_rates = [r + 0.03 for r in base_rates]
            st.warning(f"High mileage ({annual_miles} mi/yr) accelerates depreciation ~3% extra per year.")

        def dep_values(price):
            values = [price]
            for r in base_rates:
                values.append(values[-1] * (1 - r))
            return values

        values = dep_values(purchase_price)
        drive_off = purchase_price * 0.12
        st.warning(f"🚨 Drive-Off Loss: ~${drive_off:,.0f} (12%)")

        forecast_years = [int(year)] + [int(year) + i for i in range(1, 6)]
        df_dep = pd.DataFrame({"Year": forecast_years, "Value ($)": [round(v) for v in values]})
        df_dep["Loss ($)"] = df_dep["Value ($)"].diff().fillna(0) * -1
        st.subheader("5-Year Depreciation")
        st.dataframe(df_dep.style.format({"Value ($)": "${:,.0f}", "Loss ($)": "${:,.0f}"}))

        # Chart
        fig, ax = plt.subplots()
        ax.plot(df_dep["Year"], df_dep["Value ($)"], marker="o", color="#e74c3c")
        ax.set_title("Projected Value")
        ax.grid(True)
        st.pyplot(fig)

        # New Features in Expanders
        with st.expander("1. Depreciation-Aware Loan Simulator"):
            down = st.slider("Down Payment ($)", 0, purchase_price//2, purchase_price//10)
            loan_amt = purchase_price - down
            term = st.slider("Loan Term (months)", 36, 84, 60)
            rate = st.slider("Interest Rate (%)", 4.0, 12.0, 7.0)
            monthly = loan_amt * (rate/1200) / (1 - (1 + rate/1200)**(-term))
            total_paid = monthly * term
            st.write(f"Monthly: ${monthly:,.0f} | Total Interest: ${total_paid - loan_amt:,.0f}")
            # Equity chart
            balance = [loan_amt]
            equity_years = [int(year)]
            for y in range(1, 6):
                remaining = balance[-1] * (1 + rate/1200)**12 - monthly * 12 * ((1 + rate/1200)**12 - 1) / (rate/1200)
                balance.append(max(0, remaining))
            if len(values) > 1:
                upside = any(b > v for b, v in zip(balance[1:], values[1:]))
                if upside:
                    st.error("Upside down risk! Increase down payment.")
            fig2, ax2 = plt.subplots()
            ax2.plot(forecast_years, values, label="Value")
            ax2.plot(forecast_years, [purchase_price - down] + balance, label="Loan Balance")
            ax2.legend()
            st.pyplot(fig2)

        with st.expander("2. Lease vs. Buy Comparator"):
            residual_pct = st.slider("Lease Residual (%)", 50, 70, 58)
            lease_term = st.slider("Lease Term (months)", 24, 48, 36)
            money_factor = st.number_input("Money Factor", 0.0015, 0.0040, 0.0025)
            lease_monthly = ((purchase_price - purchase_price * residual_pct / 100) / lease_term) + (purchase_price * money_factor)
            st.write(f"Estimated Lease Monthly: ${lease_monthly:,.0f}")
            st.write(f"Buy Monthly (from simulator): ${monthly:,.0f if 'monthly' in locals() else 0}")

        with st.expander("3. Low-Depreciation Recommender"):
            if any(m in full_name for m in low_dep_models):
                st.success("Your vehicle holds value well!")
            st.write("Top low-dep models (2025): Toyota Tacoma, 4Runner, Corolla Cross, Honda Civic/CR-V, Porsche 911, Jeep Wrangler.")

        with st.expander("4. GAP Insurance Recommender"):
            if down < purchase_price * 0.2:
                st.warning("Low down payment – high upside-down risk.")
            gap_cost = st.checkbox("Add GAP (~$88/year)")
            if gap_cost:
                st.info("GAP covers gap if totaled – e.g., $5,000 protection.")

        with st.expander("5. Total Ownership Cost (TCO) Dashboard"):
            insurance_est = 2000
            fuel_est = annual_miles * 0.15  # rough
            maint_est = 800
            total_tco = (purchase_price - values[-1]) + total_paid if 'total_paid' in locals() else 0 + insurance_est*5 + fuel_est*5 + maint_est*5
            st.write(f"5-Year Est: Depreciation ${purchase_price - values[-1]:,.0f} + Interest/Other ~${total_tco - (purchase_price - values[-1]):,.0f}")

st.markdown("---")
st.markdown("Deprecia Enhanced Demo | Smarter Financing Features")
