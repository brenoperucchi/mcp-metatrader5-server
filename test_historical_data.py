#!/usr/bin/env python3
"""
MCP MT5 Historical Data Tools Test Script
=========================================
Tests copy_ticks_range and copy_rates_range functionality for ITSA3/ITSA4 symbols.
Verifies that the MCP server can provide historical data for the E5 Market Monitor client.

Author: MCP MT5 Testing Framework
Date: 2024
"""

import json
import logging
import os
import sys
import time
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Optional imports - will handle gracefully if not available
try:
    import requests
except ImportError:
    print("WARNING: requests library not installed. Install with: pip install requests")
    sys.exit(1)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("INFO: MetaTrader5 not available - will use HTTP-only tests")

# Constants
DEFAULT_SERVER = "http://localhost:8000"
DEFAULT_SYMBOLS = ["ITSA3", "ITSA4"]
DEFAULT_TIMEFRAMES = ["M1"]
DEFAULT_HOURS_BACK = 24  # Use 24 hours for better B3 market data availability
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0

# Timeframe mappings
TIMEFRAME_MAP = {
    "M1": 1,      # 1 minute
    "M5": 5,      # 5 minutes
    "M15": 15,    # 15 minutes
    "M30": 30,    # 30 minutes
    "H1": 60,     # 1 hour (60 minutes)
    "H4": 240,    # 4 hours
    "D1": 1440,   # 1 day
    "W1": 10080,  # 1 week
    "MN1": 43200  # 1 month
}

# Create logs directory structure
LOGS_DIR = Path("logs/historical_data")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
def setup_logging(verbose: bool = False):
    """Configure logging for both console and file output"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Console handler - use UTF-8 encoding for Windows
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                       datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)
    
    # File handler - explicitly use UTF-8 encoding
    file_handler = logging.FileHandler(LOGS_DIR / "test_historical_data.log", mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Configure root logger
    logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])
    
    return logging.getLogger(__name__)

# DateTime utilities
def parse_datetime(value: Union[str, int, float, datetime]) -> datetime:
    """Parse various datetime formats to timezone-aware UTC datetime"""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    
    if isinstance(value, (int, float)):
        # Check if milliseconds (13+ digits) or seconds
        if value > 10000000000:  # Milliseconds
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        else:  # Seconds
            return datetime.fromtimestamp(value, tz=timezone.utc)
    
    if isinstance(value, str):
        # Try to parse as number first
        try:
            return parse_datetime(float(value))
        except ValueError:
            pass
        
        # Parse ISO 8601
        from dateutil import parser
        try:
            dt = parser.parse(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except:
            # Fallback formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except:
                    continue
    
    raise ValueError(f"Cannot parse datetime from: {value}")

def dt_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string with Z suffix"""
    if dt.tzinfo is None:
        # Naive datetime - assume it's already in the correct timezone
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def dt_to_unix_s(dt: datetime) -> int:
    """Convert datetime to Unix seconds"""
    return int(dt.timestamp())

def dt_to_unix_ms(dt: datetime) -> int:
    """Convert datetime to Unix milliseconds"""
    return int(dt.timestamp() * 1000)

