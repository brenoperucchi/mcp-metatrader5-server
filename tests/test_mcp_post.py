#!/usr/bin/env python3
"""
Test MCP POST endpoints (simulating Claude CLI)
"""

import json
import urllib.request
import sys

def test_mcp_post():
    """Test POST requests to MCP endpoints"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing MCP POST endpoints...")
    print("=" * 50)
    
    # Test 1: POST to /mcp with initialize
    test_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {}
        }
    }
    
    try:
        req = urllib.request.Request(
            f"{base_url}/mcp",
            data=json.dumps(test_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            print(f"✅ POST /mcp (initialize): {response.status}")
            print(f"   Protocol: {data.get('result', {}).get('protocolVersion')}")
            print(f"   Server: {data.get('result', {}).get('serverInfo', {}).get('name')}")
            
    except Exception as e:
        print(f"❌ POST /mcp (initialize): {e}")
    
    print()
    
    # Test 2: POST to /mcp with tools/list
    test_data2 = {
        "jsonrpc": "2.0", 
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        req = urllib.request.Request(
            f"{base_url}/mcp",
            data=json.dumps(test_data2).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            tools = data.get('result', {}).get('tools', [])
            print(f"✅ POST /mcp (tools/list): {response.status}")
            print(f"   Tools count: {len(tools)}")
            if tools:
                print(f"   First tool: {tools[0].get('name', 'unknown')}")
            
    except Exception as e:
        print(f"❌ POST /mcp (tools/list): {e}")
    
    print()
    
    # Test 3: POST to / (fallback)
    try:
        req = urllib.request.Request(
            f"{base_url}/",
            data=json.dumps(test_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            print(f"✅ POST / (fallback): {response.status}")
            if 'result' in data:
                print(f"   Handled as MCP request")
            else:
                print(f"   Error response: {data.get('error', 'unknown')}")
            
    except Exception as e:
        print(f"❌ POST / (fallback): {e}")
    
    print("=" * 50)
    print("🎯 Test complete!")

if __name__ == "__main__":
    test_mcp_post()