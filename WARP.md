# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This is a **MetaTrader 5 MCP Server** - a Model Context Protocol server that connects AI assistants (like Claude) to MetaTrader 5 for financial trading and market data analysis. It uses FastMCP to expose trading tools, market data, and account information via the MCP protocol.

**Key capabilities:**
- Connect to MetaTrader 5 terminal
- Retrieve account information and terminal status
- Access market data and trading history
- Execute trading operations (initialize, login, get account info)
- Real-mode testing with full order lifecycle (OPEN → MODIFY → CLOSE)

## Repository Architecture

```
fork_mcp/
├── src/mcp_metatrader5_server/        # Core MCP server implementation
│   ├── server.py                      # Main FastMCP server (mcp instance)
│   ├── cli.py                         # Command line interface (mt5mcp)
│   ├── main.py                        # MCP tools and resources
│   ├── market_data.py                 # Market data functionality
│   └── trading.py                     # Trading operations
├── main.py                            # Alternative entry point with prompts
├── tests/                             # Comprehensive test suite
│   ├── run_all_tests.py              # Main test runner
│   ├── unit/                         # Unit tests (MT5, MCP server)
│   ├── integration/                  # Integration tests (connectivity, workflows)
│   └── utils/                        # Environment validation
├── client/                           # MCP client code
├── config/                           # Configuration files
├── docs/                             # Documentation
├── scripts/                          # Development scripts
└── pyproject.toml                    # Python package configuration
```

**Core Components:**
- **FastMCP Server**: `src/mcp_metatrader5_server/server.py` exports `mcp = FastMCP("MetaTrader 5 MCP Server")`
- **Tools**: `@mcp.tool()` decorators register MT5 functions (initialize, login, get_account_info, etc.)
- **Models**: Pydantic models (SymbolInfo, AccountInfo, OrderRequest, Position, Deal, etc.)
- **CLI**: `mt5mcp dev|install` commands via `src/mcp_metatrader5_server/cli.py`

## Prerequisites

- **OS**: Windows (recommended - MetaTrader5 Python package integrates with installed MT5 terminal)
- **Python**: 3.11+
- **MetaTrader 5 Desktop**: Installed and logged in to broker account (DEMO or REAL)
- **Tools**: uv (recommended), pip, git
- **Optional**: Claude Desktop for MCP integration

**Dependencies** (from pyproject.toml):
- fastmcp>=0.4.1
- mcp[cli]>=1.6.0
- MetaTrader5>=5.0.5200
- pandas>=2.2.3, numpy>=1.24.0, pydantic>=2.0.0

**Important**: Ensure MT5 terminal is running and accessible to Python API before using initialize/login tools.

## Quick Start

### Installation
```bash
cd fork_mcp
pip install -e .
```

### Development Server (Recommended)
```bash
# FastMCP direct
uv run fastmcp dev src/mcp_metatrader5_server/server.py

# Alternative: CLI (after applying fixes below)
uv run mt5mcp dev --host 127.0.0.1 --port 50051

# Alternative: uvicorn direct
uv run uvicorn mcp_metatrader5_server.server:mcp --host 127.0.0.1 --port 50051 --reload
```

### Claude Desktop Integration
```bash
# Install for Claude Desktop
uv run fastmcp install src/mcp_metatrader5_server/server.py
```

**Claude Desktop Config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "MetaTrader 5 MCP Server": {
      "command": "uv",
      "args": [
        "run",
        "--with", "MetaTrader5",
        "--with", "fastmcp",
        "--with", "numpy",
        "--with", "pandas",
        "--with", "pydantic",
        "fastmcp",
        "run",
        "C:\\REPLACE_WITH_ACTUAL_PATH\\fork_mcp\\src\\mcp_metatrader5_server\\server.py"
      ]
    }
  }
}
```

## Commands Reference

### CLI Commands
```bash
# Show version
uv run mt5mcp --version

# Development server
uv run mt5mcp dev [--host HOST] [--port PORT]

# Install for Claude Desktop (after fixes)
uv run mt5mcp install
```

### FastMCP Commands
```bash
# Development with hot reload
uv run fastmcp dev src/mcp_metatrader5_server/server.py [--port PORT]

