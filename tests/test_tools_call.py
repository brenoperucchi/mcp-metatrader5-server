#!/usr/bin/env python3
"""
Test script for tools/call implementation
Tests the call_tool function without running the full HTTP server
"""
import sys
import os
import asyncio
from pathlib import Path

# Setup paths
fork_mcp_path = Path(__file__).parent / "fork_mcp"
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(fork_mcp_path))
sys.path.insert(0, str(src_path))

# Mock MetaTrader5 to avoid import error on Linux
class MockMT5:
    @staticmethod
    def initialize():
        print("[MOCK] MT5 initialized")
        return True
    
    @staticmethod
    def shutdown():
        print("[MOCK] MT5 shutdown")
        
    @staticmethod
    def login(login, password, server):
        print(f"[MOCK] MT5 login: {login}@{server}")
        return True
        
    @staticmethod
    def account_info():
        # Mock account info response
        from collections import namedtuple
        AccountInfo = namedtuple('AccountInfo', [
            'login', 'trade_mode', 'leverage', 'limit_orders', 'margin_so_mode',
            'trade_allowed', 'trade_expert', 'margin_mode', 'currency_digits', 
            'fifo_close', 'balance', 'credit', 'profit', 'equity', 'margin',
            'margin_free', 'margin_level', 'margin_so_call', 'margin_so_so',
            'margin_initial', 'margin_maintenance', 'assets', 'liabilities',
            'commission_blocked', 'name', 'server', 'currency', 'company'
        ])
        return AccountInfo(
            login=123456789, trade_mode=0, leverage=1000, limit_orders=100,
            margin_so_mode=0, trade_allowed=True, trade_expert=True, margin_mode=0,
            currency_digits=2, fifo_close=False, balance=95420.50, credit=0.0,
            profit=0.0, equity=95420.50, margin=0.0, margin_free=95420.50,
            margin_level=0.0, margin_so_call=50.0, margin_so_so=30.0,
            margin_initial=0.0, margin_maintenance=0.0, assets=95420.50,
            liabilities=0.0, commission_blocked=0.0, name="Demo Account",
            server="Demo-Server", currency="BRL", company="MetaQuotes Demo"
        )
    
    @staticmethod
    def terminal_info():
        from collections import namedtuple
        TerminalInfo = namedtuple('TerminalInfo', ['community_account', 'community_connection', 'connected', 'dlls_allowed', 'trade_allowed', 'tradeapi_disabled', 'email_enabled', 'ftp_enabled', 'notifications_enabled', 'mqid', 'name', 'company', 'language', 'data_path', 'commondata_path'])
        return TerminalInfo(
            community_account=False, community_connection=False, connected=True,
            dlls_allowed=True, trade_allowed=True, tradeapi_disabled=False,
            email_enabled=False, ftp_enabled=False, notifications_enabled=False,
            mqid=False, name="MetaTrader 5", company="MetaQuotes",
            language=1046, data_path="/mock/path", commondata_path="/mock/path"
        )
    
    @staticmethod
    def version():
        return (5, 0, 4874, "01 Jan 2024")
        
    @staticmethod
    def last_error():
        return (0, "No error")

# Mock pandas
class MockPD:
    pass

# Inject mocks
sys.modules['MetaTrader5'] = MockMT5
sys.modules['pandas'] = MockPD
sys.modules['numpy'] = MockPD

async def test_tools_call():
    """Test the tools/call implementation"""
    print("🧪 Testing tools/call implementation...")
    
    # Import the call_tool function
    from run_http_server import call_tool
    
    # Test cases
    test_cases = [
        {
            "name": "initialize",
            "args": {},
            "description": "Test MT5 initialization"
        },
        {
            "name": "get_account_info", 
            "args": {},
            "description": "Test account info retrieval"
        },
        {
            "name": "get_terminal_info",
            "args": {},
            "description": "Test terminal info retrieval"
        },
        {
            "name": "get_version",
            "args": {},
            "description": "Test version retrieval"
        },
        {
            "name": "login",
            "args": {"login": 123456, "password": "test123", "server": "Demo-Server"},
            "description": "Test MT5 login"
        },
        {
            "name": "validate_demo_for_trading",
            "args": {},
            "description": "Test demo validation (not implemented yet)"
        },
        {
            "name": "get_symbols",
            "args": {},
            "description": "Test symbols retrieval (market data)"
        },
        {
            "name": "order_send",
            "args": {"request": {"symbol": "ITSA3", "volume": 100}},
            "description": "Test order send (trading)"
        },
        {
            "name": "nonexistent_tool",
            "args": {},
            "description": "Test unknown tool handling"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        print(f"Tool: {test_case['name']}")
        print(f"Args: {test_case['args']}")
        
        try:
            result = await call_tool(test_case['name'], test_case['args'])
            print(f"✅ Result: {result}")
            results.append({"test": test_case['name'], "status": "success", "result": result})
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append({"test": test_case['name'], "status": "error", "error": str(e)})
    
    # Summary
    print(f"\n🔍 Test Summary:")
    print(f"Total tests: {len(test_cases)}")
    success_count = len([r for r in results if r["status"] == "success"])
    error_count = len([r for r in results if r["status"] == "error"])
    print(f"✅ Successful: {success_count}")
    print(f"❌ Errors: {error_count}")
    
    # Test MCP response format
    print(f"\n🧪 Testing MCP response format...")
    result = await call_tool("get_version", {})
    
    # Simulate MCP response formatting
    import json
    result_text = json.dumps(result) if not isinstance(result, str) else result
    
    mcp_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
    }
    
    print(f"MCP Response format test:")
    print(json.dumps(mcp_response, indent=2))
    
    return results

if __name__ == "__main__":
    asyncio.run(test_tools_call())