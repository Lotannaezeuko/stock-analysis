from fetch import fetch_overview, insert_fundamentals
from screener import run_screener

if __name__ == "__main__":
    symbols =  ["INTC","T","CSCO","ORCL","ABT","CVS","CAT","UPS","GS","C","PYPL","PLTR","CRM","TGT","NKE","ADBE","BMY","INTU","BA","GM","SBUX","LOW","LMT","SPGI","EL"] # Example symbols
    for symbol in symbols:
        print(f"Fetching {symbol}...")
        data = fetch_overview(symbol)
        if "Symbol" in data:
            insert_fundamentals(data)
            print(f"{symbol} inserted.")
        else:
            print(f"Failed to fetch data for {symbol}")

    run_screener()