from fetch import fetch_overview, insert_fundamentals

if __name__ == "__main__":
    symbols = ["AAPL", "MSFT", "JNJ", "NVDA", "V"]  # Example symbols
    for symbol in symbols:
        print(f"Fetching {symbol}...")
        data = fetch_overview(symbol)
        if "Symbol" in data:
            insert_fundamentals(data)
            print(f"{symbol} inserted.")
        else:
            print(f"Failed to fetch data for {symbol}")