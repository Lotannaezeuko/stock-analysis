import requests
import os
from dotenv import load_dotenv
from db import get_connection

load_dotenv()
API_KEY = os.getenv("API_KEY")

# Fetch stock data from Alpha Vantage
def fetch_overview(symbol):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    res = requests.get(url)
    return res.json()

# Insert stock fundamentals into the database
def insert_fundamentals(data):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO stock_fundamentals
            (symbol, name, sector, market_cap, pe_ratio, dividend_yield, eps, pb_ratio, debt_to_equity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                sector = EXCLUDED.sector,
                market_cap = EXCLUDED.market_cap,
                pe_ratio = EXCLUDED.pe_ratio,
                dividend_yield = EXCLUDED.dividend_yield,
                eps = EXCLUDED.eps,
                pb_ratio = EXCLUDED.pb_ratio,
                debt_to_equity = EXCLUDED.debt_to_equity;
        """
        cursor.execute(query, (
            data.get("Symbol"),
            data.get("Name"),
            data.get("Sector"),
            int(data.get("MarketCapitalization") or 0),
            float(data.get("PERatio") or 0),
            float(data.get("DividendYield") or 0),
            float(data.get("EPS") or 0),
            float(data.get("PriceToBookRatio") or 0),
            float(data.get("DebtToEquity") or 0)
        ))
        conn.commit()
    except Exception as e:
        print("DB Error:", e)
    finally:
        conn.close()