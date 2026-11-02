-- Stock universe. 20 active tickers, so daily price loads (1 call each) leave
-- 5 of the free tier's 25 daily calls for refreshing earnings.
-- To change what the pipeline tracks, edit this file and re-run it.
-- Re-runnable: existing symbols are updated, not duplicated.
INSERT INTO symbols (symbol, name, sector, is_active) VALUES
    -- Technology
    ('AAPL', 'Apple',                      'Information Technology', TRUE),
    ('MSFT', 'Microsoft',                  'Information Technology', TRUE),
    ('NVDA', 'NVIDIA',                     'Information Technology', TRUE),
    ('ORCL', 'Oracle',                     'Information Technology', TRUE),
    ('STX',  'Seagate',                    'Information Technology', TRUE),
    ('GOOGL','Alphabet',                   'Communication Services', TRUE),
    ('META', 'Meta Platforms',             'Communication Services', TRUE),
    ('AMZN', 'Amazon',                     'Consumer Discretionary', TRUE),
    -- Everything else
    ('PFE',  'Pfizer',                     'Healthcare',             TRUE),
    ('MMM',  '3M',                         'Industrials',            TRUE),
    ('FDX',  'FedEx',                      'Industrials',            TRUE),
    ('DUK',  'Duke Energy',                'Utilities',              TRUE),
    ('MO',   'Altria',                     'Consumer Staples',       TRUE),
    ('CL',   'Colgate-Palmolive',          'Consumer Staples',       TRUE),
    ('VZ',   'Verizon',                    'Communication Services', TRUE),
    ('NEM',  'Newmont',                    'Materials',              TRUE),
    ('PGR',  'Progressive',                'Financials',             TRUE),
    ('JPM',  'JPMorgan Chase',             'Financials',             TRUE),
    ('PSX',  'Phillips 66',                'Energy',                 TRUE),
    ('XOM',  'ExxonMobil',                 'Energy',                 TRUE),
    -- Paused to stay within the free API limit (kept so history isn't orphaned)
    ('SO',   'Southern Company',           'Utilities',              FALSE),
    ('AFL',  'Aflac',                      'Financials',             FALSE),
    ('TROW', 'T. Rowe Price',              'Financials',             FALSE),
    ('ADM',  'Archer-Daniels-Midland',     'Consumer Staples',       FALSE),
    ('HII',  'Huntington Ingalls',         'Industrials',            FALSE),
    ('LUV',  'Southwest Airlines',         'Industrials',            FALSE),
    ('DOW',  'Dow Inc',                    'Materials',              FALSE)
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    sector = EXCLUDED.sector,
    is_active = EXCLUDED.is_active;
