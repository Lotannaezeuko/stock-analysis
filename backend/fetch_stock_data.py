from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

# Load environment variables
load_dotenv()

# Constants
api_key = os.getenv('API_KEY')
url_template = (
    "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={apikey}&outputsize=full"
)

# Flask app
app = Flask(__name__)

# Function to fetch full historical data for a single stock
def fetch_stock_data(symbol):
    url = url_template.format(symbol=symbol, apikey=api_key)
    response = requests.get(url)
    data = response.json()

    if 'Time Series (Daily)' not in data:
        return {"error": f"Error fetching data for {symbol}: {data.get('Note', 'Unknown error')}"}

    daily_data = data['Time Series (Daily)']
    ten_years_ago = datetime.now() - timedelta(days=365 * 10)

    # Filter the data to include only the last 10 years
    filtered_data = [
        {
            "date": date,
            "open_price": daily_info['1. open'],
            "high_price": daily_info['2. high'],
            "low_price": daily_info['3. low'],
            "close_price": daily_info['4. close'],
            "volume": daily_info['5. volume'],
        }
        for date, daily_info in daily_data.items()
        if datetime.strptime(date, "%Y-%m-%d") >= ten_years_ago
    ]

    return filtered_data

# Endpoint to fetch data for a single stock
@app.route('/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol):
    data = fetch_stock_data(symbol)
    return jsonify(data)

# Endpoint to fetch data for multiple stocks
@app.route('/stocks', methods=['GET'])
def get_multiple_stocks_data():
    symbols = request.args.get('symbols', '')  # e.g., "AAPL,GOOGL,MSFT"
    symbol_list = symbols.split(',')

    all_data = {}
    for symbol in symbol_list:
        all_data[symbol] = fetch_stock_data(symbol)

    return jsonify(all_data)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)