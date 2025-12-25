import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Deprecia - Smart Financing", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation")
st.markdown("VIN lookup, depreciation forecast, smarter financing + **Smart Buy Score** and tips to avoid loss.")

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

# Sidebar
st.sidebar.header("Vehicle Selection")
vin = st.sidebar.text_input("Enter VIN (17 chars)", help="Optional – auto-fills make/model/year")
decoded = None
if vin:
    with st.spinner("Decoding VIN..."):
        decoded = decode_vin(vin.strip())
    if decoded and decoded["year"]:
        st.sidebar.success(f"✅ {decoded['year']} {decoded['make']} {decoded['model']}")
    else:
        st.sidebar.warning("Invalid VIN – use manual selection")

vehicle_type = st.sidebar.selectbox("New or Used?", ["New", "Used (2+ years old)"], help="Used cars depreciate slower – skip the big first-year drop!")

make = decoded["make"] if decoded else st.sidebar.selectbox("Make", [""] + get_makes())
models = get_models(make) if make else []
model = decoded["model"] if decoded else st.sidebar.selectbox("Model", [""] + models)
year = st.sidebar.selectbox("Year", [decoded["year"]] if decoded and decoded["year"] else [""] + [str(y) for y in range(2025, 2009, -1)])

purchase_price = st.sidebar.number_input("Purchase Price (€)", min_value=5000, max_value=500000, value=45000, step=1000)
fair_market_value = st.sidebar.number_input("Estimated Fair Market Value (€)", min_value=0, value=purchase_price, step=1000,
                                            help="Look up on AutoScout24, Mobile.de, KBB, or Edmunds for current market price")

annual_miles = st.sidebar.number_input("Annual Miles / km", value=12000, step=1000)

# Low-dep keywords
low_dep_keywords = ["Tacoma", "4Runner", "Civic", "CR-V", "Wrangler", "911", "RAV4", "Lexus", "Camry", "Corolla"]

if st.sidebar.button("Calculate"):
    if not all([year, make, model]):
        st.error("Complete vehicle selection")
    else:
        st.success(f"### {year} {make} {model}")

        # Depreciation rates
        if vehicle_type == "Used (2+ years old)":
            rates = [0.10, 0.12, 0.12, 0.11, 0.10]  # Slower for used
            st.info("Used car selected: Lower depreciation rates applied (you skip the 20-30% new-car drop)")
        else:
            rates = [0.25, 0.18, 0.16, 0.14, 0.12]

        if annual_miles > 15000:
            rates = [r + 0.03 for r in rates]
            st.warning(f"High mileage adds ~3% extra depreciation per year")

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

        # Enhanced Chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["Year"], df["Value (€)"], marker="o", color="#e74c3c", linewidth=4)
        ax.axhline(y=purchase_price * 0.5, color="orange", linestyle="--", label="50% of Purchase")
        ax.fill_between(df["Year"], df["Value (€)"], purchase_price, alpha=0.2, color="#e74c3c", label="Total Depreciation Loss")
        ax.set_title("Depreciation Impact – Clear Visual of Value Loss", fontsize=16)
        ax.set_ylabel("Value (€)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
        st.pyplot(fig)

        # Market Value Impact
        price_diff = purchase_price - fair_market_value
        if price_diff > 500:
            st.error(f"🔴 Paying €{price_diff:,.0f} ABOVE market – this will hit hard when reselling!")
        elif price_diff < -500:
            st.success(f"🟢 Great bargain! €{-price_diff:,.0f} BELOW market – minimizes your effective loss.")
        else:
            st.info("Paying near market value – fair deal.")

        # Smart Buy Score
        remaining_pct = values[-1] / purchase_price * 100
        is_low_dep = any(k in f"{make} {model}" for k in low_dep_keywords)
        mileage_factor = annual_miles < 12000

        if remaining_pct > 55 or (is_low_dep and vehicle_type == "Used (2+ years old)"):
            score = "Smart"
            st.success(f"🟢 **Smart Buy!** Remaining ~{remaining_pct:.0f}% after 5 years. Low-depreciation model + good deal.")
        elif remaining_pct > 40:
            score = "Caution"
            st.warning(f"🟡 **Caution** – Remaining ~{remaining_pct:.0f}%. Average risk – negotiate better or consider alternatives.")
        else:
            score = "High Risk"
            st.error(f"🔴 **High Risk** – Remaining only ~{remaining_pct:.0f}%. Strong depreciation expected – lease instead?")

        monthly = None

        with st.expander("1. Loan Simulator", expanded=True):
            down = st.slider("Down Payment (€)", 0, purchase_price//2, max(5000, purchase_price//10), 1000)
            loan = purchase_price - down
            term = st.slider("Term (months)", 36, 84, 60)
            rate = st.slider("Interest Rate (%)", 3.0, 12.0, 6.0) / 100

            if loan > 0 and rate > 0:
                r = rate / 12
                monthly = loan * r * (1 + r)**term / ((1 + r)**term - 1)
                total_paid = monthly * term
                st.write(f"**Monthly Payment:** €{monthly:,.0f}")
                st.write(f"**Total Interest:** €{total_paid - loan:,.0f}")

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
                    st.error(f"Upside down risk in year(s): {', '.join(str(i) for i in upside)} – increase down payment!")

                fig2, ax2 = plt.subplots(figsize=(10, 5))
                ax2.plot(years_list, values, label="Vehicle Value", marker="o", color="#e74c3c")
                ax2.plot(years_list, balances, label="Loan Balance", marker="s", color="#3498db")
                ax2.fill_between(years_list, values, balances, where=[b > v for b, v in zip(balances, values)], color="red", alpha=0.3, label="Upside-Down Risk")
                ax2.legend()
                ax2.set_title("Loan vs Value – Stay Above Water")
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
            else:
                st.write("**Buy Monthly:** N/A (run Loan Simulator first)")

        with st.expander("3. How to Avoid Depreciation Impact"):
            st.markdown("""
            ### Top Strategies to Minimize Loss
            - **Buy used (2+ years old)**: Skip the 20-30% first-year drop
            - **Buy below market value**: Bargains reduce your effective loss
            - **Choose low-depreciation models**: Toyota Camry/Corolla, Honda Civic/CR-V, Jeep Wrangler
            - **Keep mileage low**: Under 12,000 km/year
            - **Maintain perfectly**: Service history boosts resale
            - **Lease high-depreciation cars** (luxury/EVs): Pay only for the drop you use
            - **Larger down payment + shorter loan**: Avoid upside-down risk
            """)
            if score == "High Risk":
                st.error("High depreciation risk – strongly consider leasing or walking away.")
            elif score == "Caution":
                st.warning("Moderate risk – negotiate price down and increase down payment.")
            else:
                st.success("You're making a smart decision – low risk of big loss!")

        with st.expander("4. GAP Insurance"):
            if 'down' in locals() and down < purchase_price * 0.20:
                st.warning("Low down payment increases upside-down risk")
                st.info("Recommend GAP insurance (~€500–€1000)")

        with st.expander("5. TCO Dashboard"):
            years = 5
            dep_loss = purchase_price - values[-1]
            interest = (total_paid - loan) if 'total_paid' in locals() and 'loan' in locals() and loan > 0 else 0
            tco = dep_loss + interest + 9000 + (annual_miles * 0.15 * years) + 4000
            st.metric("Estimated 5-Year TCO", f"€{tco:,.0f}")

st.markdown("---")
st.markdown("Deprecia – Updated with Used Car Support, Market Value Impact & Euro Currency")
