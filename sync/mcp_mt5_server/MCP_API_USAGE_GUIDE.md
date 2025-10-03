# MCP MetaTrader5 Server - API Usage Guide

## Overview

This guide shows how to correctly integrate with the MCP MT5 Server from stock-dividend (macOS client). All examples are proven working based on investigation tests that successfully retrieved 391 ticks for the same date range that MT5 CSV export contained.

## Server Information

- **Base URL**: `http://localhost:8000` (when connecting from Windows)
- **Base URL**: `http://192.168.0.235:8000` (when connecting from macOS/WSL)
- **Protocol**: HTTP with JSON-RPC 2.0
- **MCP Endpoint**: `/mcp`
- **Health Check**: `/health`

## Important Notes

### Date Format Requirements

**CRITICAL**: MT5 requires timezone-naive datetime strings in ISO format:

✅ **CORRECT**: `"2025-10-02T00:00:00"`
❌ **WRONG**: `"2025-10-02T00:00:00+00:00"` (timezone suffix breaks MT5)
❌ **WRONG**: `"2025-10-02"` (missing time component)
❌ **WRONG**: Unix timestamps

### Symbol Format

- Use exact symbol name from MT5: `"ITSA3"` (not `"ITSA3.SA"`)
- Symbol must be visible in Market Watch (server auto-selects it)
- Check available symbols first with `get_symbols` tool

## API Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "mt5_connected": true,
  "tick_persistence": "enabled"
}
```

### 2. Get Available Symbols

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbols",
      "arguments": {}
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": ["ITSA3", "PETR4", "VALE3", ...]
  }
}
```

### 3. Get Symbol Information

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info",
      "arguments": {
        "symbol": "ITSA3"
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": {
      "name": "ITSA3",
      "description": "Itaúsa PN",
      "visible": true,
      "digits": 2,
      "trade_contract_size": 1.0,
      "volume_min": 100.0
    }
  }
}
```

### 4. Get Latest Tick

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info_tick",
      "arguments": {
        "symbol": "ITSA3"
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": {
      "time": 1727961600,
      "bid": 9.87,
      "ask": 9.88,
      "last": 9.87,
      "volume": 100
    }
  }
}
```

### 5. Get Historical Ticks by Date Range (PROVEN WORKING)

**This is the most important endpoint for stock-dividend auto-import.**

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "copy_ticks_range",
      "arguments": {
        "symbol": "ITSA3",
        "date_from": "2025-10-02T00:00:00",
        "date_to": "2025-10-03T23:59:59",
        "flags": 2
      }
    }
  }'
```

**Parameters:**
- `symbol`: Symbol name (exact match from MT5)
- `date_from`: Start datetime in ISO format (timezone-naive)
- `date_to`: End datetime in ISO format (timezone-naive)
- `flags`: Tick type flag
  - `0` = COPY_TICKS_INFO (info ticks only)
  - `1` = COPY_TICKS_TRADE (trade ticks only)
  - `2` = COPY_TICKS_ALL (all ticks) **← RECOMMENDED**

**Successful Response (391 ticks):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "time": 1727875200,
        "bid": 9.85,
        "ask": 9.86,
        "last": 9.85,
        "volume": 100,
        "flags": 2
      },
      {
        "time": 1727875201,
        "bid": 9.85,
        "ask": 9.86,
        "last": 9.85,
        "volume": 200,
        "flags": 2
      }
      // ... 389 more ticks
    ]
  }
}
```

**Empty Response (0 ticks - not an error):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": []
  }
}
```

### 6. Get Recent Ticks (from position)

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "copy_ticks_from_pos",
      "arguments": {
        "symbol": "ITSA3",
        "start_pos": 0,
        "count": 10,
        "flags": 2
      }
    }
  }'
```

**Parameters:**
- `start_pos`: Position to start from (0 = most recent)
- `count`: Number of ticks to retrieve
- `flags`: Same as copy_ticks_range

### 7. Get Ticks from Date with Count

**Request:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "copy_ticks_from_date",
      "arguments": {
        "symbol": "ITSA3",
        "date_from": "2025-10-02T09:00:00",
        "count": 100,
        "flags": 2
      }
    }
  }'
```

## Python Integration Example

### Using requests library

```python
import requests
from datetime import datetime, timedelta

# Server configuration
MCP_SERVER_URL = "http://localhost:8000"  # or "http://192.168.0.235:8000"

