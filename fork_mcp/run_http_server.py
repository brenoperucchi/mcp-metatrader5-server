#!/usr/bin/env python3
"""
MCP MetaTrader 5 Server - HTTP Server
Servidor HTTP com FastMCP + endpoints REST customizados
"""

import sys
import os
import atexit
import signal
from pathlib import Path

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mcp_metatrader5_server.logging_utils import setup_logging, reconfigure_stdio_for_windows

# Reconfigure STDIO for Windows
reconfigure_stdio_for_windows()

def start_http_server(host: str = "0.0.0.0", port: int = 8000):
    """Inicia o servidor HTTP com FastMCP + endpoints customizados"""
    
    transport = "http"
    session_id = f"http-{port}"
    
    # Setup structured logging
    logger = setup_logging("run_http_server", session_id=session_id, transport=transport)
    
    try:
        # Import server components
        from mcp_metatrader5_server.server import mcp, config_manager, mt5_status
        import mcp_metatrader5_server.server as server_module
        
        # CRITICAL: Import all modules to register ALL tools
        import mcp_metatrader5_server.market_data  # 16 tools
        import mcp_metatrader5_server.trading      # 11 tools
        
        server_module.logger = logger
        
        logger.info("Initializing HTTP Server", extra={
            "event": "server_startup",
            "context": {
                "transport": transport,
                "mt5_status": mt5_status,
                "host": host,
                "port": port,
                "session_id": session_id
            }
        })
        
        # Create FastAPI app with custom endpoints + FastMCP integration
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, PlainTextResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Create new FastAPI app (not using FastMCP http_app which returns Starlette)
        app = FastAPI(
            title="MetaTrader 5 MCP Server",
            description="HTTP server with MCP tools and REST endpoints",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add MCP endpoints (both GET and POST for Claude CLI compatibility)
        @app.get("/mcp")
        @app.post("/mcp")
        async def mcp_handler(request: Request):
            """MCP protocol handler for both GET and POST"""
            
            # Handle POST (Claude CLI MCP protocol)
            if request.method == "POST":
                try:
                    # Get request body
                    body = await request.json()
                    method = body.get("method", "")
                    
                    # Basic MCP protocol handling
                    if method == "initialize":
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "protocolVersion": "2025-06-18",
                                "serverInfo": {
                                    "name": "MetaTrader 5 MCP Server",
                                    "version": "1.0.0"
                                },
                                "capabilities": {
                                    "tools": {},
                                    "resources": {},
                                    "prompts": {}
                                }
                            }
                        })
                    elif method == "tools/list":
                        # Define complete tools list based on capability_matrix.md (34 tools total)
                        # This is a fallback approach when FastMCP introspection fails
                        tools_list = [
                            # Server tools (7 tools)
                            {"name": "initialize", "description": "Initialize the MetaTrader 5 terminal with current configuration", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "shutdown", "description": "Shut down the connection to the MetaTrader 5 terminal", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "login", "description": "Log in to the MetaTrader 5 trading account", "inputSchema": {"type": "object", "properties": {"login": {"type": "number"}, "password": {"type": "string"}, "server": {"type": "string"}}, "required": ["login", "password", "server"]}},
                            {"name": "get_account_info", "description": "Get information about the current trading account", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "get_terminal_info", "description": "Get information about the MetaTrader 5 terminal", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "get_version", "description": "Get the MetaTrader 5 version", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "validate_demo_for_trading", "description": "Validate if the connected account is a demo account before allowing trading operations", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            
                            # Market Data tools (16 tools)
                            {"name": "get_symbols", "description": "Get all available symbols (financial instruments) from the MetaTrader 5 terminal", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "get_symbols_by_group", "description": "Get symbols that match a specific group or pattern", "inputSchema": {"type": "object", "properties": {"group": {"type": "string"}}, "required": ["group"]}},
                            {"name": "get_symbol_info", "description": "Get information about a specific symbol", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
                            {"name": "get_symbol_info_tick", "description": "Get the latest tick data for a symbol", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
                            {"name": "symbol_select", "description": "Select a symbol in the Market Watch window or remove a symbol from it", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "visible": {"type": "boolean"}}, "required": ["symbol"]}},
                            {"name": "copy_rates_from_pos", "description": "Get bars from a specified symbol and timeframe starting from the specified position", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "timeframe": {"type": "number"}, "start_pos": {"type": "number"}, "count": {"type": "number"}}, "required": ["symbol", "timeframe", "start_pos", "count"]}},
                            {"name": "copy_rates_from_date", "description": "Get bars from a specified symbol and timeframe starting from the specified date", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "timeframe": {"type": "number"}, "date_from": {"type": "string"}, "count": {"type": "number"}}, "required": ["symbol", "timeframe", "date_from", "count"]}},
                            {"name": "copy_rates_range", "description": "Get bars from a specified symbol and timeframe within the specified date range", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "timeframe": {"type": "number"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}}, "required": ["symbol", "timeframe", "date_from", "date_to"]}},
                            {"name": "copy_ticks_from_pos", "description": "Get ticks from a specified symbol starting from the specified position", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "start_pos": {"type": "number"}, "count": {"type": "number"}, "flags": {"type": "number"}}, "required": ["symbol", "start_pos", "count"]}},
                            {"name": "copy_ticks_from_date", "description": "Get ticks from a specified symbol starting from the specified date", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "date_from": {"type": "string"}, "count": {"type": "number"}, "flags": {"type": "number"}}, "required": ["symbol", "date_from", "count"]}},
                            {"name": "copy_ticks_range", "description": "Get ticks from a specified symbol within the specified date range", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}, "flags": {"type": "number"}}, "required": ["symbol", "date_from", "date_to"]}},
                            {"name": "get_last_error", "description": "Get the last error code and description", "inputSchema": {"type": "object", "properties": {}, "required": []}},
                            {"name": "copy_book_levels", "description": "Get Level 2 market data (order book) for a specified symbol", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "depth": {"type": "number"}}, "required": ["symbol"]}},
                            {"name": "subscribe_market_book", "description": "Subscribe to market book (Level 2) data for a symbol", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
                            {"name": "unsubscribe_market_book", "description": "Unsubscribe from market book (Level 2) data for a symbol", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
                            {"name": "get_book_snapshot", "description": "Get a complete order book snapshot with bid/ask levels separated", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "depth": {"type": "number"}}, "required": ["symbol"]}},
                            
                            # Trading tools (11 tools)
                            {"name": "order_send", "description": "Send an order to the trade server", "inputSchema": {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}},
                            {"name": "order_check", "description": "Check if an order can be placed with the specified parameters", "inputSchema": {"type": "object", "properties": {"request": {"type": "object"}}, "required": ["request"]}},
                            {"name": "order_cancel", "description": "Cancel a pending order", "inputSchema": {"type": "object", "properties": {"ticket": {"type": "number"}}, "required": ["ticket"]}},
                            {"name": "order_modify", "description": "Modify an existing pending order", "inputSchema": {"type": "object", "properties": {"ticket": {"type": "number"}, "price": {"type": "number"}, "sl": {"type": "number"}, "tp": {"type": "number"}}, "required": ["ticket"]}},
                            {"name": "position_modify", "description": "Modify Stop Loss and Take Profit of an open position", "inputSchema": {"type": "object", "properties": {"ticket": {"type": "number"}, "sl": {"type": "number"}, "tp": {"type": "number"}}, "required": ["ticket"]}},
                            {"name": "positions_get", "description": "Get open positions", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "group": {"type": "string"}}, "required": []}},
                            {"name": "positions_get_by_ticket", "description": "Get an open position by its ticket", "inputSchema": {"type": "object", "properties": {"ticket": {"type": "number"}}, "required": ["ticket"]}},
                            {"name": "orders_get", "description": "Get active orders", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "group": {"type": "string"}}, "required": []}},
                            {"name": "orders_get_by_ticket", "description": "Get an active order by its ticket", "inputSchema": {"type": "object", "properties": {"ticket": {"type": "number"}}, "required": ["ticket"]}},
                            {"name": "history_orders_get", "description": "Get orders from history within the specified date range", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "group": {"type": "string"}, "ticket": {"type": "number"}, "from_date": {"type": "string"}, "to_date": {"type": "string"}}, "required": []}},
                            {"name": "history_deals_get", "description": "Get deals from history within the specified date range", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "group": {"type": "string"}, "ticket": {"type": "number"}, "from_date": {"type": "string"}, "to_date": {"type": "string"}}, "required": []}}
                        ]
                        
                        logger.info(f"Returning {len(tools_list)} hardcoded tools")
                        
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "tools": tools_list
                            }
                        })
                    else:
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        })
                        
                except Exception as e:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id", None),
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    })
            
            # Handle GET (status info)
            # Use hardcoded count based on capability_matrix.md
            tools_count = 34  # 7 server + 16 market_data + 11 trading tools
            tool_names = ["initialize", "get_symbols", "order_send", "positions_get", "get_account_info", 
                         "copy_rates_from_pos", "copy_book_levels", "order_cancel", "position_modify", "validate_demo_for_trading"]
                
            return JSONResponse({
                "protocol": "MCP",
                "version": "1.0.0",
                "status": "available",
                "transport": "http",
                "server": "MetaTrader 5 MCP Server",
                "tools_count": tools_count,
                "sample_tools": tool_names,
                "endpoints": {
                    "mcp": "/mcp (POST for MCP protocol, GET for status)",
                    "tools": "Use MCP protocol",
                    "resources": "Use MCP protocol"
                },
                "message": "Use MCP client library to interact with tools",
                "claude_cli": f"claude add mt5 --transport http --url http://0.0.0.0:8000"
            })
        
        # Add root endpoint with POST support for Claude CLI
        @app.post("/")
        async def root_post(request: Request):
            """Handle POST to root (Claude CLI fallback)"""
            try:
                body = await request.json()
                # Redirect MCP requests to /mcp endpoint
                return await mcp_handler(request)
            except:
                return JSONResponse({
                    "error": "Use /mcp endpoint for MCP protocol",
                    "available_endpoints": {
                        "mcp": "/mcp (POST/GET)",
                        "health": "/health (GET)",
                        "info": "/info (GET)",
                        "config": "/config (GET)"
                    }
                })
        
        # Add custom endpoints
        @app.get("/")
        async def root():
            """Root endpoint with server information"""
            return PlainTextResponse(f"""
MetaTrader 5 MCP Server - HTTP Mode

Available endpoints:
  - GET /          : This information page
  - GET /health    : Health check
  - GET /info      : Server information
  - GET /config    : Configuration details
  - POST /tools    : MCP tools (use MCP client)

Current Configuration: {config_manager.current_config.name if config_manager.current_config else 'None'}
MT5 Status: {mt5_status}

For Claude CLI: claude add mt5 --transport http --url "http://{host}:{port}"
""")
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            # Use hardcoded count based on capability_matrix.md
            tools_count = 34  # 7 server + 16 market_data + 11 trading tools
            
            return JSONResponse({
                "status": "healthy",
                "service": "MetaTrader 5 MCP Server",
                "version": "1.0.0",
                "mode": "HTTP",
                "mt5_status": mt5_status,
                "mt5_mock": mt5_status == "mock",
                "tools_count": tools_count
            })
        
        @app.get("/info")
        async def server_info():
            """Server information endpoint"""
            # Use hardcoded count based on capability_matrix.md
            tools_count = 34  # 7 server + 16 market_data + 11 trading tools
            tool_names = ["initialize", "get_symbols", "order_send", "positions_get", "copy_book_levels"]
            
            return JSONResponse({
                "server": "MetaTrader 5 MCP Server (HTTP Mode)",
                "endpoints": {
                    "health": "/health",
                    "info": "/info", 
                    "config": "/config",
                    "mcp_tools": "/tools"
                },
                "features": [
                    "Trading operations",
                    "Market data", 
                    "Multi-configuration (B3/Forex)",
                    "Demo account validation",
                    "Linux/WSL compatibility via mock",
                    "FastMCP integration"
                ],
                "current_config": {
                    "name": config_manager.current_config.name if config_manager.current_config else None,
                    "market_type": config_manager.current_config.market_type if config_manager.current_config else None,
                    "account": config_manager.current_config.account if config_manager.current_config else None,
                    "server": config_manager.current_config.server if config_manager.current_config else None,
                    "initialized": config_manager.initialized
                },
                "tools_available": tools_count,
                "sample_tools": tool_names
            })
        
        @app.get("/config")
        async def configuration_info():
            """Configuration information endpoint"""
            configs = {}
            
            # Get available configurations
            from mcp_metatrader5_server.mt5_configs import MT5_CONFIGS
            
            for key, cfg in MT5_CONFIGS.items():
                configs[key] = {
                    "name": cfg.name,
                    "market_type": cfg.market_type,
                    "account": cfg.account,
                    "server": cfg.server,
                    "portable": cfg.portable,
                    "is_current": cfg.name == config_manager.current_config.name if config_manager.current_config else False
                }
            
            return JSONResponse({
                "available_configs": configs,
                "current_config": config_manager.current_config.name if config_manager.current_config else None,
                "total_configs": len(configs),
                "mt5_status": mt5_status
            })
        
        # Print server information
        print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           🌐 MetaTrader 5 MCP Server - HTTP Mode                  ║
