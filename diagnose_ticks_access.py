#!/usr/bin/env python3
"""
Diagnose why MCP Server cannot access ticks that MT5 clearly has.

This script tests direct MT5 API access vs MCP Server access.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("🔍 MCP Ticks Access Diagnosis")
print("=" * 80)
print()

# Test 1: Direct MT5 Connection
print("1️⃣  Testing Direct MT5 Connection...")
print("-" * 80)

try:
    import MetaTrader5 as mt5

    # Initialize MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)

    print(f"✅ MT5 initialized successfully")

    # Get terminal info
    terminal_info = mt5.terminal_info()
    print(f"   Terminal: {terminal_info.name}")
    print(f"   Build: {terminal_info.build}")
    print(f"   Connected: {terminal_info.connected}")
    print()

    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print(f"   Account: {account_info.login}")
        print(f"   Server: {account_info.server}")
        print(f"   Balance: {account_info.balance} {account_info.currency}")
    print()

except ImportError:
    print("❌ MetaTrader5 module not available (expected in WSL)")
    print("   This test should run on Windows where MT5 is installed")
    print()

# Test 2: Symbol Info
print("2️⃣  Testing Symbol Access...")
print("-" * 80)

symbol = "ITSA3"

try:
    # Check if symbol exists
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Symbol '{symbol}' not found")
        print(f"   Error: {mt5.last_error()}")

        # Try to find similar symbols
        print("\n   🔍 Searching for similar symbols...")
        all_symbols = mt5.symbols_get()
        if all_symbols:
            similar = [s.name for s in all_symbols if "ITSA" in s.name]
            if similar:
                print(f"   Found similar symbols: {similar}")
            else:
                print("   No similar symbols found")
    else:
        print(f"✅ Symbol '{symbol}' found")
        print(f"   Name: {symbol_info.name}")
        print(f"   Description: {symbol_info.description}")
        print(f"   Visible: {symbol_info.visible}")
        print(f"   Trade mode: {symbol_info.trade_mode}")

        # Try to make it visible if not
        if not symbol_info.visible:
            print(f"\n   ⚠️  Symbol is not visible, attempting to select...")
            if mt5.symbol_select(symbol, True):
                print(f"   ✅ Symbol selected successfully")
            else:
                print(f"   ❌ Failed to select symbol: {mt5.last_error()}")
    print()

except Exception as e:
    print(f"❌ Error checking symbol: {e}")
    print()

# Test 3: Tick Data Access
print("3️⃣  Testing Tick Data Access...")
print("-" * 80)

# Test date range (same as CSV export)
date_from = datetime(2025, 10, 2, 0, 0, 0)
date_to = datetime(2025, 10, 3, 23, 59, 59)

print(f"   Date range: {date_from} to {date_to}")
print()

try:
    # Test 3a: Last tick
    print("   3a. Testing get latest tick...")
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"   ✅ Latest tick retrieved")
        print(f"      Time: {datetime.fromtimestamp(tick.time)}")
        print(f"      Bid: {tick.bid}, Ask: {tick.ask}, Last: {tick.last}")
        print(f"      Volume: {tick.volume}")
    else:
        print(f"   ❌ Failed to get latest tick: {mt5.last_error()}")
    print()

    # Test 3b: Recent ticks (from position)
    print("   3b. Testing recent ticks (from position)...")
    ticks_pos = mt5.copy_ticks_from_pos(symbol, 0, 10, mt5.COPY_TICKS_ALL)
    if ticks_pos is not None and len(ticks_pos) > 0:
        print(f"   ✅ Retrieved {len(ticks_pos)} recent ticks")
        print(f"      First tick time: {datetime.fromtimestamp(ticks_pos[0][0])}")
        print(f"      Last tick time: {datetime.fromtimestamp(ticks_pos[-1][0])}")
    else:
        print(f"   ❌ No ticks from position: {mt5.last_error()}")
    print()

    # Test 3c: Ticks by date range
    print("   3c. Testing ticks by date range...")
    print(f"      Using timezone-naive datetime (as required by MT5)")

    ticks_range = mt5.copy_ticks_range(symbol, date_from, date_to, mt5.COPY_TICKS_ALL)

    if ticks_range is not None and len(ticks_range) > 0:
        print(f"   ✅ Retrieved {len(ticks_range)} ticks in date range")
        print(f"      First tick: {datetime.fromtimestamp(ticks_range[0][0])}")
        print(f"      Last tick: {datetime.fromtimestamp(ticks_range[-1][0])}")

        # Show sample ticks
        print(f"\n      Sample ticks:")
        for i, tick in enumerate(ticks_range[:5]):
            tick_time = datetime.fromtimestamp(tick[0])
            print(f"        {i+1}. {tick_time} - Bid: {tick[1]}, Ask: {tick[2]}, Last: {tick[3]}, Vol: {tick[4]}")
    else:
        error = mt5.last_error()
        print(f"   ❌ No ticks in date range!")
        print(f"      Error code: {error}")

        # Try alternative approaches
        print(f"\n   🔍 Trying alternative date formats...")

        # Try with timezone info
        from datetime import timezone
        date_from_utc = date_from.replace(tzinfo=timezone.utc)
        date_to_utc = date_to.replace(tzinfo=timezone.utc)

        print(f"      Trying with UTC timezone...")
        ticks_range_utc = mt5.copy_ticks_range(symbol, date_from_utc, date_to_utc, mt5.COPY_TICKS_ALL)
        if ticks_range_utc is not None and len(ticks_range_utc) > 0:
            print(f"   ✅ SUCCESS with UTC! Retrieved {len(ticks_range_utc)} ticks")
        else:
            print(f"   ❌ Failed with UTC too: {mt5.last_error()}")

        # Try shorter range (just today)
        print(f"\n      Trying shorter range (today only)...")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        ticks_today = mt5.copy_ticks_range(symbol, today, tomorrow, mt5.COPY_TICKS_ALL)
        if ticks_today is not None and len(ticks_today) > 0:
            print(f"   ✅ Retrieved {len(ticks_today)} ticks for today")
        else:
            print(f"   ❌ No ticks for today: {mt5.last_error()}")
    print()

except Exception as e:
    print(f"   ❌ Exception during tick access: {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 4: Market Hours
print("4️⃣  Checking Market Hours...")
print("-" * 80)

try:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        print(f"   Trade mode: {symbol_info.trade_mode}")
        print(f"   Trade execution: {symbol_info.trade_exemode}")

        # Check if market is currently trading
        now = datetime.now()
        print(f"\n   Current time: {now}")
        print(f"   Current date: {now.strftime('%A, %B %d, %Y')}")

        # Get session info
        print(f"\n   Session quote info:")
        session_quote = mt5.symbol_info_sessionquote(symbol, now.weekday(), 0)
        if session_quote:
            print(f"      From: {datetime.fromtimestamp(session_quote[0])}")
            print(f"      To: {datetime.fromtimestamp(session_quote[1])}")
        else:
            print(f"      ❌ Could not get session quote info")
    print()

except Exception as e:
    print(f"   ❌ Error checking market hours: {e}")
    print()

# Test 5: Compare with CSV
print("5️⃣  Comparing with CSV Export...")
print("-" * 80)

csv_path = "/Users/brenoperucchi/Devs/stock-dividend/data/ITSA3_202501020945_202510030948.csv"
print(f"   CSV path: {csv_path}")

# This will only work on macOS where the CSV exists
if Path(csv_path).exists():
    import pandas as pd
    try:
        df = pd.read_csv(csv_path, sep='\s+', header=0)
        print(f"   ✅ CSV loaded: {len(df)} rows")
        print(f"      First row date: {df.iloc[0]['<DATE>']} {df.iloc[0]['<TIME>']}")
        print(f"      Last row date: {df.iloc[-1]['<DATE>']} {df.iloc[-1]['<TIME>']}")

        # Compare with MCP data
        if 'ticks_range' in locals() and ticks_range is not None and len(ticks_range) > 0:
            print(f"\n   📊 Comparison:")
            print(f"      CSV rows: {len(df)}")
            print(f"      MCP ticks: {len(ticks_range)}")
            print(f"      Difference: {len(df) - len(ticks_range)}")
        else:
            print(f"\n   ⚠️  MCP returned 0 ticks, but CSV has {len(df)} rows!")
            print(f"      This confirms the problem: MT5 has data but MCP can't access it")
    except Exception as e:
        print(f"   ❌ Error reading CSV: {e}")
else:
    print(f"   ℹ️  CSV not accessible from this machine (expected if running on Windows)")
print()

# Cleanup
try:
    mt5.shutdown()
    print("✅ MT5 shutdown successfully")
except:
    pass

print()
print("=" * 80)
print("📋 DIAGNOSIS COMPLETE")
print("=" * 80)
print()
print("💡 Next steps:")
print("   1. Review errors above")
print("   2. Check if symbol name format is correct")
print("   3. Verify timezone handling in MCP code")
print("   4. Check if MT5 connection is properly initialized in MCP")
print("   5. Test with shorter date ranges")
print()
