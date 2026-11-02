import streamlit as st
import pandas as pd
from db import get_connection
from screener import build_query, load_saved_screens, save_new_screen

st.set_page_config(page_title="Lotanna's Stock Screener", layout="wide")
st.title("📈 Lotanna's Stock Screener")

st.markdown("""
Screen the stocks tracked by my daily ETL pipeline, then explore their price history below.
Prices (open, high, low, close, volume) are refreshed every weekday from AlphaVantage.
Fundamentals (P/E, EPS, dividend yield, ...) are an earlier snapshot, as that AlphaVantage endpoint is now premium-only.
""")


def read_sql(query, params=None):
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()

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

sectors = read_sql("SELECT DISTINCT sector FROM symbols WHERE is_active ORDER BY sector")["sector"].tolist()
sector_choice = st.sidebar.selectbox("Sector", ["All sectors"] + sectors)
sector = "" if sector_choice == "All sectors" else sector_choice

# Filters left empty don't filter. Stocks without a fundamentals snapshot only
# drop out once you set a fundamentals filter.
min_pe = st.sidebar.number_input("Min P/E Ratio", value=None, step=0.1)
max_pe = st.sidebar.number_input("Max P/E Ratio", value=None, step=0.1)
min_div = st.sidebar.number_input("Min Dividend Yield (%)", value=None, step=0.1)
min_mcap = st.sidebar.number_input("Min Market Cap", value=None, step=1_000_000_000)
min_eps = st.sidebar.number_input("Min EPS", value=None, step=0.1)
max_pb = st.sidebar.number_input("Max Price-to-Book Ratio", value=None, step=0.1)
max_debt = st.sidebar.number_input("Max Debt-to-Equity", value=None, step=0.1)
sort_by = st.sidebar.selectbox(
    "Sort by",
    ["change_pct", "close", "volume", "market_cap", "pe_ratio", "dividend_yield", "eps", "pb_ratio", "debt_to_equity"],
)
order = st.sidebar.radio("Order", ["desc", "asc"])

# -------- Save/Load Screens --------
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Save or Load Screens")

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

saved_screens = load_saved_screens()
screen_options = [s["label"] for s in saved_screens]
selected_screen = st.sidebar.selectbox("📂 Load Saved Screen", ["None"] + screen_options)

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

# Apply selected screen if chosen
if selected_screen != "None":
    selected = next(s for s in saved_screens if s["label"] == selected_screen)
    filters = selected["filters"]
    st.sidebar.info(f"Loaded screen: {selected_screen}")
else:
    filters = manual_filters

# -------- Query + Display --------
query, params = build_query(filters)
df = read_sql(query, params)

# Results display
if df.empty:
    st.warning("⚠️ No matching stocks found. Try adjusting your filters.")
else:
    price_date = df["price_date"].dropna().max()
    as_of = f" · prices as of {price_date:%d %b %Y}" if pd.notna(price_date) else ""
    st.success(f"✅ {len(df)} stocks matched your criteria{as_of}.")
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "symbol": "Symbol",
            "name": "Name",
            "sector": "Sector",
            "price_date": st.column_config.DateColumn("Price date", format="D MMM YYYY"),
            "open": st.column_config.NumberColumn("Open", format="dollar"),
            "high": st.column_config.NumberColumn("High", format="dollar"),
            "low": st.column_config.NumberColumn("Low", format="dollar"),
            "close": st.column_config.NumberColumn("Close", format="dollar"),
            "change_pct": st.column_config.NumberColumn("Change", format="percent"),
            "volume": st.column_config.NumberColumn("Volume", format="compact"),
            "market_cap": st.column_config.NumberColumn("Market cap*", format="compact"),
            "pe_ratio": st.column_config.NumberColumn("P/E*", format="%.2f"),
            "dividend_yield": st.column_config.NumberColumn("Div. yield*", format="percent"),
            "eps": st.column_config.NumberColumn("EPS*", format="%.2f"),
            "pb_ratio": st.column_config.NumberColumn("P/B*", format="%.2f"),
            "debt_to_equity": st.column_config.NumberColumn("Debt/Equity*", format="%.2f"),
        },
    )
    st.caption("\\* Fundamentals snapshot (not refreshed daily). Blank where no snapshot exists for that stock.")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Results as CSV", csv, "filtered_stocks.csv", "text/csv")

    if st.checkbox("Show match explanation per stock"):
        df["why_it_matched"] = df.apply(
            lambda row: f"P/E={row['pe_ratio']}, Div Yield={row['dividend_yield']}, Debt/Equity={row['debt_to_equity']}",
            axis=1
        )
        st.dataframe(df[["symbol", "name", "why_it_matched"]])

# -------- Daily prices (loaded by the ETL pipeline) --------
st.markdown("---")
st.header("📉 Daily Prices")

tracked = read_sql("""
    SELECT s.symbol, s.name
    FROM symbols s
    WHERE s.is_active AND EXISTS (SELECT 1 FROM daily_prices d WHERE d.symbol = s.symbol)
    ORDER BY s.symbol
""")

if tracked.empty:
    st.info("No price data yet. Run the pipeline first: `python -m pipeline.run`")
else:
    options = {f"{row.symbol} — {row.name}": row.symbol for row in tracked.itertuples()}
    symbol = options[st.selectbox("Stock", list(options))]

    prices = read_sql("""
        SELECT trade_date, close::float AS close, sma_20::float AS sma_20,
               return_1d::float AS return_1d, volatility_20d::float AS volatility_20d
        FROM price_features
        WHERE symbol = %s
        ORDER BY trade_date
    """, (symbol,))
    latest = prices.iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        f"Close ({latest.trade_date:%d %b %Y})",
        f"${latest.close:,.2f}",
        f"{latest.return_1d:+.2%} on the day" if pd.notna(latest.return_1d) else None,
    )
    col2.metric("20-day average", f"${latest.sma_20:,.2f}" if pd.notna(latest.sma_20) else "n/a")
    col3.metric(
        "20-day volatility",
        f"{latest.volatility_20d:.2%}" if pd.notna(latest.volatility_20d) else "n/a",
        help="Standard deviation of daily returns over the last 20 trading days",
    )

    chart = prices.set_index("trade_date")[["close", "sma_20"]].rename(
        columns={"close": "Close", "sma_20": "20-day average"}
    )
    st.line_chart(chart, color=["#2a78d6", "#eb6834"], y_label="Price (USD)", x_label="")

    with st.expander("Show data table"):
        st.dataframe(prices.sort_values("trade_date", ascending=False), hide_index=True)

    last_run = read_sql("""
        SELECT finished_at, status, rows_loaded FROM pipeline_runs
        WHERE finished_at IS NOT NULL ORDER BY run_id DESC LIMIT 1
    """)
    if not last_run.empty:
        run = last_run.iloc[0]
        st.caption(
            f"Last pipeline run: {run.finished_at:%d %b %Y %H:%M} · {run.status} · {run.rows_loaded} rows loaded"
        )