#!/usr/bin/env python3
"""
Debug MT5 copy_ticks_range error
================================
Test the exact same parameters that the server is using to understand the error.
"""

import MetaTrader5 as mt5
from datetime import datetime, timezone
import traceback

def test_ticks_range_debug():
    """Debug the copy_ticks_range error"""
    
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return
    
    print("✅ MT5 initialized")
    
    # Select symbol
    if not mt5.symbol_select("ITSA3", True):
        print(f"❌ Symbol selection failed: {mt5.last_error()}")
        return
    
    print("✅ Symbol selected")
    
    # Test the exact same parameters that cause the error
    date_from_str = "2025-09-09T20:00:00Z"
    date_to_str = "2025-09-10T02:00:00Z"
    
    # Parse the same way the server does
    try:
        # Parse as timezone-aware, then convert to naive (as server does now)
        dt_from_aware = datetime.fromisoformat(date_from_str.replace('Z', '+00:00'))
        date_from = dt_from_aware.replace(tzinfo=None)
        
        dt_to_aware = datetime.fromisoformat(date_to_str.replace('Z', '+00:00'))
        date_to = dt_to_aware.replace(tzinfo=None)
        
        print(f"Date from: {date_from} (type: {type(date_from)})")
        print(f"Date to: {date_to} (type: {type(date_to)})")
        
        # Test copy_ticks_range with different flag values
        flags_to_test = [0, mt5.COPY_TICKS_ALL, mt5.COPY_TICKS_INFO, mt5.COPY_TICKS_TRADE]
        
        for flags in flags_to_test:
            print(f"\nTesting with flags={flags}:")
            try:
                ticks = mt5.copy_ticks_range("ITSA3", date_from, date_to, flags)
                
                if ticks is not None:
                    print(f"  ✅ Success: {len(ticks)} ticks")
                else:
                    error = mt5.last_error()
                    print(f"  ❌ Failed: {error}")
                    
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Date parsing error: {e}")
        traceback.print_exc()
    
    # Also test with the current timestamp approach  
    print("\n" + "="*50)
    print("Testing with current time approach:")
    try:
        now = datetime.now()
        from_time = now - timedelta(hours=24)
        
        print(f"Current time from: {from_time} (type: {type(from_time)})")
        print(f"Current time to: {now} (type: {type(now)})")
        
        ticks = mt5.copy_ticks_range("ITSA3", from_time, now, mt5.COPY_TICKS_ALL)
        if ticks is not None:
            print(f"✅ Success with current time: {len(ticks)} ticks")
        else:
            error = mt5.last_error()
            print(f"❌ Failed with current time: {error}")
    
    except Exception as e:
        print(f"❌ Current time test exception: {e}")
        traceback.print_exc()
    
    mt5.shutdown()

if __name__ == "__main__":
    from datetime import timedelta
    test_ticks_range_debug()
