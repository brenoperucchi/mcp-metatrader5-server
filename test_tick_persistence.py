#!/usr/bin/env python3
"""
Test script for tick persistence functionality.

Tests:
1. Basic persistence (Acceptance Test 1)
2. Batch flush with timeout (Acceptance Test 2)
3. Idempotency (Acceptance Test 4)

Run this script with PostgreSQL running and server configured.
"""

import asyncio
import requests
import json
from datetime import datetime
import time

MCP_SERVER_URL = "http://localhost:8000"

def test_mcp_call(tool_name: str, arguments: dict = None):
    """Call an MCP tool via HTTP"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }

    response = requests.post(f"{MCP_SERVER_URL}/mcp", json=payload)
    return response.json()

def check_database_records(symbol: str, expected_min: int = 0):
    """Check how many records exist in the database for a symbol"""
    # This would require database connection - for now just informational
    print(f"\n📊 Check database for {symbol} - expecting at least {expected_min} records")
    print("   Run: SELECT COUNT(*) FROM trading.mt5_ticks_1s WHERE symbol = '{symbol}';")

def main():
    print("=" * 70)
    print("🧪 Testing Tick Persistence Functionality")
    print("=" * 70)

    # Test 1: Check server health
    print("\n1️⃣  Testing server health...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health")
        health = response.json()
        print(f"   ✅ Server healthy: {health.get('status')}")
        print(f"   💾 Tick persistence: {health.get('tick_persistence', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Server not reachable: {e}")
        return

    # Test 2: Get tick data for ITSA3 (50 times to test batch)
    print("\n2️⃣  Testing basic persistence (Acceptance Test 1)...")
    print("   Fetching 50 ticks for ITSA3 and ITSA4...")

    symbols = ["ITSA3", "ITSA4"]
    for i in range(25):
        for symbol in symbols:
            try:
                result = test_mcp_call("get_symbol_info_tick", {"symbol": symbol})
                if "error" in result:
                    print(f"   ⚠️  Error getting tick for {symbol}: {result['error']}")
                else:
                    tick = result.get("result", {}).get("content", {})
                    print(f"   ✅ Tick {i+1}/25 for {symbol}: bid={tick.get('bid')}, ask={tick.get('ask')}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")

        time.sleep(0.1)  # Small delay between requests

    print("\n   ⏳ Waiting 10 seconds for batch processing...")
    time.sleep(10)

    check_database_records("ITSA3", expected_min=25)
    check_database_records("ITSA4", expected_min=25)

    # Test 3: Batch flush timeout (Acceptance Test 2)
    print("\n3️⃣  Testing batch flush with timeout (Acceptance Test 2)...")
    print("   Sending 5 ticks and waiting for timeout flush (5 seconds)...")

    for i in range(5):
        result = test_mcp_call("get_symbol_info_tick", {"symbol": "ITSA3"})
        print(f"   ✅ Tick {i+1}/5 sent")
        time.sleep(0.5)

    print("   ⏳ Waiting 6 seconds for timeout flush...")
    time.sleep(6)

    check_database_records("ITSA3", expected_min=30)

    # Test 4: Idempotency (Acceptance Test 4)
    print("\n4️⃣  Testing idempotency (Acceptance Test 4)...")
    print("   This would require sending same timestamp+symbol twice")
    print("   Check logs for 'ON CONFLICT DO NOTHING' behavior")

    # Summary
    print("\n" + "=" * 70)
    print("📋 Test Summary:")
    print("=" * 70)
    print("✅ Basic persistence test completed (50 ticks sent)")
    print("✅ Batch timeout test completed (5 ticks + timeout)")
    print("📝 Check PostgreSQL database:")
    print("   SELECT symbol, COUNT(*) FROM trading.mt5_ticks_1s GROUP BY symbol;")
    print("   SELECT * FROM trading.mt5_ticks_1s ORDER BY timestamp DESC LIMIT 10;")
    print("\n💡 Check server logs for:")
    print("   - 'Batch persisted' messages")
    print("   - Queue sizes")
    print("   - Any errors")
    print("=" * 70)

if __name__ == "__main__":
    main()
