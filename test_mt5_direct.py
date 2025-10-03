#!/usr/bin/env python3
"""
Direct MT5 Historical Data Test
==============================
Tests copy_ticks_range and copy_rates_range directly with MetaTrader5 library
to diagnose issues before testing via MCP server.
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

def test_mt5_connection():
    """Test MT5 connection"""
    print("Testing MT5 connection...")
    
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return False
    
    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print(f"✅ MT5 connected - Account: {account_info.login} ({account_info.server})")
        print(f"   Balance: {account_info.balance} {account_info.currency}")
        print(f"   Demo: {'Yes' if 'demo' in account_info.server.lower() else 'No'}")
    else:
        print("❌ Failed to get account info")
        return False
    
    return True

def test_symbol_selection():
    """Test symbol selection"""
    symbols = ["ITSA3", "ITSA4"]
    selected = {}
    
    print("\nTesting symbol selection...")
    for symbol in symbols:
        if mt5.symbol_select(symbol, True):
            info = mt5.symbol_info(symbol)
            if info:
                selected[symbol] = True
                print(f"✅ {symbol} - Bid: {info.bid}, Ask: {info.ask}, Visible: {info.visible}")
            else:
                selected[symbol] = False
                print(f"❌ {symbol} - No info available")
        else:
            selected[symbol] = False
            print(f"❌ {symbol} - Selection failed: {mt5.last_error()}")
    
    return selected

def test_rates_basic():
    """Test basic rates functionality"""
    print("\nTesting copy_rates_from_pos (basic)...")
    
    # Try to get last 10 M1 bars for ITSA3
    rates = mt5.copy_rates_from_pos("ITSA3", mt5.TIMEFRAME_M1, 0, 10)
    
    if rates is not None:
        print(f"✅ Got {len(rates)} rates from position")
        if len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            print(f"   First: {df.iloc[0]['time']} - Last: {df.iloc[-1]['time']}")
            print(f"   Sample: O:{df.iloc[-1]['open']:.2f} H:{df.iloc[-1]['high']:.2f} L:{df.iloc[-1]['low']:.2f} C:{df.iloc[-1]['close']:.2f}")
        return True
    else:
        error = mt5.last_error()
        print(f"❌ Failed to get rates: {error}")
        return False

def test_rates_range():
    """Test copy_rates_range with different date formats"""
    print("\nTesting copy_rates_range...")
    
    # Use recent past dates - last week
    date_to = datetime.now()
    date_from = date_to - timedelta(days=7)
    
    print(f"Date range: {date_from.strftime('%Y-%m-%d %H:%M:%S')} to {date_to.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Using datetime objects directly
    print("Test 1: Using datetime objects...")
    rates = mt5.copy_rates_range("ITSA3", mt5.TIMEFRAME_M1, date_from, date_to)
    
    if rates is not None:
        print(f"✅ Got {len(rates)} rates with datetime objects")
        return True
    else:
        error = mt5.last_error()
        print(f"❌ Failed with datetime objects: {error}")
    
    # Test 2: Using timestamps
    print("Test 2: Using timestamps...")
    from_timestamp = int(date_from.timestamp())
    to_timestamp = int(date_to.timestamp())
    
    rates = mt5.copy_rates_range("ITSA3", mt5.TIMEFRAME_M1, from_timestamp, to_timestamp)
    
    if rates is not None:
        print(f"✅ Got {len(rates)} rates with timestamps")
        return True
    else:
        error = mt5.last_error()
        print(f"❌ Failed with timestamps: {error}")
    
    return False

def test_ticks_basic():
    """Test basic ticks functionality"""
    print("\nTesting copy_ticks_from (basic)...")
    
    # Try to get last 100 ticks for ITSA3
    ticks = mt5.copy_ticks_from("ITSA3", datetime.now(), 100, mt5.COPY_TICKS_ALL)
    
    if ticks is not None:
        print(f"✅ Got {len(ticks)} ticks from date")
        if len(ticks) > 0:
            df = pd.DataFrame(ticks)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            print(f"   First: {df.iloc[0]['time']} - Last: {df.iloc[-1]['time']}")
            print(f"   Sample: Bid:{df.iloc[-1]['bid']:.2f} Ask:{df.iloc[-1]['ask']:.2f}")
        return True
    else:
        error = mt5.last_error()
        print(f"❌ Failed to get ticks: {error}")
        return False

def test_ticks_range():
    """Test copy_ticks_range with different approaches"""
    print("\nTesting copy_ticks_range...")
    
    # Use recent past - last few hours
    date_to = datetime.now()
    date_from = date_to - timedelta(hours=24)  # Last 24 hours
    
    print(f"Date range: {date_from.strftime('%Y-%m-%d %H:%M:%S')} to {date_to.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Using datetime objects
    print("Test 1: Using datetime objects...")
    try:
        ticks = mt5.copy_ticks_range("ITSA3", date_from, date_to, mt5.COPY_TICKS_ALL)
        
        if ticks is not None:
            print(f"✅ Got {len(ticks)} ticks with datetime objects")
            return True
        else:
            error = mt5.last_error()
            print(f"❌ Failed with datetime objects: {error}")
    except Exception as e:
        print(f"❌ Exception with datetime objects: {e}")
    
    # Test 2: Using timestamps (milliseconds for ticks)
    print("Test 2: Using timestamps...")
    try:
        from_timestamp = int(date_from.timestamp() * 1000)  # milliseconds
        to_timestamp = int(date_to.timestamp() * 1000)
        
        ticks = mt5.copy_ticks_range("ITSA3", from_timestamp, to_timestamp, mt5.COPY_TICKS_ALL)
        
        if ticks is not None:
            print(f"✅ Got {len(ticks)} ticks with timestamps")
            return True
        else:
            error = mt5.last_error()
            print(f"❌ Failed with timestamps: {error}")
    except Exception as e:
        print(f"❌ Exception with timestamps: {e}")
    
    return False

def main():
    """Main test function"""
    print("=" * 60)
    print("MT5 Historical Data Direct Test")
    print("=" * 60)
    
    # Test connection
    if not test_mt5_connection():
        return
    
    # Test symbol selection
    symbols = test_symbol_selection()
    if not any(symbols.values()):
        print("❌ No symbols available - cannot continue")
        return
    
    # Test basic rates
    if test_rates_basic():
        print("✅ Basic rates test passed")
    
    # Test rates range
    if test_rates_range():
        print("✅ Rates range test passed")
    
    # Test basic ticks
    if test_ticks_basic():
        print("✅ Basic ticks test passed")
    
    # Test ticks range
    if test_ticks_range():
        print("✅ Ticks range test passed")
    
    print("\n" + "=" * 60)
    print("Direct MT5 test completed")
    
    # Cleanup
    mt5.shutdown()

if __name__ == "__main__":
    main()
