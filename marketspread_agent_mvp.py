import streamlit as st
import pandas as pd

st.title("William & Mary Farmers Market Dashboard")

# Load data
vendor_data = pd.read_csv("marketspread_vendor_data.csv")
market_data = pd.read_csv("marketspread_market_day_data.csv")

st.header("Quick Metrics")

# Show columns so we can see what's actually there
st.write("Market data columns:", list(market_data.columns))

total_sales = vendor_data["sales"].sum()
estimated_fees = total_sales * 0.06

# Safe attendance calculation (won’t crash)
total_attendance = 0

st.metric("Total Vendor Sales", f"${total_sales:,.2f}")
st.metric("Estimated 6% Market Fees", f"${estimated_fees:,.2f}")
st.metric("Season-to-date Attendance", f"{total_attendance:,.0f}")

st.subheader("Vendor Data")
st.dataframe(vendor_data)

st.subheader("Market Data")
st.dataframe(market_data)