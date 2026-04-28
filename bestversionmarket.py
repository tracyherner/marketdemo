from __future__ import annotations  # Allows cleaner type hints inside the file.

# ============================================================
# WILLIAM & MARY FARMERS MARKET DASHBOARD
# FULL DEMO VERSION WITH COMMENTS
# ============================================================
# PURPOSE:
# This local dashboard demonstrates how agentic AI can replace or improve
# a fragile spreadsheet process for farmers market operations.
#
# CORE DEMO STORY:
# 1. We replaced a multi-spreadsheet process with a structured operations dashboard.
# 2. Vendor names and categories are controlled through an approved vendor list.
# 3. Vendor sales, token reimbursements, payments, attendance, and reporting status are tracked by market date.
# 4. The 6% vendor fee, net token reimbursement, balance due, and paid status are calculated automatically.
# 5. A separate market-day context layer tracks weather, customer counts, programming, community events, and nonprofit tabling.
# 6. Customer traffic is estimated from four timed counts using the validated 2.43 market multiplier.
# 7. The dashboard compares weather, attendance, programming, and sales to support hypothesis-driven decisions.
# 8. The system identifies missing reports, unpaid fees, underperforming vendors, and follow-up actions.
# 9. A constrained built-in agent answers approved market questions only after running a math audit.
# 10. The system drafts follow-up messages and supports CSV download for transparency.
#
# CHECKS AND BALANCES BUILT INTO THE SYSTEM:
# - Approved vendor dropdown prevents misspelled vendor names.
# - Vendor category is assigned from the approved list, not typed manually.
# - Total sales are calculated, not manually entered.
# - Token reimbursements are included consistently in total sales.
# - Vendor fee is always calculated from the 6% rule in one central place.
# - Balance due is calculated from fee due minus payment received.
# - Paid status is calculated from the balance logic, not manually trusted.
# - Customer counts are estimated using the validated 2.43 market multiplier.
# - The agent runs a math audit before answering questions.
# - Data exports are available through CSV download for transparency.
# ============================================================

# ---------- IMPORTS ----------
# These are all standard Python libraries. No extra packages are required.

import argparse  # Lets us run this file with --serve from the terminal.
import csv  # Reads and writes CSV data, similar to a spreadsheet export.
import html  # Escapes text so user input does not break the webpage.
import json  # Reads Weather.gov API responses.
import urllib.request  # Calls Weather.gov without needing extra packages.
from datetime import date, timedelta  # Used to build weekly Saturday schedule ranges.
from collections import Counter, defaultdict  # Helps count categories and group vendor records.
from dataclasses import dataclass  # Creates a simple structured data object for each vendor record.
from http import HTTPStatus  # Provides readable HTTP response codes.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # Built-in local web server.
from pathlib import Path  # Handles file paths cleanly.
from urllib.parse import parse_qs, quote_plus, urlparse  # Parses form data and URL query strings.

# ---------- CONFIGURATION ----------
# Added schedule file to track expected vendors (planned attendance)
SCHEDULE_FILE = Path("vendor_schedule.csv")  # NEW: holds who is scheduled each market date
MARKET_DAY_FILE = Path("market_day_context.csv")  # NEW: holds date-level market context like events, nonprofits, weather, and attendance
APPROVED_VENDOR_FILE = Path("approved_vendors.csv")  # NEW: lets the dashboard admin update approved vendors without editing code
# These are the main settings for the demo.
# Keeping them here makes the code easier to modify later.

VENDOR_DATA_FILE = Path("wm_farmers_market_demo.csv")  # Local CSV file used as the demo database.
DEFAULT_HOST = "127.0.0.1"  # Localhost address for the dashboard.
DEFAULT_PORT = 8000  # Browser port. The dashboard opens at http://127.0.0.1:8000.
SALES_FEE_RATE = 0.06  # CHECK: one central fee rate prevents inconsistent manual fee calculations.
CUSTOMER_MULTIPLIER = 2.43  # CHECK: validated attendance multiplier applied consistently to all customer counts.
WM_GREEN = "#115740"  # William & Mary green.
WM_GOLD = "#C99700"  # William & Mary gold.
WEATHER_ZIP = "23185"  # Williamsburg test ZIP code for the class demo.
WEATHER_LAT = 37.2707  # Approximate latitude for Williamsburg, VA / ZIP 23185.
WEATHER_LON = -76.7075  # Approximate longitude for Williamsburg, VA / ZIP 23185.

# CSV columns. These are the fields saved to and loaded from the local CSV.
VENDOR_FIELDNAMES = [
    "market_date",
    "vendor_name",
    "category",
    "reported_sales",
    "token_reimbursement",
    "sales_reported",
    "paid_amount",
    "attended",
    "weather",
    "count_830",
    "count_930",
    "count_1030",
    "count_1130",
]

# Market-day context columns.
# WHY: These are date-level details, so they belong in a separate sheet/table from vendor sales.
MARKET_DAY_FIELDNAMES = [
    "market_date",
    "weather",
    "count_830",
    "count_930",
    "count_1030",
    "count_1130",
    "music_event",
    "chefs_tent",
    "childrens_programming",
    "community_events",
    "nonprofit_orgs",
]

# Approved vendor columns.
# WHY: This powers the admin-managed approved vendor list.
APPROVED_VENDOR_FIELDNAMES = ["vendor_name", "category"]

# Approved vendor list.
# WHY: A dropdown prevents typos like "Colonial Bakes" vs. "Colonial Bakery".
# In production, this could come from Marketspread, an application system, Airtable, or a CRM.
# Average sales benchmarks (used for demo insights)
# WHY: gives context for what "good" performance looks like
AVERAGE_VENDOR_SALES = {
    "Pure Earth Organics": 4000.00,  # Organic produce benchmark per market
    "Regular Produce": 2500.00,  # Standard produce benchmark per market
}

# Category-level minimum expectations
# WHY: gives quick rule-of-thumb performance thresholds
CATEGORY_MINIMUMS = {
    "Baked Goods": 1000.00,
    "Prepared Foods": 1000.00,
}

# CHECK: This is the official vendor/category source of truth.
# The form uses this list as a dropdown, and the backend validates against it again.
# That means a typo or unauthorized vendor name cannot silently create bad data.
DEFAULT_APPROVED_VENDORS = {
    "Green Garden Farm": "Produce",
    "Berry Patch Produce": "Produce",
    "York River Vegetables": "Produce",
    "Pure Earth Organics": "Produce",  # NEW: Organic produce vendor
    "Colonial Bakes": "Baked Goods",
    "River City Tacos": "Prepared Foods",
    "Hearthside Meats": "Meat",
    "Campus Crafts": "Other",
    "Williamsburg Pickles": "Prepared Foods",  # NEW: Pickle vendor
    "Jamestown Jams": "Prepared Foods",  # UPDATED: Jam is prepared food (more accurate classification)
    "Daily Bread Co": "Baked Goods",  # NEW: Bread-only vendor (weekly staple)
    "Williamsburg Pops": "Prepared Foods",  # NEW: Popsicle vendor (summer)
    "Colonial Kettle Corn": "Prepared Foods",  # NEW: Kettle corn vendor
    "Pasta Fresca": "Prepared Foods",  # NEW: Pasta vendor (explicit, instead of tacos placeholder)
    "Artisan Cheese Co": "Prepared Foods",  # NEW: Cheese vendor
    "Sweet Crumb Cookies": "Baked Goods",  # NEW: Cookie vendor
    "Salsa Verde Kitchen": "Prepared Foods",  # NEW: Salsa vendor
    "Spice Route Blends": "Other",  # NEW: Spice vendor
    "Williamsburg Coffee Co": "Prepared Foods",  # NEW: Coffee vendor (hot & cold drinks)
    "Happy Tails Treats": "Other",  # NEW: Dog treat vendor
    "Goat Milk Soap Co": "Other",  # NEW: Goat milk soap vendor
    "Sunny Side Eggs": "Produce",  # NEW: Egg vendor 1
    "Heritage Hen Farm": "Produce",  # NEW: Egg vendor 2
    "Old Dominion Sausage Co": "Meat",  # NEW: Sausage vendor
}

# Runtime approved vendor list.
# CHECK: This starts with the default vendor list and can be updated by the Admin section.
APPROVED_VENDORS = dict(DEFAULT_APPROVED_VENDORS)

# Topics the built-in agent is allowed to discuss.
# WHY: This keeps the agent constrained to approved dashboard topics.
APPROVED_AGENT_TOPICS = [
    "vendor attendance",
    "weather",
    "sales reporting",
    "payments",
    "tokens",
    "vendor categories",
    "marketing mix",
    "total sales",
    "vendor roles",
    "traffic drivers",
    "staple vendors",
]


# ---------- MARKET DAY CONTEXT MODEL ----------
# This stores one row per market day.
# WHY: Attendance, weather, events, and nonprofit tabling apply to the whole market date,
# not to one specific vendor.

@dataclass
class MarketDayContext:
    market_date: str
    weather: str = "Not recorded"
    count_830: int = 0
    count_930: int = 0
    count_1030: int = 0
    count_1130: int = 0
    music_event: str = ""
    chefs_tent: str = ""
    childrens_programming: str = ""
    community_events: str = ""
    nonprofit_orgs: str = ""

    @property
    def estimated_customers(self) -> int:
        # CHECK: Customer estimates are calculated from timed counts, not guessed.
        # The function ignores blank/zero counts and applies the validated 2.43 multiplier.
        counts = [self.count_830, self.count_930, self.count_1030, self.count_1130]
        valid = [c for c in counts if c > 0]
        if not valid:
            return 0
        avg = sum(valid) / len(valid)
        return int(avg * CUSTOMER_MULTIPLIER)

    def to_row(self) -> dict[str, str]:
        return {
            "market_date": self.market_date,
            "weather": self.weather,
            "count_830": str(self.count_830),
            "count_930": str(self.count_930),
            "count_1030": str(self.count_1030),
            "count_1130": str(self.count_1130),
            "music_event": self.music_event,
            "chefs_tent": self.chefs_tent,
            "childrens_programming": self.childrens_programming,
            "community_events": self.community_events,
            "nonprofit_orgs": self.nonprofit_orgs,
        }


# ---------- DATA MODEL ----------
# VendorRecord represents one vendor for one market date.
# This is the structured replacement for a spreadsheet row.

