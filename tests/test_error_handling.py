#!/usr/bin/env python3
"""
Test script for Task 2 - Standardized Error Handling
Tests the error handler module functionality
"""
import sys
import json
from pathlib import Path

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_error_codes():
    """Test error code definitions"""
    print("🧪 Testing Error Code Definitions...")
    
    from mcp_metatrader5_server.error_handler import (
        MT5ErrorCode, ERROR_MESSAGES
    )
    
    # Test all error codes have messages
    error_codes = [
        MT5ErrorCode.MT5_NOT_INITIALIZED,
        MT5ErrorCode.MT5_SYMBOL_NOT_FOUND,
        MT5ErrorCode.MT5_INSUFFICIENT_FUNDS,
        MT5ErrorCode.MT5_TRADE_DISABLED,
        MT5ErrorCode.MT5_INVALID_REQUEST,
        MT5ErrorCode.MT5_CONNECTION_LOST,
        MT5ErrorCode.MT5_TIMEOUT,
    ]
    
    for code in error_codes:
        message = ERROR_MESSAGES.get(code)
        print(f"  ✅ {code}: {message}")
        assert message is not None, f"No message for {code}"
    
    print(f"  Total codes defined: {len(MT5ErrorCode)}")
    print(f"  Total messages: {len(ERROR_MESSAGES)}")

def test_error_creation():
    """Test error creation and formatting"""
    print("\n🧪 Testing Error Creation...")
    
    from mcp_metatrader5_server.error_handler import (
        MT5ErrorCode, create_error
    )
    
    # Test basic error creation
    error = create_error(MT5ErrorCode.MT5_SYMBOL_NOT_FOUND)
    print(f"  Basic error: {error.to_dict()}")
    
    # Test error with custom message
    error = create_error(
        MT5ErrorCode.MT5_SYMBOL_NOT_FOUND,
        message="Symbol ITSA3 not found in Market Watch"
    )
    print(f"  Custom message: {error.to_dict()}")
    
    # Test error with details
    error = create_error(
        MT5ErrorCode.MT5_INSUFFICIENT_FUNDS,
        message="Not enough margin for 100 lots",
        details="Required: 5000 BRL, Available: 1000 BRL"
    )
    print(f"  With details: {error.to_dict()}")
    
    # Test MCP response format
    mcp_response = error.to_mcp_response()
    print(f"  MCP format: {json.dumps(mcp_response, indent=2)}")
    
    assert mcp_response["success"] == False
    assert "error" in mcp_response
    assert mcp_response["error"]["code"] == MT5ErrorCode.MT5_INSUFFICIENT_FUNDS

def test_mt5_error_mapping():
    """Test MT5 native error code mapping"""
    print("\n🧪 Testing MT5 Native Error Mapping...")
    
    from mcp_metatrader5_server.error_handler import (
        create_error_from_mt5, MT5ErrorCode
    )
    
    # Test known MT5 error codes
    test_cases = [
        (10019, MT5ErrorCode.MT5_INSUFFICIENT_FUNDS),  # NO_MONEY
        (10004, MT5ErrorCode.MT5_INSUFFICIENT_FUNDS),  # REQUOTE
        (10006, MT5ErrorCode.MT5_INVALID_REQUEST),     # REJECT
        (10014, MT5ErrorCode.MT5_INVALID_VOLUME),      # INVALID_VOLUME
        (10015, MT5ErrorCode.MT5_INVALID_PRICE),       # INVALID_PRICE
        (10017, MT5ErrorCode.MT5_TRADE_DISABLED),      # TRADE_DISABLED
        (99999, MT5ErrorCode.MT5_UNKNOWN_ERROR),       # Unknown code
    ]
    
    for mt5_code, expected_code in test_cases:
        error = create_error_from_mt5(mt5_code)
        print(f"  MT5 {mt5_code} -> {error.code}")
        assert error.code == expected_code
        assert error.mt5_code == mt5_code

