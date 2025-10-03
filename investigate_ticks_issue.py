#!/usr/bin/env python3
"""
Complete investigation of why MCP cannot retrieve ticks that MT5 has.
Tests via HTTP API to running MCP Server.
"""

import requests
import json
from datetime import datetime, timedelta
import sys

MCP_SERVER_URL = "http://localhost:8000"
SYMBOL = "ITSA3"

print("=" * 80)
print("🔍 MCP Ticks Investigation - HTTP API Testing")
print("=" * 80)
print(f"MCP Server: {MCP_SERVER_URL}")
print(f"Symbol: {SYMBOL}")
print()

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

    try:
        response = requests.post(f"{MCP_SERVER_URL}/mcp", json=payload, timeout=30)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

# Test 1: Server Health
print("1️⃣  Testing MCP Server Health...")
print("-" * 80)

try:
    health = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
    if health.status_code == 200:
        print(f"✅ MCP Server is healthy")
        health_data = health.json()
        print(f"   Status: {health_data.get('status')}")
        if 'tick_persistence' in health_data:
            print(f"   Tick Persistence: {health_data.get('tick_persistence')}")
    else:
        print(f"⚠️  Server responded with status {health.status_code}")
except Exception as e:
    print(f"❌ Cannot reach MCP Server: {e}")
    print("   Make sure the server is running on Windows")
    sys.exit(1)

print()

# Test 2: Get Available Symbols
print("2️⃣  Testing Available Symbols...")
print("-" * 80)

result = mcp_call("get_symbols", {})

if "error" in result:
    print(f"❌ Error getting symbols: {result['error']}")
elif "result" in result:
    symbols_data = result["result"]

    # Extract symbols from response
    if isinstance(symbols_data, dict) and "content" in symbols_data:
        symbols = symbols_data["content"]
    else:
        symbols = symbols_data

    if isinstance(symbols, list):
        print(f"✅ Retrieved {len(symbols)} symbols")

        # Check if ITSA3 exists
        itsa_symbols = [s for s in symbols if "ITSA" in str(s)]
        if itsa_symbols:
            print(f"   Found ITSA symbols: {itsa_symbols[:10]}")
            if SYMBOL in symbols:
                print(f"   ✅ {SYMBOL} is available!")
            else:
                print(f"   ⚠️  {SYMBOL} not found in exact format")
                print(f"   Try using: {itsa_symbols[0] if itsa_symbols else 'N/A'}")
        else:
            print(f"   ⚠️  No ITSA symbols found")
            print(f"   Sample symbols: {symbols[:10]}")
    else:
        print(f"   Unexpected format: {type(symbols)}")
else:
    print(f"   Unexpected response: {result}")

print()

# Test 3: Get Symbol Info
print("3️⃣  Testing Symbol Info...")
print("-" * 80)

result = mcp_call("get_symbol_info", {"symbol": SYMBOL})

if "error" in result:
    print(f"❌ Error: {result['error']}")
elif "result" in result:
    info = result["result"].get("content", {})
    if info:
        print(f"✅ Symbol info retrieved")
        print(f"   Name: {info.get('name')}")
        print(f"   Description: {info.get('description')}")
        print(f"   Visible: {info.get('visible')}")
        print(f"   Digits: {info.get('digits')}")
    else:
        print(f"   Empty response")

print()

# Test 4: Get Latest Tick
print("4️⃣  Testing Latest Tick...")
print("-" * 80)

result = mcp_call("get_symbol_info_tick", {"symbol": SYMBOL})

if "error" in result:
    print(f"❌ Error: {result['error']}")
elif "result" in result:
    tick = result["result"].get("content", {})
    if tick:
        print(f"✅ Latest tick retrieved")
        print(f"   Time: {tick.get('time')}")
        print(f"   Bid: {tick.get('bid')}")
        print(f"   Ask: {tick.get('ask')}")
        print(f"   Last: {tick.get('last')}")
        print(f"   Volume: {tick.get('volume')}")
    else:
        print(f"   Empty tick data")

print()

# Test 5: Get Recent Ticks (from position)
print("5️⃣  Testing Recent Ticks (from position)...")
print("-" * 80)

result = mcp_call("copy_ticks_from_pos", {
    "symbol": SYMBOL,
    "start_pos": 0,
    "count": 10,
    "flags": 2  # COPY_TICKS_ALL
})

