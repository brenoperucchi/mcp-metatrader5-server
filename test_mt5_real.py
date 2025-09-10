#!/usr/bin/env python3
"""
Test script to verify MT5 real connection vs mock
"""
import os
import sys

# Add src to path
sys.path.insert(0, 'src')

def test_mt5_connection():
    """Test MT5 connection in different modes"""
    
    print("="*60)
    print("MT5 CONNECTION TEST")
    print("="*60)
    
    # Test 1: Production mode (default - should use real MT5)
    print("\n1. Testing PRODUCTION mode (default):")
    print("-" * 40)
    os.environ.pop('USE_MOCK', None)  # Remove USE_MOCK if exists
    
    try:
        # Re-import to get fresh module with new env var
        if 'mcp_metatrader5_server.server' in sys.modules:
            del sys.modules['mcp_metatrader5_server.server']
        
        from mcp_metatrader5_server.server import MT5_AVAILABLE, USE_MOCK
        
        print(f"   USE_MOCK env var: {os.environ.get('USE_MOCK', 'Not set')}")
        print(f"   USE_MOCK flag: {USE_MOCK}")
        print(f"   MT5_AVAILABLE: {MT5_AVAILABLE}")
        
        if not USE_MOCK and not MT5_AVAILABLE:
            print("   ⚠️ MT5 not available - will fallback to mock")
        elif not USE_MOCK and MT5_AVAILABLE:
            print("   ✅ Using REAL MetaTrader5")
        else:
            print("   🔧 Using MOCK mode")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Mock mode (explicit)
    print("\n2. Testing MOCK mode (USE_MOCK=true):")
    print("-" * 40)
    os.environ['USE_MOCK'] = 'true'
    
    try:
        # Re-import to get fresh module with new env var
        if 'mcp_metatrader5_server.server' in sys.modules:
            del sys.modules['mcp_metatrader5_server.server']
        
        from mcp_metatrader5_server.server import MT5_AVAILABLE, USE_MOCK
        
        print(f"   USE_MOCK env var: {os.environ.get('USE_MOCK')}")
        print(f"   USE_MOCK flag: {USE_MOCK}")
        print(f"   MT5_AVAILABLE: {MT5_AVAILABLE}")
        
        if USE_MOCK:
            print("   🔧 Using MOCK mode as requested")
        else:
            print("   ❌ Should be using mock but isn't!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Get symbols to verify data source
    print("\n3. Testing get_symbols() to verify data source:")
    print("-" * 40)
    
    # First in production mode
    os.environ.pop('USE_MOCK', None)
    if 'mcp_metatrader5_server.market_data' in sys.modules:
        del sys.modules['mcp_metatrader5_server.market_data']
    
    from mcp_metatrader5_server.market_data import get_symbols
    
    print("   Production mode symbols:")
    symbols = get_symbols()
    print(f"   First 10 symbols: {symbols[:10]}")
    
    if symbols == ["EURUSD", "GBPUSD", "USDJPY", "PETR4", "ITSA4", "VALE3"]:
        print("   ⚠️ These are MOCK symbols - MT5 not connected!")
    else:
        print(f"   ✅ Got {len(symbols)} symbols from real MT5")
    
    print("\n" + "="*60)
    print("INSTRUCTIONS TO FIX:")
    print("="*60)
    print("""
1. On Windows machine (192.168.0.125):
   - Stop the current server (Ctrl+C or kill process)
   - Pull latest changes or copy updated files
   - Restart server WITHOUT USE_MOCK:
     python mcp_mt5_server.py --port 8000
   
2. Verify MT5 is running:
   - MetaTrader 5 terminal must be open
   - Account must be logged in
   - Check MT5_CONFIG environment variable (default: 'b3')
   
3. Check server health:
   curl http://192.168.0.125:8000/health
   
   Should show:
   - "mt5_status": "connected" (not "mock")
   - "mt5_mock": false
""")

if __name__ == "__main__":
    test_mt5_connection()