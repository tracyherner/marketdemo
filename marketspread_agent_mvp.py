"""
Streamlit dashboard for the William & Mary Farmers Market.

This app loads market vendor and market-day data from CSV files, calculates
key KPIs, and displays a polished operations dashboard with role intelligence,
weather performance analysis, and a simple market assistant question box.

The goal is to keep the code readable and maintainable with comments next
to every major section, so future users understand what each part does.
"""

import streamlit as st
import pandas as pd

# ---------- PAGE CONFIGURATION ----------
PAGE_TITLE = "William & Mary Farmers Market Dashboard"
WM_GREEN = "#115740"
WM_GOLD = "#C99700"
SALES_FEE_RATE = 0.06  # The central fee rate used for follow-up and fee calculations.

# Configure the page layout and title for Streamlit.
st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# Apply custom CSS styling for cards, metrics, and the assistant response.
st.markdown(
    f"""
    <style>
    .main {{ background-color: #F7F4EA; }}
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; }}
    h1, h2, h3 {{ color: {WM_GREEN}; }}
    .dashboard-card {{ background-color: white; border-left: 6px solid {WM_GREEN}; padding: 20px; border-radius: 14px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    .dashboard-card.gold {{ border-left-color: {WM_GOLD}; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .metric-card {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px; }}
    .metric-label {{ color: #6b7280; font-size: 14px; margin-bottom: 6px; }}
    .metric-value {{ color: {WM_GREEN}; font-size: 28px; font-weight: 700; }}
    .note {{ color: #4b5563; }}
    .summary-list {{ margin: 0; padding-left: 20px; }}
    .summary-list li {{ margin-bottom: 8px; }}
    .agent-answer {{ background: #f9fafb; border-left: 4px solid {WM_GOLD}; padding: 14px; border-radius: 10px; margin-top: 14px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Top title card with a short explanation of the dashboard.
st.markdown(
    f"<div class='dashboard-card'><h1>{PAGE_TITLE}</h1><p class='note'>A polished market operations dashboard for vendor follow-up, fee tracking, and attendance analysis.</p></div>",
    unsafe_allow_html=True,
)

# ---------- DATA LOADING ----------
try:
    # Load the vendor-level and market-level CSV data used throughout the dashboard.
    vendor_data = pd.read_csv("marketspread_vendor_data.csv")
    market_data = pd.read_csv("marketspread_market_day_data.csv")
except FileNotFoundError as exc:
    # If the CSV files are missing, show an error and stop the app.
    st.error(f"Missing data file: {exc.filename}")
    st.stop()

# ---------- CORE CALCULATIONS ----------
# Convert boolean-like columns to integers for consistent filtering.
vendor_data["sales_reported"] = vendor_data["sales_reported"].astype(int)
vendor_data["attended"] = vendor_data["attended"].astype(int)

# Total season sales from the vendor dataset.
total_sales = vendor_data["sales"].sum()

# Estimated vendor fees based on the 6% fee rule.
estimated_fees = total_sales * SALES_FEE_RATE

# Total attendance from the market-day dataset.
total_attendance = market_data["attendance_total"].sum()

# Number of unique vendors represented in the dataset.
vendor_count = vendor_data["vendor_name"].nunique()

# Vendors whose sales fall below the dataset average.
low_sales = vendor_data[vendor_data["sales"] < vendor_data["sales"].mean()]

# Vendors that need follow-up because they either did not report sales or have unpaid fees.
open_followups = vendor_data[
    (vendor_data["sales_reported"] == 0)
    | (vendor_data["paid_amount"] < vendor_data["sales"] * SALES_FEE_RATE)
]

# ---------- QUICK METRICS ----------
# Render the main summary cards for the season.
st.markdown("<div class='dashboard-card'><h2>Quick Metrics</h2>", unsafe_allow_html=True)
st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
for label, value in [
    ("Total Vendor Sales", f"${total_sales:,.2f}"),
    ("Estimated 6% Market Fees", f"${estimated_fees:,.2f}"),
    ("Season-to-Date Attendance", f"{total_attendance:,.0f}"),
    ("Unique Vendors", str(vendor_count)),
    ("Underperforming Vendors", str(low_sales["vendor_name"].nunique())),
    ("Open Follow-Ups", str(len(open_followups))),
]:
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )
st.markdown("</div></div>", unsafe_allow_html=True)

# ---------- MARKET ASSISTANT ----------
# Simple keyword-based assistant for common market questions.
question = st.text_input("Ask a question about your market data:")
if question:
    q = question.lower()
    answer = None

    if any(term in q for term in ["past due", "follow up", "follow-up", "need action"]):
        # If there are open follow-up cases, list the vendor names.
        if not open_followups.empty:
            names = ", ".join(sorted(open_followups["vendor_name"].dropna().unique()))
            answer = (
                f"There are {open_followups['vendor_name'].nunique()} vendor(s) needing follow-up: {names}. "
                "This includes missing reports or unpaid fees."
            )
        else:
            answer = "No vendors are currently past due. All records look complete."

    elif any(term in q for term in ["at risk", "underperform", "below target"]):
        # If vendors are underperforming relative to average sales, list them.
        if not low_sales.empty:
            names = ", ".join(sorted(low_sales["vendor_name"].dropna().unique()))
            answer = f"These vendors may need support: {names}."
        else:
            answer = "No vendors are currently underperforming."

    elif "sales" in q:
        answer = f"Total recorded sales are ${total_sales:,.2f}."

    elif "attendance" in q:
        answer = f"Total estimated attendance is {total_attendance:,.0f}."

    elif "vendor" in q or "vendors" in q:
        answer = f"There are {vendor_count} unique vendors in the dataset."

    else:
        answer = "Try asking about past due vendors, at-risk vendors, sales, attendance, or vendor count."

    # Show the assistant response in a highlighted panel.
    st.markdown(f"<div class='agent-answer'>{answer}</div>", unsafe_allow_html=True)

# ---------- VENDOR ROLE INTELLIGENCE ----------
# Show how vendors are grouped by their operational role.
st.markdown("<div class='dashboard-card gold'><h2>Vendor Role Intelligence</h2>", unsafe_allow_html=True)
vendor_roles = {
    "Weekly Staples": [
        "Green Garden Farm", "Berry Patch Produce", "York River Vegetables",
        "Pure Earth Organics", "Sunny Side Eggs", "Heritage Hen Farm",
        "Colonial Bakes", "Daily Bread Co", "Hearthside Meats",
        "Old Dominion Sausage Co",
    ],
    "Traffic Drivers": [
        "Williamsburg Pickles", "Colonial Kettle Corn", "Williamsburg Coffee Co",
    ],
    "Seasonal Vendors": ["Williamsburg Pops", "Campus Crafts"],
    "Rotating / Biweekly Vendors": ["Pasta Fresca"],
    "Specialty Food Vendors": ["Artisan Cheese Co", "Salsa Verde Kitchen", "Spice Route Blends"],
    "Pet & Home Vendors": ["Happy Tails Treats", "Goat Milk Soap Co"],
}
role_rows = []
for role, vendors in vendor_roles.items():
    for vendor in vendors:
        # Add one row per vendor for the table display.
        role_rows.append({"Role": role, "Vendor": vendor})
role_df = pd.DataFrame(role_rows)
st.dataframe(role_df)
st.markdown("</div>", unsafe_allow_html=True)

# ---------- WEATHER + PERFORMANCE ANALYSIS ----------
# Compare attendance and sales across weather conditions.
st.markdown("<div class='dashboard-card'><h2>Weather + Performance Analysis</h2>", unsafe_allow_html=True)
if "weather_descriptor" in market_data.columns:
    # Average attendance by weather condition.
    weather_summary = market_data.groupby("weather_descriptor")["attendance_total"].mean().reset_index()
    st.subheader("Attendance by Weather")
    st.dataframe(weather_summary)

    if "sales" in vendor_data.columns:
        # Merge vendor sales with weather details from market data.
        vendor_weather = vendor_data.merge(
            market_data[["market_date", "weather_descriptor"]],
            on="market_date",
            how="left",
        )
        sales_summary = vendor_weather.groupby("weather_descriptor")["sales"].mean().reset_index()
        st.subheader("Average Sales by Weather")
        st.dataframe(sales_summary)

        if len(sales_summary) >= 2:
            # Show a simple observation about the best and worst weather types.
            best = sales_summary.sort_values("sales", ascending=False).iloc[0]
            worst = sales_summary.sort_values("sales", ascending=True).iloc[0]
            st.write(
                f"Hypothesis: {best['weather_descriptor']} conditions drive higher vendor sales ($"
                f"{best['sales']:.2f}) than {worst['weather_descriptor']} ($"
                f"{worst['sales']:.2f})."
            )
else:
    # If weather data is not available, show an info message.
    st.info("Weather data is not available in the current market dataset.")
st.markdown("</div>", unsafe_allow_html=True)

# ---------- MANAGER SUMMARY ----------
# Create a concise, manager-friendly readout of the dashboard findings.
st.markdown("<div class='dashboard-card gold'><h2>Manager Summary</h2>", unsafe_allow_html=True)
summary_points = [
    f"Total recorded vendor sales are ${total_sales:,.2f}.",
    f"Estimated 6% market fees are ${estimated_fees:,.2f}.",
    f"Season-to-date attendance is {total_attendance:,.0f}.",
]
if not low_sales.empty:
    summary_points.append(
        f"{low_sales['vendor_name'].nunique()} vendor(s) may need sales or marketing support."
    )
if not open_followups.empty:
    summary_points.append(f"{len(open_followups)} vendor record(s) need follow-up.")
else:
    summary_points.append("All vendor records appear complete.")

st.markdown("<ul class='summary-list'>", unsafe_allow_html=True)
for point in summary_points:
    st.markdown(f"<li>{point}</li>", unsafe_allow_html=True)
st.markdown("</ul>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------- RAW DATA ----------
# Allow users to expand and inspect the raw input files.
with st.expander("Show Raw Vendor Data"):
    st.dataframe(vendor_data)
with st.expander("Show Raw Market Data"):
    st.dataframe(market_data)