# Install for Claude Desktop
uv run fastmcp install src/mcp_metatrader5_server/server.py
```

### Testing Commands
```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test suites
python -m pytest tests/
python tests/unit/test_mt5_basic.py
python tests/integration/test_complete_flow.py
```

## Logging Conventions

**All logs must be saved in the root directory under `/logs/command_name/`:**

### Directory Structure
```
logs/
├── dev/                              # Development server logs
├── tests/                            # Test execution logs  
└── trading/                          # Trading session logs with account tracking
```

### File Naming Patterns
- `logs/dev/server_YYYYMMDD_HHMMSS.log`
- `logs/tests/run_all_tests_YYYYMMDD_HHMMSS.log`
- `logs/trading/trade_session_{ACCOUNT}_{DEMO|REAL}_YYYYMMDD_HHMMSS.json`

### Logging Commands
```bash
# Capture server logs
uv run fastmcp dev src/mcp_metatrader5_server/server.py | tee logs/dev/server_$(date +%Y%m%d_%H%M%S).log

# Capture test logs  
python tests/run_all_tests.py | tee logs/tests/run_all_tests_$(date +%Y%m%d_%H%M%S).log
```

### Code Example: Add File Logging
```python
import os
import logging
from datetime import datetime

# Create logs directory
os.makedirs("logs/dev", exist_ok=True)

# Add file handler
log_file = f"logs/dev/server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(file_handler)
```

## Development Workflow

### Adding Tools (@mcp.tool)
```python
@mcp.tool()
def your_tool(param: str) -> dict:
    """Tool description for AI assistant."""
    # Validate MT5 state first
    if not mt5.initialize():
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        raise ValueError("MT5 not initialized")
    
    # Your logic here
    result = mt5.some_function(param)
    if result is None:
        logger.error(f"MT5 operation failed: {mt5.last_error()}")
        raise ValueError("Operation failed")
    
    return {"status": "success", "data": result}
```

### Adding Prompts (@mcp.prompt)
```python
@mcp.prompt()
def trading_workflow(symbol: str, volume: float) -> list:
    """Prompt for trading workflow."""
    return [
        UserMessage(f"I want to trade {symbol} with volume {volume}"),
        AssistantMessage("I'll help you with that trade...")
    ]
```

### Adding Resources (@mcp.resource)
```python
@mcp.resource("mt5://your_guide")
def your_guide() -> str:
    """Resource providing guidance."""
    with open("docs/your_guide.md", "r") as f:
        return f.read()
```

### Code Guidelines
- Keep tools idempotent and return JSON-serializable data
- Use Pydantic models for inputs/outputs
- Validate MetaTrader5 state before trading/data calls
- Handle and log `mt5.last_error()` on failures
- Use contextual logging (symbol, order id, account)
- Use `--reload` for hot reloading during development

## Real-Mode Testing & Account Tracking

**User preference**: Test in real mode with orders sent directly to MCP, including full lifecycle OPEN → MODIFY → CLOSE, and track account number and DEMO/REAL mode.

### Account Session Tracking
```python
import json
from datetime import datetime
from mcp_metatrader5_server.server import initialize, login, get_account_info

def track_trading_session(login_num, password, server):
    """Track trading session with account info."""
    # Initialize and login
    if not initialize():
        raise ValueError("MT5 initialization failed")
    
    if not login(login_num, password, server):
        raise ValueError("MT5 login failed")
    
    # Get account info
    account = get_account_info()
    
    # Determine DEMO/REAL from account info
    account_type = "DEMO" if "demo" in server.lower() or account.trade_mode == 0 else "REAL"
    
    # Create session log
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "account": account.login,
        "server": account.server,
        "type": account_type,
        "balance": account.balance,
        "equity": account.equity,
        "margin_level": account.margin_level,
        "currency": account.currency,
        "leverage": account.leverage
    }
    
    # Save to logs/trading/
    os.makedirs("logs/trading", exist_ok=True)
    log_file = f"logs/trading/trade_session_{account.login}_{account_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(log_file, "w") as f:
        json.dump(session_data, f, indent=2)
    
    return session_data
