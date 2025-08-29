#!/usr/bin/env python3
"""
Test script to verify MCP tools registration
"""
import sys
from pathlib import Path

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_tools_registration():
    """Test if tools are properly registered"""
    print("🧪 Testing MCP tools registration...")
    
    try:
        # Import server components FIRST (creates MCP instance)
        print("1️⃣ Importing server module...")
        from mcp_metatrader5_server.server import mcp, config_manager, mt5_status
        print(f"   ✅ Server imported - MCP type: {type(mcp)}")
        print(f"   🔍 MCP attributes: {dir(mcp)[:10]}...")
        
        # Check FastMCP internals
        print(f"   🔍 MCP has _tools: {hasattr(mcp, '_tools')}")
        print(f"   🔍 MCP has tools: {hasattr(mcp, 'tools')}")
        print(f"   🔍 MCP has get_tools: {hasattr(mcp, 'get_tools')}")
        
        # Use the correct FastMCP API
        try:
            initial_tools = mcp.get_tools()
            initial_count = len(initial_tools)
            print(f"   📊 Initial tools (server.py only): {initial_count}")
            if initial_count > 0:
                print(f"   🔧 Initial tools: {[t.name for t in initial_tools[:5]]}")
        except Exception as e:
            print(f"   ❌ Error calling get_tools(): {e}")
            initial_count = 0
            
        if initial_count == 0:
            print("   ❓ Checking why no tools in server.py...")
            # List all functions with @mcp.tool in current module
            import mcp_metatrader5_server.server as server_mod
            server_functions = [name for name in dir(server_mod) if callable(getattr(server_mod, name))]
            print(f"   📋 Functions in server module: {server_functions[:10]}...")
        
        # Test direct tool registration
        print("   🧪 Testing direct tool registration...")
        
        @mcp.tool()
        def test_tool():
            """Test tool for debug"""
            return {"message": "test"}
            
        try:
            test_tools = mcp.get_tools()
            after_test = len(test_tools)
            print(f"   📊 After test tool: {after_test} tools")
        except Exception as e:
            print(f"   ❌ Error after test: {e}")
            after_test = 0
        
        # Import market_data module
        print("2️⃣ Importing market_data module...")
        import mcp_metatrader5_server.market_data
        
        try:
            md_tools = mcp.get_tools()
            market_data_count = len(md_tools)
            print(f"   📊 After market_data: {market_data_count} tools")
        except Exception as e:
            print(f"   ❌ Error after market_data: {e}")
            market_data_count = 0
        
        # Import trading module  
        print("3️⃣ Importing trading module...")
        import mcp_metatrader5_server.trading
        
        try:
            all_tools = mcp.get_tools()
            final_count = len(all_tools)
            print(f"   📊 Final count: {final_count} tools")
            
            if final_count > 0:
                print(f"\n✅ SUCCESS: {final_count} tools registered")
                print(f"🔧 Sample tools: {[t.name for t in all_tools[:10]]}")
                
                # Test specific tool
                tool_names = [t.name for t in all_tools]
                if 'get_symbols' in tool_names:
                    print("✅ 'get_symbols' tool found")
                else:
                    print("❌ 'get_symbols' tool NOT found")
                    print(f"Available tools: {tool_names[:10]}")
            else:
                print("❌ FAIL: No tools registered")
                
        except Exception as e:
            print(f"   ❌ Error getting final tools: {e}")
            final_count = 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tools_registration()