if "error" in result:
    print(f"❌ Error: {result['error']}")
elif "result" in result:
    ticks = result["result"].get("content", [])
    if ticks:
        print(f"✅ Retrieved {len(ticks)} recent ticks")
        print(f"   First tick: {ticks[0]}")
        print(f"   Last tick: {ticks[-1]}")
    else:
        print(f"   No ticks returned")

print()

# Test 6: Get Ticks by Date Range (THE CRITICAL TEST)
print("6️⃣  Testing Ticks by Date Range (CRITICAL TEST)...")
print("-" * 80)

# Test multiple date ranges
test_ranges = [
    # Range 1: Yesterday to today
    {
        "name": "Yesterday to Today",
        "date_from": (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat(),
        "date_to": datetime.now().isoformat()
    },
    # Range 2: Last week
    {
        "name": "Last Week",
        "date_from": (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0).isoformat(),
        "date_to": datetime.now().isoformat()
    },
    # Range 3: Specific range from CSV (2025-10-02 to 2025-10-03)
    {
        "name": "CSV Export Range (2025-10-02 to 2025-10-03)",
        "date_from": "2025-10-02T00:00:00",
        "date_to": "2025-10-03T23:59:59"
    },
    # Range 4: Just Oct 2, 2025
    {
        "name": "October 2, 2025",
        "date_from": "2025-10-02T00:00:00",
        "date_to": "2025-10-02T23:59:59"
    }
]

for test_range in test_ranges:
    print(f"\n   Testing: {test_range['name']}")
    print(f"   From: {test_range['date_from']}")
    print(f"   To: {test_range['date_to']}")

    result = mcp_call("copy_ticks_range", {
        "symbol": SYMBOL,
        "date_from": test_range['date_from'],
        "date_to": test_range['date_to'],
        "flags": 2  # COPY_TICKS_ALL
    })

    if "error" in result:
        error_msg = result.get("error", {})
        if isinstance(error_msg, dict):
            print(f"   ❌ Error: {error_msg.get('message', error_msg)}")
        else:
            print(f"   ❌ Error: {error_msg}")
    elif "result" in result:
        ticks = result["result"].get("content", [])
        if ticks and len(ticks) > 0:
            print(f"   ✅ SUCCESS! Retrieved {len(ticks)} ticks")
            print(f"      First tick: {ticks[0].get('time')} - {ticks[0].get('last')}")
            print(f"      Last tick: {ticks[-1].get('time')} - {ticks[-1].get('last')}")
        else:
            print(f"   ⚠️  0 ticks returned (but no error)")
            print(f"      Response: {result}")
    else:
        print(f"   ⚠️  Unexpected response format: {result}")

print()

# Test 7: Try with count parameter instead of range
print("7️⃣  Testing Ticks from Date with Count...")
print("-" * 80)

result = mcp_call("copy_ticks_from_date", {
    "symbol": SYMBOL,
    "date_from": "2025-10-02T09:00:00",
    "count": 100,
    "flags": 2
})

if "error" in result:
    print(f"❌ Error: {result['error']}")
elif "result" in result:
    ticks = result["result"].get("content", [])
    if ticks:
        print(f"✅ Retrieved {len(ticks)} ticks")
        print(f"   First: {ticks[0]}")
        print(f"   Last: {ticks[-1]}")
    else:
        print(f"   No ticks returned")

print()

# Summary
print("=" * 80)
print("📋 INVESTIGATION SUMMARY")
print("=" * 80)
print()
print("Key Findings:")
print("1. Server connectivity: Check output above")
print("2. Symbol availability: Check if ITSA3 exists in exact format")
print("3. Latest tick access: Check if current data is accessible")
print("4. Historical ticks: Check if date range queries work")
print()
print("💡 If date range queries return 0 ticks:")
print("   - Problem is likely in date format/timezone handling")
print("   - MT5 might need timezone-naive datetimes")
print("   - Symbol might be in different format (e.g., ITSA3.SA)")
print("   - Market data might not be available for that period")
print()
print("Next Steps:")
print("   1. Check server logs: logs/mcp_mt5_server/server_*.log")
print("   2. Run diagnose_ticks_access.py on Windows")
print("   3. Check MT5 terminal if data exists there")
print()
