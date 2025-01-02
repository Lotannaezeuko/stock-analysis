from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import psycopg2
import requests

load_dotenv()

app = Flask(__name__)

# PostgreSQL connection details
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', 5432)
    )

@app.route('/fetch_api_data', methods=['GET'])
def fetch_api_data():
    # Fetch stock data from the API
    stock_symbol = "AAPL"
    api_key = os.getenv('API_KEY')
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock_symbol}&apikey={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Display fetched data for testing
        daily_data = data.get('Time Series (Daily)', {})
        if not daily_data:
            return jsonify({"error": "No data found for the requested symbol."}), 404
        
        # Parse data to return as JSON
        parsed_data = []
        for date, daily_info in daily_data.items():
            parsed_data.append({
                "date": date,
                "open_price": daily_info['1. open'],
                "high_price": daily_info['2. high'],
                "low_price": daily_info['3. low'],
                "close_price": daily_info['4. close'],
                "volume": daily_info['5. volume']
            })
        
        return jsonify(parsed_data), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to fetch data: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)