"""
MetaTrader 5 MCP Server - Simple Main Entry Point
Only imports to register all tools, without prompts
"""

# Import server modules to register all tools
from mcp_metatrader5_server.server import mcp
import mcp_metatrader5_server.market_data
import mcp_metatrader5_server.trading

# This file exists only to import all modules and register all tools
# Used by HTTP server to ensure all 41 tools are available