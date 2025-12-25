import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np

st.set_page_config(page_title="Deprecia - Smart Financing", page_icon="🚗")
st.title("🚗 Deprecia – Smart Car Financing & Depreciation")
st.markdown("VIN lookup, depreciation forecast, and smarter financing to avoid value loss.")

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
        return ["Toyota", "Honda", "Tesla"]

@st.cache_data(ttl=3600)
def get_models(make):
    if not make:
        return []
    try:
        return sorted(set(m['Model_Name'].title() for m in requests.get(f"{BASE_URL}/GetModelsForMake/{make.upper()}?format=json").json()['Results']))
    except:
        return []

st.sidebar.header("Vehicle")
vin = st.sidebar.text_input("VIN (17 chars)")
decoded = None
if vin:
    with st.spinner("Decoding..."):
        decoded = decode_vin(vin.strip())
    if decoded and decoded["year"]:
        st.sidebar.success(f"✅ {decoded['year']} {decoded['make']} {decoded['model']}")
    else:
        st.sidebar.warning("Invalid VIN")

make = decoded["make"] if decoded else st.sidebar.selectbox("Make", [""] + get_makes())
models = get_models(make) if make else []
model = decoded["model"] if decoded else st.sidebar.selectbox("Model", [""] + models)
year = st.sidebar.selectbox("Year", [decoded["year"]] if decoded and decoded["year"] else [""] + [str(y) for y in range(2025, 2010, -1)])

purchase_price = st.sidebar.number_input("Price ($)", 10000, 300000, 45000, 1000)
annual_miles = st.sidebar.number_input("Annual Miles", value=12000)

low_dep = ["Toyota Tacoma", "Toyota 4Runner", "Honda Civic"]

if st.sidebar.button("Calculate"):
    if not all([year, make, model]):
        st.error("Select vehicle")
    else:
        st.success(f"### {year} {make} {model}")

        rates = [0.25, 0.18, 0.16, 0.14, 0.12]
        if annual_miles > 15000:
            rates = [r + 0.03 for r in rates]
            st.warning("High mileage adds extra depreciation")

        values = [purchase_price]
        for r in rates:
            values.append(values[-1] * (1 - r))

        st.warning(f"Drive-Off Loss: ~${purchase_price * 0.12:,.0f}")

        years_list = [int(year) + i for i in range(6)]
        df = pd.DataFrame({"Year": years_list, "Value": [round(v) for v in values]})
        st.dataframe(df.style.format({"Value": "${:,.0f}"}))

        fig, ax = plt.subplots()
        ax.plot(df["Year"], df["Value"], marker="o", color="red")
        ax.set_title("Value Over Time")
        st.pyplot(fig)

        with st.expander("Loan Simulator"):
            down = st.slider("Down Payment", 0, purchase_price//2, purchase_price//10, 1000)
            loan = purchase_price - down
            term = st.slider("Term (months)", 36, 84, 60)
            rate = st.slider("Rate (%)", 4.0, 15.0, 7.0) / 100

            if loan > 0:
                monthly = np.pmt(rate/12, term, -loan)
                total_paid = monthly * term
                st.write(f"Monthly: ${monthly:,.0f} | Interest: ${total_paid - loan:,.0f}")

                balance = loan
                balances = [loan]
                for _ in range(5):
                    for _ in range(12):
                        interest = balance * (rate / 12)
                        principal = monthly - interest
                        balance -= principal
                        if balance < 0:
                            balance = 0
                    balances.append(balance)

                upside = [i for i, (b, v) in enumerate(zip(balances, values)) if b > v]
                if upside:
                    st.error(f"Upside down years: {', '.join(str(i) for i in upside)}")

                fig2, ax2 = plt.subplots()
                ax2.plot(years_list, values, label="Value", marker="o")
                ax2.plot(years_list, balances, label="Loan", marker="s")
                ax2.fill_between(years_list, values, balances, where=np.array(balances) > np.array(values), color="red", alpha=0.3)
                ax2.legend()
                ax2.set_title("Loan vs Value")
                st.pyplot(fig2)

        with st.expander("Lease vs Buy"):
            residual = st.slider("Residual (%)", 45, 70, 58)
            lease_term = st.slider("Lease Months", 24, 48, 36)
            mf = st.number_input("Money Factor", 0.001, 0.004, 0.0025, 0.0001)
            lease_pay = (purchase_price * (1 - residual/100) / lease_term) + (purchase_price * mf)
            st.write(f"Lease Monthly: ${lease_pay:,.0f}")

        with st.expander("Low-Dep Recommender"):
            if any(m in f"{make} {model}" for m in low_dep):
                st.success("Good choice – holds value well!")
            st.write("Top: Toyota Tacoma, Honda Civic, etc.")

st.markdown("Deprecia – Fixed Version")