def mcp_call(tool_name: str, arguments: dict):
    """Call MCP tool via HTTP"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    response = requests.post(
        f"{MCP_SERVER_URL}/mcp",
        json=payload,
        timeout=30
    )
    return response.json()

# Example: Get historical ticks
result = mcp_call("copy_ticks_range", {
    "symbol": "ITSA3",
    "date_from": "2025-10-02T00:00:00",
    "date_to": "2025-10-03T23:59:59",
    "flags": 2
})

if "result" in result:
    ticks = result["result"].get("content", [])
    print(f"Retrieved {len(ticks)} ticks")

    if ticks:
        first_tick = ticks[0]
        last_tick = ticks[-1]

        print(f"First: {first_tick['time']} - {first_tick['last']}")
        print(f"Last: {last_tick['time']} - {last_tick['last']}")
elif "error" in result:
    print(f"Error: {result['error']}")
```

### Date Format Helper

```python
from datetime import datetime, timedelta

def format_mt5_datetime(dt: datetime) -> str:
    """
    Format datetime for MT5 API (timezone-naive ISO format)

    IMPORTANT: MT5 requires timezone-naive strings
    """
    # Remove timezone info if present
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    # Return ISO format without timezone suffix
    return dt.isoformat()

# Example usage
start_date = datetime(2025, 10, 2, 0, 0, 0)
end_date = datetime(2025, 10, 3, 23, 59, 59)

date_from = format_mt5_datetime(start_date)  # "2025-10-02T00:00:00"
date_to = format_mt5_datetime(end_date)      # "2025-10-03T23:59:59"
```

## Common Errors and Solutions

### Error: "Request failed: Connection refused"

**Problem**: Cannot reach MCP server

**Solutions**:
1. Check if server is running: `curl http://localhost:8000/health`
2. Verify correct host/port
3. Check firewall rules (especially for cross-machine connections)

### Error: "Symbol not found" or "Invalid symbol"

**Problem**: Symbol doesn't exist or wrong format

**Solutions**:
1. Call `get_symbols` to get exact symbol name
2. Remove any suffixes (use `"ITSA3"` not `"ITSA3.SA"`)
3. Check if symbol is visible in MT5 Market Watch

### Result: 0 ticks (empty array, no error)

**Problem**: Date range has no data OR date format issue

**Solutions**:
1. Verify dates are timezone-naive: `"2025-10-02T00:00:00"` (no `+00:00`)
2. Check if MT5 has data for this period (export to CSV to verify)
3. Try different date ranges (yesterday, last week)
4. Use `flags: 2` (COPY_TICKS_ALL) for maximum coverage
5. Verify market was open during requested period

### Error: "Object of type coroutine is not JSON serializable"

**Problem**: Server-side async handling issue

**Solution**: This is fixed in latest version (feature/tick-persistence branch merged to main)

## Testing Checklist

Use this checklist to verify your integration:

- [ ] Health check returns `"status": "healthy"`
- [ ] `get_symbols` returns list of symbols including your target
- [ ] `get_symbol_info` returns symbol details
- [ ] `get_symbol_info_tick` returns latest tick
- [ ] `copy_ticks_from_pos` returns recent ticks (count: 10)
- [ ] `copy_ticks_range` returns historical ticks for known date range
- [ ] Date format is timezone-naive ISO format
- [ ] Error handling works for invalid symbols/dates

## Investigation Scripts

Two ready-to-use investigation scripts are available:

### 1. `investigate_ticks_issue_windows.py`
- Tests all endpoints via HTTP API
- Runs on Windows (where MCP server runs)
- Tests multiple date ranges
- Proven to retrieve 391 ticks successfully

### 2. `diagnose_ticks_access.py`
- Tests direct MT5 API connection
- Bypasses HTTP layer
- Verifies MT5 data availability

**Run investigation:**
```bash
# On Windows
python investigate_ticks_issue_windows.py

# Or use batch file
RUN_INVESTIGATION.bat
```

## Performance Notes

### Tick Persistence

The server automatically persists all ticks to PostgreSQL:

- **Database**: PostgreSQL on macOS (192.168.0.235:5432)
- **Table**: `trading.mt5_ticks`
- **Batch size**: 20 ticks or 5 second timeout
- **Backpressure**: Max 1000 ticks in queue
- **Performance**: Enqueue < 0.01ms (non-blocking)

Tick persistence is transparent to API clients and doesn't affect response times.

### Rate Limits

No explicit rate limits, but consider:

- Large date ranges may take time to retrieve from MT5
- Use pagination with `copy_ticks_from_date` + count for large datasets
- Batch multiple symbol requests when possible

## Support and Troubleshooting

### Server Logs

Check server logs for detailed diagnostics:

```bash
# Latest log file
ls -lt logs/mcp_mt5_server/server_*.log | head -1

# Watch logs in real-time
tail -f logs/mcp_mt5_server/server_<timestamp>.log
```

Look for:
- `🔍 copy_ticks_range called:` (request received)
- `✅ MT5 returned X ticks` (successful retrieval)
- `⚠️ MT5 returned None` (no data available)

### Database Verification

Verify ticks are being persisted:

```sql
-- Connect to PostgreSQL
psql -h 192.168.0.235 -U postgres -d jumpstart_development

-- Check recent ticks
SELECT symbol, tick_time, bid, ask, volume
FROM trading.mt5_ticks
WHERE symbol = 'ITSA3'
ORDER BY tick_time DESC
LIMIT 10;

-- Count ticks by symbol
SELECT symbol, COUNT(*) as tick_count
FROM trading.mt5_ticks
GROUP BY symbol
ORDER BY tick_count DESC;
```

## Conclusion

This guide is based on proven working tests that successfully retrieved 391 ticks for the date range 2025-10-02 to 2025-10-03. The MCP server is working correctly. If you encounter issues:

1. Use the investigation scripts to diagnose
2. Check server logs for details
3. Verify date format is timezone-naive
4. Confirm symbol format matches MT5 exactly

For questions or issues, check:
- Server logs: `logs/mcp_mt5_server/`
- Investigation results: `INVESTIGATION_RESULTS.md`
- Database config: `database_configuration.yaml`
