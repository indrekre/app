import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np  # Added for financial calc

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
    if not year or not selected_make or not selected_model:
        st.error("Complete vehicle selection.")
    else:
        full_name = f"{year} {selected_make} {selected_model}"
        st.success(f"### Vehicle: {full_name}")

        # Depreciation (high mileage penalty)
        base_rates = [0.25, 0.18, 0.16, 0.14, 0.12]
        if annual_miles > 15000:
            base_rates = [r + 0.03 for r in base_rates]
            st.warning(f"High mileage ({annual_miles:,} mi/yr) adds ~3% extra depreciation per year.")

        def dep_values(price):
            values = [price]
            for r in base_rates:
                values.append(values[-1] * (1 - r))
            return values

        values = dep_values(purchase_price)
        drive_off = purchase_price * 0.12
        st.warning(f"🚨 Drive-Off Loss: ~${drive_off:,.0f} (12%)")

        forecast_years = [int(year) + i for i in range(6)]
        df_dep = pd.DataFrame({"Year": forecast_years, "Value ($)": [round(v) for v in values]})
        df_dep["Loss ($)"] = df_dep["Value ($)"].diff().fillna(0) * -1
        st.subheader("5-Year Depreciation Forecast")
        st.dataframe(df_dep.style.format({"Value ($)": "${:,.0f}", "Loss ($)": "${:,.0f}"}))

        # Value chart
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_dep["Year"], df_dep["Value ($)"], marker="o", color="#e74c3c", linewidth=3)
        ax.set_title("Projected Vehicle Value")
        ax.set_ylabel("Value ($)")
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        st.pyplot(fig)

        # === NEW FEATURES ===
        with st.expander("1. Depreciation-Aware Loan Simulator", expanded=True):
            down = st.slider("Down Payment ($)", 0, purchase_price//2, purchase_price//10, step=1000)
            loan_amount = purchase_price - down
            term_months = st.slider("Loan Term (months)", 36, 84, 60)
            rate = st.slider("Interest Rate (%)", 4.0, 15.0, 7.0) / 100

            if loan_amount > 0 and rate > 0:
                monthly_payment = np.pmt(rate/12, term_months, -loan_amount)
                total_paid = monthly_payment * term_months
                st.write(f"**Monthly Payment:** ${monthly_payment:,.0f}")
                st.write(f"**Total Interest Paid:** ${total_paid - loan_amount:,.0f}")

                # Proper yearly loan balance
                remaining_balance = loan_amount
                balances = [loan_amount]  # Year 0
                for year in range(1, 6):
                    for month in range(12):
                        interest = remaining_balance * (rate / 12)
                        principal = monthly_payment - interest
                        remaining_balance -= principal
                        if remaining_balance < 0:
                            remaining_balance = 0
                    balances.append(remaining_balance)

                # Upside-down check
                upside_down_years = [i for i, (bal, val) in enumerate(zip(balances, values)) if bal > val]
                if upside_down_years:
                    st.error(f"⚠️ Upside down in year(s): {', '.join(str(y) for y in upside_down_years)} – consider larger down payment!")

                # Equity chart
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                ax2.plot(forecast_years, values, label="Vehicle Value", marker="o", color="#e74c3c")
                ax2.plot(forecast_years, balances, label="Loan Balance", marker="s", color="#3498db")
                ax2.fill_between(forecast_years, values, balances, where=np.array(balances) > np.array(values), color="red", alpha=0.3, label="Upside Down Risk")
                ax2.legend()
                ax2.set_title("Loan Balance vs Vehicle Value")
                ax2.set_ylabel("Amount ($)")
                ax2.grid(True, alpha=0.3)
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
                st.pyplot(fig2)
            else:
                st.info("Enter a valid loan to simulate.")

        with st.expander("2. Lease vs. Buy Comparator"):
            residual_pct = st.slider("Lease Residual Value (%)", 45, 70, 58)
            lease_term = st.slider("Lease Term (months)", 24, 48, 36)
            money_factor = st.number_input("Money Factor (e.g., 0.0025 = 6%)", 0.0010, 0.0040, 0.0025, step=0.0001)

            dep_in_lease = purchase_price * (1 - residual_pct / 100)
            lease_monthly = (dep_in_lease / lease_term) + (purchase_price * money_factor)
            st.write(f"**Estimated Lease Payment:** ${lease_monthly:,.0f}/month")
            if 'monthly_payment' in locals():
                st.write(f"**Buy Payment (from simulator):** ${monthly_payment:,.0f}/month")
                if lease_monthly < monthly_payment:
                    st.success("Leasing may be cheaper monthly, but you build no equity.")
                else:
                    st.info("Buying builds equity over time.")

        with st.expander("3. Low-Depreciation Vehicle Recommender"):
            current = f"{selected_make} {selected_model}"
            if any(low in current or current in low for low in low_dep_models):
                st.success("✅ Your selected vehicle is known for holding value well!")
            st.write("**Top low-depreciation models (2025 data):**")
            st.write("- Toyota Tacoma, 4Runner, RAV4 Prime")
            st.write("- Honda Civic, CR-V")
            st.write("- Porsche 911, Jeep Wrangler, Subaru Crosstrek")

        with st.expander("4. GAP Insurance Recommender"):
            if down < purchase_price * 0.20:
                st.warning("Low down payment increases upside-down risk.")
                st.info("Consider **GAP Insurance** (~$500–$1,000 one-time or $88/year) – covers the difference if totaled.")
            else:
                st.success("Good down payment – lower GAP need.")

        with st.expander("5. Total Ownership Cost (TCO) Dashboard"):
            years = 5
            insurance_est = 1800 * years
            fuel_cost_per_mile = 0.15  # rough average
            fuel_est = annual_miles * fuel_cost_per_mile * years
            maint_est = 800 * years
            dep_loss = purchase_price - values[-1]
            interest_est = total_paid - loan_amount if 'total_paid' in locals() and loan_amount > 0 else 0

            tco = dep_loss + interest_est + insurance_est + fuel_est + maint_est
            st.metric("Estimated 5-Year TCO", f"${tco:,.0f}")
            st.write(f"- Depreciation: ${dep_loss:,.0f}")
            st.write(f"- Interest: ${interest_est:,.0f}")
            st.write(f"- Insurance: ${insurance_est:,.0f}")
            st.write(f"- Fuel: ${fuel_est:,.0f}")
            st.write(f"- Maintenance: ${maint_est:,.0f}")

st.markdown("---")
st.markdown("Deprecia – Fixed & Enhanced | Smart Financing Demo")