@dataclass
class VendorRecord:
    market_date: str
    vendor_name: str
    category: str
    reported_sales: float = 0.0
    token_reimbursement: float = 0.0
    sales_reported: bool = False
    paid_amount: float = 0.0
    attended: bool = True
    weather: str = "Not recorded"
    count_830: int = 0
    count_930: int = 0
    count_1030: int = 0
    count_1130: int = 0

    @property
    def sales(self) -> float:
        # CHECK: Total sales are calculated from self-reported sales + token reimbursements.
        # This prevents someone from manually entering a total that does not reconcile.
        return round(self.reported_sales + self.token_reimbursement, 2)

    @property
    def token_net(self) -> float:
        # CHECK: Token reimbursement is netted after the 6% fee using the same central fee rate.
        # This prevents inconsistent token reimbursement math.
        return round(self.token_reimbursement * (1 - SALES_FEE_RATE), 2)

    @property
    def fee_due(self) -> float:
        # CHECK: Fee due is calculated automatically from total sales x 6%.
        # If sales are not reported, the fee stays at $0 because there is no verified sales basis.
        if not self.sales_reported:
            return 0.0
        return round(self.sales * SALES_FEE_RATE, 2)

    @property
    def paid(self) -> bool:
        # CHECK: Paid status is calculated from payment amount compared with fee due.
        # The user does not manually decide whether a vendor is paid.
        return self.sales_reported and self.paid_amount >= self.fee_due

    @property
    def balance_due(self) -> float:
        # CHECK: Balance due is calculated from fee due minus payment received.
        # max(..., 0) prevents negative balances from showing as money owed.
        if not self.sales_reported:
            return 0.0
        return round(max(self.fee_due - self.paid_amount, 0.0), 2)

    @property
    def is_underperforming(self) -> bool:
        """Check if vendor is below category expectations.

        WHY: helps identify vendors to support with marketing.
        """
        minimum = CATEGORY_MINIMUMS.get(self.category)
        if minimum is None:
            return False
        return self.sales < minimum

    @property
    def action_needed(self) -> str:
        # CHECK: Action Needed follows a fixed decision tree.
        # Missing sales is checked before payment because payment cannot be verified without reported sales.
        if not self.sales_reported:
            return "Send sales reminder"
        if not self.paid:
            return "Send payment reminder"
        return "Complete"

    def to_row(self) -> dict[str, str]:
        """Convert the record to a CSV row.

        WHY: CSV files store values as text, so this formats each value safely.
        """
        return {
            "market_date": self.market_date,
            "vendor_name": self.vendor_name,
            "category": self.category,
            "reported_sales": f"{self.reported_sales:.2f}",
            "token_reimbursement": f"{self.token_reimbursement:.2f}",
            "sales_reported": "1" if self.sales_reported else "0",
            "paid_amount": f"{self.paid_amount:.2f}",
            "attended": "1" if self.attended else "0",
            "weather": self.weather,
            "count_830": str(self.count_830),
            "count_930": str(self.count_930),
            "count_1030": str(self.count_1030),
            "count_1130": str(self.count_1130),
        }


# ---------- HELPER FUNCTIONS ----------

def parse_float(value: object, default: float = 0.0) -> float:
    """Safely convert user or CSV input into a float.

    CHECK: Bad or blank numeric input becomes 0 instead of crashing the dashboard.
    """
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def parse_bool(value: object) -> bool:
    """Safely convert text values into True/False.

    CHECK: Normalizes yes/no, true/false, and checkbox-style values consistently.
    """
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def estimate_customers(record: VendorRecord) -> int:
    # CHECK: Uses the same calculation every time customer traffic is estimated.
    # Formula: average valid timed counts x CUSTOMER_MULTIPLIER.
    counts = [record.count_830, record.count_930, record.count_1030, record.count_1130]
    valid = [c for c in counts if c > 0]
    if not valid:
        return 0
    avg = sum(valid) / len(valid)
    return int(avg * CUSTOMER_MULTIPLIER)


def normalize_vendor_key(vendor_name: str) -> str:
    """Normalize vendor names for grouping.

    WHY: Prevents extra spaces or capitalization from creating duplicate emails.
    """
    return " ".join(vendor_name.lower().split())


def build_vendor_dropdown_options() -> str:
    """Build dropdown options from the approved vendor list."""
    refresh_approved_vendors()
    options = ['<option value="">Select approved vendor</option>']
    for vendor_name in sorted(APPROVED_VENDORS):
        safe_name = html.escape(vendor_name)
        options.append(f'<option value="{safe_name}">{safe_name}</option>')
    return "".join(options)


# ---------- APPROVED VENDOR ADMIN STORAGE ----------

def save_approved_vendors(file_path: Path = APPROVED_VENDOR_FILE) -> None:
    """Save the approved vendor list to CSV.

    WHY: This lets approved vendor changes survive after the server restarts.
    """
    with file_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=APPROVED_VENDOR_FIELDNAMES)
        writer.writeheader()
        for vendor_name, category in sorted(APPROVED_VENDORS.items()):
            writer.writerow({"vendor_name": vendor_name, "category": category})


def load_approved_vendors(file_path: Path = APPROVED_VENDOR_FILE) -> dict[str, str]:
    """Load approved vendors from CSV, falling back to the starter list.

    CHECK: If the CSV is missing or incomplete, the dashboard still has the starter vendor list.
    """
    vendors = dict(DEFAULT_APPROVED_VENDORS)
    if not file_path.exists():
        return vendors

    with file_path.open("r", newline="", encoding="utf-8") as file_handle:
        for row in csv.DictReader(file_handle):
            vendor_name = row.get("vendor_name", "").strip()
            category = row.get("category", "").strip()
            if vendor_name and category:
                vendors[vendor_name] = category
    return vendors


def refresh_approved_vendors() -> None:
    """Refresh the in-memory approved vendor list from CSV.

    WHY: The admin form can update the CSV while the server is running.
    Refreshing before display/validation keeps dropdowns and backend checks aligned.
    """
    APPROVED_VENDORS.clear()
    APPROVED_VENDORS.update(load_approved_vendors())


def build_category_options(selected_category: str = "Produce") -> str:
    """Build category dropdown options for the admin form."""
    categories = ["Produce", "Baked Goods", "Prepared Foods", "Meat", "Other"]
    options = []
    for category in categories:
        selected = "selected" if category == selected_category else ""
        options.append(f"<option value='{html.escape(category)}' {selected}>{html.escape(category)}</option>")
    return "".join(options)


def agent_scope_message() -> str:
    """Default message for questions outside the allowed scope."""
    topics = ", ".join(APPROVED_AGENT_TOPICS)
    return (
        "I can only answer questions about approved market dashboard topics. "
        f"Approved topics include: {topics}. "
        "Try asking: How many vendors are past due? What does attendance look like? "
        "How much token reimbursement do we owe?"
    )


# ---------- SCHEDULE DATA (EXPECTED VENDORS) ----------

def load_schedule(file_path: Path = SCHEDULE_FILE) -> dict[str, list[str]]:
    """Load vendor schedule by date.

    WHY: lets us compare who SHOULD be there vs who actually reported.
    CHECK: Schedule data is kept separate from sales data so planned attendance is not confused with reporting/payment records.
    CSV format expected:
    market_date,vendor_name
    """
    schedule: dict[str, list[str]] = defaultdict(list)
    if not file_path.exists():
        return schedule

    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_value = row.get("market_date", "").strip()
            vendor = row.get("vendor_name", "").strip()
            if date_value and vendor:
                schedule[date_value].append(vendor)

    return schedule


def saturday_dates(start_date: date, end_date: date) -> list[date]:
    """Return every Saturday between two dates, inclusive.

    WHY: the market schedule is weekly, so this creates the recurring market dates.
    """
    current = start_date
    dates: list[date] = []
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def last_saturday_in_september(year: int) -> date:
    """Find the last Saturday in September for the given year."""
    current = date(year, 9, 30)
    while current.weekday() != 5:  # Monday = 0, Saturday = 5
        current -= timedelta(days=1)
    return current


def create_sample_schedule(file_path: Path = SCHEDULE_FILE) -> None:
    """Create a sample season schedule CSV.

    WHY: demonstrates how a real market could upload the season vendor schedule once,
    then use it throughout the dashboard and agent.
    """
    produce_rotation = ["Green Garden Farm", "Berry Patch Produce", "York River Vegetables", "Pure Earth Organics", "Sunny Side Eggs", "Heritage Hen Farm"]
    every_market_vendors = ["Colonial Bakes", "Daily Bread Co"]  # Baked goods staples every market (incl. bread-only vendor)
    biweekly_vendors = ["Pasta Fresca"]  # Pasta vendor comes every other week.
    monthly_summer_vendors = ["Campus Crafts"]  # Chocolate vendor comes once a month in summer.
    weekly_specialty_vendors = ["Williamsburg Pickles", "Colonial Kettle Corn", "Salsa Verde Kitchen", "Williamsburg Coffee Co", "Happy Tails Treats"]  # add dog treats weekly  # Pickles + kettle corn weekly crowd draws
    summer_weekly_vendors = ["Williamsburg Pops"]  # Popsicles every week in summer months
    monthly_vendors = ["Jamestown Jams", "Sweet Crumb Cookies", "Spice Route Blends", "Goat Milk Soap Co"]  # soap vendor monthly  # Jam vendor once per month
    other_vendors = ["Hearthside Meats", "Old Dominion Sausage Co"]
    start_date = date(2026, 4, 11)
    end_date = last_saturday_in_september(2026)

    with file_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=["market_date", "vendor_name"])
        writer.writeheader()
        for i, market_date in enumerate(saturday_dates(start_date, end_date)):
            # Produce vendors every week
            for vendor_name in produce_rotation:
                writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Every market vendors (baked goods)
            for vendor_name in every_market_vendors:
                writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Biweekly vendors (every other week)
            if i % 2 == 0:
                for vendor_name in biweekly_vendors:
                    writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Monthly summer vendors (June–August, first Saturday of each month)
            if market_date.month in [6, 7, 8] and market_date.day <= 7:
                for vendor_name in monthly_summer_vendors:
                    writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Summer weekly vendors (popsicles every summer market)
            if market_date.month in [6, 7, 8]:
                for vendor_name in summer_weekly_vendors:
                    writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Weekly specialty vendors (pickles + kettle corn)
            for vendor_name in weekly_specialty_vendors:
                writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Monthly vendors (jam - first Saturday of each month)
            if market_date.day <= 7:
                for vendor_name in monthly_vendors:
                    writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})

            # Other weekly vendors
            for vendor_name in other_vendors:
                writer.writerow({"market_date": market_date.isoformat(), "vendor_name": vendor_name})


# ---------- VENDOR ROLE INTELLIGENCE ----------

VENDOR_ROLE_RULES = {
    "Weekly Staples": ["Green Garden Farm", "Berry Patch Produce", "York River Vegetables", "Pure Earth Organics", "Sunny Side Eggs", "Heritage Hen Farm", "Colonial Bakes", "Daily Bread Co", "Hearthside Meats", "Old Dominion Sausage Co"],
    "Traffic Drivers": ["Williamsburg Pickles", "Colonial Kettle Corn", "Williamsburg Coffee Co"],
    "Seasonal Vendors": ["Williamsburg Pops", "Campus Crafts"],
    "Monthly Specialty Vendors": ["Jamestown Jams"],
    "Rotating / Biweekly Vendors": ["Pasta Fresca"],
    "Specialty Food Vendors": ["Artisan Cheese Co", "Salsa Verde Kitchen", "Spice Route Blends"],
    "Pet & Home Vendors": ["Happy Tails Treats", "Goat Milk Soap Co"],
    "Dessert & Treat Vendors": ["Sweet Crumb Cookies"],
}


