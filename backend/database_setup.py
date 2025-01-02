from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_connection():
    """Create and return a database connection"""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )

def insert_stock_data(symbol: str, data: list):
    """
    Insert stock data into the database
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        data: List of dictionaries containing daily stock data
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get or insert stock symbol
        cur.execute("""
            INSERT INTO stocks (symbol)
            VALUES (%s)
            ON CONFLICT (symbol) DO UPDATE SET symbol = EXCLUDED.symbol
            RETURNING id;
        """, (symbol,))
        stock_id = cur.fetchone()[0]
        
        # Prepare data for batch insert
        stock_prices_data = [
            (
                stock_id,
                datetime.strptime(day['date'], '%Y-%m-%d').date(),
                float(day['open_price']),
                float(day['high_price']),
                float(day['low_price']),
                float(day['close_price']),
                int(day['volume'])
            )
            for day in data
        ]
        
        # Batch insert stock prices
        execute_batch(cur, """
            INSERT INTO stock_prices (
                stock_id, date, open_price, high_price, 
                low_price, close_price, volume
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stock_id, date) 
            DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume;
        """, stock_prices_data)
        
        conn.commit()
        print(f"Successfully inserted data for {symbol}")
        
    except Exception as e:
        print(f"Error inserting data for {symbol}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()