# ============================================================
# WILLIAM & MARY FARMERS MARKET DASHBOARD
# STREAMLIT VERSION (BASED ON ORIGINAL FULL DEMO)
# ============================================================
# PURPOSE:
# This dashboard demonstrates how agentic AI can replace or improve
# a fragile spreadsheet process for farmers market operations.
#
# ORIGINAL SYSTEM INCLUDED:
# - Approved vendor controls (prevents bad data entry)
# - Automated fee calculation (6% rule)
# - Token reimbursement logic
# - Attendance estimation using 2.43 multiplier
# - Vendor performance tracking and benchmarking
# - Follow-up identification (sales + payment)
# - Weather + attendance + programming analysis
# - Decision loop (10–11am traffic dip → programming intervention)
# - Built-in constrained AI assistant
#
# CURRENT VERSION:
# This Streamlit version preserves the business logic and insights
# while replacing the local web server with a deployable dashboard.
#
# DESIGN PRINCIPLES:
# - No manual math (everything is calculated)
# - One source of truth for fee logic
# - Clean separation between data, logic, and insights
# ============================================================

import streamlit as st
import pandas as pd


# CORE DEMO STORY:
# 1. Replaces multi-spreadsheet tracking with one operations dashboard.
# 2. Tracks vendor sales, 6% fees, attendance, weather, and market context.
# 3. Separates vendor-level data from market-day information.
# 4. Uses calculated fields instead of manually trusted spreadsheet values.
# 5. Supports better decisions about follow-up, marketing, and attendance trends.
# ============================================================

st.set_page_config(
    page_title="W&M Farmers Market Dashboard",
    layout="wide"
)

st.markdown("""
<style>
.main {
    background-color: #F7F4EA;
}

h1, h2, h3 {
    color: #115740;
}

[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #C99700;
    padding: 18px;
    border-radius: 14px;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<h1 style='color:#115740;'>William & Mary Farmers Market Dashboard</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='color:#115740; font-weight:600;'>Agentic AI operations dashboard for market management</p>",
    unsafe_allow_html=True
)


st.markdown("""
<style>
.main {
    background-color: #F7F4EA;
}

h1, h2, h3 {
    color: #115740;
}

[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #C99700;
    padding: 18px;
    border-radius: 14px;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.wm-card {
    background-color: white;
    border-left: 6px solid #115740;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 18px;
}

.wm-gold-card {
    background-color: white;
    border-left: 6px solid #C99700;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 18px;
}
</style>
""", unsafe_allow_html=True)

SALES_FEE_RATE = 0.06



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

    st.header("Market Assistant")

question = st.text_input("Ask a question about your market data:")

if question:
    question_lower = question.lower()

    if "sales" in question_lower:
        total_sales = vendor_data["sales"].sum()
        st.write(f"Total recorded sales are ${total_sales:,.2f}.")

    elif "attendance" in question_lower:
        total_attendance = market_data["attendance_total"].sum()
        st.write(f"Estimated total attendance is {total_attendance:,.0f}.")

    elif "vendors" in question_lower:
        vendor_count = vendor_data["vendor_name"].nunique()
        st.write(f"There are {vendor_count} unique vendors in the dataset.")

    elif "at risk" in question_lower or "underperform" in question_lower:
        low_sales = vendor_data[vendor_data["sales"] < vendor_data["sales"].mean()]
        if not low_sales.empty:
            names = ", ".join(low_sales["vendor_name"].unique())
            st.write(f"These vendors may need support: {names}.")
        else:
            st.write("No vendors are currently underperforming.")

    else:
        st.write("Try asking about sales, attendance, vendors, or at-risk vendors.")

        st.header("Operations Dashboard")

st.caption("Operational tracking of vendor performance, fees, and follow-up actions.")

operations_df = vendor_data.copy()

# Build logic from your original system
operations_df["total_sales"] = operations_df["sales"] + operations_df.get("token_reimbursement", 0)
operations_df["fee_due"] = operations_df["total_sales"] * 0.06
operations_df["balance_due"] = operations_df["fee_due"] - operations_df.get("paid_amount", 0)

def action_needed(row):
    if row.get("sales", 0) == 0:
        return "Send sales reminder"
    elif row.get("paid_amount", 0) < row["fee_due"]:
        return "Send payment reminder"
    else:
        return "Complete"

operations_df["action_needed"] = operations_df.apply(action_needed, axis=1)

st.dataframe(operations_df)

# ============================================================
# DECISION LOOP: ATTENDANCE + PROGRAMMING INSIGHT
# ============================================================
# WHY:
# This section shows the analytics loop:
# observe attendance by time of day → identify a weak period →
# recommend programming → measure whether attendance improves.

st.header("Decision Loop: Attendance + Programming")

st.caption(
    "This section connects timed attendance counts to programming decisions, "
    "such as adding children's activities during softer traffic windows."
)

if {"attendance_930", "attendance_1030"}.issubset(market_data.columns):
    avg_930 = market_data["attendance_930"].mean()
    avg_1030 = market_data["attendance_1030"].mean()

    col1, col2, col3 = st.columns(3)

    col1.metric("Avg. 9:30 Count", f"{avg_930:,.0f}")
    col2.metric("Avg. 10:30 Count", f"{avg_1030:,.0f}")

    if avg_1030 < avg_930:
        col3.metric("Pattern", "10–11am Dip")
        st.warning(
            "Observed pattern: attendance is softer around the 10:30 count. "
            "Recommendation: add or promote children’s programming, music, chef demos, "
            "or other engagement during the 10–11am window."
        )
    else:
        col3.metric("Pattern", "Stable Traffic")
        st.success(
            "Attendance does not currently show a clear 10–11am dip, but the market "
            "should continue tracking this window."
        )

    st.line_chart(
        market_data[["attendance_830", "attendance_930", "attendance_1030", "attendance_1130"]]
    )

else:
    st.info(
        "Timed attendance columns are not available yet. "
        "Expected columns: attendance_830, attendance_930, attendance_1030, attendance_1130."
    )