#!/usr/bin/env python3
"""
Quick test for HTTP server startup
"""

import sys
from pathlib import Path

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test if all imports work"""
    try:
        from mcp_metatrader5_server.logging_utils import setup_logging
        print("✅ logging_utils import OK")
        
        # Test datetime fix
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        print(f"✅ datetime.now(timezone.utc) OK: {ts[:19]}")
        
        from mcp_metatrader5_server.server import mcp, config_manager, mt5_status
        print("✅ server imports OK")
        
        import mcp_metatrader5_server.market_data
        import mcp_metatrader5_server.trading
        print("✅ market_data and trading imports OK")
        
        from fastapi import FastAPI
        print("✅ FastAPI import OK")
        
        # Test FastMCP app creation
        try:
            app_obj = mcp.http_app()
            print(f"✅ mcp.http_app() returns: {type(app_obj)}")
        except Exception as e:
            print(f"⚠️ mcp.http_app() error: {e}")
        
        print("🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)