import streamlit as st
import pandas as pd

# ============================================================
# WILLIAM & MARY FARMERS MARKET DASHBOARD
# STREAMLIT DEMO VERSION WITH COMMENTS
# ============================================================
# PURPOSE:
# This dashboard demonstrates how agentic AI can replace or improve
# a fragile spreadsheet process for farmers market operations.
#
# CORE DEMO STORY:
# 1. Replaces multi-spreadsheet tracking with one operations dashboard.
# 2. Tracks vendor sales, 6% fees, attendance, weather, and market context.
# 3. Separates vendor-level data from market-day information.
# 4. Uses calculated fields instead of manually trusted spreadsheet values.
# 5. Supports better decisions about follow-up, marketing, and attendance trends.
# ============================================================

SALES_FEE_RATE = 0.06

st.title("William & Mary Farmers Market Dashboard")
st.caption("Agentic AI operations dashboard demo for farmers market management.")

vendor_data = pd.read_csv("marketspread_vendor_data.csv")
market_data = pd.read_csv("marketspread_market_day_data.csv")

st.header("Quick Metrics")

total_sales = vendor_data["sales"].sum()
estimated_fees = total_sales * SALES_FEE_RATE
total_attendance = market_data["attendance_total"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total Vendor Sales", f"${total_sales:,.2f}")
col2.metric("Estimated 6% Market Fees", f"${estimated_fees:,.2f}")
col3.metric("Season-to-date Attendance", f"{total_attendance:,.0f}")

st.subheader("Vendor Data")
st.dataframe(vendor_data)

st.subheader("Market Data")
st.dataframe(market_data)