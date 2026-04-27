import streamlit as st
<<<<<<< HEAD

st.title("William & Mary Farmers Market Dashboard")
st.write("App is running!")
st.write("Next step: convert the local dashboard code into Streamlit layout.")
=======
import pandas as pd

st.title("William & Mary Farmers Market Dashboard")

st.success("App is running 🎉")

# Load data
vendor_data = pd.read_csv("marketspread_vendor_data.csv")
market_data = pd.read_csv("marketspread_market_day_data.csv")

st.subheader("Vendor Data")
st.dataframe(vendor_data)

st.subheader("Market Data")
st.dataframe(market_data)
>>>>>>> be78ab4 (Add Streamlit app)
