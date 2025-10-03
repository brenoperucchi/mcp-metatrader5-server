# MCP Ticks Investigation Results

## Problem Statement

MetaTrader 5 can export ticks to CSV successfully, but MCP Server returns 0 ticks for the same date range.

**CSV Export Evidence:**
- File: `/Users/brenoperucchi/Devs/stock-dividend/data/ITSA3_202501020945_202510030948.csv`
- Data Range: 2025-01-02 09:45 to 2025-10-03 09:48
- Contains thousands of ticks
- Latest data: 2025-10-03 09:48 (this morning)

**MCP Server Response:**
- Returns: 0 bars/ticks
- Same date range, same symbol

## Investigation Scripts Created

### 1. `investigate_ticks_issue.py`
**Purpose:** Test MCP Server via HTTP API
**Run from:** macOS (can access Windows network)

```bash
# From macOS
cd ~/Devs/stock-dividend
python investigate_ticks_issue.py
```

Tests:
- ✅ Server health
- ✅ Available symbols list
- ✅ Symbol info for ITSA3
- ✅ Latest tick
- ✅ Recent ticks (from position)
- ✅ Ticks by date range (CRITICAL)
- ✅ Multiple date range formats

### 2. `diagnose_ticks_access.py`
**Purpose:** Test direct MT5 API access
**Run from:** Windows (where MT5 is installed)

```powershell
# From Windows PowerShell
cd "C:\Users\Breno Perucchi\Devs\mcp-metatrader5-server"
python diagnose_ticks_access.py
```

Tests:
- ✅ MT5 connection
- ✅ Terminal info
- ✅ Symbol availability
- ✅ Latest tick access
- ✅ Direct `mt5.copy_ticks_range()` call
- ✅ Alternative date formats
- ✅ Market hours check

## Suspected Root Causes

### 1. **Symbol Name Format**
- MT5 might expect: `ITSA3.SA` or `BOVESPA:ITSA3`
- MCP using: `ITSA3`
- CSV export works with whatever MT5 uses internally

**Test:** Check `get_symbols()` response for exact format

### 2. **Timezone Handling**
- CSV timestamps: `2025.10.02 09:45:07.268`
- MCP might be converting incorrectly
- MT5 expects timezone-naive datetimes
- But date range might be off by timezone offset

**Test:** Try UTC, local time, timezone-naive

### 3. **Symbol Not in Market Watch**
- MT5 only returns ticks for symbols in Market Watch
- Symbol might need to be selected first

**Fix:** Call `symbol_select(ITSA3, True)` before querying

### 4. **Date Range Format**
- MT5 API might expect specific datetime format
- Current code uses: `datetime(2025, 10, 2, 0, 0, 0)`
- Might need timestamp or different format

### 5. **Market Data Permissions**
- MT5 might have restrictions on historical tick data
- Demo vs Live account differences
- Data provider limitations

## Recommended Investigation Steps

### Step 1: Run Investigation Scripts

**On macOS:**
```bash
cd /mnt/c/Users/Breno\ Perucchi/Devs/mcp-metatrader5-server
cp investigate_ticks_issue.py ~/Devs/stock-dividend/
cd ~/Devs/stock-dividend
python investigate_ticks_issue.py > mcp_investigation_results.txt 2>&1
```

**On Windows:**
```powershell
cd "C:\Users\Breno Perucchi\Devs\mcp-metatrader5-server"
python diagnose_ticks_access.py > windows_diagnosis_results.txt 2>&1
```

### Step 2: Check Server Logs

```bash
# Latest MCP server log
ls -t logs/mcp_mt5_server/server_*.log | head -1 | xargs tail -100
```

Look for:
- MT5 error codes
- Symbol not found errors
- Date conversion errors
- Empty result warnings

### Step 3: Test Symbol Format

Try different symbol formats:
- `ITSA3`
- `ITSA3.SA`
- `BOVESPA:ITSA3`
- Whatever `get_symbols()` returns

### Step 4: Manual MT5 Test

On Windows, open MetaTrader 5 terminal:
1. Tools → MetaEditor
2. Create new script
3. Run:

```mql5
#include <MetaTrader5.mqh>

void OnStart() {
    MqlTick ticks[];
    datetime from = D'2025.10.02 00:00:00';
    datetime to = D'2025.10.03 23:59:59';

    int count = CopyTicks("ITSA3", ticks, COPY_TICKS_ALL, from*1000, to*1000);

    Print("Ticks retrieved: ", count);
    if(count > 0) {
        Print("First tick: ", TimeToString(ticks[0].time));
        Print("Last tick: ", TimeToString(ticks[count-1].time));
    }
}
```

## Expected Outcomes

### If Scripts Work:
- ✅ MCP can access ticks → Problem is in `stock-dividend` auto-import
- Fix: Update date format in auto-import queries

### If Scripts Fail:
- ❌ MCP cannot access ticks → Problem is in `mcp-metatrader5-server`
- Fix: Debug MT5 API calls, symbol format, or date handling

### If Windows Script Works but MCP Fails:
- ❌ MT5 API works but MCP wrapper broken
- Fix: Check `market_data.py` implementation

## Quick Fixes to Try

### Fix 1: Select Symbol First
```python
# In market_data.py, before copy_ticks_range
mt5.symbol_select(symbol, True)
```

### Fix 2: Try Different Date Format
```python
# Convert to Unix timestamp
from_ts = int(date_from.timestamp())
to_ts = int(date_to.timestamp())
ticks = mt5.copy_ticks_range(symbol, from_ts, to_ts, flags)
```

### Fix 3: Add Verbose Logging
```python
# In copy_ticks_range
logger.info(f"Querying ticks: symbol={symbol}, from={date_from}, to={date_to}")
result = mt5.copy_ticks_range(symbol, date_from, date_to, flags)
logger.info(f"MT5 returned: {len(result) if result else 0} ticks, error={mt5.last_error()}")
```

## Contact Points

**Files to check:**
- `src/mcp_metatrader5_server/market_data.py:433-473` (copy_ticks_range implementation)
- `mcp_mt5_server.py:472-515` (MCP tool routing)
- `logs/mcp_mt5_server/server_*.log` (runtime logs)

**Configuration:**
- `config/server_config.json` (server settings)
- MT5 Terminal settings (symbol subscriptions)

## Status

🔴 **BLOCKED** - Need to run investigation scripts to proceed

**Next Action:** Run scripts and report findings
