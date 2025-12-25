import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Deprecia - Smart Financing", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation")

# Front Page Sample Test Section
st.markdown("### Quick Sample Test: 2023 Porsche Taycan Base (High Depreciation EV Example)")
st.markdown("""
**Scenario**: Dealer asks €72,000 for a used 2023 Taycan base. Market value ~€65,000-75,000 (average €70,000).  
Expected resale in 2-3 years: €55,000-60,000.  
This is a classic high-depreciation luxury EV – load the example and see why leasing is often wiser!
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.image("https://media.ed.edmunds-media.com/porsche/taycan/2023/oem/2023_porsche_taycan_sedan_base_fq_oem_1_1600.jpg", caption="2023 Porsche Taycan Base")
with col2:
    st.image("https://www.porsche.com/media/image/2023-taycan-turbo-s-cross-turismo.jpg", caption="Taycan Side View")
with col3:
    st.image("https://www.porsche.com/media/image/2023-taycan-interior.jpg", caption="Taycan Interior")

if st.button("Load Porsche Taycan 2023 Sample Test"):
    st.session_state.sample_loaded = True
    st.session_state.vin = "WP0AA2Y1XPSA12345"  # Sample VIN (decodes to Taycan)
    st.session_state.vehicle_type = "Used (2+ years old)"
    st.session_state.make = "Porsche"
    st.session_state.model = "Taycan"
    st.session_state.year = "2023"
    st.session_state.purchase_price = 72000
    st.session_state.fair_market_value = 70000
    st.session_state.annual_miles = 10000
    st.success("Porsche Taycan sample loaded! Scroll to sidebar and click Calculate.")

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
        }
    except:
        return None

@st.cache_data(ttl=3600)
def get_makes():
    try:
        data = requests.get(f"{BASE_URL}/getallmakes?format=json").json()['Results']
        makes = [m['Make_Name'].title() for m in data if m['VehicleType_Name'] == 'Passenger Car']
        return sorted(set(makes))
    except:
        return ["Toyota", "Honda", "Tesla", "Ford", "Porsche"]

@st.cache_data(ttl=3600)
def get_models(make):
    if not make:
        return []
    try:
        return sorted(set(m['Model_Name'].title() for m in requests.get(f"{BASE_URL}/GetModelsForMake/{make.upper()}?format=json").json()['Results']))
    except:
        return []

# Sidebar inputs with session_state defaults
vin = st.sidebar.text_input("Enter VIN (17 chars)", value=st.session_state.get('vin', ''), help="Optional – auto-fills details")

vehicle_type = st.sidebar.selectbox("New or Used?", ["New", "Used (2+ years old)"],
                                    index=["New", "Used (2+ years old)"].index(st.session_state.get('vehicle_type', "New")) if 'vehicle_type' in st.session_state else 0)

# Make with safe index
makes_list = [""] + get_makes()
default_make = st.session_state.get('make', "")
make_index = makes_list.index(default_make) if default_make in makes_list else 0
make = st.sidebar.selectbox("Make", makes_list, index=make_index)

# Model
models = get_models(make)
default_model = st.session_state.get('model', "")
model_index = models.index(default_model) if default_model in models else 0
model = st.sidebar.selectbox("Model", [""] + models, index=model_index + 1 if model_index > -1 else 0)

# Year
default_year = st.session_state.get('year', "")
year_options = [""] + [str(y) for y in range(2025, 2009, -1)]
year_index = year_options.index(default_year) if default_year in year_options else 0
year = st.sidebar.selectbox("Year", year_options, index=year_index)

purchase_price = st.sidebar.number_input("Purchase Price (€)", min_value=5000, max_value=500000,
                                         value=st.session_state.get('purchase_price', 45000), step=1000)

fair_market_value = st.sidebar.number_input("Estimated Fair Market Value (€)", min_value=0,
                                             value=st.session_state.get('fair_market_value', purchase_price), step=1000,
                                             help="From AutoScout24, Mobile.de, etc.")

annual_miles = st.sidebar.number_input("Annual Miles / km", value=st.session_state.get('annual_miles', 12000), step=1000)

low_dep_keywords = ["Tacama", "4Runner", "Civic", "CR-V", "Wrangler", "911", "RAV4", "Lexus", "Camry", "Corolla"]

if st.sidebar.button("Calculate"):
    if not all([year, make, model]):
        st.error("Complete vehicle selection")
    else:
        st.success(f"### {year} {make} {model}")

        # Depreciation rates
        if vehicle_type == "Used (2+ years old)":
            rates = [0.10, 0.12, 0.12, 0.11, 0.10]
            st.info("Used car: Lower depreciation rates applied")
        else:
            rates = [0.25, 0.18, 0.16, 0.14, 0.12]

        if annual_miles > 15000:
            rates = [r + 0.03 for r in rates]
            st.warning("High mileage adds ~3% extra dep/year")

        values = [purchase_price]
        for r in rates:
            values.append(values[-1] * (1 - r))

        drive_off = purchase_price * (0.12 if vehicle_type == "New" else 0.08)
        st.warning(f"🚨 Immediate Drive-Off Loss: ~€{drive_off:,.0f}")

        years_list = [int(year) + i for i in range(6)]
        df = pd.DataFrame({"Year": years_list, "Value (€)": [round(v) for v in values]})
        df["Loss (€)"] = df["Value (€)"].diff().fillna(0) * -1
        st.subheader("5-Year Depreciation Forecast")
        st.dataframe(df.style.format({"Value (€)": "€{:.0f}", "Loss (€)": "€{:.0f}"}))

        # Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["Year"], df["Value (€)"], marker="o", color="#e74c3c", linewidth=4)
        ax.axhline(y=purchase_price * 0.5, color="orange", linestyle="--", label="50% of Purchase")
        ax.fill_between(df["Year"], df["Value (€)"], purchase_price, alpha=0.2, color="#e74c3c")
        ax.set_title("Depreciation Impact")
        ax.set_ylabel("Value (€)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
        st.pyplot(fig)

        # Market value impact
        price_diff = purchase_price - fair_market_value
        if price_diff > 500:
            st.error(f"Paying €{price_diff:,.0f} ABOVE market – hits resale hard!")
        elif price_diff < -500:
            st.success(f"Bargain! €{-price_diff:,.0f} BELOW market")
        else:
            st.info("Near market value")

        # Smart Buy Score
        remaining_pct = values[-1] / purchase_price * 100
        is_low_dep = any(k in f"{make} {model}" for k in low_dep_keywords)
        if remaining_pct > 55 or (is_low_dep and vehicle_type == "Used (2+ years old)"):
            st.success(f"🟢 Smart Buy! ~{remaining_pct:.0f}% remaining")
        elif remaining_pct > 40:
            st.warning(f"🟡 Caution – ~{remaining_pct:.0f}% remaining")
        else:
            st.error(f"🔴 High Risk – only ~{remaining_pct:.0f}% remaining")

        monthly = None

        with st.expander("1. Loan Simulator"):
            down = st.slider("Down Payment (€)", 0, purchase_price//2, max(5000, purchase_price//10), 1000)
            loan = purchase_price - down
            term = st.slider("Term (months)", 36, 84, 60)
            rate = st.slider("Interest Rate (%)", 3.0, 12.0, 6.0) / 100

            if loan > 0 and rate > 0:
                r = rate / 12
                monthly = loan * r * (1 + r)**term / ((1 + r)**term - 1)
                total_paid = monthly * term
                st.write(f"**Monthly:** €{monthly:,.0f}")
                st.write(f"**Interest:** €{total_paid - loan:,.0f}")

                balance = loan
                balances = [loan]
                for _ in range(5):
                    for _ in range(12):
                        interest = balance * r
                        principal = monthly - interest
                        balance -= principal
                        if balance < 0:
                            balance = 0
                    balances.append(balance)

                upside = [i for i, (b, v) in enumerate(zip(balances, values)) if b > v]
                if upside:
                    st.error(f"Upside down risk in year(s): {', '.join(str(i) for i in upside)}")

                fig2, ax2 = plt.subplots(figsize=(10, 5))
                ax2.plot(years_list, values, label="Value", marker="o")
                ax2.plot(years_list, balances, label="Loan", marker="s")
                ax2.fill_between(years_list, values, balances, where=[b > v for b, v in zip(balances, values)], color="red", alpha=0.3)
                ax2.legend()
                ax2.set_title("Loan vs Value")
                ax2.grid(True)
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
                st.pyplot(fig2)

        with st.expander("2. Lease vs Buy"):
            residual = st.slider("Residual (%)", 45, 70, 58)
            lease_term = st.slider("Lease Term (months)", 24, 48, 36)
            mf = st.number_input("Money Factor", 0.0010, 0.0040, 0.0025, 0.0001)
            dep_lease = purchase_price * (1 - residual/100)
            lease_monthly = (dep_lease / lease_term) + (purchase_price * mf)
            st.write(f"**Lease Monthly:** €{lease_monthly:,.0f}")
            if monthly is not None:
                st.write(f"**Buy Monthly:** €{monthly:,.0f}")

        with st.expander("3. How to Avoid Depreciation"):
            st.markdown("""
            - Buy used to skip first-year drop
            - Buy below market value
            - Choose low-dep models (Toyota, Honda)
            - Lease luxury/high-dep cars (like Taycan)
            - Larger down payment
            """)

st.markdown("---")
st.markdown("Deprecia – With Porsche Taycan Sample & Fixed Session State")
