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