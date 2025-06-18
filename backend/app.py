import streamlit as st
import pandas as pd
from db import get_connection
from screener import build_query, load_saved_screens, save_new_screen  # Reuse your query builder

st.set_page_config(page_title="Lotanna's Stock Screener", layout="wide")
st.title("📈 Lotanna's Stock Screener")

st.markdown("""
Welcome to your custom stock screener.  
Use the filters in the sidebar to discover quality investment opportunities based on fundamentals.
""")

# Sidebar filters
st.sidebar.header("🔍 Filter Criteria")

with st.sidebar.expander("📚 What do these metrics mean?"):
    st.markdown("""
- **Sector**: The industry the company operates in (e.g., Technology, Healthcare).
- **P/E Ratio** *(Price to Earnings)*: How much investors pay for each $1 of profit. Lower can mean undervalued.
- **Dividend Yield**: The percentage of the stock price paid back to investors as dividends.
- **Market Capitalization**: The total value of all a company’s shares. Large cap = more stable.
- **EPS (Earnings Per Share)**: Company profit divided by the number of shares. Higher = more profitable.
- **Price-to-Book Ratio**: Compares the stock price to the company’s net worth. Under 1 can suggest undervaluation.
- **Debt-to-Equity**: Shows how much debt a company has vs. shareholder equity. Lower = less financial risk.
    """)

sector = st.sidebar.text_input(
    "Sector (e.g. TECHNOLOGY)", 
    "",
    help="Filter by the company's industry, like TECHNOLOGY, HEALTHCARE, etc."
)

min_pe = st.sidebar.number_input(
    "Min P/E Ratio", 
    value=0.0, 
    step=0.1,
    help="Price-to-Earnings ratio. Shows how much investors pay for $1 of earnings. Lower can mean undervalued."
)

max_pe = st.sidebar.number_input(
    "Max P/E Ratio", 
    value=100.0, 
    step=0.1,
    help="Set an upper limit for the P/E ratio. High P/E often reflects growth expectations or overvaluation."
)

min_div = st.sidebar.number_input(
    "Min Dividend Yield (%)", 
    value=0.0, 
    step=0.1,
    help="Percentage of the stock price returned to investors as dividends annually. Great for income-focused investors."
)

min_mcap = st.sidebar.number_input(
    "Min Market Cap", 
    value=0,
    help="Total market value of a company. Large cap companies are usually more stable and less volatile."
)

min_eps = st.sidebar.number_input(
    "Min EPS", 
    value=0.0, 
    step=0.1,
    help="Earnings Per Share. Indicates how much profit the company makes per share. Higher = more profitable."
)

max_pb = st.sidebar.number_input(
    "Max Price-to-Book Ratio", 
    value=100.0, 
    step=0.1,
    help="Compares stock price to the company’s book value (assets - liabilities). Under 1 might suggest undervaluation."
)

max_debt = st.sidebar.number_input(
    "Max Debt-to-Equity", 
    value=100.0, 
    step=0.1,
    help="Measures how much debt a company has compared to its shareholder equity. Lower = less financial risk."
)

sort_by = st.sidebar.selectbox(
    "Sort by", 
    ["market_cap", "pe_ratio", "dividend_yield", "eps", "pb_ratio", "debt_to_equity"],
    help="Choose which metric to sort the screened results by."
)

order = st.sidebar.radio(
    "Order", 
    ["asc", "desc"],
    help="Sort in ascending or descending order."
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Save or Load Screens")

# Save current screen
screen_name = st.sidebar.text_input("Name this screen", placeholder="e.g. Dividend Picks")
if st.sidebar.button("✅ Save This Screen"):
    if screen_name.strip() == "":
        st.sidebar.warning("Please enter a name for this screen.")
    else:
        manual_filters = {
            "sector": sector,
            "min_pe": min_pe,
            "max_pe": max_pe,
            "min_div": min_div,
            "min_mcap": min_mcap,
            "min_eps": min_eps,
            "max_pb": max_pb,
            "max_debt": max_debt,
            "sort_by": sort_by,
            "order": order
        }
        save_new_screen(screen_name, manual_filters)
        st.sidebar.success(f"Saved screen as '{screen_name}'")

# Load saved screens
saved_screens = load_saved_screens()
screen_options = [s["label"] for s in saved_screens]
selected_screen = st.sidebar.selectbox("📂 Load Saved Screen", ["None"] + screen_options)

# Use filters from selected screen if available, else from manual inputs
manual_filters = {
    "sector": sector,
    "min_pe": min_pe,
    "max_pe": max_pe,
    "min_div": min_div,
    "min_mcap": min_mcap,
    "min_eps": min_eps,
    "max_pb": max_pb,
    "max_debt": max_debt,
    "sort_by": sort_by,
    "order": order
}

if selected_screen != "None":
    selected = next(s for s in saved_screens if s["label"] == selected_screen)
    filters = selected["filters"]
    st.sidebar.info(f"Loaded screen: {selected_screen}")
else:
    filters = manual_filters

# Query the database
query, params = build_query(filters)

try:
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
finally:
    conn.close()

# Display results
if df.empty:
    st.warning("⚠️ No matching stocks found. Try adjusting your filters.")
else:
    st.success(f"✅ {len(df)} stocks matched your criteria.")
    st.dataframe(df)

    # Download CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Results as CSV", csv, "filtered_stocks.csv", "text/csv")

    # Optional explanation per stock (simple form)
    if st.checkbox("Show match explanation per stock"):
        df["why_it_matched"] = df.apply(
            lambda row: f"P/E={row['pe_ratio']}, Div Yield={row['dividend_yield']}, Debt/Equity={row['debt_to_equity']}",
            axis=1
        )
        st.dataframe(df[["symbol", "name", "why_it_matched"]])