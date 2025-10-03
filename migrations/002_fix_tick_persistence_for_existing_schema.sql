-- Migration: Fix tick persistence to work with existing mt5_ticks table
-- The mt5_ticks_1s is a materialized view, so we need to insert into mt5_ticks instead

\c jumpstart_development

-- Show current mt5_ticks table structure
\echo 'Current mt5_ticks table structure:'
\d trading.mt5_ticks

-- Show current mt5_ticks_1s materialized view
\echo ''
\echo 'Current mt5_ticks_1s materialized view:'
\d trading.mt5_ticks_1s

-- Verify the base table has the correct columns
\echo ''
\echo 'Sample data from mt5_ticks:'
SELECT * FROM trading.mt5_ticks LIMIT 5;

\echo ''
\echo '===================================================================='
\echo 'ACTION REQUIRED:'
\echo '===================================================================='
\echo 'The tick_persister.py needs to be updated to insert into mt5_ticks'
\echo 'instead of mt5_ticks_1s (which is a materialized view).'
\echo ''
\echo 'Update server_config.json:'
\echo '  "table": "mt5_ticks"  (instead of mt5_ticks_1s)'
\echo '===================================================================='
