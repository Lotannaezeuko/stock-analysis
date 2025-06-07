# 📈 Lotanna's Stock Screener

An interactive, web-based stock screener built with Python, PostgreSQL, and Streamlit.  
It helps investors filter and discover high-quality stocks based on real financial data and user-defined criteria.

---

## 🚀 Features

- 🔍 Filter stocks by:
  - Sector
  - P/E Ratio
  - Dividend Yield
  - Market Capitalization
  - EPS
  - Price-to-Book Ratio
  - Debt-to-Equity
- 📊 Sort results by any key metric
- 📥 Download filtered results as CSV
- 💬 Get explanation text on why each stock matched
- ⚡️ Powered by Alpha Vantage API
- 🐘 PostgreSQL backend with data persistence

---

## 🖥️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python (modular architecture)
- **Database:** PostgreSQL
- **Data Source:** Alpha Vantage API

---

## 📸 Preview

![App Screenshot](your-screenshot-url-if-any)

---

## 📂 Getting Started (Local Setup)

1. **Clone the repo**
    ```bash
    git clone https://github.com/lotannaezeuko/stock-analysis.git
    cd stock-screener
    ```
2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up PostgreSQL**
   - Ensure you have PostgreSQL installed and running
   - Create a database named `stocks`
   - Run the database code below to create the table:
     ```sql
        CREATE TABLE stock_fundamentals (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        market_cap BIGINT,
        pe_ratio FLOAT,
        dividend_yield FLOAT,
        eps FLOAT,
        pb_ratio FLOAT,
        debt_to_equity FLOAT
        );
     ```

4. **Set up environment variables**
   - Create a `.env` file in the root directory
   - Add your Alpha Vantage API key:
     ```
     ALPHA_VANTAGE_API_KEY=your_api_key_here
     ```
   - Create a `.env` file in the root directory
   - Add your PostgreSQL database connection details:
     ``` bash
     DB_HOST=localhost
     DB_NAME=your_db_name
     DB_USER=your_username
     DB_PASSWORD=your_password
     ```
5. **Run the app**
    ```bash
    streamlit run app.py
    ```