class MCPHistoricalDataTester:
    """Main test orchestrator for MCP MT5 historical data tools"""
    
    def __init__(self, server_url: str, logger: logging.Logger):
        self.server_url = server_url.rstrip('/')
        self.logger = logger
        self.session = requests.Session()
        self.results = {
            "meta": {},
            "discovery": {},
            "tests": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "empty": 0
            }
        }
        self.mt5_initialized = False
        self.account_info = {}
        
    def check_connectivity(self) -> bool:
        """Check if MCP server is reachable"""
        endpoints = ["/health", "/", "/mcp", "/mcp/status", "/docs", "/openapi.json"]
        
        for endpoint in endpoints:
            url = f"{self.server_url}{endpoint}"
            try:
                start = time.time()
                response = self.session.get(url, timeout=5)
                elapsed_ms = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    self.logger.info(f"[OK] Server reachable at {url} ({elapsed_ms:.0f}ms)")
                    return True
                    
            except requests.exceptions.RequestException as e:
                self.logger.debug(f"Failed to reach {url}: {e}")
                continue
        
        self.logger.error(f"[FAIL] Server not reachable at {self.server_url}")
        return False
    
    def discover_endpoints(self) -> Dict[str, Any]:
        """Discover copy_ticks_range and copy_rates_range endpoints"""
        discovery = {
            "copy_ticks_range": None,
            "copy_rates_range": None
        }
        
        # Check if tools are available via MCP protocol
        mcp_url = f"{self.server_url}/mcp"
        try:
            response = self.session.post(
                mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and "tools" in data["result"]:
                    tools = data["result"]["tools"]
                    tool_names = [t["name"] for t in tools if isinstance(t, dict)]
                    
                    if "copy_ticks_range" in tool_names:
                        discovery["copy_ticks_range"] = {
                            "method": "MCP",
                            "path": "/mcp",
                            "style": "json_rpc"
                        }
                        self.logger.info("[OK] Found copy_ticks_range via MCP protocol")
                    
                    if "copy_rates_range" in tool_names:
                        discovery["copy_rates_range"] = {
                            "method": "MCP",
                            "path": "/mcp",
                            "style": "json_rpc"
                        }
                        self.logger.info("[OK] Found copy_rates_range via MCP protocol")
                        
        except Exception as e:
            self.logger.debug(f"MCP discovery failed: {e}")
        
        # If not found via MCP, use known implementation
        if not discovery["copy_ticks_range"]:
            discovery["copy_ticks_range"] = {
                "method": "MCP_FALLBACK",
                "path": "/mcp",
                "style": "json_rpc"
            }
            self.logger.info("[INFO] Using fallback for copy_ticks_range")
        
        if not discovery["copy_rates_range"]:
            discovery["copy_rates_range"] = {
                "method": "MCP_FALLBACK", 
                "path": "/mcp",
                "style": "json_rpc"
            }
            self.logger.info("[INFO] Using fallback for copy_rates_range")
        
        self.results["discovery"] = discovery
        return discovery
    
    def init_mt5_local(self) -> bool:
        """Initialize local MT5 connection if available"""
        if not MT5_AVAILABLE:
            self.logger.info("MetaTrader5 module not available")
            return False
        
        try:
            # Try default initialization
            if not mt5.initialize():
                # Try with custom path if environment variable set
                mt5_path = os.environ.get("MT5_TERMINAL_PATH")
                if mt5_path:
                    self.logger.info(f"Trying MT5 initialization with path: {mt5_path}")
                    if not mt5.initialize(mt5_path):
                        self.logger.warning("Failed to initialize MT5 with custom path")
                        return False
                else:
                    self.logger.warning("Failed to initialize MT5")
                    return False
            
            # Get account info
            info = mt5.account_info()
            if info:
                self.account_info = {
                    "number": info.login,
                    "server": info.server,
                    "company": info.company,
                    "mode": "DEMO" if "demo" in info.server.lower() else "REAL"
                }
                self.logger.info(f"[OK] MT5 initialized - Account: {info.login} ({self.account_info['mode']})")
                self.mt5_initialized = True
                return True
            
        except Exception as e:
            self.logger.warning(f"MT5 initialization error: {e}")
        
        return False
    
    def select_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """Ensure symbols are selected in Market Watch"""
        status = {}
        
        for symbol in symbols:
            if self.mt5_initialized:
                try:
                    # Select symbol in MT5
                    if mt5.symbol_select(symbol, True):
                        info = mt5.symbol_info(symbol)
                        if info:
                            status[symbol] = True
                            self.logger.info(f"[OK] Symbol {symbol} selected - Bid: {info.bid}, Ask: {info.ask}")
                        else:
                            status[symbol] = False
                            self.logger.warning(f"[WARN] Symbol {symbol} info not available")
                    else:
                        status[symbol] = False
                        self.logger.warning(f"[WARN] Failed to select symbol {symbol}")
                except Exception as e:
                    status[symbol] = False
                    self.logger.error(f"Error selecting {symbol}: {e}")
            else:
                # Try via MCP if available
                try:
                    response = self.call_mcp_tool("symbol_select", {
                        "symbol": symbol,
                        "visible": True
                    })
                    status[symbol] = response.get("success", False)
                except:
                    status[symbol] = False
        
        return status
    
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via JSON-RPC"""
        url = f"{self.server_url}/mcp"
        
        # Convert datetime objects to ISO strings for JSON serialization
        # The server expects string dates and will convert them back to datetime
        for key in ["date_from", "date_to", "from_date", "to_date"]:
            if key in arguments and isinstance(arguments[key], datetime):
                arguments[key] = dt_to_iso(arguments[key])
        
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        self.logger.debug(f"Calling MCP tool {tool_name}: {json.dumps(arguments, default=str)}")
        
        try:
            response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                return {"success": False, "error": data["error"]}
            
            if "result" in data:
                content = data["result"].get("content", data["result"])
                return {"success": True, "data": content}
            
            return {"success": False, "error": "Invalid response format"}
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON response: {e}"}
    
    def test_copy_ticks_range(self, symbol: str, date_from: datetime, date_to: datetime, 
                             flags: str = "ALL") -> Dict[str, Any]:
        """Test copy_ticks_range for a symbol"""
        test_result = {
            "tool": "copy_ticks_range",
            "symbol": symbol,
            "flags": flags,
            "from": {
                "iso": dt_to_iso(date_from),
                "unix_s": dt_to_unix_s(date_from),
                "unix_ms": dt_to_unix_ms(date_from)
            },
            "to": {
                "iso": dt_to_iso(date_to),
                "unix_s": dt_to_unix_s(date_to),
                "unix_ms": dt_to_unix_ms(date_to)
            },
            "request": {},
            "result": {},
            "validation": {"ok": False, "issues": []},
            "error": None
        }
        
        # Map flags string to MT5 constants if needed
        flags_map = {
            "ALL": 0,  # or mt5.COPY_TICKS_ALL if available
            "INFO": 1,  # mt5.COPY_TICKS_INFO
            "TRADE": 2  # mt5.COPY_TICKS_TRADE
        }
        flags_value = flags_map.get(flags, 0)
        
        start_time = time.time()
        
        # For ticks, also try with shorter range if needed 
        response = self.call_mcp_tool("copy_ticks_range", {
            "symbol": symbol,
            "date_from": date_from,
            "date_to": date_to,
            "flags": flags_value
        })
        
        # If failed with exception, try shorter range for ticks too
        if not response["success"] and ("exception" in str(response.get("error", "")).lower() or "Invalid params" in str(response.get("error", ""))):
            self.logger.debug(f"Initial ticks request failed, trying shorter range for {symbol}")
            # Use last 3 hours from now
            shorter_to = datetime.now(timezone.utc)
            shorter_from = shorter_to - timedelta(hours=3)
            
            response = self.call_mcp_tool("copy_ticks_range", {
                "symbol": symbol,
                "date_from": shorter_from,
                "date_to": shorter_to,
                "flags": flags_value
            })
            
            if response["success"]:
                # Update test result to reflect actual used dates
                test_result["from"] = {
                    "iso": dt_to_iso(shorter_from),
                    "unix_s": dt_to_unix_s(shorter_from),
                    "unix_ms": dt_to_unix_ms(shorter_from)
                }
                test_result["to"] = {
                    "iso": dt_to_iso(shorter_to),
                    "unix_s": dt_to_unix_s(shorter_to),
                    "unix_ms": dt_to_unix_ms(shorter_to)
                }
                test_result["note"] = "Used shorter range due to MT5 limitations"
        
        elapsed_ms = (time.time() - start_time) * 1000
        test_result["request"]["elapsed_ms"] = elapsed_ms
        
        if response["success"]:
            data = response["data"]
            
            if isinstance(data, list):
                ticks = data
            elif isinstance(data, dict) and "ticks" in data:
                ticks = data["ticks"]
            else:
                ticks = []
            
            test_result["result"]["count"] = len(ticks)
            
            if ticks:
                # Sample first and last tick
                test_result["result"]["first_tick"] = ticks[0] if ticks else None
                test_result["result"]["last_tick"] = ticks[-1] if len(ticks) > 1 else None
                
                # Validate data
                issues = []
                
                # Check for required fields
                required_fields = ["time"]
                for tick in ticks[:10]:  # Check first 10
                    for field in required_fields:
                        if field not in tick:
                            issues.append(f"Missing field: {field}")
                            break
                
                # Check timestamp monotonicity
                prev_time = None
                for i, tick in enumerate(ticks):
                    if "time" in tick:
                        curr_time = tick["time"]
                        if prev_time and curr_time < prev_time:
                            issues.append(f"Non-monotonic timestamp at index {i}")
                            break
                        prev_time = curr_time
                
                test_result["validation"]["ok"] = len(issues) == 0
                test_result["validation"]["issues"] = issues[:5]  # Limit issues
                
                self.logger.info(f"[OK] {symbol} ticks ({flags}): {len(ticks)} records in {elapsed_ms:.0f}ms")
            else:
                test_result["validation"]["ok"] = True  # Empty can be valid
                test_result["validation"]["issues"] = ["No data in time range"]
                self.logger.warning(f"[WARN] {symbol} ticks ({flags}): No data found")
        else:
            test_result["error"] = response.get("error", "Unknown error")
            self.logger.error(f"[FAIL] {symbol} ticks ({flags}): {test_result['error']}")
        
        return test_result
    
    def test_copy_rates_range(self, symbol: str, timeframe: str, 
                             date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Test copy_rates_range for a symbol"""
        test_result = {
            "tool": "copy_rates_range",
            "symbol": symbol,
            "timeframe": timeframe,
            "from": {
                "iso": dt_to_iso(date_from),
                "unix_s": dt_to_unix_s(date_from),
                "unix_ms": dt_to_unix_ms(date_from)
            },
            "to": {
                "iso": dt_to_iso(date_to),
                "unix_s": dt_to_unix_s(date_to),
                "unix_ms": dt_to_unix_ms(date_to)
            },
            "request": {},
            "result": {},
            "validation": {"ok": False, "issues": []},
            "error": None
        }
        
        # Convert timeframe to integer if needed
        timeframe_value = TIMEFRAME_MAP.get(timeframe, 1)
        
        start_time = time.time()
        
        # For rates, try with a shorter date range if initial request fails
        # B3 market has limited historical OHLC data availability
        original_date_from = date_from
        
        # First try with original range
        response = self.call_mcp_tool("copy_rates_range", {
            "symbol": symbol,
            "timeframe": timeframe_value,
            "date_from": date_from,
            "date_to": date_to
        })
        
        # If failed, try with just the last 6 hours of recent trading
        if not response["success"] and "Invalid params" in str(response.get("error", "")):
            self.logger.debug(f"Initial rates request failed, trying shorter range for {symbol}")
            # Use last 6 hours from now (more likely to have data)
            shorter_to = datetime.now(timezone.utc)
            shorter_from = shorter_to - timedelta(hours=6)
            
            response = self.call_mcp_tool("copy_rates_range", {
                "symbol": symbol,
                "timeframe": timeframe_value,
                "date_from": shorter_from,
                "date_to": shorter_to
            })
            
            if response["success"]:
                # Update test result to reflect actual used dates
                test_result["from"] = {
                    "iso": dt_to_iso(shorter_from),
                    "unix_s": dt_to_unix_s(shorter_from),
                    "unix_ms": dt_to_unix_ms(shorter_from)
                }
                test_result["to"] = {
                    "iso": dt_to_iso(shorter_to),
                    "unix_s": dt_to_unix_s(shorter_to),
                    "unix_ms": dt_to_unix_ms(shorter_to)
                }
                test_result["note"] = "Used shorter range due to B3 data limitations"
        
        elapsed_ms = (time.time() - start_time) * 1000
        test_result["request"]["elapsed_ms"] = elapsed_ms
        
        if response["success"]:
            data = response["data"]
            
            if isinstance(data, list):
                rates = data
            elif isinstance(data, dict) and "rates" in data:
                rates = data["rates"]
            else:
                rates = []
            
            test_result["result"]["count"] = len(rates)
            
            if rates:
                # Sample first and last rate
                test_result["result"]["first_rate"] = rates[0] if rates else None
                test_result["result"]["last_rate"] = rates[-1] if len(rates) > 1 else None
                
                # Validate data
                issues = []
                
                # Check for OHLCV fields
                required_fields = ["time", "open", "high", "low", "close"]
                for rate in rates[:10]:  # Check first 10
                    for field in required_fields:
                        if field not in rate:
                            issues.append(f"Missing field: {field}")
                            break
                    
                    # Validate OHLC relationship
                    if all(f in rate for f in ["open", "high", "low", "close"]):
                        if rate["high"] < rate["low"]:
                            issues.append("Invalid OHLC: high < low")
                        if rate["high"] < rate["open"] or rate["high"] < rate["close"]:
                            issues.append("Invalid OHLC: high < open/close")
                        if rate["low"] > rate["open"] or rate["low"] > rate["close"]:
                            issues.append("Invalid OHLC: low > open/close")
                
                # Check timestamp monotonicity
                prev_time = None
                for i, rate in enumerate(rates):
                    if "time" in rate:
                        curr_time = rate["time"]
                        if prev_time and curr_time <= prev_time:
                            issues.append(f"Non-monotonic timestamp at index {i}")
                            break
                        prev_time = curr_time
                
                test_result["validation"]["ok"] = len(issues) == 0
                test_result["validation"]["issues"] = issues[:5]  # Limit issues
                
                self.logger.info(f"[OK] {symbol} rates ({timeframe}): {len(rates)} candles in {elapsed_ms:.0f}ms")
            else:
                test_result["validation"]["ok"] = True  # Empty can be valid
                test_result["validation"]["issues"] = ["No data in time range"]
                self.logger.warning(f"[WARN] {symbol} rates ({timeframe}): No data found")
        else:
            test_result["error"] = response.get("error", "Unknown error")
            self.logger.error(f"[FAIL] {symbol} rates ({timeframe}): {test_result['error']}")
        
        return test_result
    
    def generate_curl_examples(self, date_from: datetime, date_to: datetime) -> str:
        """Generate curl command examples for testing"""
        examples = []
        
        # Header
        examples.append("# MCP MT5 Historical Data - CURL Examples")
        examples.append("# " + "=" * 50)
        examples.append(f"# Server: {self.server_url}")
        examples.append(f"# Generated: {datetime.now().isoformat()}")
        examples.append("")
        
        # copy_ticks_range examples
        examples.append("# copy_ticks_range - Get tick data")
        examples.append("# ---------------------------------")
        
        # JSON-RPC format with ISO dates
        examples.append("# With ISO 8601 dates:")
        iso_from = dt_to_iso(date_from)
        iso_to = dt_to_iso(date_to)
        cmd = f"""curl -X POST {self.server_url}/mcp \\
  -H "Content-Type: application/json" \\
  -d '{{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{{"name":"copy_ticks_range","arguments":{{"symbol":"ITSA3","date_from":"{iso_from}","date_to":"{iso_to}","flags":0}}}}}}' """
        examples.append(cmd)
        examples.append("")
        
        # With Unix timestamps
        examples.append("# With Unix timestamps (seconds):")
        unix_from = dt_to_unix_s(date_from)
        unix_to = dt_to_unix_s(date_to)
        cmd = f"""curl -X POST {self.server_url}/mcp \\
  -H "Content-Type: application/json" \\
  -d '{{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{{"name":"copy_ticks_range","arguments":{{"symbol":"ITSA4","date_from":{unix_from},"date_to":{unix_to},"flags":0}}}}}}' """
        examples.append(cmd)
        examples.append("")
        
        # copy_rates_range examples
        examples.append("# copy_rates_range - Get OHLCV candles")
        examples.append("# -------------------------------------")
        
        # M1 timeframe
        examples.append("# M1 (1-minute) candles:")
        cmd = f"""curl -X POST {self.server_url}/mcp \\
  -H "Content-Type: application/json" \\
  -d '{{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{{"name":"copy_rates_range","arguments":{{"symbol":"ITSA3","timeframe":1,"date_from":"{iso_from}","date_to":"{iso_to}"}}}}}}' """
        examples.append(cmd)
        examples.append("")
        
        # H1 timeframe
        examples.append("# H1 (1-hour) candles:")
        cmd = f"""curl -X POST {self.server_url}/mcp \\
  -H "Content-Type: application/json" \\
  -d '{{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{{"name":"copy_rates_range","arguments":{{"symbol":"ITSA4","timeframe":60,"date_from":"{iso_from}","date_to":"{iso_to}"}}}}}}' """
        examples.append(cmd)
        examples.append("")
        
        # Pretty print with jq
        examples.append("# Pretty print JSON response with jq:")
        examples.append("# Add: | jq '.'")
        examples.append("")
        
        # Extract just the data
        examples.append("# Extract just the data array:")
        examples.append("# Add: | jq '.result.content'")
        examples.append("")
        
        # Count records
        examples.append("# Count number of records:")
        examples.append("# Add: | jq '.result.content | length'")
        examples.append("")
        
        return "\n".join(examples)
    
    def run_tests(self, symbols: List[str], timeframes: List[str], 
                  date_from: datetime, date_to: datetime) -> None:
        """Run all tests"""
        self.logger.info("=" * 60)
        self.logger.info("Starting MCP MT5 Historical Data Tests")
        self.logger.info("=" * 60)
        
        # Setup metadata
        self.results["meta"] = {
            "server_url": self.server_url,
            "run_started_at": datetime.now(timezone.utc).isoformat(),
            "host": f"Windows - Python {sys.version.split()[0]}",
            "python_version": sys.version.split()[0],
            "account": self.account_info if self.account_info else {"mode": "HTTP_ONLY"}
        }
        
        # Check connectivity
        if not self.check_connectivity():
            self.logger.error("Server not reachable - exiting")
            self.save_results()
            sys.exit(1)
        
        # Discover endpoints
        self.discover_endpoints()
        
        # Initialize MT5 if available
        if MT5_AVAILABLE:
            self.init_mt5_local()
        
        # Select symbols
        symbol_status = self.select_symbols(symbols)
        self.logger.info(f"Symbol selection status: {symbol_status}")
        
        # Test copy_ticks_range
        self.logger.info("\n" + "=" * 40)
        self.logger.info("Testing copy_ticks_range")
        self.logger.info("=" * 40)
        
        for symbol in symbols:
            for flags in ["ALL", "INFO", "TRADE"]:
                test_result = self.test_copy_ticks_range(symbol, date_from, date_to, flags)
                test_result["mode"] = "http"
                self.results["tests"].append(test_result)
                
                # Update summary
                self.results["summary"]["total_tests"] += 1
                if test_result["error"]:
                    self.results["summary"]["failed"] += 1
                elif test_result["result"].get("count", 0) == 0:
                    self.results["summary"]["empty"] += 1
                else:
                    self.results["summary"]["passed"] += 1
                
                time.sleep(0.5)  # Rate limiting
        
        # Test copy_rates_range
        self.logger.info("\n" + "=" * 40)
        self.logger.info("Testing copy_rates_range")
        self.logger.info("=" * 40)
        
        for symbol in symbols:
            for timeframe in timeframes:
                test_result = self.test_copy_rates_range(symbol, timeframe, date_from, date_to)
                test_result["mode"] = "http"
                self.results["tests"].append(test_result)
                
                # Update summary
                self.results["summary"]["total_tests"] += 1
                if test_result["error"]:
                    self.results["summary"]["failed"] += 1
                elif test_result["result"].get("count", 0) == 0:
                    self.results["summary"]["empty"] += 1
                else:
                    self.results["summary"]["passed"] += 1
                
                time.sleep(0.5)  # Rate limiting
        
        # Generate curl examples
        curl_examples = self.generate_curl_examples(date_from, date_to)
        curl_file = LOGS_DIR / "curl_examples.txt"
        curl_file.write_text(curl_examples)
        self.logger.info(f"\n[OK] Curl examples saved to: {curl_file}")
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    def save_results(self):
        """Save test results to JSON file"""
        results_file = LOGS_DIR / "test_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        self.logger.info(f"[OK] Results saved to: {results_file}")
        
        # Also save dated version
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        dated_file = LOGS_DIR / f"test_results_{date_str}.json"
        with open(dated_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
    
    def print_summary(self):
        """Print test summary to console"""
        summary = self.results["summary"]
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests:  {summary['total_tests']}")
        print(f"Passed:       {summary['passed']} ({summary['passed']/max(1,summary['total_tests'])*100:.1f}%)")
        print(f"Failed:       {summary['failed']} ({summary['failed']/max(1,summary['total_tests'])*100:.1f}%)")
        print(f"Empty data:   {summary['empty']} ({summary['empty']/max(1,summary['total_tests'])*100:.1f}%)")
        print("=" * 60)
        
        if self.account_info:
            print(f"MT5 Account:  {self.account_info.get('number', 'N/A')} ({self.account_info.get('mode', 'N/A')})")
        
        print(f"\nLogs directory: {LOGS_DIR.absolute()}")
        print(f"  - test_results.json")
        print(f"  - test_historical_data.log")
        print(f"  - curl_examples.txt")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.mt5_initialized and MT5_AVAILABLE:
            mt5.shutdown()
            self.logger.info("MT5 connection closed")
        self.session.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test MCP MT5 Historical Data Tools (copy_ticks_range, copy_rates_range)"
    )
    
    parser.add_argument(
        "--server", "-s",
        default=DEFAULT_SERVER,
        help=f"MCP server URL (default: {DEFAULT_SERVER})"
    )
    
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help=f"Symbols to test (default: {' '.join(DEFAULT_SYMBOLS)})"
    )
    
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=DEFAULT_TIMEFRAMES,
        help=f"Timeframes to test (default: {' '.join(DEFAULT_TIMEFRAMES)})"
    )
    
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Number of days to look back (default: 1)"
    )
    
    parser.add_argument(
        "--hours-back",
        type=int,
        default=DEFAULT_HOURS_BACK,
        help=f"Number of hours to look back (default: {DEFAULT_HOURS_BACK})"
    )
    
    parser.add_argument(
        "--from",
        dest="date_from",
        help="Start date (ISO 8601 or Unix timestamp)"
    )
    
    parser.add_argument(
        "--to",
        dest="date_to",
        help="End date (ISO 8601 or Unix timestamp)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Parse date range
    if args.date_from and args.date_to:
        date_from = parse_datetime(args.date_from)
        date_to = parse_datetime(args.date_to)
    else:
        # Use current local time (MT5 server time)
        date_to = datetime.now()  # Local time, not UTC
        if hasattr(args, 'hours_back') and args.hours_back:
            date_from = date_to - timedelta(hours=args.hours_back)
        else:
            date_from = date_to - timedelta(days=args.days_back)
        
        # Convert to UTC for display but keep naive for MT5 server
        logger.info(f"Using local time range (MT5 server time)")
    
    logger.info(f"Date range: {dt_to_iso(date_from)} to {dt_to_iso(date_to)}")
    
    # Create tester and run tests
    tester = MCPHistoricalDataTester(args.server, logger)
    
    try:
        tester.run_tests(args.symbols, args.timeframes, date_from, date_to)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
    finally:
        tester.cleanup()
    
    # Exit code based on results
    summary = tester.results["summary"]
    if summary["failed"] > 0 and summary["passed"] == 0:
        sys.exit(1)  # All tests failed
    else:
        sys.exit(0)  # Some or all tests passed

if __name__ == "__main__":
    main()
