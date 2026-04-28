"""
Streamlit dashboard version of the William & Mary Farmers Market app.

This app preserves the key bestversionmarket.py data model and
dashboard logic while making the demo shareable through Streamlit.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path('.')
VENDOR_FILE = DATA_DIR / 'wm_farmers_market_demo.csv'
MARKET_DAY_FILE = DATA_DIR / 'market_day_context.csv'
SCHEDULE_FILE = DATA_DIR / 'vendor_schedule.csv'
APPROVED_VENDOR_FILE = DATA_DIR / 'approved_vendors.csv'

PAGE_TITLE = 'William & Mary Farmers Market Dashboard'
WM_GREEN = '#115740'
WM_GOLD = '#C99700'
SALES_FEE_RATE = 0.06
CUSTOMER_MULTIPLIER = 2.43
CATEGORY_MINIMUMS = {
    'Baked Goods': 1000.0,
    'Prepared Foods': 1000.0,
}
VENDOR_ROLE_RULES = {
    'Weekly Staples': [
        'Green Garden Farm', 'Berry Patch Produce', 'York River Vegetables',
        'Pure Earth Organics', 'Sunny Side Eggs', 'Heritage Hen Farm',
        'Colonial Bakes', 'Daily Bread Co', 'Hearthside Meats',
        'Old Dominion Sausage Co',
    ],
    'Traffic Drivers': [
        'Williamsburg Pickles', 'Colonial Kettle Corn', 'Williamsburg Coffee Co',
    ],
    'Seasonal Vendors': ['Williamsburg Pops', 'Campus Crafts'],
    'Rotating / Biweekly Vendors': ['Pasta Fresca'],
    'Specialty Food Vendors': ['Artisan Cheese Co', 'Salsa Verde Kitchen', 'Spice Route Blends'],
    'Pet & Home Vendors': ['Happy Tails Treats', 'Goat Milk Soap Co'],
}


def parse_bool(value: object) -> bool:
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def format_currency(value: float) -> str:
    return f'${value:,.2f}'


def estimate_attendance_from_counts(row: pd.Series) -> int:
    counts = [row.get('count_830', 0), row.get('count_930', 0), row.get('count_1030', 0), row.get('count_1130', 0)]
    valid = [float(c) for c in counts if pd.notna(c) and float(c) > 0]
    if not valid:
        return 0
    return int(sum(valid) / len(valid) * CUSTOMER_MULTIPLIER)


def load_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, **kwargs)


def load_vendor_data() -> pd.DataFrame:
    df = load_csv(VENDOR_FILE)
    if df.empty:
        return df

    numeric_cols = [
        'reported_sales', 'token_reimbursement', 'paid_amount',
        'count_830', 'count_930', 'count_1030', 'count_1130',
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0.0)

    df['sales_reported'] = df['sales_reported'].apply(parse_bool)
    df['attended'] = df['attended'].apply(parse_bool)
    df['total_sales'] = (df['reported_sales'] + df['token_reimbursement']).round(2)
    df['fee_due'] = df.apply(lambda row: round(row['total_sales'] * SALES_FEE_RATE, 2) if row['sales_reported'] else 0.0, axis=1)
    df['paid'] = df.apply(lambda row: bool(row['sales_reported'] and row['paid_amount'] >= row['fee_due']), axis=1)
    df['balance_due'] = df.apply(lambda row: max(row['fee_due'] - row['paid_amount'], 0.0) if row['sales_reported'] else 0.0, axis=1)
    df['token_net'] = (df['token_reimbursement'] * (1 - SALES_FEE_RATE)).round(2)

    def underperforming(row: pd.Series) -> bool:
        minimum = CATEGORY_MINIMUMS.get(row['category'])
        return bool(minimum is not None and row['total_sales'] < minimum)

    df['underperforming'] = df.apply(underperforming, axis=1)

    def action_needed(row: pd.Series) -> str:
        if not row['sales_reported']:
            return 'Send sales reminder'
        if not row['paid']:
            return 'Send payment reminder'
        return 'Complete'

    df['action_needed'] = df.apply(action_needed, axis=1)
    return df


def load_market_day_context() -> pd.DataFrame:
    df = load_csv(MARKET_DAY_FILE)
    if df.empty:
        return df

    count_cols = ['count_830', 'count_930', 'count_1030', 'count_1130']
    for col in count_cols:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0.0)

    df['estimated_attendance'] = df.apply(estimate_attendance_from_counts, axis=1)
    return df


def load_schedule() -> pd.DataFrame:
    df = load_csv(SCHEDULE_FILE)
    if df.empty:
        return df
    return df


def load_approved_vendors() -> pd.DataFrame:
    df = load_csv(APPROVED_VENDOR_FILE)
    if df.empty:
        return pd.DataFrame(columns=['vendor_name', 'category'])
    return df


def vendor_role_for(vendor_name: str) -> str:
    for role, names in VENDOR_ROLE_RULES.items():
        if vendor_name in names:
            return role
    return 'Other Vendors'


def answer_question(question: str, vendor_df: pd.DataFrame, market_df: pd.DataFrame) -> str:
    q = str(question).strip().lower()
    if not q:
        return ''

    name_lists = {
        'follow' : vendor_df.loc[~vendor_df['paid'], 'vendor_name'].unique(),
        'underperform': vendor_df.loc[vendor_df['underperforming'], 'vendor_name'].unique(),
    }

    if any(term in q for term in ['past due', 'follow up', 'need action']):
        vendors = sorted(name_lists['follow'])
        if vendors:
            return f"There are {len(vendors)} vendor(s) needing follow-up: {', '.join(vendors)}."
        return 'No vendor follow-up actions are required at the moment.'

    if any(term in q for term in ['at risk', 'underperform', 'below target']):
        vendors = sorted(name_lists['underperform'])
        if vendors:
            return f"These vendors may need support: {', '.join(vendors)}."
        return 'No vendors are currently underperforming against category expectations.'

    if 'sales' in q:
        total_sales = vendor_df['total_sales'].sum()
        return f'Total recorded sales are {format_currency(total_sales)}.'

    if 'attendance' in q:
        total_attendance = int(market_df['estimated_attendance'].sum())
        return f'Total estimated attendance is {total_attendance}.'

    if 'vendor' in q or 'vendors' in q:
        return f"There are {vendor_df['vendor_name'].nunique()} unique vendors in the dataset."

    return 'Try asking about past due vendors, at-risk vendors, sales, attendance, or vendor count.'


def build_followup_email(vendor_name: str, vendor_df: pd.DataFrame) -> str:
    rows = vendor_df[vendor_df['vendor_name'] == vendor_name]
    if rows.empty:
        return ''

    total_sales = rows['total_sales'].sum()
    balance = rows['balance_due'].sum()
    missing = rows.loc[~rows['sales_reported'], 'market_date'].tolist()
    unpaid = rows.loc[rows['sales_reported'] & ~rows['paid'], 'market_date'].tolist()
    lines = [
        f'Hello {vendor_name},',
        '',
        'This is a quick summary of your recent market records:',
        f'- Reported sales total: {format_currency(total_sales)}',
        f'- Balance due: {format_currency(balance)}',
    ]
    if missing:
        lines.append(f'- Missing sales report for: {", ".join(missing)}')
    if unpaid:
        lines.append(f'- Outstanding payment items for: {", ".join(unpaid)}')
    if not missing and not unpaid:
        lines.append('- All records appear complete and paid.')
    lines += ['', 'Please let us know if you need help with your next market.']
    return '\n'.join(lines)


def build_role_table() -> pd.DataFrame:
    rows = []
    for role, names in VENDOR_ROLE_RULES.items():
        for name in names:
            rows.append({'Vendor Role': role, 'Vendor': name})
    return pd.DataFrame(rows)


def format_event_summary(row: pd.Series) -> str:
    details = [
        row.get('music_event', ''),
        row.get('chefs_tent', ''),
        row.get('childrens_programming', ''),
        row.get('community_events', ''),
        row.get('nonprofit_orgs', ''),
    ]
    return ' | '.join([item for item in details if item])


def build_schedule_summary(schedule_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    if schedule_df.empty:
        return pd.DataFrame()

    summary = []
    for market_date, group in schedule_df.groupby('market_date'):
        scheduled_vendors = sorted(group['vendor_name'].dropna().unique())
        actual_vendors = sorted(
            vendor_df.loc[vendor_df['market_date'] == market_date, 'vendor_name'].dropna().unique()
        )
        missing = sorted(set(scheduled_vendors) - set(actual_vendors))
        estimated_attendance = 0
        day_info = market_df.loc[market_df['market_date'] == market_date]
        if not day_info.empty:
            estimated_attendance = int(day_info['estimated_attendance'].iloc[0])

        summary.append({
            'market_date': market_date,
            'scheduled_vendors': len(scheduled_vendors),
            'reported_vendors': len(actual_vendors),
            'missing_vendors': len(missing),
            'estimated_attendance': estimated_attendance,
            'missing_names': ', '.join(missing),
        })

    return pd.DataFrame(summary)


st.set_page_config(page_title=PAGE_TITLE, layout='wide')

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

st.markdown(f"<div class='dashboard-card'><h1>{PAGE_TITLE}</h1><p class='note'>A Streamlit-ready version of the full market operations dashboard.</p></div>", unsafe_allow_html=True)

vendor_df = load_vendor_data()
market_df = load_market_day_context()
schedule_df = load_schedule()
approved_vendors_df = load_approved_vendors()

missing_files = [
    f.name for f in [VENDOR_FILE, MARKET_DAY_FILE, SCHEDULE_FILE, APPROVED_VENDOR_FILE] if not f.exists()
]
if missing_files:
    st.error(f"Missing data files: {', '.join(missing_files)}")
    st.stop()

if vendor_df.empty or market_df.empty:
    st.error('Vendor or market-day data is missing or could not be loaded.')
    st.stop()

market_df['event_summary'] = market_df.apply(format_event_summary, axis=1)
market_df['attendance_total'] = market_df['estimated_attendance']

summary_total_sales = float(vendor_df['total_sales'].sum())
summary_fees = float(vendor_df['fee_due'].sum())
summary_attendance = int(market_df['estimated_attendance'].sum())
summary_vendors = int(vendor_df['vendor_name'].nunique())
summary_underperforming = int(vendor_df['underperforming'].sum())
summary_open_followups = int(vendor_df.loc[vendor_df['action_needed'] != 'Complete'].shape[0])

tabs = st.tabs(['Overview', 'Vendor Ops', 'Schedule', 'Admin', 'Raw Data'])

with tabs[0]:
    st.markdown("<div class='dashboard-card'><h2>Quick Metrics</h2>", unsafe_allow_html=True)
    st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
    for label, value in [
        ('Total Vendor Sales', format_currency(summary_total_sales)),
        ('Estimated 6% Fees', format_currency(summary_fees)),
        ('Season-to-Date Attendance', f'{summary_attendance:,}'),
        ('Unique Vendors', f'{summary_vendors:,}'),
        ('Underperforming Vendors', f'{summary_underperforming:,}'),
        ('Open Follow-Ups', f'{summary_open_followups:,}'),
    ]:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("<div class='dashboard-card gold'><h2>Manager Summary</h2>", unsafe_allow_html=True)
    bullets = [
        f'Total recorded sales are {format_currency(summary_total_sales)}.',
        f'Estimated market fees are {format_currency(summary_fees)}.',
        f'Estimated season attendance is {summary_attendance:,}.',
    ]
    if summary_underperforming:
        bullets.append(f'{summary_underperforming} vendor(s) are below category expectations.')
    if summary_open_followups:
        bullets.append(f'{summary_open_followups} record(s) need follow-up action.')
    else:
        bullets.append('All vendor records appear complete.')

    st.markdown('<ul class="summary-list">', unsafe_allow_html=True)
    for item in bullets:
        st.markdown(f'<li>{item}</li>', unsafe_allow_html=True)
    st.markdown('</ul></div>', unsafe_allow_html=True)

    st.markdown("<div class='dashboard-card'><h2>Weather & Attendance</h2></div>", unsafe_allow_html=True)
    if 'weather' in market_df.columns:
        with st.expander('Weather summary and attendance by market day'):
            st.dataframe(market_df[['market_date', 'weather', 'estimated_attendance', 'event_summary']].sort_values('market_date'))
            if not market_df['weather'].isna().all():
                weather_groups = market_df.groupby('weather')['estimated_attendance'].mean().reset_index()
                st.bar_chart(weather_groups.set_index('weather')['estimated_attendance'])
    else:
        st.info('No weather data is available in the market-day context file.')

    question = st.text_input('Ask a question about this market data:')
    if question:
        answer = answer_question(question, vendor_df, market_df)
        st.markdown(f"<div class='agent-answer'>{answer}</div>", unsafe_allow_html=True)

with tabs[1]:
    st.markdown("<div class='dashboard-card gold'><h2>Vendor Operations</h2></div>", unsafe_allow_html=True)
    action_df = vendor_df.copy()
    display_cols = [
        'market_date', 'vendor_name', 'category', 'total_sales', 'token_reimbursement',
        'token_net', 'fee_due', 'paid_amount', 'balance_due', 'action_needed', 'sales_reported', 'paid', 'underperforming',
    ]
    st.dataframe(action_df[display_cols].sort_values(['market_date', 'vendor_name']))

    if summary_open_followups:
        st.subheader('Follow-up vendors')
        followups = action_df[action_df['action_needed'] != 'Complete']
        st.dataframe(followups[['market_date', 'vendor_name', 'action_needed', 'balance_due', 'fee_due']])
        selected_vendor = st.selectbox('Select a vendor to view a follow-up email', sorted(followups['vendor_name'].unique()))
        if selected_vendor:
            st.code(build_followup_email(selected_vendor, action_df), language='text')
    else:
        st.success('No follow-up vendors currently require action.')

    st.markdown("<div class='dashboard-card'><h2>Vendor Role Intelligence</h2></div>", unsafe_allow_html=True)
    st.dataframe(build_role_table())

with tabs[2]:
    st.markdown("<div class='dashboard-card gold'><h2>Schedule & Attendance</h2></div>", unsafe_allow_html=True)
    if not schedule_df.empty:
        schedule_summary = build_schedule_summary(schedule_df, market_df)
        st.dataframe(schedule_summary.sort_values('market_date'))
    else:
        st.info('No schedule data is available.')

    st.markdown("<div class='dashboard-card'><h2>Market Day Context</h2></div>", unsafe_allow_html=True)
    st.dataframe(market_df[['market_date', 'weather', 'count_830', 'count_930', 'count_1030', 'count_1130', 'estimated_attendance', 'event_summary']].sort_values('market_date'))

with tabs[3]:
    st.markdown("<div class='dashboard-card gold'><h2>Admin & Approved Vendors</h2></div>", unsafe_allow_html=True)
    if not approved_vendors_df.empty:
        st.dataframe(approved_vendors_df.sort_values('vendor_name'))
    else:
        st.info('Approved vendor list is not available.')

with tabs[4]:
    st.markdown("<div class='dashboard-card'><h2>Raw Data</h2></div>", unsafe_allow_html=True)
    with st.expander('Vendor data'):
        st.dataframe(vendor_df)
    with st.expander('Market day context'):
        st.dataframe(market_df)
    with st.expander('Vendor schedule'):
        st.dataframe(schedule_df)
    with st.expander('Approved vendors'):
        st.dataframe(approved_vendors_df)
