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
st.header("Insights")

# At-risk vendors (simple version)
if "sales" in vendor_data.columns:
    low_sales = vendor_data[vendor_data["sales"] < vendor_data["sales"].mean()]

    if not low_sales.empty:
        st.subheader("At-Risk Vendors")
        st.write("These vendors are performing below average and may need support:")
        st.dataframe(low_sales[["vendor_name", "sales"]])
    else:
        st.success("No at-risk vendors right now")

# Weather + attendance relationship (simple)
if "weather_descriptor" in market_data.columns:
    st.subheader("Weather Impact Insight")
    weather_summary = market_data.groupby("weather_descriptor")["attendance_total"].mean()
    st.write(weather_summary)

    st.caption("Insight: Compare attendance across weather conditions to guide programming and vendor mix.")
    st.header("Next Market Planning")

st.write("This section will identify upcoming vendors, expected attendance, weather context, and at-risk vendors for the next market.")

st.header("Next Market Planning")

# Simulated upcoming market inputs (you can make this dynamic later)
expected_vendors = len(vendor_data["vendor_name"].unique())

# Simple weather assumption (replace later with real API if you want)
weather_outlook = "Sunny"

# Attendance expectation logic
if expected_vendors > 25 and weather_outlook == "Sunny":
    expected_attendance = "1,000+"
else:
    expected_attendance = "Moderate"

st.metric("Expected Vendors", expected_vendors)
st.metric("Weather Outlook", weather_outlook)
st.metric("Expected Attendance", expected_attendance)

st.caption("Insight: Vendor count and weather conditions drive expected attendance. High vendor volume + good weather suggests a strong market day.")

# At-risk vendors (reuse logic)
low_sales = vendor_data[vendor_data["sales"] < vendor_data["sales"].mean()]

if not low_sales.empty:
    st.subheader("Vendors to Support This Week")
    st.write("These vendors may benefit from marketing or placement support:")
    st.dataframe(low_sales[["vendor_name", "sales"]])