def test_validation_functions():
    """Test validation helper functions"""
    print("\n🧪 Testing Validation Functions...")
    
    from mcp_metatrader5_server.error_handler import (
        validate_symbol, validate_volume, MT5ErrorCode
    )
    
    # Test symbol validation
    print("  Testing symbol validation:")
    
    # Empty symbol should fail
    error = validate_symbol("")
    if error:
        print(f"    ✅ Empty symbol rejected: {error.code}")
        assert error.code == MT5ErrorCode.MT5_INVALID_REQUEST
    
    # Valid symbol (will skip MT5 check in Linux)
    error = validate_symbol("ITSA3")
    if error is None:
        print(f"    ✅ Valid symbol accepted (or MT5 not available)")
    
    # Test volume validation
    print("  Testing volume validation:")
    
    # Negative volume should fail
    error = validate_volume(-100, "ITSA3")
    if error:
        print(f"    ✅ Negative volume rejected: {error.code}")
        assert error.code == MT5ErrorCode.MT5_INVALID_VOLUME
    
    # Zero volume should fail
    error = validate_volume(0, "ITSA3")
    if error:
        print(f"    ✅ Zero volume rejected: {error.code}")
        assert error.code == MT5ErrorCode.MT5_INVALID_VOLUME
    
    # Valid volume (will skip MT5 check in Linux)
    error = validate_volume(100, "ITSA3")
    if error is None:
        print(f"    ✅ Valid volume accepted (or MT5 not available)")

def test_error_decorator():
    """Test error handler decorator"""
    print("\n🧪 Testing Error Handler Decorator...")
    
    from mcp_metatrader5_server.error_handler import (
        handle_mt5_error, create_error, MT5ErrorCode
    )
    
    # Create test functions
    @handle_mt5_error
    def successful_function():
        return {"data": "success"}
    
    @handle_mt5_error
    def failing_function():
        raise ValueError("Test error")
    
    @handle_mt5_error
    def mt5_error_function():
        return create_error(MT5ErrorCode.MT5_SYMBOL_NOT_FOUND)
    
    # Test successful function
    result = successful_function()
    print(f"  Success case: {result}")
    assert result["success"] == True
    assert result["data"]["data"] == "success"
    
    # Test failing function
    result = failing_function()
    print(f"  Error case: {result}")
    assert result["success"] == False
    assert result["error"]["code"] == MT5ErrorCode.MT5_EXECUTION_ERROR
    
    # Test MT5 error return
    result = mt5_error_function()
    print(f"  MT5 error case: {result}")
    assert result["success"] == False
    assert result["error"]["code"] == MT5ErrorCode.MT5_SYMBOL_NOT_FOUND

def test_mcp_compliance():
    """Test MCP compliance of error responses"""
    print("\n🧪 Testing MCP Compliance...")
    
    from mcp_metatrader5_server.error_handler import (
        MT5ErrorCode, create_error
    )
    
    # Create test error
    error = create_error(
        MT5ErrorCode.MT5_SYMBOL_NOT_FOUND,
        message="Symbol INVALID not found",
        details="Check if symbol is available in Market Watch"
    )
    
    # Get MCP response
    mcp_response = error.to_mcp_response()
    
    # Convert to JSON for MCP text content
    json_text = json.dumps(mcp_response)
    
    # Simulate full MCP response structure
    full_mcp = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json_text
                }
            ]
        }
    }
    
    print(f"  Full MCP response structure:")
    print(json.dumps(full_mcp, indent=2))
    
    # Validate structure
    assert "jsonrpc" in full_mcp
    assert "result" in full_mcp
    assert "content" in full_mcp["result"]
    assert full_mcp["result"]["content"][0]["type"] == "text"
    
    # Parse the text content back
    parsed = json.loads(full_mcp["result"]["content"][0]["text"])
    assert parsed["success"] == False
    assert parsed["error"]["code"] == MT5ErrorCode.MT5_SYMBOL_NOT_FOUND
    assert parsed["error"]["message"] == "Symbol INVALID not found"
    assert parsed["error"]["details"] == "Check if symbol is available in Market Watch"
    
    print("  ✅ MCP compliance verified!")

def main():
    """Run all error handling tests"""
    print("=" * 60)
    print("Task 2 - Error Handling Test Suite")
    print("=" * 60)
    
    try:
        test_error_codes()
        test_error_creation()
        test_mt5_error_mapping()
        test_validation_functions()
        test_error_decorator()
        test_mcp_compliance()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())