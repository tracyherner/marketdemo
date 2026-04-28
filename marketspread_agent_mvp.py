# ============================================================
# WILLIAM & MARY FARMERS MARKET DASHBOARD
# STREAMLIT VERSION (BASED ON ORIGINAL FULL DEMO)
# ============================================================

import streamlit as st
import pandas as pd

# ---------- CONFIGURATION ----------
SALES_FEE_RATE = 0.06
WM_GREEN = "#115740"
WM_GOLD = "#C99700"

st.set_page_config(
    page_title="W&M Farmers Market Dashboard",
    layout="wide"
)

# ---------- W&M STYLE ----------
st.markdown("""
<style>
.main {
    background-color: #F7F4EA;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: #115740;
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

[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #C99700;
    padding: 18px;
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown(
    "<h1 style='color:#115740;'>William & Mary Farmers Market Dashboard</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='color:#115740; font-weight:600;'>Agentic AI operations dashboard for market management</p>",
    unsafe_allow_html=True
)

# ---------- DATA LOADING ----------
vendor_data = pd.read_csv("marketspread_vendor_data.csv")
market_data = pd.read_csv("marketspread_market_day_data.csv")

# ---------- CORE CALCULATIONS ----------
total_sales = vendor_data["sales"].sum()
estimated_fees = total_sales * SALES_FEE_RATE
total_attendance = market_data["attendance_total"].sum()
vendor_count = vendor_data["vendor_name"].nunique()

low_sales = vendor_data[vendor_data["sales"] < vendor_data["sales"].mean()]

# ---------- OPERATIONS LOGIC ----------
operations_df = vendor_data.copy()

operations_df["total_sales"] = operations_df["sales"] + operations_df.get("token_reimbursement", 0)
operations_df["fee_due"] = operations_df["total_sales"] * SALES_FEE_RATE
operations_df["balance_due"] = operations_df["fee_due"] - operations_df.get("paid_amount", 0)

def action_needed(row):
    if row.get("sales", 0) == 0:
        return "Send sales reminder"
    elif row.get("paid_amount", 0) < row["fee_due"]:
        return "Send payment reminder"
    else:
        return "Complete"

operations_df["action_needed"] = operations_df.apply(action_needed, axis=1)

open_followups = operations_df[operations_df["action_needed"] != "Complete"]

# ============================================================
# MARKET ASSISTANT
# ============================================================

st.markdown("<div class='wm-gold-card'>", unsafe_allow_html=True)
st.header("Market Assistant")

question = st.text_input("Ask a question about your market data:")

if question:
    question_lower = question.lower()

    if "past due" in question_lower or "follow up" in question_lower or "follow-up" in question_lower or "need action" in question_lower:
        if not open_followups.empty:
            vendor_names = ", ".join(open_followups["vendor_name"].dropna().unique())
            st.write(
                f"There are {open_followups['vendor_name'].nunique()} vendor(s) needing follow-up: {vendor_names}."
            )
            st.dataframe(open_followups[["vendor_name", "market_date", "action_needed", "balance_due"]])
        else:
            st.write("No vendors are currently past due. All vendor records appear complete.")

    elif "at risk" in question_lower or "underperform" in question_lower:
        if not low_sales.empty:
            names = ", ".join(low_sales["vendor_name"].dropna().unique())
            st.write(f"These vendors may need support: {names}.")
            st.dataframe(low_sales[["vendor_name", "sales"]])
        else:
            st.write("No vendors are currently underperforming.")

    elif "sales" in question_lower:
        st.write(f"Total recorded sales are ${total_sales:,.2f}.")

    elif "attendance" in question_lower:
        st.write(f"Estimated total attendance is {total_attendance:,.0f}.")

    elif "vendors" in question_lower:
        st.write(f"There are {vendor_count} unique vendors in the dataset.")

    else:
        st.write("Try asking about past due vendors, at-risk vendors, sales, attendance, or vendor count.")

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# QUICK METRICS
# ============================================================

st.markdown("<div class='wm-card'>", unsafe_allow_html=True)
st.header("Quick Metrics")

col1, col2, col3 = st.columns(3)
col1.metric("Total Vendor Sales", f"${total_sales:,.2f}")
col2.metric("Estimated 6% Market Fees", f"${estimated_fees:,.2f}")
col3.metric("Season-to-date Attendance", f"{total_attendance:,.0f}")

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# NEXT MARKET PLANNING
# ============================================================

st.markdown("<div class='wm-card'>", unsafe_allow_html=True)
st.header("Next Market Planning")

expected_vendors = vendor_count
weather_outlook = "Sunny"

if expected_vendors > 25 and weather_outlook == "Sunny":
    expected_attendance = "1,000+"
else:
    expected_attendance = "Moderate"

col1, col2, col3 = st.columns(3)
col1.metric("Expected Vendors", expected_vendors)
col2.metric("Weather Outlook", weather_outlook)
col3.metric("Expected Attendance", expected_attendance)

st.caption(
    "Insight: Vendor count and weather conditions drive expected attendance. "
    "High vendor volume plus favorable weather suggests a strong market day."
)

if not low_sales.empty:
    st.subheader("Vendors to Support This Week")
    st.write("These vendors may benefit from marketing or placement support:")
    st.dataframe(low_sales[["vendor_name", "sales"]])

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# OPERATIONS DASHBOARD
# ============================================================

st.markdown("<div class='wm-gold-card'>", unsafe_allow_html=True)
st.header("Operations Dashboard")

st.caption("Operational tracking of vendor performance, fees, and follow-up actions.")
st.dataframe(operations_df)

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# INSIGHTS
# ============================================================

st.markdown("<div class='wm-card'>", unsafe_allow_html=True)
st.header("Insights")

if not low_sales.empty:
    st.subheader("At-Risk Vendors")
    st.write("These vendors are performing below average and may need support:")
    st.dataframe(low_sales[["vendor_name", "sales"]])
else:
    st.success("No at-risk vendors right now.")

if "weather_descriptor" in market_data.columns:
    st.subheader("Weather Impact Insight")
    weather_summary = market_data.groupby("weather_descriptor")["attendance_total"].mean()
    st.write(weather_summary)
    st.caption("Insight: Compare attendance across weather conditions to guide programming and vendor mix.")

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DECISION LOOP: ATTENDANCE + PROGRAMMING INSIGHT
# ============================================================

st.markdown("<div class='wm-card'>", unsafe_allow_html=True)
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

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VENDOR ROLE INTELLIGENCE
# ============================================================

st.markdown("<div class='wm-gold-card'>", unsafe_allow_html=True)
st.header("Vendor Role Intelligence")

vendor_roles = {
    "Weekly Staples": [
        "Green Garden Farm", "Berry Patch Produce", "York River Vegetables",
        "Pure Earth Organics", "Sunny Side Eggs", "Heritage Hen Farm",
        "Colonial Bakes", "Daily Bread Co", "Hearthside Meats",
        "Old Dominion Sausage Co"
    ],
    "Traffic Drivers": [
        "Williamsburg Pickles", "Colonial Kettle Corn", "Williamsburg Coffee Co"
    ],
    "Seasonal Vendors": [
        "Williamsburg Pops", "Campus Crafts"
    ],
    "Rotating / Biweekly Vendors": [
        "Pasta Fresca"
    ],
    "Specialty Food Vendors": [
        "Artisan Cheese Co", "Salsa Verde Kitchen", "Spice Route Blends"
    ],
    "Pet & Home Vendors": [
        "Happy Tails Treats", "Goat Milk Soap Co"
    ],
}

role_rows = []

for role, vendors in vendor_roles.items():
    for vendor in vendors:
        role_rows.append({
            "vendor_role": role,
            "vendor_name": vendor
        })

role_df = pd.DataFrame(role_rows)

st.caption(
    "This translates the vendor schedule into operational strategy by identifying "
    "which vendors anchor the market, drive traffic, or add seasonal variety."
)

st.dataframe(role_df)

if "vendor_name" in vendor_data.columns:
    active_role_df = role_df.merge(
        vendor_data[["vendor_name"]].drop_duplicates(),
        on="vendor_name",
        how="inner"
    )

    st.subheader("Active Vendors by Role")
    st.dataframe(active_role_df)

    role_counts = active_role_df["vendor_role"].value_counts()
    st.bar_chart(role_counts)

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# WEATHER + PERFORMANCE ANALYSIS
# ============================================================

st.markdown("<div class='wm-card'>", unsafe_allow_html=True)
st.header("Weather + Performance Analysis")

st.caption(
    "This section analyzes how weather conditions impact both customer attendance "
    "and vendor sales performance."
)

if "weather" in market_data.columns:
    weather_summary = market_data.groupby("weather").agg({
        "attendance_total": "mean"
    }).reset_index()

    st.subheader("Attendance by Weather")
    st.dataframe(weather_summary)

    if "sales" in vendor_data.columns:
        vendor_weather = vendor_data.merge(
            market_data[["market_date", "weather"]],
            on="market_date",
            how="left"
        )

        sales_summary = vendor_weather.groupby("weather")["sales"].mean().reset_index()

        st.subheader("Average Sales by Weather")
        st.dataframe(sales_summary)

        if len(sales_summary) >= 2:
            best = sales_summary.sort_values("sales", ascending=False).iloc[0]
            worst = sales_summary.sort_values("sales").iloc[0]

            st.subheader("Insight")
            st.write(
                f"Hypothesis: {best['weather']} conditions drive higher vendor sales "
                f"(${best['sales']:.2f}) compared to {worst['weather']} "
                f"(${worst['sales']:.2f})."
            )

            st.write(
                "This insight can guide vendor mix, marketing, and programming decisions."
            )

else:
    st.info("Weather data not available yet.")

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MANAGER SUMMARY
# ============================================================

st.markdown("<div class='wm-gold-card'>", unsafe_allow_html=True)
st.header("Manager Summary")

summary_points = []

summary_points.append(f"Total recorded vendor sales are ${total_sales:,.2f}.")
summary_points.append(f"Estimated 6% market fees are ${estimated_fees:,.2f}.")
summary_points.append(f"Season-to-date attendance is {total_attendance:,.0f}.")

if not low_sales.empty:
    summary_points.append(
        f"{low_sales['vendor_name'].nunique()} vendor(s) may need sales or marketing support."
    )

if not open_followups.empty:
    summary_points.append(
        f"{len(open_followups)} vendor record(s) need follow-up."
    )
else:
    summary_points.append("All vendor records appear complete.")

st.markdown("### Executive Readout")

for point in summary_points:
    st.write(f"- {point}")

st.caption(
    "This summary is generated from the dashboard data and is designed to support "
    "quick manager decision-making."
)

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DATA TABLES
# ============================================================

with st.expander("Show Raw Vendor Data"):
    st.dataframe(vendor_data)

with st.expander("Show Raw Market Data"):
    st.dataframe(market_data)