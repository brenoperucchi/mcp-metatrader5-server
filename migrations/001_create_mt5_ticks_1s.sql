-- Migration: Create mt5_ticks_1s table for tick persistence
-- Database: jumpstart_development
-- Schema: trading
-- Run on macOS PostgreSQL

\c jumpstart_development

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS trading;

-- Drop existing table if structure is wrong (CAREFUL!)
-- Uncomment only if you want to recreate:
-- DROP TABLE IF EXISTS trading.mt5_ticks_1s;

-- Create table with correct structure
CREATE TABLE IF NOT EXISTS trading.mt5_ticks_1s (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol)
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_mt5_ticks_1s_symbol_time
ON trading.mt5_ticks_1s (symbol, timestamp DESC);

-- Verify table structure
\d trading.mt5_ticks_1s

-- Grant permissions (if needed)
GRANT ALL ON trading.mt5_ticks_1s TO postgres;

-- Test insert
INSERT INTO trading.mt5_ticks_1s (timestamp, symbol, open, high, low, close, volume, bid, ask)
VALUES (NOW(), 'TEST', 100.0, 100.0, 100.0, 100.0, 1000, 99.9, 100.1)
ON CONFLICT (timestamp, symbol) DO NOTHING;

-- Verify insert
SELECT * FROM trading.mt5_ticks_1s WHERE symbol = 'TEST';

-- Cleanup test
DELETE FROM trading.mt5_ticks_1s WHERE symbol = 'TEST';

-- Show table info
SELECT
    schemaname,
    tablename,
    tableowner,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'trading' AND tablename = 'mt5_ticks_1s';

\echo 'Migration complete! Table trading.mt5_ticks_1s ready for tick persistence.'
