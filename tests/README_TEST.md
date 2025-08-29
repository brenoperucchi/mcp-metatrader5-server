# 🧪 MCP MetaTrader 5 - Test Suite

This directory contains all tests for the MCP MetaTrader 5 server, organized in a clean structure.

## 📁 Directory Structure

```
tests/
├── run_all_tests.py          # 🚀 Main test runner - run this to execute all tests
├── unit/                     # Unit tests for individual components
│   ├── test_mt5_basic.py     # Basic MT5 functionality (symbols, data, account)
│   └── test_mcp_server.py    # MCP server protocol tests
├── integration/              # Integration tests for full workflows
│   ├── test_connectivity.py  # Network connectivity tests
│   └── test_complete_flow.py # Complete trading workflow tests
└── utils/                    # Utility tests and setup validation
    └── test_setup.py         # Environment and dependency validation
```

## 🚀 Running Tests

### Run All Tests
```bash
python tests/run_all_tests.py
```

### Run Individual Test Categories

**Environment Validation:**
```bash
python tests/utils/test_setup.py
```

**Unit Tests:**
```bash
python tests/unit/test_mt5_basic.py
python tests/unit/test_mcp_server.py
```

**Integration Tests:**
```bash
python tests/integration/test_connectivity.py
python tests/integration/test_complete_flow.py
```

## 📋 Test Categories

### 🔧 Unit Tests
- **MT5 Basic**: Tests core MetaTrader 5 functionality
  - Connection and initialization
  - Symbol information retrieval
  - Historical data access
  - Market book (Level 2) data
  - Account information

- **MCP Server**: Tests Model Context Protocol server
  - HTTP endpoints
  - JSON-RPC protocol compliance
  - Tool registration and execution

### 🔄 Integration Tests
- **Connectivity**: End-to-end connectivity testing
  - Network connectivity (Windows ↔ macOS)
  - MCP protocol communication
  - MT5 server integration

- **Complete Flow**: Full trading workflow validation
  - Demo account validation
  - Market data retrieval
  - Order placement and management
  - Position modification and closure
  - Error handling and safety checks

### 🛠️ Utility Tests
- **Setup**: Environment validation
  - Dependency checking
  - MT5 installation verification
  - Configuration validation

## 🔒 Safety Features

All trading tests include safety mechanisms:
- ✅ **Demo Account Only**: Tests verify demo accounts before trading
- ✅ **Small Volumes**: Uses minimum trade sizes
- ✅ **Auto Cleanup**: Automatically closes test positions
- ✅ **Error Handling**: Comprehensive error reporting

## 📊 Test Results

Tests generate comprehensive reports including:
- ✅ Pass/fail status for each test
- 📊 Detailed execution logs
- 🔍 Error diagnostics
- 📈 Performance metrics

## 🚨 Troubleshooting

### Common Issues

**MT5 Connection Failed:**
- Ensure MT5 is running and logged in
- Check no other applications are using MT5
- Verify account permissions

**Network Connectivity Issues:**
- Check firewall settings (port 50051)
- Verify server IP address
- Test basic HTTP connectivity

**Trading Tests Fail:**
- Ensure using demo account only
- Check market hours for selected symbols
- Verify sufficient demo balance

### Debug Mode

Run individual tests with debug output:
```bash
python -u tests/unit/test_mt5_basic.py
```

## 📝 Test Maintenance

### Adding New Tests
1. Choose appropriate category (unit/integration/utils)
2. Follow existing naming convention
3. Add safety checks for trading tests
4. Update this README

### Updating Tests
- Keep safety mechanisms intact
- Maintain backward compatibility
- Update documentation

## 🎯 Coverage

### ✅ **100% Method Coverage Achieved!**

**All 16 MT5Client methods are now tested:**

**Integration Tests:**
```bash
python tests/integration/test_connectivity.py      # 3 basic methods + MCP tools
python tests/integration/test_complete_flow.py     # 12 main trading methods  
python tests/integration/test_comprehensive_coverage.py  # 4 specific methods
```

**Detailed Coverage:**
- ✅ Connection & Account: `test_connection`, `get_account_info`, `validate_demo_for_trading`
- ✅ Market Data: `list_symbols`, `get_symbol_info`, `get_book_l2`
- ✅ Positions: `get_positions`, `get_position_by_ticket`, `position_modify`
- ✅ Orders: `get_orders`, `get_order_by_ticket`, `order_send`, `order_send_limit`, `order_modify`, `order_cancel`, `order_close`

**Quality Assurance:**
- ✅ Only retcode 10009 (success) passes trading tests
- ✅ MARKET_CLOSED correctly fails tests
- ✅ Robust error handling and cleanup
- ✅ Real market symbols and volumes

📈 **See `COVERAGE_REPORT.md` for complete details**

---

**🔥 Quick Start**: `python tests/run_all_tests.py`
