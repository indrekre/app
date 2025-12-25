import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Deprecia - Smart Financing", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation")
st.markdown("VIN lookup, depreciation forecast, and smarter financing tools.")

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
        return ["Toyota", "Honda", "Tesla", "Ford"]

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
vin = st.sidebar.text_input("Enter VIN (17 chars)")
decoded = None
if vin:
    with st.spinner("Decoding VIN..."):
        decoded = decode_vin(vin.strip())
    if decoded and decoded["year"]:
        st.sidebar.success(f"✅ {decoded['year']} {decoded['make']} {decoded['model']}")
    else:
        st.sidebar.warning("Invalid VIN – use manual")

make = decoded["make"] if decoded else st.sidebar.selectbox("Make", [""] + get_makes())
models = get_models(make) if make else []
model = decoded["model"] if decoded else st.sidebar.selectbox("Model", [""] + models)
year = st.sidebar.selectbox("Year", [decoded["year"]] if decoded and decoded["year"] else [""] + [str(y) for y in range(2025, 2010, -1)])

purchase_price = st.sidebar.number_input("Purchase Price ($)", 10000, 300000, 45000, 1000)
annual_miles = st.sidebar.number_input("Annual Miles", value=12000)

low_dep = ["Tacoma", "4Runner", "Civic", "CR-V"]

if st.sidebar.button("Calculate"):
    if not all([year, make, model]):
        st.error("Complete vehicle selection")
    else:
        st.success(f"### {year} {make} {model}")

        rates = [0.25, 0.18, 0.16, 0.14, 0.12]
        if annual_miles > 15000:
            rates = [r + 0.03 for r in rates]
            st.warning(f"High mileage adds ~3% extra dep/year")

        values = [purchase_price]
        for r in rates:
            values.append(values[-1] * (1 - r))

        st.warning(f"🚨 Drive-Off Loss: ~${purchase_price * 0.12:,.0f}")

        years_list = [int(year) + i for i in range(6)]
        df = pd.DataFrame({"Year": years_list, "Value ($)": [round(v) for v in values]})
        df["Loss ($)"] = df["Value ($)"].diff().fillna(0) * -1
        st.subheader("5-Year Depreciation")
        st.dataframe(df.style.format({"Value ($)": "${:,.0f}", "Loss ($)": "${:,.0f}"}))

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["Year"], df["Value ($)"], marker="o", color="#e74c3c", linewidth=3)
        ax.set_title("Projected Value")
        ax.grid(True)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        st.pyplot(fig)

        monthly = None  # Define outside

        with st.expander("1. Loan Simulator", expanded=True):
            down = st.slider("Down Payment ($)", 0, purchase_price//2, purchase_price//10, 1000)
            loan = purchase_price - down
            term = st.slider("Term (months)", 36, 84, 60)
            rate = st.slider("Interest Rate (%)", 4.0, 15.0, 7.0) / 100

            if loan > 0 and rate > 0:
                r = rate / 12
                monthly = loan * r * (1 + r)**term / ((1 + r)**term - 1)
                total_paid = monthly * term
                st.write(f"**Monthly Payment:** ${monthly:,.0f}")
                st.write(f"**Total Interest:** ${total_paid - loan:,.0f}")

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
                    st.error(f"Upside down in year(s): {', '.join(str(i) for i in upside)} – increase down payment!")

                fig2, ax2 = plt.subplots(figsize=(10, 5))
                ax2.plot(years_list, values, label="Vehicle Value", marker="o", color="#e74c3c")
                ax2.plot(years_list, balances, label="Loan Balance", marker="s", color="#3498db")
                ax2.fill_between(years_list, values, balances, where=[b > v for b, v in zip(balances, values)], color="red", alpha=0.3, label="Risk Zone")
                ax2.legend()
                ax2.set_title("Loan Balance vs Value")
                ax2.grid(True)
                ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
                st.pyplot(fig2)

        with st.expander("2. Lease vs Buy"):
            residual = st.slider("Residual (%)", 45, 70, 58)
            lease_term = st.slider("Lease Term (months)", 24, 48, 36)
            mf = st.number_input("Money Factor", 0.0010, 0.0040, 0.0025, 0.0001)
            dep_lease = purchase_price * (1 - residual/100)
            lease_monthly = (dep_lease / lease_term) + (purchase_price * mf)
            st.write(f"**Lease Monthly:** ${lease_monthly:,.0f}")
            if monthly is not None:
                st.write(f"**Buy Monthly:** ${monthly:,.0f}")
            else:
                st.write("**Buy Monthly:** N/A (run Loan Simulator first)")

        with st.expander("3. Low-Dep Recommender"):
            current = f"{make} {model}"
            if any(low in current for low in low_dep):
                st.success("Great choice – holds value well!")
            st.write("Top low-dep: Toyota Tacoma/4Runner, Honda Civic/CR-V")

        with st.expander("4. GAP Insurance"):
            if 'down' in locals() and down < purchase_price * 0.20:
                st.warning("Low down payment – high risk")
                st.info("Recommend GAP insurance (~$500–$1000)")
            else:
                st.info("Down payment looks good")

        with st.expander("5. TCO Dashboard"):
            years = 5
            dep_loss = purchase_price - values[-1]
            interest = (total_paid - loan) if 'total_paid' in locals() and loan > 0 else 0
            tco = dep_loss + interest + 9000 + (annual_miles * 0.15 * years) + 4000
            st.metric("5-Year TCO Estimate", f"${tco:,.0f}")

st.markdown("---")
st.markdown("Deprecia – Final Working Version")