def vendor_role_for(vendor_name: str) -> str:
    """Return the operational role assigned to a vendor.

    WHY: The manager thinks about vendors by role, not just category.
    Staples create consistency; traffic drivers create excitement; seasonal vendors support weather-driven demand.
    """
    for role, vendors in VENDOR_ROLE_RULES.items():
        if vendor_name in vendors:
            return role
    return "Other Vendors"


def build_vendor_roles_view() -> str:
    """Build a simple table explaining vendor roles.

    WHY: This helps turn the schedule into marketing and operations strategy.
    """
    descriptions = {
        "Traffic Drivers": "Vendors that draw consistent foot traffic, especially beverages, snacks, and high-frequency purchases.",
        "Weekly Staples": "Reliable weekly vendors that anchor the market experience.",
        "Traffic Drivers": "Vendors that can pull shoppers in because they are fun, snackable, or highly recognizable.",
        "Seasonal Vendors": "Vendors whose value changes by season, weather, or summer foot traffic.",
        "Monthly Specialty Vendors": "Vendors that add variety without needing weekly space.",
        "Rotating / Biweekly Vendors": "Vendors scheduled less frequently to balance variety and table capacity.",
    }
    rows = []
    for role, vendors in VENDOR_ROLE_RULES.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(role)}</td>"
            f"<td>{html.escape(', '.join(vendors))}</td>"
            f"<td>{html.escape(descriptions.get(role, ''))}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table>"
        "<thead><tr><th>Vendor Role</th><th>Vendors</th><th>Why It Matters</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


# ---------- WEATHER.GOV DATA ----------