```

### Safety for Real Trading
- **Environment Flag**: Set `REAL_MODE_TESTS=1` to enable real trading operations
- **Minimum Volumes**: Use smallest allowed trade sizes
- **Immediate Cleanup**: Auto-close test positions
- **Clear Warnings**: Label examples that will place real orders

## Testing

### Test Structure
- **Unit Tests**: Individual components (MT5, MCP server)
- **Integration Tests**: Full workflows, connectivity, comprehensive coverage  
- **Utils Tests**: Environment validation

### Running Tests
```bash
# All tests with comprehensive reporting
python tests/run_all_tests.py

# Individual test categories  
python tests/utils/test_setup.py                           # Environment validation
python tests/unit/test_mt5_basic.py                       # MT5 basic functionality
python tests/integration/test_complete_flow.py            # Full trading workflows
```

### Test Preconditions
- MT5 terminal running and logged in
- Demo account recommended (unless `REAL_MODE_TESTS=1`)
- Market hours for test symbols
- Sufficient demo balance

### Safety Mechanisms
- ✅ Demo account validation before trading
- ✅ Minimum trade volumes only
- ✅ Automatic position cleanup
- ✅ Comprehensive error handling
- ✅ Only retcode 10009 (success) passes trading tests

## Ports & Networking

### Default Ports
- **CLI Default**: 50051 (after applying fixes)
- **Alternative**: 8000/8080 (uvicorn defaults)

### Port Configuration
```bash
# Set custom port
uv run mt5mcp dev --host 0.0.0.0 --port 8000
uv run fastmcp dev src/mcp_metatrader5_server/server.py --port 8000
```

### Claude Desktop Networking
- Ensure `uv` is in PATH
- Check firewall settings for selected port
- Verify absolute path in Claude config

## Known Issues & Immediate Fixes

### 🔧 CLI Target Mismatch (Fix Required)
**Issue**: `src/mcp_metatrader5_server/cli.py` line 79 targets wrong module
```python
# Current (incorrect)
uvicorn.run("mcp_metatrader5_server.main:mcp", ...)

# Should be
uvicorn.run("mcp_metatrader5_server.server:mcp", ...)
```

### 🔧 CLI Install Command (Fix Required)
**Issue**: `src/mcp_metatrader5_server/cli.py` line 94 uses Python flags incorrectly
```python
# Current (incorrect) 
cmd = [sys.executable, "--with", "mcp-metatrader5-server", ...]

# Should be
cmd = ["uv", "run", "fastmcp", "install", "src/mcp_metatrader5_server/server.py"]
```

### 🔧 Port Consistency
**Issue**: README mentions 8000/8080, CLI defaults to 50051
**Resolution**: Standardize on 50051 for MCP, document alternatives

### 📝 Additional TODOs
- Reconcile `main.py` imports (mt5_server* modules not found)
- Add robust file logging with rotation
- Add environment variables: `REAL_MODE_TESTS`, `LOG_LEVEL`, `LOG_DIR`
- Consider PostgreSQL integration for trade journaling (localhost:5432, db=jumpstart_development, schema=trading)

## Troubleshooting

### MT5 Initialization Fails
- Ensure MT5 terminal is installed and running
- Check account credentials and server string
- Verify no other applications using MT5
- Check logs for `mt5.last_error()` details

### No Tools Visible in MCP
- Confirm serving correct module: `mcp_metatrader5_server.server:mcp`
- Check server startup logs for registered tools
- Try FastMCP dev inspector if available

### Network/Port Conflicts  
- Change `--port` in dev command
- Check firewall settings for inbound connections
- Test basic HTTP connectivity: `curl http://localhost:50051`

### Claude Desktop Not Connecting
- Validate JSON config path is absolute and correct
- Ensure `uv` is installed and in PATH
- Test FastMCP manually before Claude integration
- Check Claude Desktop logs for connection errors

### Unintended Real Trading
- Ensure `REAL_MODE_TESTS` is not set or equals 0
- Confirm account type in `logs/trading/` before testing
- Use demo accounts for development
- Always check trading permissions and account mode

## Database Integration

Per user preferences, consider integrating with local PostgreSQL:
- **Host**: localhost:5432
- **Database**: jumpstart_development  
- **Schema**: trading
- **Use case**: Trade journaling and historical analysis

---

**Quick Commands Summary:**
```bash
# Development
uv run fastmcp dev src/mcp_metatrader5_server/server.py

# Testing  
python tests/run_all_tests.py

# Claude Desktop
uv run fastmcp install src/mcp_metatrader5_server/server.py
```
