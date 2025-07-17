from fetch import fetch_overview, insert_fundamentals
from screener import run_screener

if __name__ == "__main__":
    symbols = [
    "PFE",  # Pfizer – healthcare
    "MMM",  # 3M – industrials
    "DUK",  # Duke Energy – utilities
    "SO",   # Southern Company – utilities
    "FDX",  # FedEx – logistics
    "MO",   # Altria – tobacco
    "AEP",  # American Electric Power – utilities
    "KHC",  # Kraft Heinz – consumer staples
    "DOW",  # Dow Inc – chemicals
    "VZ",   # Verizon – telecom
    "WBA",  # Walgreens Boots Alliance – pharmacy
    "NEM",  # Newmont – gold/mining
    "PGR",  # Progressive – insurance
    "ALL",  # Allstate – insurance
    "BK",   # Bank of New York Mellon – finance
    "TROW", # T. Rowe Price – asset mgmt
    "ADM",  # Archer-Daniels-Midland – agri commodities
    "CL",   # Colgate-Palmolive – consumer staples
    "PSX",  # Phillips 66 – energy
    "AFL",  # Aflac – insurance
    "EXC",  # Exelon – utilities
    "HII",  # Huntington Ingalls – defense
    "STX",  # Seagate – data storage
    "LUV",  # Southwest Airlines – airlines
    "XOM"   # ExxonMobil – energy
    ]
    for symbol in symbols:
        print(f"Fetching {symbol}...")
        data = fetch_overview(symbol)
        if "Symbol" in data:
            insert_fundamentals(data)
            print(f"{symbol} inserted.")
        else:
            print(f"Failed to fetch data for {symbol}")

    run_screener()