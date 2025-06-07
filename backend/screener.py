from db import get_connection
import pandas as pd

def get_user_filters():
    return {
        "sector": input("Sector (blank to skip): "),
        "min_pe": input("Min P/E ratio (blank to skip): "),
        "max_pe": input("Max P/E ratio (blank to skip): "),
        "min_div": input("Min Dividend Yield % (blank to skip): "),
        "min_mcap": input("Min Market Cap (e.g. 10000000000) (blank to skip): "),
        "min_eps": input("Min EPS (blank to skip): "),
        "max_pb": input("Max P/B Ratio (blank to skip): "),
        "max_debt": input("Max Debt-to-Equity Ratio (blank to skip): "),
        "sort_by": input("Sort by (e.g. dividend_yield, pe_ratio, eps): ").strip(),
        "order": input("Order (asc/desc): ").strip().lower()
    }

def build_query(filters):
    conditions = []
    params = []

    if filters["sector"]:
        conditions.append("UPPER(sector) = %s")
        params.append(filters["sector"].upper())
    if filters["min_pe"]:
        conditions.append("pe_ratio >= %s")
        params.append(float(filters["min_pe"]))
    if filters["max_pe"]:
        conditions.append("pe_ratio <= %s")
        params.append(float(filters["max_pe"]))
    if filters["min_div"]:
        conditions.append("dividend_yield >= %s")
        params.append(float(filters["min_div"]) / 100)
    if filters["min_mcap"]:
        conditions.append("market_cap >= %s")
        params.append(int(filters["min_mcap"]))
    if filters["min_eps"]:
        conditions.append("eps >= %s")
        params.append(float(filters["min_eps"]))
    if filters["max_pb"]:
        conditions.append("pb_ratio <= %s")
        params.append(float(filters["max_pb"]))
    if filters["max_debt"]:
        conditions.append("debt_to_equity <= %s")
        params.append(float(filters["max_debt"]))

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    sort_clause = f"ORDER BY {filters['sort_by']} {filters['order'].upper()}" if filters["sort_by"] else "ORDER BY market_cap DESC"

    query = f"""
        SELECT symbol, name, sector, market_cap, pe_ratio, dividend_yield, eps, pb_ratio, debt_to_equity
        FROM stock_fundamentals
        WHERE {where_clause}
        {sort_clause};
    """
    return query, params

def run_query(query, params):
    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

def display_results(df):
    if df.empty:
        print("\nNo results found with the selected filters.")
        return

    print("\nFiltered Results:")
    print(df.to_string(index=False))

    if input("\nExport to CSV? (y/n): ").lower() == 'y':
        df.to_csv("screener_results.csv", index=False)
        print("Saved to screener_results.csv")

def run_screener():
    print("=== STOCK SCREENER ===")
    filters = get_user_filters()
    query, params = build_query(filters)
    df = run_query(query, params)
    display_results(df)