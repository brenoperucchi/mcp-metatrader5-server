#!/usr/bin/env python3
"""
Test script for unified HTTP server
"""

import subprocess
import time
import urllib.request
import json
import sys

def test_server():
    """Start server and test endpoints"""
    print("🚀 Starting Unified HTTP Server...")
    
    # Start server as subprocess
    server = subprocess.Popen(
        [sys.executable, "run_http_unified.py", "--port", "8006"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/mnt/c/Users/Breno Perucchi/Devs/mcp-metatrader5-server/fork_mcp"
    )
    
    # Wait for server to start
    time.sleep(8)
    
    print("🧪 Testing endpoints...")
    print("=" * 60)
    
    endpoints = ['/health', '/info', '/config']
    all_ok = True
    
    for endpoint in endpoints:
        try:
            url = f'http://localhost:8006{endpoint}'
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                print(f'✅ {endpoint}: OK')
                
                if endpoint == '/health':
                    print(f'   Status: {data.get("status")}')
                    print(f'   Tools Count: {data.get("tools_count")}')
                elif endpoint == '/info':
                    print(f'   Tools Available: {data.get("tools_available")}')
                elif endpoint == '/config':
                    configs = data.get("available_configs", {})
                    print(f'   Configs: {list(configs.keys())}')
                    
        except Exception as e:
            print(f'❌ {endpoint}: {e}')
            all_ok = False
    
    print("=" * 60)
    
    # Kill server
    server.terminate()
    server.wait()
    
    if all_ok:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_ok

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)