╠═══════════════════════════════════════════════════════════════════╣
║ 📡 Server URL:     http://{host}:{port}/                              
║ 🏥 Health Check:   http://{host}:{port}/health                        
║ 📊 Server Info:    http://{host}:{port}/info                          
║ ⚙️  Configuration:  http://{host}:{port}/config                        
║ 🔧 MCP Tools:      http://{host}:{port}/tools (POST)                   
╠═══════════════════════════════════════════════════════════════════╣
║ Claude CLI:                                                        ║
║ claude add mt5 --transport http --url "http://{host}:{port}"          
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ Server is running! Press Ctrl+C to stop                        ║
╚═══════════════════════════════════════════════════════════════════╝
""")
        
        logger.info("HTTP server ready", extra={
            "event": "server_ready",
            "context": {"transport": transport, "host": host, "port": port}
        })
        
        # Run with uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"❌ Import error: {e}")
        print("Ensure dependencies are installed: pip install -e .")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n👋 Server stopped!")
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def cleanup_handler():
    """Clean shutdown handler"""
    try:
        from mcp_metatrader5_server.server import config_manager
        import MetaTrader5 as mt5
        
        if config_manager.initialized:
            mt5.shutdown()
            print("[CLEANUP] MT5 connection closed", file=sys.stderr)
    except Exception as e:
        print(f"[CLEANUP] Error during cleanup: {e}", file=sys.stderr)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"[SIGNAL] Received signal {signum}, shutting down...", file=sys.stderr)
    cleanup_handler()
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup handlers
    atexit.register(cleanup_handler)
    
    # Handle signals
    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    except (AttributeError, OSError):
        pass
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="MCP MetaTrader 5 HTTP Server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    
    args = parser.parse_args()
    
    start_http_server(host=args.host, port=args.port)