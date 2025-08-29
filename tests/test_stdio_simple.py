#!/usr/bin/env python3
"""
Test STDIO MCP client - Simplified version for testing
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    print("✅ MCP imports successful")
except ImportError as e:
    print(f"❌ MCP import error: {e}")
    sys.exit(1)

async def test_connection():
    """Test basic STDIO connection"""
    
    print("🚀 Testing MCP STDIO connection...")
    
    # Use virtual environment python
    python_exe = sys.executable
    server_script = str(Path(__file__).parent / "run_fork_mcp.py")
    
    print(f"Python: {python_exe}")
    print(f"Server: {server_script}")
    
    # Setup server parameters
    server_params = StdioServerParameters(
        command=python_exe,
        args=[server_script],
        cwd=str(Path(__file__).parent),
        env=None
    )
    
    try:
        print("🔧 Creating STDIO client...")
        async with stdio_client(server_params) as (read, write):
            print("✅ STDIO client created")
            
            print("🔧 Creating client session...")
            async with ClientSession(read, write) as session:
                print("✅ Client session created")
                
                print("🔧 Initializing session...")
                init_result = await session.initialize()
                print(f"✅ Session initialized: {init_result.protocolVersion}")
                
                print("🔧 Listing tools...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"✅ Found {len(tools)} tools")
                
                # Show first 5 tools
                for i, tool in enumerate(tools[:5], 1):
                    print(f"   {i}. {tool.name}")
                
                if len(tools) > 5:
                    print(f"   ... and {len(tools) - 5} more")
                
                print("🔧 Testing ping...")
                ping_result = await session.call_tool("ping", {})
                ping_data = json.loads(ping_result.content[0].text)
                print(f"✅ Ping successful: {ping_data['ok']}")
                
                print("🎯 STDIO CONNECTION TEST SUCCESSFUL!")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())