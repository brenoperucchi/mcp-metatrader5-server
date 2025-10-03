# 🚨 URGENT: get_symbol_info_tick AsyncIO Error

**Date**: 2025-10-03 16:08
**Status**: 🔴 BLOCKER

---

## Error

When calling `get_symbol_info_tick` endpoint, the MCP server returns:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -1,
    "message": "asyncio.run() cannot be called from a running event loop"
  }
}
```

## Test Case

```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info_tick",
      "arguments": {"symbol": "ITSA3"}
    }
  }'
```

**Result**: Error (see above)

## Root Cause

The `get_symbol_info_tick` tool implementation on the MCP server (Windows) is using:

```python
# ❌ WRONG - inside async handler:
return asyncio.run(some_async_function())

# ✅ CORRECT - inside async handler:
return await some_async_function()
```

## Impact

- ❌ **Live mode broken** - cannot fetch real-time ticks
- ❌ **Tick persistence broken** - no ticks are being saved to PostgreSQL
- ✅ **Backtest mode works** - uses database directly

## Comparison

### get_symbol_info (OLD endpoint) - WORKS ✅
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info",
      "arguments": {"symbol": "ITSA3"}
    }
  }'
```

**Result**: Success (returns static symbol metadata)

### get_symbol_info_tick (NEW endpoint) - FAILS ❌
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info_tick",
      "arguments": {"symbol": "ITSA3"}
    }
  }'
```

**Result**: Error (asyncio.run in event loop)

## Historical Context

This endpoint worked before! From our testing session earlier today:

```python
# This worked and returned 491 ticks:
response = requests.post(
    "http://192.168.0.125:8000/mcp",
    json={
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
    }
)
# Result: ✅ 491 ticks successfully
```

So `copy_ticks_range` works, but `get_symbol_info_tick` doesn't!

## Fix Required (on MCP Server)

In `src/mcp_metatrader5_server/market_data.py` (or wherever `get_symbol_info_tick` is implemented):

### Find this pattern:
```python
@tool
async def get_symbol_info_tick(symbol: str):
    # ... some code ...

    # ❌ WRONG:
    tick_data = asyncio.run(mt5.symbol_info_tick(symbol))

    # or

    # ❌ WRONG:
    def sync_wrapper():
        return mt5.symbol_info_tick(symbol)

    return asyncio.run(sync_wrapper())
```

### Replace with:
```python
@tool
async def get_symbol_info_tick(symbol: str):
    # ... some code ...

    # ✅ CORRECT - run in thread pool:
    loop = asyncio.get_event_loop()
    tick_data = await loop.run_in_executor(
        None,  # default executor
        mt5.symbol_info_tick,
        symbol
    )

    # or use the existing pattern from copy_ticks_range
    # (which works correctly)
```

## Client Side Status

✅ **stock-dividend (macOS) is ready:**
- All 5 files updated to use `get_symbol_info_tick`
- `SimpleMCPClient.get_symbol_info_tick()` method added
- Client code is async/await compliant
- No `asyncio.run()` calls in client

❌ **Waiting for server fix**

## Testing After Fix

After the MCP server is fixed, test with:

```bash
# Test endpoint directly
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_symbol_info_tick",
      "arguments": {"symbol": "ITSA3"}
    }
  }'

# Expected result:
# {
#   "jsonrpc": "2.0",
#   "id": 1,
#   "result": {
#     "content": {
#       "time": 1234567890,
#       "bid": 11.15,
#       "ask": 11.20,
#       "last": 11.17,
#       "volume": 100
#     }
#   }
# }
```

Then test live mode:

```bash
# On macOS
python3 src/trading/unified_trading_engine.py \
  --result logs/optimize_unified/optimize_unified_v2_ITSA3_ITSA4_20250923_105845.json \
  --rank 1 \
  --mode live
```

Expected:
- ✅ No "asyncio.run" errors
- ✅ Ticks fetched successfully
- ✅ Ticks persisted to PostgreSQL
- ✅ Live trading operational

## Priority

🔴 **CRITICAL** - Blocks live trading mode entirely

## Next Steps

1. **On MCP Server (Windows)**: Fix `get_symbol_info_tick` to use `await loop.run_in_executor()` instead of `asyncio.run()`
2. **Test**: Verify endpoint returns tick data correctly
3. **On stock-dividend (macOS)**: Test live mode works end-to-end
4. **Merge**: Both sides can merge their branches

---

**Created by**: Claude (stock-dividend/macOS)
**For**: Claude (mcp_mt5_server/Windows)
**Status**: Waiting for server-side fix