def fetch_weather_from_weather_gov() -> dict[str, str]:
    """Fetch a simple forecast from Weather.gov for ZIP 23185.

    WHY: Weather can affect attendance and sales, so this brings external context
    into the dashboard without requiring vendors to enter it manually.

    NOTE: Weather.gov does not use ZIP codes directly in this simple endpoint,
    so the demo uses approximate Williamsburg coordinates for ZIP 23185.
    """
    fallback = {
        "source": "CSV fallback",
        "zip": WEATHER_ZIP,
        "temperature": "Not available",
        "descriptor": "Weather.gov unavailable; using stored market weather if available.",
        "forecast_date": date.today().isoformat(),
    }

    try:
        points_url = f"https://api.weather.gov/points/{WEATHER_LAT},{WEATHER_LON}"
        request = urllib.request.Request(points_url, headers={"User-Agent": "wm-farmers-market-demo/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            points_data = json.loads(response.read().decode("utf-8"))

        forecast_url = points_data["properties"]["forecast"]
        request = urllib.request.Request(forecast_url, headers={"User-Agent": "wm-farmers-market-demo/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            forecast_data = json.loads(response.read().decode("utf-8"))

        period = forecast_data["properties"]["periods"][0]
        return {
            "source": "Weather.gov",
            "zip": WEATHER_ZIP,
            "temperature": f"{period.get('temperature', 'N/A')}°{period.get('temperatureUnit', 'F')}",
            "descriptor": period.get("shortForecast", "Forecast unavailable"),
            "forecast_date": str(period.get("startTime", date.today().isoformat()))[:10],
        }
    except Exception:
        return fallback


def build_weather_card(records: list[VendorRecord]) -> str:
    """Build the weather section for the dashboard.

    WHY: Managers and vendors often compare sales and attendance against weather.
    """
    weather = fetch_weather_from_weather_gov()
    stored_weather_counts = Counter(record.weather for record in records if record.weather and record.weather != "Not recorded")
    stored_text = ", ".join(f"{label}: {count}" for label, count in stored_weather_counts.items()) or "No stored market weather yet."
    return f"""
    <div class="season-grid">
      <div class="season-stat"><div class="kpi-label">Forecast Date</div><div class="kpi-value">{html.escape(weather['forecast_date'])}</div></div>
      <div class="season-stat"><div class="kpi-label">ZIP Code</div><div class="kpi-value">{html.escape(weather['zip'])}</div></div>
      <div class="season-stat"><div class="kpi-label">Temperature</div><div class="kpi-value">{html.escape(weather['temperature'])}</div></div>
      <div class="season-stat"><div class="kpi-label">Forecast</div><div class="kpi-value">{html.escape(weather['descriptor'])}</div></div>
      <div class="season-stat"><div class="kpi-label">Source</div><div class="kpi-value">{html.escape(weather['source'])}</div></div>
    </div>
    <p class="note">Stored market weather in the CSV: {html.escape(stored_text)}</p>
    """


# ---------- MARKET DAY CONTEXT STORAGE ----------

def row_to_market_day(row: dict[str, str]) -> MarketDayContext:
    return MarketDayContext(
        market_date=row.get("market_date", "2026-04-05").strip() or "2026-04-05",
        weather=row.get("weather", "Not recorded").strip() or "Not recorded",
        count_830=int(row.get("count_830", 0) or 0),
        count_930=int(row.get("count_930", 0) or 0),
        count_1030=int(row.get("count_1030", 0) or 0),
        count_1130=int(row.get("count_1130", 0) or 0),
        music_event=row.get("music_event", "").strip(),
        chefs_tent=row.get("chefs_tent", "").strip(),
        childrens_programming=row.get("childrens_programming", "").strip(),
        community_events=row.get("community_events", "").strip(),
        nonprofit_orgs=row.get("nonprofit_orgs", "").strip(),
    )


def load_market_day_context(file_path: Path = MARKET_DAY_FILE) -> list[MarketDayContext]:
    if not file_path.exists():
        return []
    with file_path.open("r", newline="", encoding="utf-8") as file_handle:
        return [row_to_market_day(row) for row in csv.DictReader(file_handle)]


def save_market_day_context(records: list[MarketDayContext], file_path: Path = MARKET_DAY_FILE) -> None:
    with file_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=MARKET_DAY_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())


def sample_market_day_context() -> list[MarketDayContext]:
    return [
        MarketDayContext("2026-04-05", "Sunny", 90, 120, 150, 130, "Bluegrass Duo", "Chef demo: seasonal greens", "Seed planting table", "Second Sundays Art Festival", "Habitat for Humanity"),
        MarketDayContext("2026-04-12", "Cloudy", 80, 105, 125, 115, "Student jazz trio", "Chef demo: pasta primavera", "Kids craft table", "5K downtown race", "Williamsburg House of Mercy"),
        MarketDayContext("2026-04-19", "Rainy", 45, 60, 70, 55, "No music", "Chef tent cancelled", "Indoor coloring sheets", "Colonial event weekend", "FISH Williamsburg"),
    ]


def upsert_market_day_context(records: list[MarketDayContext], new_record: MarketDayContext) -> list[MarketDayContext]:
    result = []
    updated = False
    for record in records:
        if record.market_date == new_record.market_date:
            result.append(new_record)
            updated = True
        else:
            result.append(record)
    if not updated:
        result.append(new_record)
    return result


# ---------- CSV DATA STORAGE ----------

def row_to_vendor(row: dict[str, str]) -> VendorRecord:
    """Convert a CSV row into a VendorRecord.

    CHECK: Every imported CSV row is parsed through the same conversion rules.
    This protects against text numbers, blank fields, and inconsistent yes/no values.
    """
    return VendorRecord(
        market_date=row.get("market_date", "2026-04-05").strip() or "2026-04-05",
        vendor_name=row.get("vendor_name", "").strip(),
        category=row.get("category", "Other").strip() or "Other",
        reported_sales=parse_float(row.get("reported_sales", row.get("sales", 0.0))),
        token_reimbursement=parse_float(row.get("token_reimbursement", 0.0)),
        sales_reported=parse_bool(row.get("sales_reported", False)),
        paid_amount=parse_float(row.get("paid_amount", 0.0)),
        attended=parse_bool(row.get("attended", True)),
        weather=row.get("weather", "Not recorded").strip() or "Not recorded",
        count_830=int(row.get("count_830", 0) or 0),
        count_930=int(row.get("count_930", 0) or 0),
        count_1030=int(row.get("count_1030", 0) or 0),
        count_1130=int(row.get("count_1130", 0) or 0),
    )


def load_vendor_data(file_path: Path = VENDOR_DATA_FILE) -> list[VendorRecord]:
    """Read vendor data from the CSV file."""
    if not file_path.exists():
        return []
    with file_path.open("r", newline="", encoding="utf-8") as file_handle:
        return [row_to_vendor(row) for row in csv.DictReader(file_handle)]


def save_vendor_data(records: list[VendorRecord], file_path: Path = VENDOR_DATA_FILE) -> None:
    """Write vendor records to the CSV file."""
    with file_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=VENDOR_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())


def upsert_vendor(records: list[VendorRecord], new_record: VendorRecord) -> list[VendorRecord]:
    """Update one vendor/date record or add it if it does not exist.

    CHECK: Vendor name + market date is treated as the unique record key.
    This prevents duplicate rows when a vendor submission is corrected.
    """
    result: list[VendorRecord] = []
    updated = False
    for record in records:
        same_vendor = normalize_vendor_key(record.vendor_name) == normalize_vendor_key(new_record.vendor_name)
        same_date = record.market_date == new_record.market_date
        if same_vendor and same_date:
            result.append(new_record)
            updated = True
        else:
            result.append(record)
    if not updated:
        result.append(new_record)
    return result


# ---------- SAMPLE DATA ----------

def sample_vendor_records() -> list[VendorRecord]:
    """Create sample data for a meaningful demo."""
    return [
        VendorRecord("2026-04-05", "Green Garden Farm", "Produce", 500.00, 20.00, True, 31.20, True, "Sunny"),
        VendorRecord("2026-04-05", "Colonial Bakes", "Baked Goods", 250.00, 0.00, True, 0.00, True, "Sunny"),
        VendorRecord("2026-04-05", "River City Tacos", "Prepared Foods", 0.00, 0.00, False, 0.00, True, "Sunny"),
        VendorRecord("2026-04-12", "Green Garden Farm", "Produce", 610.00, 30.00, True, 38.40, True, "Cloudy"),
        VendorRecord("2026-04-12", "Colonial Bakes", "Baked Goods", 280.00, 0.00, True, 16.80, True, "Cloudy"),
        VendorRecord("2026-04-12", "Hearthside Meats", "Meat", 390.00, 20.00, True, 24.60, True, "Cloudy"),
        VendorRecord("2026-04-19", "Green Garden Farm", "Produce", 560.00, 30.00, True, 35.40, True, "Rainy"),
        VendorRecord("2026-04-19", "River City Tacos", "Prepared Foods", 450.00, 25.00, True, 0.00, True, "Rainy"),
        VendorRecord("2026-04-19", "Campus Crafts", "Other", 125.00, 0.00, True, 7.50, True, "Rainy"),
    ]


def ensure_sample_file_exists() -> None:
    """Create sample CSV data if the files do not exist yet."""
    if not APPROVED_VENDOR_FILE.exists():
        save_approved_vendors()
    refresh_approved_vendors()
    if not VENDOR_DATA_FILE.exists():
        save_vendor_data(sample_vendor_records())
    if not SCHEDULE_FILE.exists():
        create_sample_schedule()
    if not MARKET_DAY_FILE.exists():
        save_market_day_context(sample_market_day_context())


# ---------- MARKET DAY INPUT VIEW ----------

def build_market_day_input_view() -> str:
    """Build the manager-only market day input form.

    WHY: Weather, customer counts, programming, community events, and nonprofit tabling
    are market-level details. They should be entered by the market manager, not by vendors.
    """
    return """
    <p class="note">Use this manager-only form after each market to enter date-level context. This data feeds season analytics, weather impact, attendance estimates, and decision-loop insights.</p>
    <form method="post" action="/submit_market_day">
      <label>Market Date<input name="market_date" type="date" value="2026-04-19" required></label>
      <label>Weather<input name="weather" placeholder="Sunny, Rainy, Windy, Hot >90, Cold <40"></label>
      <label>8:30 Count<input name="count_830" type="number" min="0"></label>
      <label>9:30 Count<input name="count_930" type="number" min="0"></label>
      <label>10:30 Count<input name="count_1030" type="number" min="0"></label>
      <label>11:30 Count<input name="count_1130" type="number" min="0"></label>
      <label>Musician / Music Event<input name="music_event" placeholder="Bluegrass Duo"></label>
      <label>Chef's Tent<input name="chefs_tent" placeholder="Chef demo: seasonal greens"></label>
      <label>POP Club / Children's Programming<input name="childrens_programming" placeholder="POP Club: 18 children participated"></label>
      <label>External Community Events<input name="community_events" placeholder="5K, festival, campus event"></label>
      <label>Nonprofit Organizations Tabling<input name="nonprofit_orgs" placeholder="Habitat for Humanity"></label>
      <button type="submit">Save Market Day Context</button>
    </form>
    """


# ---------- APPROVED VENDOR ADMIN VIEW ----------

def build_vendor_admin_view() -> str:
    """Build the admin section for maintaining approved vendors.

    WHY: Vendor changes happen throughout the season. This allows controlled updates
    without editing Python code while preserving data integrity.
    """
    refresh_approved_vendors()
    vendor_rows = []
    for vendor_name, category in sorted(APPROVED_VENDORS.items()):
        vendor_rows.append(
            "<tr>"
            f"<td>{html.escape(vendor_name)}</td>"
            f"<td>{html.escape(category)}</td>"
            "</tr>"
        )

    return f"""
    <p class="note">Use this section to add a vendor to the approved list. Once added, the vendor appears in the Guided Vendor Input dropdown and is validated by the backend.</p>
    <form method="post" action="/add_vendor">
      <label>Vendor Name<input name="new_vendor_name" placeholder="New vendor name" required></label>
      <label>Category
        <select name="new_vendor_category" required>
          {build_category_options()}
        </select>
      </label>
      <button type="submit">Add Approved Vendor</button>
    </form>
    <h3>Current Approved Vendors</h3>
    <div class="table-wrap"><table>
      <thead><tr><th>Vendor</th><th>Category</th></tr></thead>
      <tbody>{''.join(vendor_rows)}</tbody>
    </table></div>
    """


# ---------- OPERATIONS TABLE ----------

def build_operations_table(records: list[VendorRecord]) -> str:
    """Build the manager operations table.

    CHECK: This table only displays calculated values from VendorRecord properties.
    It does not recalculate business rules separately, which prevents logic drift.
    """
    if not records:
        return "<p>No vendors have been entered yet.</p>"

    rows = []
    for record in records:
        action_class = {
            "Send sales reminder": "action-red",
            "Send payment reminder": "action-gold",
            "Complete": "action-green",
        }[record.action_needed]

        rows.append(
            "<tr>"
            f"<td>{html.escape(record.market_date)}</td>"
            f"<td>{html.escape(record.vendor_name)}</td>"
            f"<td>{html.escape(record.category)}</td>"
            f"<td>{estimate_customers(record)}</td>"
            f"<td>{format_currency(record.reported_sales)}</td>"
            f"<td>{format_currency(record.token_reimbursement)}</td>"
            f"<td>{format_currency(record.token_net)}</td>"
            f"<td>{format_currency(record.sales)}</td>"
            f"<td>{format_currency(record.fee_due)}</td>"
            f"<td>{format_currency(record.balance_due)}</td>"
            f"<td>{'Below Target' if record.is_underperforming else 'On Track'}</td>"
            f"<td>{'Yes' if record.sales_reported else 'No'}</td>"
            f"<td>{'Yes' if record.paid else 'No'}</td>"
            f"<td><span class='{action_class}'>{record.action_needed}</span></td>"
            "</tr>"
        )

    return (
        "<div class='table-wrap'><table>"
        "<thead><tr>"
        "<th>Date</th><th>Vendor</th><th>Category</th><th>Customers</th><th>Self-Reported Sales</th>"
        "<th>Tokens</th><th>Net Tokens</th><th>Total Sales</th><th>6% Fee</th><th>Balance Due</th><th>Performance</th><th>Reported</th><th>Paid</th><th>Action Needed</th>"
        "</tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


# ---------- BUILT-IN AGENT: EMAIL DRAFTING ----------

def build_combined_followup_email(vendor_name: str, vendor_records: list[VendorRecord]) -> str:
    """Create one combined follow-up email per vendor."""
    missing_sales_records = [record for record in vendor_records if record.action_needed == "Send sales reminder"]
    payment_records = [record for record in vendor_records if record.action_needed == "Send payment reminder"]
    total_balance = sum(record.balance_due for record in payment_records)

    lines = [
        f"Hi {vendor_name},",
        "",
        "I hope you are doing well. This is a friendly follow-up from the William & Mary Farmers Market.",
        "",
    ]

    if missing_sales_records:
        dates = ", ".join(record.market_date for record in missing_sales_records)
        lines.append(f"Sales reporting reminder: We are missing your sales report for: {dates}.")
        lines.append("")

    if payment_records:
        lines.append("Payment reminder: Our records show an outstanding balance for the following market date(s):")
        for record in payment_records:
            lines.append(
                f"- {record.market_date}: gross sales {format_currency(record.sales)}, "
                f"6% fee {format_currency(record.fee_due)}, paid {format_currency(record.paid_amount)}, "
                f"balance {format_currency(record.balance_due)}"
            )
        lines.append(f"Total outstanding balance: {format_currency(total_balance)}")
        lines.append("")

    lines.extend([
        "Please submit any missing sales reports and payments when convenient.",
        "",
        "Thank you!",
        "William & Mary Farmers Market Team",
    ])

    return "\n".join(lines)


def build_ai_agent_section(records: list[VendorRecord]) -> str:
    """Build one email card per vendor needing follow-up."""
    records_needing_followup = [record for record in records if record.action_needed != "Complete"]
    if not records_needing_followup:
        return "<p class='complete'>No follow-up needed. All vendors are complete.</p>"

    grouped_records: dict[str, list[VendorRecord]] = defaultdict(list)
    display_names: dict[str, str] = {}
    for record in records_needing_followup:
        vendor_key = normalize_vendor_key(record.vendor_name)
        display_names[vendor_key] = record.vendor_name.strip()
        grouped_records[vendor_key].append(record)

    cards = []
    for vendor_key, vendor_records in sorted(grouped_records.items()):
        vendor_name = display_names[vendor_key]
        issue_types = sorted({record.action_needed for record in vendor_records})
        if len(issue_types) > 1:
            label = "Combined Follow-Up"
            pill_class = "gold"
        elif issue_types[0] == "Send sales reminder":
            label = "Sales Reminder"
            pill_class = "green"
        else:
            label = "Payment Reminder"
            pill_class = "gold"

        cards.append(
            "<div class='email-draft'>"
            f"<span class='pill {pill_class}'>{label}</span>"
            f"<h3>{html.escape(vendor_name)}</h3>"
            f"<p class='note'>This combines {len(vendor_records)} open issue(s) into one vendor follow-up.</p>"
            f"<pre>{html.escape(build_combined_followup_email(vendor_name, vendor_records))}</pre>"
            "</div>"
        )

    return "".join(cards)


# ---------- EXPECTED ATTENDANCE LOGIC ----------

def is_nice_weather(weather_text: str) -> bool:
    """Determine if weather meets 'nice weather' criteria.

    RULE:
    - Temperature between 60–84°F (assumed from descriptor for now)
    - No rain
    - No wind

    WHY: This is a business rule based on observed market behavior.
    """
    text = (weather_text or "").lower()

    if "rain" in text or "wind" in text:
        return False

    # NOTE: temperature parsing could be expanded later from API
    if "cold" in text or "hot" in text:
        return False

    return True


def expected_customer_threshold(scheduled_vendor_count: int, weather_text: str) -> int:
    """Return expected customer baseline based on conditions.

    RULE:
    - Nice weather + >25 vendors → 1000+ customers expected

    WHY: This creates a benchmark for performance evaluation.
    """
    if is_nice_weather(weather_text) and scheduled_vendor_count > 25:
        return 1000
    return 0


def market_context_lookup() -> dict[str, MarketDayContext]:
    """Return market-day context by date for quick lookup.

    WHY: Weather and attendance are market-level details, so date-based lookup
    lets the schedule and season views compare vendor count, weather, and traffic.
    """
    return {record.market_date: record for record in load_market_day_context()}


def attendance_performance_label(actual_customers: int, expected_customers: int) -> str:
    """Label attendance performance compared with expectation."""
    if expected_customers <= 0:
        return "No benchmark"
    if actual_customers >= expected_customers:
        return "Meets expectation"
    return "Below expectation"


def upcoming_market_insight(
    scheduled_vendor_count: int,
    weather_text: str,
    weather_source: str,
    expected_customers: int,
    performance_label: str,
) -> str:
    """Create a plain-English insight for the upcoming market.

    WHY: The upcoming market section should not just display raw KPIs. It should explain
    what the forecast and vendor count imply for planning.
    """
    if expected_customers >= 1000:
        return (
            f"Planning insight: With {scheduled_vendor_count} scheduled vendors and favorable weather from {weather_source}, "
            "the market should plan for a high-attendance day of 1,000+ customers."
        )

    if "rain" in weather_text.lower() or "wind" in weather_text.lower():
        return (
            f"Planning insight: Weather may suppress attendance because the signal is '{weather_text}'. "
            "Consider extra customer communication, covered programming, and vendor support."
        )

    return (
        f"Planning insight: {scheduled_vendor_count} vendors are scheduled. No 1,000-customer benchmark is triggered yet, "
        f"and the current attendance signal is {performance_label}."
    )


# ---------- WEATHER + SALES ANALYSIS ----------

def analyze_weather_impact(records: list[VendorRecord]) -> str:
    # ENHANCED: Now includes expected attendance benchmarking logic

    """Enhanced analysis of how weather impacts BOTH sales and customer traffic.

    WHY: This mirrors real market analysis by connecting weather → attendance → sales.
    It also identifies intra-market attendance dips, such as a 10–11am programming gap.
    """
    if not records:
        return "Not enough data to analyze weather impact."

    segments: dict[str, list[dict]] = defaultdict(list)

    for r in records:
        weather_text = (r.weather or "").lower()
        sales = r.sales
        customers = estimate_customers(r)

        if "rain" in weather_text:
            key = "Rainy"
        elif "wind" in weather_text:
            key = "Windy"
        else:
            key = "Mild"

        segments[key].append({"sales": sales, "customers": customers})

        if "cold" in weather_text or "<40" in weather_text:
            segments["Cold (<40°F)"].append({"sales": sales, "customers": customers})
        if "hot" in weather_text or ">90" in weather_text:
            segments["Hot (>90°F)"].append({"sales": sales, "customers": customers})

    if not segments:
        return "No usable weather data available yet."

    insights = []
    summary = {}

    for seg, vals in segments.items():
        if not vals:
            continue
        avg_sales = sum(v["sales"] for v in vals) / len(vals)
        avg_customers = sum(v["customers"] for v in vals) / len(vals)
        summary[seg] = (avg_sales, avg_customers)
        insights.append(f"{seg}: avg sales {format_currency(avg_sales)}, avg customers {int(avg_customers)}")

    sorted_segments = sorted(summary.items(), key=lambda x: x[1][0], reverse=True)

    if len(sorted_segments) >= 2:
        best = sorted_segments[0]
        worst = sorted_segments[-1]
        hypothesis = (
            f"Hypothesis: {best[0]} conditions drive higher performance than {worst[0]}. "
            f"This appears to be driven by differences in customer traffic "
            f"({int(best[1][1])} vs {int(worst[1][1])} customers)."
        )
    else:
        hypothesis = "More data needed to form a strong weather hypothesis."

    time_insight = ""
    all_counts_930 = [r.count_930 for r in records if r.count_930 > 0]
    all_counts_1030 = [r.count_1030 for r in records if r.count_1030 > 0]

    if all_counts_1030 and all_counts_930:
        avg_930 = sum(all_counts_930) / len(all_counts_930)
        avg_1030 = sum(all_counts_1030) / len(all_counts_1030)

        if avg_1030 < avg_930:
            time_insight = (
                " Observed pattern: attendance dips between 9:30 and 10:30. "
                "This supports adding programming, such as children's activities, from 10–11am to sustain traffic."
            )

    return "Weather impact analysis: " + " | ".join(insights) + ". " + hypothesis + time_insight


# ---------- DECISION LOOP ANALYSIS ----------

def analyze_decision_loop() -> str:
    """Analyze the programming decision loop using market-day context.

    WHY: This demonstrates the full analytics loop:
    observe attendance → diagnose a dip → recommend programming → track results.
    """
    context_records = load_market_day_context()
    if not context_records:
        return "No market-day context data is available yet."

    with_childrens = [r for r in context_records if r.childrens_programming and "none" not in r.childrens_programming.lower()]
    without_childrens = [r for r in context_records if not r.childrens_programming or "none" in r.childrens_programming.lower()]

    avg_930 = sum(r.count_930 for r in context_records) / len(context_records)
    avg_1030 = sum(r.count_1030 for r in context_records) / len(context_records)

    avg_with_programming = 0
    avg_without_programming = 0

    if with_childrens:
        avg_with_programming = sum(r.estimated_customers for r in with_childrens) / len(with_childrens)
    if without_childrens:
        avg_without_programming = sum(r.estimated_customers for r in without_childrens) / len(without_childrens)

    if avg_1030 < avg_930:
        diagnosis = "Attendance is lower around the 10:30 count than the 9:30 count, suggesting a mid-market traffic dip."
    else:
        diagnosis = "Attendance does not currently show a clear 10:30 dip, but the window should continue to be monitored."

    if with_childrens and without_childrens:
        evaluation = (
            f"Markets with children's programming average {int(avg_with_programming)} estimated customers, "
            f"compared with {int(avg_without_programming)} estimated customers without it."
        )
    elif with_childrens:
        evaluation = f"Children's programming is being tracked; current average attendance is {int(avg_with_programming)} estimated customers."
    else:
        evaluation = "No children's programming has been recorded yet, so impact cannot be evaluated."

    return (
        "Decision loop: Observe attendance by time of day → diagnose the 10–11am softness → "
        "add children's programming during that window → track attendance and sales afterward. "
        f"{diagnosis} {evaluation}"
    )


def build_decision_loop_view() -> str:
    """Build a dashboard card explaining the decision loop.

    WHY: Shows how the dashboard moves from reporting to prescriptive action.
    """
    return f"""
    <div class="season-grid">
      <div class="season-stat"><div class="kpi-label">Observed Pattern</div><div class="kpi-value">10–11am Dip</div></div>
      <div class="season-stat"><div class="kpi-label">Intervention</div><div class="kpi-value">Children's Programming</div></div>
      <div class="season-stat"><div class="kpi-label">Goal</div><div class="kpi-value">Sustain Traffic</div></div>
    </div>
    <p class="note">{html.escape(analyze_decision_loop())}</p>
    <p class="note"><strong>Full loop:</strong> Track attendance → identify weak time period → add programming → measure whether attendance and sales improve.</p>
    """


# ---------- MATH AND DATA VALIDATION ----------

def audit_vendor_math(records: list[VendorRecord]) -> list[str]:
    """Run a math and data-quality audit before the agent answers.

    WHY: The agent should not answer from unchecked data.

    CHECKS PERFORMED:
    1. Vendor category must match the approved vendor list.
    2. Total sales must equal reported sales + token reimbursement.
    3. Fee due must equal total sales x 6% when sales are reported.
    4. Balance due must equal fee due minus payment received.
    5. Paid status must match the calculated fee/payment relationship.
    6. Customer counts cannot be negative.
    """
    issues: list[str] = []

    for record in records:
        # CHECK 1: approved category validation
        expected_category = APPROVED_VENDORS.get(record.vendor_name)
        if expected_category and record.category != expected_category:
            issues.append(
                f"{record.vendor_name} has category '{record.category}', but the approved list says '{expected_category}'."
            )

        # CHECK 2: total sales reconciliation
        expected_sales = round(record.reported_sales + record.token_reimbursement, 2)
        if round(record.sales, 2) != expected_sales:
            issues.append(
                f"{record.vendor_name} on {record.market_date} has a total sales mismatch."
            )

        # CHECK 3: 6% fee recalculation
        expected_fee = round(expected_sales * SALES_FEE_RATE, 2) if record.sales_reported else 0.0
        if round(record.fee_due, 2) != expected_fee:
            issues.append(
                f"{record.vendor_name} on {record.market_date} has a 6% fee mismatch."
            )

        # CHECK 4: balance due reconciliation
        expected_balance = round(max(expected_fee - record.paid_amount, 0.0), 2) if record.sales_reported else 0.0
        if round(record.balance_due, 2) != expected_balance:
            issues.append(
                f"{record.vendor_name} on {record.market_date} has a balance due mismatch."
            )

        # CHECK 5: paid status validation
        expected_paid = record.sales_reported and record.paid_amount >= expected_fee
        if record.paid != expected_paid:
            issues.append(
                f"{record.vendor_name} on {record.market_date} has an inconsistent paid status."
            )

        counts = [record.count_830, record.count_930, record.count_1030, record.count_1130]
        if any(count < 0 for count in counts):
            issues.append(
                f"{record.vendor_name} on {record.market_date} has a negative customer count."
            )

    return issues


def math_audit_prefix(records: list[VendorRecord]) -> str:
    """Create a short plain-English audit note for agent answers.

    WHY: This makes it clear that answers are based on checked calculations.
    """
    issues = audit_vendor_math(records)
    if not issues:
        return "I checked the vendor math first. Sales, fees, balances, payments, and customer-count calculations look consistent. "

    preview = "; ".join(issues[:3])
    extra = "" if len(issues) <= 3 else f" There are {len(issues) - 3} additional issue(s)."
    return (
        "I checked the vendor math first and found data-quality issue(s) that may affect the answer: "
        f"{preview}.{extra} "
    )


# ---------- BUILT-IN AGENT: QUESTION ANSWERING ----------

def answer_agent_question(records: list[VendorRecord], question: str) -> str:
    """Answer approved market-operations questions in full, readable sentences.

    WHY: The agent should feel like a business assistant, not a raw data dump.

    CHECK: The math audit runs before every answer. The answer includes the audit note,
    so the user knows whether the response is based on clean data or flagged data.
    """
    audit_note = math_audit_prefix(records)
    q = question.lower().strip()
    if not q:
        return audit_note + "Please type a market operations question, such as, 'How many vendors are past due?'"

    underperforming = [r for r in records if r.is_underperforming]
    past_due = [r for r in records if r.action_needed != "Complete"]
    missing_sales = [r for r in records if r.action_needed == "Send sales reminder"]
    payment_due = [r for r in records if r.action_needed == "Send payment reminder"]

    if "underperform" in q or "below" in q or "not meeting" in q:
        unique_vendors = sorted({r.vendor_name for r in underperforming})
        if not unique_vendors:
            return audit_note + "No vendors are currently below their category performance expectations."
        names = ", ".join(unique_vendors)
        return (
            audit_note
            + f"There are {len(unique_vendors)} vendor(s) currently below performance expectations: {names}. "
            "A good next step would be to feature these vendors in the newsletter or on social media to help drive traffic to their booths."
        )

    if "past due" in q or "follow up" in q or "follow-up" in q or "need action" in q:
        unique_vendors = sorted({r.vendor_name for r in past_due})
        if not unique_vendors:
            return audit_note + "No vendors are currently past due. All vendor records are complete based on the data available."
        names = ", ".join(unique_vendors)
        return (
            audit_note
            + f"There are {len(unique_vendors)} vendor(s) who need follow-up: {names}. "
            "This may include missing sales reports, unpaid fees, or both."
        )

    if "missing" in q or "not reported" in q or "need to report" in q or "still need to report" in q:
        unique_vendors = sorted({r.vendor_name for r in missing_sales})
        if not unique_vendors:
            return audit_note + "All vendors have reported their sales based on the current records."
        names = ", ".join(unique_vendors)
        return audit_note + f"There are {len(unique_vendors)} vendor(s) who still need to report sales: {names}."

    if "payment" in q or "paid" in q or "owe" in q or "balance" in q:
        unique_vendors = sorted({r.vendor_name for r in payment_due})
        total_balance = sum(r.balance_due for r in payment_due)
        if not unique_vendors:
            return audit_note + "No vendors currently need payment follow-up based on the current records."
        names = ", ".join(unique_vendors)
        return (
            audit_note
            + f"There are {len(unique_vendors)} vendor(s) who need payment follow-up: {names}. "
            f"The total outstanding balance is {format_currency(total_balance)}."
        )

    if "category" in q or "breakdown" in q or "mix" in q:
        if not records:
            return audit_note + "There is no vendor data available yet, so I cannot calculate a category breakdown."
        category_counts = Counter(r.category for r in records)
        total = sum(category_counts.values()) or 1
        parts = []
        for category, count in sorted(category_counts.items()):
            pct = (count / total) * 100
            parts.append(f"{category}: {count} vendor record(s), or {pct:.1f}% of the current records")
        return audit_note + "Here is the current vendor category breakdown: " + "; ".join(parts) + "."

    if "top" in q and ("vendor" in q or "selling" in q or "sales" in q):
        if not records:
            return audit_note + "There is no sales data available yet, so I cannot identify a top-selling vendor."
        sales_by_vendor: dict[str, float] = defaultdict(float)
        for r in records:
            sales_by_vendor[r.vendor_name] += r.sales
        top_vendor = max(sales_by_vendor, key=sales_by_vendor.get)
        top_sales = sales_by_vendor[top_vendor]
        return audit_note + f"The top-selling vendor is {top_vendor}, with total recorded sales of {format_currency(top_sales)}."

    if "decision loop" in q or "children" in q or "programming" in q or ("10" in q and "11" in q):
        return audit_note + analyze_decision_loop()

    if "weather" in q and ("impact" in q or "affect" in q or "influence" in q):
        return audit_note + analyze_weather_impact(records)

    if "customer" in q or "attendance" in q:
        total_customers = sum(estimate_customers(r) for r in records)
        return (
            audit_note
            + f"The estimated total customer count is {total_customers}. "
            f"This estimate uses the market multiplier of {CUSTOMER_MULTIPLIER} applied to the timed attendance counts."
        )

    if "sales" in q or "revenue" in q:
        total_sales = sum(r.sales for r in records)
        return audit_note + f"Total recorded season sales are {format_currency(total_sales)}."

    return audit_note + agent_scope_message()


# ---------- MARKETING INSIGHTS ----------

def build_marketing_insights(records: list[VendorRecord]) -> str:
    """Build vendor mix and sales mix summary."""
    if not records:
        return "<p>No marketing insight available yet.</p>"

    category_counts = Counter(record.category for record in records)
    sales_by_category: dict[str, float] = defaultdict(float)
    for record in records:
        sales_by_category[record.category] += record.sales

    total_vendors = sum(category_counts.values()) or 1
    total_sales = sum(sales_by_category.values()) or 1

    rows = []
    for category in sorted(category_counts):
        vendor_pct = (category_counts[category] / total_vendors) * 100
        sales_pct = (sales_by_category[category] / total_sales) * 100
        rows.append(
            "<tr>"
            f"<td>{html.escape(category)}</td>"
            f"<td>{category_counts[category]}</td>"
            f"<td>{vendor_pct:.1f}%</td>"
            f"<td>{sales_pct:.1f}%</td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr><th>Category</th><th>Vendor Count</th><th>% of Vendors</th><th>% of Sales</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
        "<p class='note'>This helps the market team compare vendor mix with sales contribution. Vendors below category benchmarks can be highlighted in social media or newsletters to drive traffic and improve performance.</p>"
    )


# ---------- FULL SEASON VIEW ----------

def build_full_season_view(records: list[VendorRecord]) -> str:
    """Build full-season summary cards and sales-by-date table.

    WHY: Section 3 gives the manager a season-level snapshot, including approved vendors
    versus vendors who have actually attended at least once.
    """
    refresh_approved_vendors()
    schedule = load_schedule()
    if not records:
        approved_vendor_count = len(APPROVED_VENDORS)
        return f"<p>No season data available yet. Approved vendors in the system: {approved_vendor_count}.</p>"

    market_dates = sorted({record.market_date for record in records})
    context_by_date = market_context_lookup()
    scheduled_total = sum(len(schedule.get(date_value, [])) for date_value in market_dates)

    nice_market_days = 0
    not_nice_market_days = 0
    nice_customer_total = 0
    not_nice_customer_total = 0

    for date_value in market_dates:
        context = context_by_date.get(date_value)
        weather_text = context.weather if context else "Not recorded"
        customers = context.estimated_customers if context else 0
        if is_nice_weather(weather_text):
            nice_market_days += 1
            nice_customer_total += customers
        else:
            not_nice_market_days += 1
            not_nice_customer_total += customers

    avg_nice_customers = int(nice_customer_total / nice_market_days) if nice_market_days else 0
    avg_not_nice_customers = int(not_nice_customer_total / not_nice_market_days) if not_nice_market_days else 0
    approved_vendor_count = len(APPROVED_VENDORS)
    unique_attended_vendors = sorted({record.vendor_name for record in records if record.attended})
    attended_vendor_count = len(unique_attended_vendors)
    total_sales = sum(record.sales for record in records)
    total_customers = sum(estimate_customers(r) for r in records)
    total_fees = sum(record.fee_due for record in records)
    total_paid = sum(record.paid_amount for record in records)
    total_balance = max(total_fees - total_paid, 0.0)
    missing_sales = sum(1 for record in records if not record.sales_reported)
    payment_followups = sum(1 for record in records if record.sales_reported and not record.paid)
    gross_tokens = sum(record.token_reimbursement for record in records)
    net_tokens = sum(record.token_net for record in records)

    sales_by_date: dict[str, float] = defaultdict(float)
    vendors_by_date: dict[str, set[str]] = defaultdict(set)
    for record in records:
        sales_by_date[record.market_date] += record.sales
        vendors_by_date[record.market_date].add(record.vendor_name)

    date_rows = []
    for market_date in market_dates:
        date_rows.append(
            "<tr>"
            f"<td>{html.escape(market_date)}</td>"
            f"<td>{len(vendors_by_date[market_date])}</td>"
            f"<td>{format_currency(sales_by_date[market_date])}</td>"
            "</tr>"
        )

    return f"""
    <div class="season-grid">
      <div class="season-stat"><div class="kpi-label">Approved Vendors</div><div class="kpi-value">{approved_vendor_count}</div></div>
      <div class="season-stat"><div class="kpi-label">Vendors Attended</div><div class="kpi-value">{attended_vendor_count}</div></div>
      <div class="season-stat"><div class="kpi-label">Scheduled Vendor-Date Records</div><div class="kpi-value">{scheduled_total}</div></div>
      <div class="season-stat"><div class="kpi-label">Market Days</div><div class="kpi-value">{len(market_dates)}</div></div>
      <div class="season-stat"><div class="kpi-label">Nice Weather Days</div><div class="kpi-value">{nice_market_days}</div></div>
      <div class="season-stat"><div class="kpi-label">Not Nice Weather Days</div><div class="kpi-value">{not_nice_market_days}</div></div>
      <div class="season-stat"><div class="kpi-label">Avg Customers: Nice Days</div><div class="kpi-value">{avg_nice_customers}</div></div>
      <div class="season-stat"><div class="kpi-label">Avg Customers: Not Nice Days</div><div class="kpi-value">{avg_not_nice_customers}</div></div>
      <div class="season-stat"><div class="kpi-label">Season Sales</div><div class="kpi-value">{format_currency(total_sales)}</div></div>
      <div class="season-stat"><div class="kpi-label">Season 6% Fees</div><div class="kpi-value">{format_currency(total_fees)}</div></div>
      <div class="season-stat"><div class="kpi-label">Season Balance</div><div class="kpi-value">{format_currency(total_balance)}</div></div>
      <div class="season-stat"><div class="kpi-label">Gross Tokens</div><div class="kpi-value">{format_currency(gross_tokens)}</div></div>
      <div class="season-stat"><div class="kpi-label">Net Tokens</div><div class="kpi-value">{format_currency(net_tokens)}</div></div>
      <div class="season-stat"><div class="kpi-label">Missing Sales Reports</div><div class="kpi-value">{missing_sales}</div></div>
      <div class="season-stat"><div class="kpi-label">Payment Follow-Ups</div><div class="kpi-value">{payment_followups}</div></div>
    </div>
    <h3>Sales by Market Date</h3>
    <table>
      <thead><tr><th>Market Date</th><th>Vendor Count</th><th>Total Sales</th></tr></thead>
      <tbody>{''.join(date_rows)}</tbody>
    </table>
    <p class="note">This gives the manager a full-season view while the operations table still supports day-to-day follow-up. Approved Vendors counts the current approved vendor list. Vendors Attended counts unique vendors with at least one attended market record. Scheduled Vendor-Date Records counts scheduled appearances across market dates. Nice weather is defined as 60–84°F with no rain and no wind; in this demo, text labels such as rain, wind, cold, or hot are used as the weather signal.</p>
    """


# ---------- SCHEDULE FILTER VIEW ----------

def build_schedule_filter_options(selected_category: str = "All") -> str:
    """Build the category filter dropdown for the schedule section.

    WHY: replaces the separate produce schedule with one flexible schedule view.
    """
    categories = ["All"] + sorted(set(APPROVED_VENDORS.values()))
    options = []
    for category in categories:
        selected = "selected" if category == selected_category else ""
        options.append(f"<option value='{html.escape(category)}' {selected}>{html.escape(category)}</option>")
    return "".join(options)


# ---------- NEXT MARKET SCHEDULE VIEW ----------

def next_saturday_from(today: date | None = None) -> date:
    """Return the next Saturday from today.

    WHY: Section 6 should always focus on the next market date rather than the whole season.
    """
    today = today or date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    return today + timedelta(days=days_until_saturday)


def build_next_market_schedule_view(selected_category: str = "All") -> str:
    """Build an expandable category schedule for the next Saturday market.

    WHY: Managers need a quick view of who is scheduled next, first by total count,
    then by category with vendor names underneath. The category filter keeps this flexible
    without needing a separate produce-only section.
    """
    schedule = load_schedule()
    next_market = next_saturday_from()
    next_market_key = next_market.isoformat()
    scheduled_vendors = schedule.get(next_market_key, [])
    context_by_date = market_context_lookup()
    market_context = context_by_date.get(next_market_key)

    # CHECK: For past markets, use recorded weather from market_day_context.csv.
    # For future markets, if recorded weather is missing, use the Weather.gov forecast.
    # This lets the dashboard anticipate attendance instead of waiting for manual weather entry.
    forecast = fetch_weather_from_weather_gov()
    if market_context and market_context.weather != "Not recorded":
        weather_text = market_context.weather
        weather_source = "Recorded market context"
    else:
        weather_text = forecast.get("descriptor", "Not recorded")
        weather_source = "Weather.gov forecast"

    actual_customers = market_context.estimated_customers if market_context else 0

    # If the generated sample schedule does not include the real current next Saturday,
    # fall back to the first available schedule date so the demo still shows something.
    if not scheduled_vendors and schedule:
        next_market_key = sorted(schedule.keys())[0]
        scheduled_vendors = schedule.get(next_market_key, [])
        market_context = context_by_date.get(next_market_key)
        if market_context and market_context.weather != "Not recorded":
            weather_text = market_context.weather
            weather_source = "Recorded market context"
        else:
            weather_text = forecast.get("descriptor", "Not recorded")
            weather_source = "Weather.gov forecast"
        actual_customers = market_context.estimated_customers if market_context else 0

    expected_customers = expected_customer_threshold(len(scheduled_vendors), weather_text)
    performance_label = attendance_performance_label(actual_customers, expected_customers)
    planning_insight = upcoming_market_insight(
        scheduled_vendor_count=len(scheduled_vendors),
        weather_text=weather_text,
        weather_source=weather_source,
        expected_customers=expected_customers,
        performance_label=performance_label,
    )

    vendors_by_category: dict[str, list[str]] = defaultdict(list)
    for vendor_name in scheduled_vendors:
        category = APPROVED_VENDORS.get(vendor_name, "Other")
        if selected_category == "All" or category == selected_category:
            vendors_by_category[category].append(vendor_name)

    category_cards = []
    for category in sorted(vendors_by_category):
        vendor_items = "".join(f"<li>{html.escape(vendor)}</li>" for vendor in sorted(vendors_by_category[category]))
        category_cards.append(
            "<details class='category-details'>"
            f"<summary>{html.escape(category)} ({len(vendors_by_category[category])})</summary>"
            f"<ul>{vendor_items}</ul>"
            "</details>"
        )

    if not category_cards:
        category_cards.append("<p class='note'>No vendors are scheduled for the next market date yet.</p>")

    return f"""
    <p class="note"><strong>{html.escape(planning_insight)}</strong></p>
    <p class="note">Next market date: <strong>{html.escape(next_market_key)}</strong></p>
    <form method="get" action="/#schedule-section" class="agent-question-form">
      <label>Filter by vendor type
        <select name="schedule_category">
          {build_schedule_filter_options(selected_category)}
        </select>
      </label>
      <button type="submit">Apply Filter</button>
    </form>
    <div class="season-grid">
      <div class="season-stat"><div class="kpi-label">Scheduled Vendors Shown</div><div class="kpi-value">{sum(len(vendors) for vendors in vendors_by_category.values())}</div></div>
      <div class="season-stat"><div class="kpi-label">Categories Represented</div><div class="kpi-value">{len(vendors_by_category)}</div></div>
      <div class="season-stat"><div class="kpi-label">Forecast Date</div><div class="kpi-value">{html.escape(forecast.get('forecast_date', 'Not available'))}</div></div>
      <div class="season-stat"><div class="kpi-label">Forecast Temp</div><div class="kpi-value">{html.escape(forecast.get('temperature', 'Not available'))}</div></div>
      <div class="season-stat"><div class="kpi-label">Expected Conditions</div><div class="kpi-value">{html.escape(weather_text)}</div></div>
      <div class="season-stat"><div class="kpi-label">Weather Source</div><div class="kpi-value">{html.escape(weather_source)}</div></div>
      <div class="season-stat"><div class="kpi-label">Expected Customers</div><div class="kpi-value">{expected_customers if expected_customers else 'No benchmark'}</div></div>
      <div class="season-stat"><div class="kpi-label">Actual / Estimated Customers</div><div class="kpi-value">{actual_customers}</div></div>
      <div class="season-stat"><div class="kpi-label">Attendance Signal</div><div class="kpi-value">{html.escape(performance_label)}</div></div>
    </div>
    <p class="note">Click each category to see which vendors are scheduled under that category. Current filter: <strong>{html.escape(selected_category)}</strong>.</p>
    {''.join(category_cards)}
    """


# ---------- DASHBOARD RENDERING ----------

def build_dashboard_html(records: list[VendorRecord], flash_message: str = "", agent_question: str = "", agent_answer: str = "", schedule_category: str = "All") -> str:
    """Build the full HTML dashboard."""
    total_sales = sum(record.sales for record in records)
    # FIX: Customer counts should come from market-day context (not vendor records)
    context_records = load_market_day_context()
    if context_records:
        total_customers = sum(r.estimated_customers for r in context_records)
    else:
        # fallback to vendor-level estimate if no context exists yet
        total_customers = sum(estimate_customers(record) for record in records)
    total_fees = sum(record.fee_due for record in records)
    missing_sales = sum(1 for record in records if record.action_needed == "Send sales reminder")
    payment_followups = sum(1 for record in records if record.action_needed == "Send payment reminder")
    flash_html = f"<div class='flash'>{html.escape(flash_message)}</div>" if flash_message else ""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>William & Mary Farmers Market Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#f6f8fb; color:#1f2937; margin:0; padding:0; }}
    .topbar {{ position:sticky; top:0; z-index:100; background:{WM_GREEN}; color:white; box-shadow:0 2px 10px rgba(0,0,0,.12); }}
    .topbar-inner {{ max-width:980px; margin:0 auto; padding:12px 20px; display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    .brand {{ font-weight:800; letter-spacing:.2px; }}
    .menu {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    .menu a {{ color:white; text-decoration:none; font-size:13px; padding:7px 9px; border-radius:999px; background:rgba(255,255,255,.12); }}
    .menu a:hover {{ background:{WM_GOLD}; color:white; }}
    .container {{ max-width:980px; margin:0 auto; padding:24px 20px 40px; }}
    h1 {{ color:{WM_GREEN}; margin-bottom:4px; }}
    h2 {{ color:{WM_GREEN}; margin-top:0; }}
    .subtitle {{ color:#4b5563; margin-bottom:22px; }}
    .dashboard-section-title {{ color:{WM_GREEN}; font-size:20px; margin:22px 0 4px; }}
    .card {{ background:white; padding:20px; margin-bottom:20px; border-radius:14px; box-shadow:0 2px 10px rgba(0,0,0,.06); }}
    .story {{ border-left:8px solid {WM_GOLD}; }}
    .agent-card-feature {{ border-top:6px solid {WM_GREEN}; }}
    .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:14px; margin-bottom:20px; }}
    .season-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; margin-bottom:18px; }}
    .season-stat, .kpi {{ background:white; border-radius:14px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.06); }}
    .season-stat {{ background:#f9fafb; border:1px solid #e5e7eb; }}
    .kpi-label {{ color:#6b7280; font-size:13px; margin-bottom:6px; }}
    .kpi-value {{ font-size:24px; font-weight:bold; color:{WM_GREEN}; }}
    form {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; align-items:end; }}
    .agent-question-form {{ grid-template-columns:1fr auto; }}
    input, select, button {{ padding:10px; border:1px solid #d1d5db; border-radius:8px; font:inherit; }}
    label {{ display:grid; gap:6px; font-size:14px; }}
    button, .button-link {{ background:{WM_GOLD}; color:white; border:none; font-weight:bold; cursor:pointer; text-decoration:none; padding:10px 14px; border-radius:8px; display:inline-block; }}
    .button-green {{ background:{WM_GREEN}; }}
    .table-wrap {{ width:100%; overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; table-layout:auto; }}
    th, td {{ border-bottom:1px solid #e5e7eb; padding:8px 10px; text-align:left; vertical-align:top; }}
    th {{ background:#f9fafb; font-size:13px; white-space:nowrap; }}
    td {{ font-size:14px; }}
    td:last-child {{ min-width:165px; white-space:nowrap; }}
    .action-red {{ background:#fee2e2; color:#991b1b; padding:6px 10px; border-radius:999px; font-weight:bold; }}
    .action-gold {{ background:#fef3c7; color:#92400e; padding:6px 10px; border-radius:999px; font-weight:bold; }}
    .action-green {{ background:#dcfce7; color:#166534; padding:6px 10px; border-radius:999px; font-weight:bold; }}
    .email-draft {{ border:1px solid #ddd; border-left:6px solid {WM_GREEN}; padding:15px; margin-bottom:15px; border-radius:10px; background:#fafafa; }}
    .email-draft pre {{ white-space:pre-wrap; font-family:Arial, sans-serif; line-height:1.4; }}
    .pill {{ display:inline-block; color:white; padding:5px 10px; border-radius:999px; font-size:12px; font-weight:bold; }}
    .pill.green {{ background:{WM_GREEN}; }}
    .pill.gold {{ background:{WM_GOLD}; }}
    .complete {{ color:{WM_GREEN}; font-weight:bold; }}
    .note {{ color:#4b5563; line-height:1.5; }}
    .flash {{ background:#dcfce7; color:#166534; padding:12px 16px; border-radius:10px; margin-bottom:18px; }}
    .agent-answer {{ background:#f9fafb; border-left:6px solid {WM_GREEN}; padding:14px; border-radius:10px; margin-top:10px; font-weight:bold; animation:fadeSlideIn .35s ease-out; }}
    .agent-ready {{ background:#f9fafb; border:1px dashed #cbd5e1; padding:12px 14px; border-radius:10px; margin-top:10px; color:#64748b; }}
    .agent-response-label {{ margin-top:16px; font-weight:bold; color:{WM_GREEN}; }}
    @keyframes fadeSlideIn {{ from {{ opacity:0; transform:translateY(-6px); }} to {{ opacity:1; transform:translateY(0); }} }}
    .category-details {{ border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; margin:10px 0; background:#f9fafb; }}
    .category-details summary {{ cursor:pointer; font-weight:bold; color:{WM_GREEN}; }}
    .category-details ul {{ margin-bottom:0; }}
    details.section-card {{ background:white; padding:0; margin-bottom:20px; border-radius:14px; box-shadow:0 2px 10px rgba(0,0,0,.06); overflow:hidden; }}
    details.section-card > summary {{ cursor:pointer; padding:16px 20px; font-size:19px; font-weight:bold; color:{WM_GREEN}; list-style:none; }}
    details.section-card > summary::-webkit-details-marker {{ display:none; }}
    .section-body {{ padding:0 20px 20px 20px; }}
    details.section-card > summary::after {{ content:'+'; float:right; color:{WM_GOLD}; font-size:26px; }}
    details.section-card[open] > summary::after {{ content:'−'; }}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="topbar-inner">
      <div class="brand">W&M Farmers Market</div>
      <nav class="menu">
        <a href="#ask-agent">Agent</a>
        <a href="#season-view">Season</a>
        <a href="#schedule-section">Schedule</a>
        <a href="#admin-vendors">Admin</a>
        <a href="#market-day-input">Market Day</a>
        <a href="#vendor-input">Input</a>
        <a href="#operations-table">Operations</a>
        <a href="#marketing-insight">Marketing</a>
      </nav>
    </div>
  </div>
  <div class="container">
    <h1>William & Mary Farmers Market Dashboard</h1>
    <p class="subtitle">A guided dashboard that protects calculations, tracks reporting and payments, and turns data into AI-ready action.</p>
    {flash_html}

    <div class="card story">
      <strong>Demo story:</strong> We replaced a multi-spreadsheet process with a guided dashboard. The system standardizes data entry, calculates the 6% vendor fee, handles token reimbursement logic, flags missing follow-up, and generates reminder drafts automatically.
    </div>

    <h2 class="dashboard-section-title">Season-to-Date Snapshot</h2>
    <p class="note">These top metrics summarize all vendor records currently loaded for the season-to-date demo dataset.</p>
    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-label">Season-to-Date Sales</div><div class="kpi-value">{format_currency(total_sales)}</div></div>
      <div class="kpi"><div class="kpi-label">Season-to-Date Attendance</div><div class="kpi-value">{total_customers}</div></div>
      <div class="kpi"><div class="kpi-label">Season-to-Date 6% Fees</div><div class="kpi-value">{format_currency(total_fees)}</div></div>
      <div class="kpi"><div class="kpi-label">Open Sales Reminders</div><div class="kpi-value">{missing_sales}</div></div>
      <div class="kpi"><div class="kpi-label">Open Payment Reminders</div><div class="kpi-value">{payment_followups}</div></div>
    </div>

    <details class="section-card agent-card-feature" id="ask-agent" open>
      <summary>1. Market Operations Assistant</summary>
      <div class="section-body">
      <form method="get" action="/#ask-agent" class="agent-question-form">
        <label>Ask a market-operations question<input name="agent_question" value="{html.escape(agent_question)}" placeholder="How many vendors are past due?"></label>
        <button type="submit">Ask Agent</button>
      </form>
      {f'<div class="agent-response-label">Agent Response</div><div class="agent-answer">{html.escape(agent_answer)}</div>' if agent_answer else '<div class="agent-ready">The assistant is ready for your question.</div>'}
      <p class="note">This assistant is intentionally constrained to approved market topics only. It can answer questions about vendor attendance, weather, sales reporting, payments, tokens, vendor categories, marketing mix, and decision-loop insights. It also runs a math audit before answering.</p>
      <div style="margin-top:16px;"><strong>Data Export</strong><br>
      <a class="button-link button-green" href="/download-csv">Download CSV</a></div>
    </div>
    </details>

    <details class="section-card" id="season-view" open>
      <summary>3. Full Season View</summary>
      <div class="section-body">
        {build_full_season_view(records)}
      </div>
    </details>

    <details class="section-card" open>
      <summary>4. Decision Loop: Programming Impact</summary>
      <div class="section-body">
        {build_decision_loop_view()}
      </div>
    </details>

    <details class="section-card">
      <summary>5. Vendor Role Intelligence</summary>
      <div class="section-body">
        <p class="note">This groups vendors by operational role, not just category, so the manager can think about consistency, traffic, seasonality, and variety.</p>
        {build_vendor_roles_view()}
      </div>
    </details>

    <details class="section-card" id="schedule-section" open>
      <summary>2. Upcoming Market Overview</summary>
      <div class="section-body">
        {build_next_market_schedule_view(schedule_category)}
      </div>
    </details>

    <details class="section-card" id="market-day-input">
      <summary>7. Market Day Input</summary>
      <div class="section-body">
        {build_market_day_input_view()}
      </div>
    </details>

    <details class="section-card" id="admin-vendors">
      <summary>8. Approved Vendor Admin</summary>
      <div class="section-body">
        {build_vendor_admin_view()}
      </div>
    </details>

    <details class="section-card" id="vendor-input">
      <summary>9. Guided Vendor Input</summary>
      <div class="section-body">
      <form method="post" action="/submit_vendor">
        <label>Market Date<input name="market_date" type="date" value="2026-04-19" required></label>
        <label>Vendor Name<select name="vendor_name" required>{build_vendor_dropdown_options()}</select></label>
        <label>Self-Reported Sales<input name="reported_sales" type="number" step="0.01" min="0" placeholder="0.00"></label>
        <label>Token Reimbursement<input name="token_reimbursement" type="number" step="0.01" min="0" placeholder="0.00"></label>
        <label>Reported Sales?<select name="sales_reported"><option value="yes">Yes</option><option value="no">No</option></select></label>
        <label>Payment Amount<input name="paid_amount" type="number" step="0.01" min="0" placeholder="0.00"></label>
        <label>Attended?<select name="attended"><option value="yes">Yes</option><option value="no">No</option></select></label>
        <p class="note">Vendor-level data only: sales, tokens, reporting, payment, and attendance. Market-level data is entered separately in Market Day Input.</p>
        <button type="submit">Submit Vendor</button>
      </form>
    </div>
    </details>

    <details class="section-card" id="operations-table">
      <summary>10. Operations Tracking Table</summary>
      <div class="section-body">
        {build_operations_table(records)}
      </div>
    </details>

    <details class="section-card">
      <summary>11. Built-In AI Action Agent</summary>
      <div class="section-body">
        <p class="note">The agent groups follow-ups by vendor, so one vendor with multiple issues receives one combined follow-up draft.</p>
        {build_ai_agent_section(records)}
      </div>
    </details>

    <details class="section-card" id="marketing-insight">
      <summary>12. Marketing Insight Section</summary>
      <div class="section-body">
        {build_marketing_insights(records)}
      </div>
    </details>
  </div>
</body>
</html>
"""


# ---------- WEB SERVER ----------

class DashboardHandler(BaseHTTPRequestHandler):
    """Local web server controller."""

    def serve_csv(self) -> None:
        """Send the CSV file to the browser as a download."""
        if not VENDOR_DATA_FILE.exists():
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            self.wfile.write(b"CSV file not found.")
            return

        content = VENDOR_DATA_FILE.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Disposition", "attachment; filename=market_data.csv")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        """Show the dashboard or serve the CSV download."""
        parsed = urlparse(self.path)
        if parsed.path == "/download-csv":
            self.serve_csv()
            return

        params = parse_qs(parsed.query)
        records = load_vendor_data()
        if not records:
            records = sample_vendor_records()
        agent_question = params.get("agent_question", [""])[0]
        agent_answer = answer_agent_question(records, agent_question) if agent_question else ""
        schedule_category = params.get("schedule_category", ["All"])[0]
        body = build_dashboard_html(records, agent_question=agent_question, agent_answer=agent_answer, schedule_category=schedule_category)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_POST(self) -> None:
        """Handle the vendor input form."""
        parsed = urlparse(self.path)
        if parsed.path == "/add_vendor":
            self.handle_add_vendor()
            return

        if parsed.path == "/submit_market_day":
            self.handle_submit_market_day()
            return

        if parsed.path != "/submit_vendor":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(raw_body).items()}

        vendor_name = form.get("vendor_name", "").strip()
        # CHECK: backend validation repeats the dropdown rule.
        # Even if someone bypasses the browser form, the server rejects unapproved vendors.
        if not vendor_name or vendor_name not in APPROVED_VENDORS:
            self.redirect_with_message("Please select an approved vendor.")
            return

        new_record = VendorRecord(
            market_date=form.get("market_date", "2026-04-19").strip() or "2026-04-19",
            vendor_name=vendor_name,
            category=APPROVED_VENDORS[vendor_name],
            reported_sales=parse_float(form.get("reported_sales", 0.0)),
            token_reimbursement=parse_float(form.get("token_reimbursement", 0.0)),
            sales_reported=form.get("sales_reported", "no") == "yes",
            paid_amount=parse_float(form.get("paid_amount", 0.0)),
            attended=form.get("attended", "yes") == "yes",
        )

        records = load_vendor_data()
        records = upsert_vendor(records, new_record)
        save_vendor_data(records)
        self.redirect_with_message(f"Saved vendor record for {vendor_name}.")

    def handle_submit_market_day(self) -> None:
        """Handle manager-only market day context input.

        CHECK: Market-level data is saved separately from vendor-level sales data.
        This prevents customer counts, weather, and programming from being duplicated across vendor rows.
        """
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(raw_body).items()}

        market_date = form.get("market_date", "").strip()
        if not market_date:
            self.redirect_with_message("Market date is required for market day context.")
            return

        new_context = MarketDayContext(
            market_date=market_date,
            weather=form.get("weather", "Not recorded").strip() or "Not recorded",
            count_830=int(form.get("count_830", 0) or 0),
            count_930=int(form.get("count_930", 0) or 0),
            count_1030=int(form.get("count_1030", 0) or 0),
            count_1130=int(form.get("count_1130", 0) or 0),
            music_event=form.get("music_event", "").strip(),
            chefs_tent=form.get("chefs_tent", "").strip(),
            childrens_programming=form.get("childrens_programming", "").strip(),
            community_events=form.get("community_events", "").strip(),
            nonprofit_orgs=form.get("nonprofit_orgs", "").strip(),
        )

        context_records = load_market_day_context()
        context_records = upsert_market_day_context(context_records, new_context)
        save_market_day_context(context_records)
        self.redirect_with_message(f"Saved market day context for {market_date}.")

    def handle_add_vendor(self) -> None:
        """Handle the approved vendor admin form.

        CHECK: Vendor additions go through controlled categories and are persisted to CSV.
        """
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(raw_body).items()}

        vendor_name = " ".join(form.get("new_vendor_name", "").strip().split())
        category = form.get("new_vendor_category", "").strip()
        allowed_categories = {"Produce", "Baked Goods", "Prepared Foods", "Meat", "Other"}

        if not vendor_name:
            self.redirect_with_message("Vendor name is required.")
            return

        if category not in allowed_categories:
            self.redirect_with_message("Please choose a valid vendor category.")
            return

        refresh_approved_vendors()
        APPROVED_VENDORS[vendor_name] = category
        save_approved_vendors()
        self.redirect_with_message(f"Added {vendor_name} to the approved vendor list.")

    def redirect_with_message(self, message: str) -> None:
        """Redirect back to dashboard after form submission."""
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?message={quote_plus(message)}")
        self.end_headers()


# ---------- CLI / APP STARTUP ----------

def build_parser() -> argparse.ArgumentParser:
    """Create command-line options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def run_server(host: str, port: int) -> None:
    """Start the local dashboard server."""
    ensure_sample_file_exists()
    with ThreadingHTTPServer((host, port), DashboardHandler) as server:
        print(f"Dashboard running at http://{host}:{port}")
        server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = build_parser().parse_args(argv)
    if args.serve:
        run_server(args.host, args.port)
    else:
        ensure_sample_file_exists()
        print(f"Sample data ready in {VENDOR_DATA_FILE}")
    return 0


if __name__ == "__main__":
    main()
