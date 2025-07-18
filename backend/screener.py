from db import get_connection
import pandas as pd
import json

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

def preset_dividend_payers():
    return {
        "sector": "",
        "min_pe": "5",
        "max_pe": "20",
        "min_div": "4",
        "min_mcap": "10000000000",
        "min_eps": "",
        "max_pb": "",
        "max_debt": "1",
        "sort_by": "dividend_yield",
        "order": "desc"
    }

def preset_growth_stocks():
    return {
        "sector": "",
        "min_pe": "15",
        "max_pe": "",
        "min_div": "0",
        "min_mcap": "",
        "min_eps": "3",
        "max_pb": "10",
        "max_debt": "0.5",
        "sort_by": "eps",
        "order": "desc"
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
    print("1. Manual filters")
    print("2. Top Dividend Payers")
    print("3. Growth Stocks")
    print("4. Load a saved screen")
    mode = input("Choose screener mode (1/2/3/4): ").strip()

    if mode == "1":
        filters = get_user_filters()
    elif mode == "2":
        filters = preset_dividend_payers()
    elif mode == "3":
        filters = preset_growth_stocks()
    elif mode == "4":
        screens = load_saved_screens()
        print("\nSaved Screens:")
        for i, s in enumerate(screens):
            print(f"{i + 1}. {s['label']}")
        idx = input("Pick one (number): ").strip()
        try:
            filters = screens[int(idx) - 1]["filters"]
        except:
            print("Invalid selection. Using manual filters.")
            filters = get_user_filters()
    else:
        print("Invalid option. Defaulting to manual.")
        filters = get_user_filters()

    query, params = build_query(filters)
    df = run_query(query, params)
    display_results(df)

def load_saved_screens():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT label, filters FROM saved_screens ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [{"label": r[0], "filters": r[1]} for r in rows]
    except Exception as e:
        print(f"Error loading saved screens: {e}")
        return []

def save_new_screen(label, filters):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO saved_screens (label, filters) VALUES (%s, %s)",
            (label, json.dumps(filters))
        )
        conn.commit()
        conn.close()
        print(f"Screen '{label}' saved.")
    except Exception as e:
        print(f"Error saving screen: {e}")