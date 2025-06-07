import streamlit as st
import pandas as pd
from db import get_connection
from screener import build_query  # Reuse your query builder

st.set_page_config(page_title="Lotanna's Stock Screener", layout="wide")
st.title("📈 Lotanna's Stock Screener")

st.markdown("""
Welcome to your custom stock screener.  
Use the filters in the sidebar to discover quality investment opportunities based on fundamentals.
""")

# Sidebar filters
st.sidebar.header("🔍 Filter Criteria")

sector = st.sidebar.text_input("Sector (e.g. TECHNOLOGY)", "")
min_pe = st.sidebar.number_input("Min P/E Ratio", value=0.0, step=0.1)
max_pe = st.sidebar.number_input("Max P/E Ratio", value=100.0, step=0.1)
min_div = st.sidebar.number_input("Min Dividend Yield (%)", value=0.0, step=0.1)
min_mcap = st.sidebar.number_input("Min Market Cap", value=0)
min_eps = st.sidebar.number_input("Min EPS", value=0.0, step=0.1)
max_pb = st.sidebar.number_input("Max Price-to-Book Ratio", value=100.0, step=0.1)
max_debt = st.sidebar.number_input("Max Debt-to-Equity", value=100.0, step=0.1)

sort_by = st.sidebar.selectbox("Sort by", ["market_cap", "pe_ratio", "dividend_yield", "eps", "pb_ratio", "debt_to_equity"])
order = st.sidebar.radio("Order", ["asc", "desc"])

# Assemble filters
filters = {
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