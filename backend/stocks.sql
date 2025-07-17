CREATE TABLE IF NOT EXISTS companies (
    company_id SERIAL NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    sector VARCHAR(50),
    country VARCHAR(50),
    description TEXT,
    PRIMARY KEY (company_id)
);

INSERT INTO companies (company_name, symbol, sector, country, description)
VALUES
('Apple Inc.', 'AAPL', 'Technology', 'USA', 'Designs, manufactures, and markets consumer electronics.'),
('Tesla Inc.', 'TSLA', 'Automotive', 'USA', 'Specializes in electric vehicles and renewable energy solutions.'),
('Amazon.com Inc.', 'AMZN', 'E-Commerce', 'USA', 'Operates an online retail platform and provides cloud services.');

CREATE TABLE IF NOT EXISTS stock_prices (
    price_id SERIAL NOT NULL,
    company_id INT NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(10, 2),
    close_price DECIMAL(10, 2),
    high_price DECIMAL(10, 2),
    low_price DECIMAL(10, 2),
    volume BIGINT,
    PRIMARY KEY (price_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

INSERT INTO stock_prices (company_id, date, open_price, close_price, high_price, low_price, volume)
VALUES
(1, '2024-12-01', 178.45, 180.32, 182.50, 176.90, 32150000),
(2, '2024-12-01', 230.12, 234.78, 238.40, 228.90, 41520000),
(3, '2024-12-01', 125.67, 127.89, 129.30, 124.80, 29200000);

CREATE TABLE IF NOT EXISTS financials (
    financial_id SERIAL NOT NULL,
    company_id INT NOT NULL,
    report_date DATE NOT NULL,
    total_assets DECIMAL(15, 2),
    total_liabilities DECIMAL(15, 2),
    operating_income DECIMAL(15, 2),
    total_revenue DECIMAL(15, 2),
    net_income DECIMAL(15, 2),
    PRIMARY KEY (financial_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

INSERT INTO financials (company_id, report_date, total_assets, total_liabilities, operating_income, total_revenue, net_income)
VALUES
(1, '2024-09-30', 351000000000, 289000000000, 26000000000, 89000000000, 21000000000),
(2, '2024-09-30', 91000000000, 35000000000, 18000000000, 69000000000, 12000000000),
(3, '2024-09-30', 212000000000, 102000000000, 32000000000, 57000000000, 27000000000);

CREATE TABLE IF NOT EXISTS news_sentiments (
    news_id SERIAL NOT NULL,
    company_id INT NOT NULL,
    date DATE NOT NULL,
    source VARCHAR(100),
    headline TEXT,
    sentiment_score DECIMAL(3, 2),
    PRIMARY KEY (news_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

INSERT INTO news_sentiments (company_id, date, source, headline, sentiment_score)
VALUES
(1, '2024-12-01', 'Reuters', 'Apple announces new iPhone features.', 0.85),
(2, '2024-12-01', 'CNBC', 'Tesla stock surges on Cybertruck delivery.', 0.75),
(3, '2024-12-01', 'Bloomberg', 'Amazon faces antitrust scrutiny.', -0.65);

CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id SERIAL NOT NULL,
    date DATE NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    value DECIMAL(10, 2),
    PRIMARY KEY (indicator_id)
);

INSERT INTO macro_indicators (date, indicator_name, value)
VALUES
('2024-12-01', 'GDP Growth', 3.5),
('2024-12-01', 'Inflation Rate', 2.1),
('2024-12-01', 'Unemployment Rate', 4.2);

CREATE TABLE stock_fundamentals (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    market_cap BIGINT,
    pe_ratio FLOAT,
    dividend_yield FLOAT,
    pb_ratio FLOAT,
    debt_to_equity FLOAT,
    eps FLOAT
);

CREATE TABLE saved_screens (
  id SERIAL PRIMARY KEY,
  label TEXT NOT NULL,
  filters JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);