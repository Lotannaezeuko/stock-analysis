from db import get_connection
import pandas as pd

def run_screener():
    sector = input("Enter sector (leave blank to skip): ")
    min_pe = input("Min P/E ratio (leave blank to skip): ")
    max_pe = input("Max P/E ratio (leave blank to skip): ")
    min_div = input("Min Dividend Yield % (leave blank to skip): ")
    min_mcap = input("Min Market Cap (e.g. 10000000000) (leave blank to skip): ")
    min_eps = input("Min EPS (leave blank to skip): ")
    max_pb = input("Max P/B Ratio (leave blank to skip): ")
    max_debt = input("Max Debt-to-Equity Ratio (leave blank to skip): ")

    filters = []
    params = []

    if sector:
        filters.append("UPPER(sector) = %s")
        params.append(sector.upper())

    if min_pe:
        filters.append("pe_ratio >= %s")
        params.append(float(min_pe))

    if max_pe:
        filters.append("pe_ratio <= %s")
        params.append(float(max_pe))

    if min_div:
        filters.append("dividend_yield >= %s")
        params.append(float(min_div) / 100)  # Convert % to decimal

    if min_mcap:
        filters.append("market_cap >= %s")
        params.append(int(min_mcap))

    if min_eps:
        filters.append("eps >= %s")
        params.append(float(min_eps))

    if max_pb:
        filters.append("pb_ratio <= %s")
        params.append(float(max_pb))

    if max_debt:
        filters.append("debt_to_equity <= %s")
        params.append(float(max_debt))

    where_clause = " AND ".join(filters) if filters else "TRUE"

    query = f"""
        SELECT symbol, name, sector, market_cap, pe_ratio, dividend_yield, eps, pb_ratio, debt_to_equity
        FROM stock_fundamentals
        WHERE {where_clause}
        ORDER BY market_cap DESC;
    """

    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        print("\nFiltered Results:")
        print(df.to_string(index=False))

        export = input("\nExport to CSV? (y/n): ")
        if export.lower() == 'y':
            df.to_csv("screener_results.csv", index=False)
            print("Saved as screener_results.csv")

    except Exception as e:
        print("Error running screener:", e)
    finally:
        conn.close()