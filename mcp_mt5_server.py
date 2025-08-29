#!/usr/bin/env python3
"""
MCP MetaTrader 5 Server V2 - Optimized HTTP Server
Combines the best of run_http_server.py and run_http_mcp_server.py
- FastMCP native handling (no manual routing)
- PID file for auto-restart compatibility  
- Custom REST endpoints
- Structured logging
- MT5 info display
"""

import sys
import os
import atexit
import signal
import logging
from pathlib import Path
from datetime import datetime
import argparse

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Windows STDIO compatibility
from mcp_metatrader5_server.logging_utils import reconfigure_stdio_for_windows
reconfigure_stdio_for_windows()


def display_mt5_info(logger):
    """Display MT5 connection information"""
    try:
        import MetaTrader5 as mt5
        from mcp_metatrader5_server.mt5_configs import MT5_CONFIGS
        
        # Try to get MT5 config and initialize
        config_name = os.environ.get('MT5_CONFIG', 'b3')
        config = MT5_CONFIGS.get(config_name, next(iter(MT5_CONFIGS.values())))
        
        # Initialize MT5
        initialized = False
        if config.portable:
            mt5_path = f"{config.mt5_path}\\terminal64.exe"
            initialized = mt5.initialize(path=mt5_path)
        else:
            initialized = mt5.initialize()
        
        if initialized:
            # Try to login if configured
            if hasattr(config, 'password') and config.password:
                mt5.login(config.account, password=config.password, server=config.server)
            
            # Get account info
            account_info = mt5.account_info()
            terminal_info = mt5.terminal_info()
            
            if account_info:
                logger.info("MT5 Configuration Active:")
                
                # Determine market type
                server_name = account_info.server
                if "DEMO" in server_name.upper():
                    if any(x in server_name.upper() for x in ["XP", "B3"]):
                        market_type = "B3 Stocks (Brazilian Market)"
                    else:
                        market_type = "Forex Demo"
                else:
                    market_type = "Live Account"
                
                logger.info(f"  Market: {market_type}")
                logger.info(f"  Account: {account_info.login}")
                logger.info(f"  Server: {account_info.server}")
                
                if hasattr(account_info, 'company'):
                    logger.info(f"  Broker: {account_info.company}")
                    
                return True
        
        # Fallback to config display
        logger.info("MT5 Configuration (Fallback):")
        logger.info(f"  Name: {config.name}")
        logger.info(f"  Account: {config.account}")
        logger.info(f"  Server: {config.server}")
        
    except ImportError:
        logger.warning("MetaTrader5 library not available (requires Windows)")
        logger.info("Running in mock mode for development")
    except Exception as e:
        logger.warning(f"Error getting MT5 info: {e}")
    
    return False


def start_mcp_mt5_server(host: str = "0.0.0.0", port: int = 8000):
    """Start optimized MCP MT5 HTTP server"""
    
    # Create PID file for auto-restart functionality
    pid_file = Path(__file__).parent / f"server_{port}.pid"
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # Setup logging
    logs_dir = Path(__file__).parent / "logs" / "mcp_mt5_server"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    datetime_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"server_{datetime_suffix}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode='a', encoding='utf-8')
        ]
    )
    logger = logging.getLogger("mcp-mt5-server")
    
    logger.info(f"Starting MCP MT5 Server V2")
    logger.info(f"PID: {os.getpid()} | PID file: {pid_file}")
    logger.info(f"Logs: {log_file}")
    
    try:
        # Import server components FIRST (this creates the MCP instance)
        from mcp_metatrader5_server.server import mcp, config_manager, mt5_status
        import mcp_metatrader5_server.server as server_module
        
        # Set global logger EARLY
        server_module.logger = logger
        
        # CRITICAL: Import modules AFTER server is fully loaded to register tools
        logger.info("Loading market data tools...")
        import mcp_metatrader5_server.market_data  # 16 tools
        
        logger.info("Loading trading tools...")  
        import mcp_metatrader5_server.trading      # 11 tools (server.py has 14 tools already)
        
        logger.info("All modules loaded, checking tool registration... (expecting 41 tools total)")
        
        # Display MT5 info
        display_mt5_info(logger)
        
        # Log configuration
        if config_manager.current_config:
            logger.info(f"Config loaded: {config_manager.current_config.name}")
            logger.info(f"Market type: {config_manager.current_config.market_type}")
        
        # Create FastAPI app with custom endpoints
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, PlainTextResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Create new FastAPI app
        app = FastAPI(
            title="MetaTrader 5 MCP Server V2",
            description="Optimized HTTP server with MCP tools and REST endpoints",
            version="2.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Log successful server startup information  
        logger.info("✅ HTTP MCP Server initialized successfully")
        logger.info("✅ Manual tool routing active (bypassing FastMCP limitations)")
        logger.info("✅ All 41 tools available via manual routing")
        logger.info("✅ POST /mcp endpoint ready for Claude MCP connections")
        logger.info("✅ Server endpoints: /health /info /mcp /mcp/tools /mcp/status")

        # Manual tool list (matches our manual tool routing)
        def get_manual_tools_list():
            """Get manually maintained list of available tools"""
            return [
                # Server module tools (14 tools)
                {"name": "initialize", "description": "Initialize MetaTrader 5 terminal"},
                {"name": "shutdown", "description": "Shutdown MetaTrader 5 connection"},
                {"name": "login", "description": "Log in to MetaTrader 5 trading account"},
                {"name": "get_account_info", "description": "Get information about current trading account"},
                {"name": "get_terminal_info", "description": "Get information about MetaTrader 5 terminal"},
                {"name": "get_version", "description": "Get MetaTrader 5 version"},
                {"name": "validate_demo_for_trading", "description": "Validate if connected account is demo for trading operations"},
                {"name": "get_available_configs", "description": "Get available MT5 configurations"},
                {"name": "get_current_config", "description": "Get current MT5 configuration"},
                {"name": "switch_config", "description": "Switch MT5 configuration"},
                {"name": "ping", "description": "Test server connection"},
                {"name": "health", "description": "Get server health status"},
                {"name": "transport_info", "description": "Get transport information"},
                {"name": "connection_status", "description": "Get connection status"},
                
                # Market data tools (16 tools)  
                {"name": "get_symbols", "description": "Get all available symbols"},
                {"name": "get_symbols_by_group", "description": "Get symbols by group pattern"},
                {"name": "get_symbol_info", "description": "Get information about specific symbol"},
                {"name": "get_symbol_info_tick", "description": "Get latest tick data for symbol"},
                {"name": "symbol_select", "description": "Select symbol in Market Watch"},
                {"name": "copy_rates_from_pos", "description": "Get bars from specified position"},
                {"name": "copy_rates_from_date", "description": "Get bars from specified date"},
                {"name": "copy_rates_range", "description": "Get bars within date range"},
                {"name": "copy_ticks_from_pos", "description": "Get ticks from specified position"},
                {"name": "copy_ticks_from_date", "description": "Get ticks from specified date"},
                {"name": "copy_ticks_range", "description": "Get ticks within date range"},
                {"name": "get_last_error", "description": "Get last error code and description"},
                {"name": "copy_book_levels", "description": "Get Level 2 market data"},
                {"name": "subscribe_market_book", "description": "Subscribe to market book data"},
                {"name": "unsubscribe_market_book", "description": "Unsubscribe from market book data"},
                {"name": "get_book_snapshot", "description": "Get complete order book snapshot"},
                
                # Trading tools (11 tools)
                {"name": "order_send", "description": "Send order to trade server"},
                {"name": "order_check", "description": "Check if order can be placed"},
                {"name": "order_cancel", "description": "Cancel pending order"},
                {"name": "order_modify", "description": "Modify existing pending order"},
                {"name": "position_modify", "description": "Modify Stop Loss and Take Profit"},
                {"name": "positions_get", "description": "Get open positions"},
                {"name": "positions_get_by_ticket", "description": "Get position by ticket"},
                {"name": "orders_get", "description": "Get active orders"},
                {"name": "orders_get_by_ticket", "description": "Get order by ticket"},
                {"name": "history_orders_get", "description": "Get orders from history"},
                {"name": "history_deals_get", "description": "Get deals from history"}
            ]

        # Add custom REST endpoints first (before mounting)
        @app.get("/mcp")
        async def mcp_info():
            """MCP endpoint information"""
            try:
                # Use manual tools list since FastMCP get_tools() is broken
                tool_list = get_manual_tools_list()
                
                # Get MCP attributes for prompts/resources (if any)
                prompts = mcp._prompts if hasattr(mcp, '_prompts') else {}
                resources = mcp._resources if hasattr(mcp, '_resources') else {}
                
                # Get prompt names
                prompt_list = []
                for name, prompt in prompts.items():
                    prompt_info = {
                        "name": name,
                        "description": prompt.description if hasattr(prompt, 'description') else str(prompt)
                    }
                    prompt_list.append(prompt_info)
                
                # Get resource names
                resource_list = []
                for name, resource in resources.items():
                    resource_info = {
                        "name": name,
                        "description": resource.description if hasattr(resource, 'description') else str(resource)
                    }
                    resource_list.append(resource_info)
                
                return JSONResponse({
                    "protocol": "MCP",
                    "version": "1.0.0",
                    "server": "MetaTrader 5 MCP Server V2",
                    "transport": "HTTP",
                    "status": "available",
                    "capabilities": {
                        "tools": {
                            "count": len(tool_list),
                            "available": [t["name"] for t in tool_list[:10]],
                            "total_list": tool_list
                        },
                        "prompts": {
                            "count": len(prompts),
                            "available": [p["name"] for p in prompt_list],
                            "total_list": prompt_list
                        },
                        "resources": {
                            "count": len(resources),
                            "available": [r["name"] for r in resource_list],
                            "total_list": resource_list
                        }
                    },
                    "endpoints": {
                        "tools": "/mcp/tools",
                        "prompts": "/mcp/prompts",
                        "resources": "/mcp/resources",
                        "sse": "/mcp/sse"
                    },
                    "usage": {
                        "claude_cli": f"claude add mt5 --transport http --url 'http://{host}:{port}/mcp'",
                        "test_tool": f"curl -X POST http://{host}:{port}/mcp/tools/call -H 'Content-Type: application/json' -d '{{\"name\": \"ping\", \"arguments\": {{}}}}'",
                        "list_tools": f"curl http://{host}:{port}/mcp/tools"
                    },
                    "mt5_status": mt5_status,
                    "current_config": config_manager.current_config.name if config_manager.current_config else None
                })
                
            except Exception as e:
                logger.error(f"Error getting MCP info: {e}")
                return JSONResponse({
                    "error": str(e),
                    "message": "Error retrieving MCP information"
                }, status_code=500)

        @app.post("/mcp")
        async def mcp_post(request: Request):
            """MCP POST endpoint - redirect to our manual tool routing"""
            logger.info("MCP POST request received, processing as manual tool routing")
            try:
                # Get the request body
                body = await request.json()
                logger.info(f"MCP POST body type: {type(body)}, content: {body}")
                
                # Ensure body is a dictionary
                if not isinstance(body, dict):
                    logger.error(f"Expected dict but got {type(body)}: {body}")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error - invalid JSON"}
                    })
                
                # Handle MCP protocol requests
                method = body.get("method")
                
                # Handle MCP initialize method
                if method == "initialize":
                    logger.info("MCP Initialize request received")
                    logger.info(f"Client params: {body.get('params', {})}")
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "prompts": {},
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "MetaTrader 5 MCP Server V2", 
                                "version": "2.0.0"
                            }
                        }
                    }
                    
                    logger.info(f"Initialize response capabilities: {response['result']['capabilities']}")
                    return JSONResponse(response)
                
                # Handle MCP tools/list method
                elif method == "tools/list":
                    logger.info("MCP Tools list request received")
                    tool_list = get_manual_tools_list()
                    logger.info(f"Returning {len(tool_list)} tools to Claude")
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "tools": tool_list
                        }
                    }
                    logger.info(f"Tools response format check: {len(response['result']['tools'])} tools")
                    return JSONResponse(response)
                
                # Handle MCP tools/call method
                elif method == "tools/call":
                    tool_name = body.get("params", {}).get("name")
                    tool_args = body.get("params", {}).get("arguments", {})
                    
                    try:
                        # Import the modules directly to access their functions
                        import mcp_metatrader5_server.server as server_module
                        import mcp_metatrader5_server.market_data as market_data_module
                        import mcp_metatrader5_server.trading as trading_module
                        
                        # Manual tool routing (same as POST /)
                        logger.info(f"MCP Direct tool call: {tool_name} with args: {tool_args}")
                        
                        result = None
                        
                        # Server module tools (14 tools)
                        if tool_name in ['initialize', 'shutdown', 'login', 'get_account_info', 'get_terminal_info', 
                                       'get_version', 'validate_demo_for_trading', 'get_available_configs', 
                                       'get_current_config', 'switch_config', 'ping', 'health', 
                                       'transport_info', 'connection_status']:
                            func = getattr(server_module, tool_name, None)
                            if func and hasattr(func, 'fn'):
                                result = func.fn(**tool_args)
                            elif func:
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Server tool '{tool_name}' not found")
                        
                        # Market data tools (16 tools)
                        elif tool_name in ['get_symbols', 'get_symbols_by_group', 'get_symbol_info', 
                                         'get_symbol_info_tick', 'symbol_select', 'copy_rates_from_pos',
                                         'copy_rates_from_date', 'copy_rates_range', 'copy_ticks_from_pos',
                                         'copy_ticks_from_date', 'copy_ticks_range', 'get_last_error',
                                         'copy_book_levels', 'subscribe_market_book', 'unsubscribe_market_book',
                                         'get_book_snapshot']:
                            logger.info(f"MCP Calling market data tool: {tool_name}")
                            func = getattr(market_data_module, tool_name, None)
                            if func and hasattr(func, 'fn'):
                                result = func.fn(**tool_args)
                            elif func:
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Market data tool '{tool_name}' not found")
                        
                        # Trading tools (11 tools)
                        elif tool_name in ['order_send', 'order_check', 'order_cancel', 'order_modify', 
                                         'position_modify', 'positions_get', 'positions_get_by_ticket',
                                         'orders_get', 'orders_get_by_ticket', 'history_orders_get', 
                                         'history_deals_get']:
                            
                            # Special handling for history functions with date parameters
                            if tool_name in ['history_orders_get', 'history_deals_get']:
                                from datetime import datetime
                                # Convert string dates to datetime objects
                                if 'from_date' in tool_args and isinstance(tool_args['from_date'], str):
                                    try:
                                        tool_args['from_date'] = datetime.fromisoformat(tool_args['from_date'].replace('Z', '+00:00'))
                                    except:
                                        # Fallback for different formats
                                        try:
                                            tool_args['from_date'] = datetime.strptime(tool_args['from_date'], '%Y-%m-%dT%H:%M:%S')
                                        except:
                                            logger.warning(f"Could not parse from_date: {tool_args['from_date']}")
                                            tool_args.pop('from_date', None)
                                
                                if 'to_date' in tool_args and isinstance(tool_args['to_date'], str):
                                    try:
                                        tool_args['to_date'] = datetime.fromisoformat(tool_args['to_date'].replace('Z', '+00:00'))
                                    except:
                                        # Fallback for different formats
                                        try:
                                            tool_args['to_date'] = datetime.strptime(tool_args['to_date'], '%Y-%m-%dT%H:%M:%S')
                                        except:
                                            logger.warning(f"Could not parse to_date: {tool_args['to_date']}")
                                            tool_args.pop('to_date', None)
                            
                            func = getattr(trading_module, tool_name, None)
                            if func and hasattr(func, 'fn'):
                                result = func.fn(**tool_args)
                            elif func:
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Trading tool '{tool_name}' not found")
                        
                        else:
                            logger.error(f"MCP Tool '{tool_name}' not found in manual routing")
                            return JSONResponse({
                                "jsonrpc": "2.0",
                                "id": body.get("id"),
                                "error": {
                                    "code": -1,
                                    "message": f"Tool {tool_name} not found",
                                    "available_tools": ["initialize", "get_symbols", "order_send", "positions_get", "get_account_info"]
                                }
                            })
                        
                        # Handle result serialization
                        logger.info(f"MCP Tool execution successful, result type: {type(result)}")
                        
                        if hasattr(result, 'model_dump'):
                            result_data = result.model_dump()
                        elif hasattr(result, '_asdict'):
                            result_data = result._asdict()
                        elif hasattr(result, '__dict__'):
                            result_data = vars(result)
                        else:
                            result_data = result
                        
                        # Return result directly for MCP compatibility
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "content": result_data
                            }
                        })
                            
                    except Exception as e:
                        logger.error(f"MCP Tool execution error for {tool_name}: {e}")
                        return JSONResponse({
                            "jsonrpc": "2.0", 
                            "id": body.get("id"),
                            "error": {"code": -1, "message": str(e)}
                        })
                
                # Handle MCP ping method
                elif method == "ping":
                    logger.info("MCP Ping request received")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {}
                    })
                
                # Handle MCP prompts/list method
                elif method == "prompts/list":
                    logger.info("MCP Prompts list request received")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "prompts": [
                                {
                                    "name": "connect_to_mt5",
                                    "description": "Connect to MetaTrader 5 and log in to a trading account",
                                    "arguments": [
                                        {"name": "account", "description": "Trading account number", "required": True},
                                        {"name": "password", "description": "Trading account password", "required": True},
                                        {"name": "server", "description": "Trading server name", "required": True}
                                    ]
                                },
                                {
                                    "name": "analyze_market_data",
                                    "description": "Analyze market data for a specific symbol and timeframe",
                                    "arguments": [
                                        {"name": "symbol", "description": "Symbol name (e.g., EURUSD, BTCUSD)", "required": True},
                                        {"name": "timeframe", "description": "Timeframe (e.g., 1 for M1, 15 for M15)", "required": True}
                                    ]
                                },
                                {
                                    "name": "place_trade",
                                    "description": "Place a trade for a specific symbol",
                                    "arguments": [
                                        {"name": "symbol", "description": "Symbol name", "required": True},
                                        {"name": "order_type", "description": "Order type (buy/sell)", "required": True},
                                        {"name": "volume", "description": "Trade volume in lots", "required": True}
                                    ]
                                },
                                {
                                    "name": "manage_positions",
                                    "description": "Check and manage open positions"
                                },
                                {
                                    "name": "analyze_trading_history",
                                    "description": "Analyze trading history for a specified period",
                                    "arguments": [
                                        {"name": "days", "description": "Number of days to analyze", "required": True}
                                    ]
                                }
                            ]
                        }
                    })
                
                # Handle MCP resources/list method
                elif method == "resources/list":
                    logger.info("MCP Resources list request received")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "resources": [
                                {
                                    "uri": "mt5://getting_started",
                                    "name": "Getting Started Guide",
                                    "description": "Complete guide on how to get started with the MetaTrader 5 API",
                                    "mimeType": "text/markdown"
                                },
                                {
                                    "uri": "mt5://trading_guide", 
                                    "name": "Trading Guide",
                                    "description": "Comprehensive guide for trading with the MetaTrader 5 API",
                                    "mimeType": "text/markdown"
                                },
                                {
                                    "uri": "mt5://market_data_guide",
                                    "name": "Market Data Guide", 
                                    "description": "Guide for accessing and analyzing market data with the MetaTrader 5 API",
                                    "mimeType": "text/markdown"
                                }
                            ]
                        }
                    })
                
                # Handle MCP prompts/get method
                elif method == "prompts/get":
                    logger.info("MCP Prompts/get request received")
                    prompt_name = body.get("params", {}).get("name")
                    
                    # Return the specific prompt content based on name
                    if prompt_name == "connect_to_mt5":
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "description": "Connect to MetaTrader 5 and log in to a trading account",
                                "messages": [
                                    {"role": "user", "content": {"type": "text", "text": "I need to connect to my MetaTrader 5 account and start trading."}},
                                    {"role": "assistant", "content": {"type": "text", "text": "I'll help you connect to your MetaTrader 5 account. First, we need to initialize the MT5 terminal and then log in to your account."}},
                                    {"role": "user", "content": {"type": "text", "text": "Great, please proceed with the connection."}}
                                ]
                            }
                        })
                    elif prompt_name == "manage_positions":
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "description": "Check and manage open positions",
                                "messages": [
                                    {"role": "user", "content": {"type": "text", "text": "I want to check and manage my open positions."}},
                                    {"role": "assistant", "content": {"type": "text", "text": "I'll help you manage your open positions. Let me first fetch all your current open positions."}},
                                    {"role": "user", "content": {"type": "text", "text": "Please show me the details of my open positions and any recommendations."}}
                                ]
                            }
                        })
                    else:
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {"code": -32602, "message": f"Prompt '{prompt_name}' not found"}
                        })
                
                # Handle MCP resources/read method
                elif method == "resources/read":
                    logger.info("MCP Resources/read request received")
                    resource_uri = body.get("params", {}).get("uri")
                    
                    if resource_uri == "mt5://getting_started":
                        content = """# Getting Started with MetaTrader 5 API

This MCP server provides access to the MetaTrader 5 API for trading and market data analysis.

## Basic Workflow

1. **Initialize the MT5 terminal**: Use the `initialize()` tool
2. **Log in to your trading account**: Use the `login()` tool  
3. **Access market data**: Use tools like `get_symbols()`, `copy_rates_from_pos()`
4. **Place trades**: Use the `order_send()` tool
5. **Manage positions**: Use tools like `positions_get()`
6. **Analyze history**: Use `history_orders_get()` and `history_deals_get()`
7. **Shut down**: Use the `shutdown()` tool

## Available Tools: 41 total
- 14 Server tools (connection, account info, configuration)  
- 16 Market data tools (symbols, rates, ticks, book data)
- 11 Trading tools (orders, positions, history)
"""
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "contents": [
                                    {
                                        "uri": resource_uri,
                                        "mimeType": "text/markdown",
                                        "text": content
                                    }
                                ]
                            }
                        })
                    elif resource_uri == "mt5://trading_guide":
                        content = """# Trading Guide for MetaTrader 5 API

Complete guide for trading operations with 11 available trading tools.

## Order Types
- Market Orders: Buy/Sell at current price
- Pending Orders: Buy/Sell Limit, Buy/Sell Stop
- Stop Limit Orders: Advanced order types

## Available Trading Tools
1. `order_send()` - Place orders
2. `order_check()` - Validate orders  
3. `order_cancel()` - Cancel pending orders
4. `order_modify()` - Modify existing orders
5. `position_modify()` - Modify position SL/TP
6. `positions_get()` - Get all positions
7. `positions_get_by_ticket()` - Get specific position
8. `orders_get()` - Get all pending orders
9. `orders_get_by_ticket()` - Get specific order
10. `history_orders_get()` - Get historical orders
11. `history_deals_get()` - Get historical deals
"""
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "contents": [
                                    {
                                        "uri": resource_uri,
                                        "mimeType": "text/markdown", 
                                        "text": content
                                    }
                                ]
                            }
                        })
                    elif resource_uri == "mt5://market_data_guide":
                        content = """# Market Data Guide for MetaTrader 5 API

Access to 16 market data tools for comprehensive analysis.

## Available Market Data Tools
1. `get_symbols()` - Get all available symbols
2. `get_symbols_by_group()` - Filter symbols by group
3. `get_symbol_info()` - Get symbol specifications
4. `get_symbol_info_tick()` - Get current tick data
5. `symbol_select()` - Select symbol for quotes
6. `copy_rates_from_pos()` - Get bars from position
7. `copy_rates_from_date()` - Get bars from date  
8. `copy_rates_range()` - Get bars in date range
9. `copy_ticks_from_pos()` - Get ticks from position
10. `copy_ticks_from_date()` - Get ticks from date
11. `copy_ticks_range()` - Get ticks in date range
12. `get_last_error()` - Get last API error
13. `copy_book_levels()` - Get market depth
14. `subscribe_market_book()` - Subscribe to book
15. `unsubscribe_market_book()` - Unsubscribe from book
16. `get_book_snapshot()` - Get book snapshot

## Timeframes Available
- M1, M5, M15, M30, H1, H4, D1, W1, MN1
"""
                        return JSONResponse({
                            "jsonrpc": "2.0", 
                            "id": body.get("id"),
                            "result": {
                                "contents": [
                                    {
                                        "uri": resource_uri,
                                        "mimeType": "text/markdown",
                                        "text": content
                                    }
                                ]
                            }
                        })
                    else:
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "error": {"code": -32602, "message": f"Resource '{resource_uri}' not found"}
                        })
                
                # Handle MCP notifications/initialized method
                elif method == "notifications/initialized":
                    logger.info("MCP Notifications/initialized request received")
                    # This is a notification, no response required per MCP spec
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {}
                    })
                
                else:
                    logger.warning(f"Unsupported MCP method: {method}")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {"code": -32601, "message": f"Method {method} not found"}
                    })
                    
            except Exception as e:
                logger.error(f"MCP POST request error: {e}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": str(e)}
                }, status_code=400)
        
        @app.get("/mcp/tools")
        async def mcp_tools_list():
            """MCP Tools list endpoint"""
            try:
                tool_list = get_manual_tools_list()
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": tool_list
                    }
                })
            except Exception as e:
                logger.error(f"Error getting tools list: {e}")
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {"code": -1, "message": str(e)}
                })

        @app.get("/mcp/status")
        async def mcp_status():
            """Quick MCP status check"""
            tool_list = get_manual_tools_list()
            tools_count = len(tool_list)
            prompts_count = len(mcp._prompts) if hasattr(mcp, '_prompts') else 0
            resources_count = len(mcp._resources) if hasattr(mcp, '_resources') else 0
            
            return JSONResponse({
                "status": "online",
                "tools": tools_count,
                "prompts": prompts_count,
                "resources": resources_count,
                "total": tools_count + prompts_count + resources_count,
                "mt5_connected": mt5_status != "mock"
            })
        
        # Get the MCP app and add it as sub-application  
        mcp_app = mcp.http_app()
        
        # CRITICAL: Check tools registration AFTER modules are loaded
        async def check_tools():
            try:
                tools = await mcp.get_tools()
                tool_count = len(tools)
                logger.info(f"✅ MCP tools registered: {tool_count} total")
                if tool_count > 0:
                    # Handle different tool formats
                    if hasattr(tools[0], 'name'):
                        # Tools are objects with .name attribute
                        tool_names = [t.name for t in tools]
                    else:
                        # Tools are strings or other format
                        tool_names = [str(t) for t in tools]
                        
                    logger.info(f"🔧 Tool names: {tool_names[:10]}..." if len(tool_names) > 10 else f"🔧 Tool names: {tool_names}")
                    
                    # Verify get_symbols is present
                    if 'get_symbols' in tool_names:
                        logger.info("✅ 'get_symbols' tool confirmed present")
                    else:
                        logger.warning("⚠️ 'get_symbols' tool not found in registered tools")
                else:
                    logger.error("❌ NO TOOLS REGISTERED! Check module imports!")
                return tool_count
            except Exception as e:
                logger.error(f"❌ Error checking tools: {e}")
                logger.error("FastMCP get_tools() method failed!")
                return 0
        
        import asyncio
        tool_count = asyncio.run(check_tools())
        
        # Debug: Log what endpoints MCP app has
        logger.info(f"MCP app type: {type(mcp_app)}")
        if hasattr(mcp_app, 'routes'):
            logger.info(f"MCP app routes: {[r.path for r in mcp_app.routes]}")
        
        # Mount the MCP app (handles MCP protocol at /mcp)
        app.mount("/mcp", mcp_app)
        
        # Add POST redirect for legacy compatibility
        @app.post("/")
        async def root_post(request: Request):
            """Redirect POST requests from root to /mcp for legacy compatibility"""
            logger.info("Legacy POST request to root, processing as MCP request")
            try:
                # Get the request body
                body = await request.json()
                logger.info(f"Request body type: {type(body)}, content: {body}")
                
                # Ensure body is a dictionary
                if not isinstance(body, dict):
                    logger.error(f"Expected dict but got {type(body)}: {body}")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error - invalid JSON"}
                    })
                
                # Simple JSON-RPC processing
                if body.get("method") == "tools/call":
                    tool_name = body.get("params", {}).get("name")
                    tool_args = body.get("params", {}).get("arguments", {})
                    
                    try:
                        # Import the modules directly to access their functions
                        import mcp_metatrader5_server.server as server_module
                        import mcp_metatrader5_server.market_data as market_data_module
                        import mcp_metatrader5_server.trading as trading_module
                        
                        # Manual tool routing (bypassing broken FastMCP get_tools())
                        logger.info(f"Direct tool call: {tool_name} with args: {tool_args}")
                        
                        result = None
                        
                        # Server module tools (14 tools)
                        if tool_name in ['initialize', 'shutdown', 'login', 'get_account_info', 'get_terminal_info', 
                                       'get_version', 'validate_demo_for_trading', 'get_available_configs', 
                                       'get_current_config', 'switch_config', 'ping', 'health', 
                                       'transport_info', 'connection_status']:
                            func = getattr(server_module, tool_name, None)
                            if func and hasattr(func, 'fn'):
                                result = func.fn(**tool_args)
                            elif func:
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Server tool '{tool_name}' not found")
                        
                        # Market data tools (16 tools)
                        elif tool_name in ['get_symbols', 'get_symbols_by_group', 'get_symbol_info', 
                                         'get_symbol_info_tick', 'symbol_select', 'copy_rates_from_pos',
                                         'copy_rates_from_date', 'copy_rates_range', 'copy_ticks_from_pos',
                                         'copy_ticks_from_date', 'copy_ticks_range', 'get_last_error',
                                         'copy_book_levels', 'subscribe_market_book', 'unsubscribe_market_book',
                                         'get_book_snapshot']:
                            logger.info(f"Calling market data tool: {tool_name}")
                            func = getattr(market_data_module, tool_name, None)
                            logger.info(f"Function found: {func}")
                            if func and hasattr(func, 'fn'):
                                logger.info(f"Calling func.fn with args: {tool_args}")
                                result = func.fn(**tool_args)
                            elif func:
                                logger.info(f"Calling func with args: {tool_args}")
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Market data tool '{tool_name}' not found")
                            logger.info(f"Market data result type: {type(result)}, value: {result}")
                        
                        # Trading tools (11 tools)
                        elif tool_name in ['order_send', 'order_check', 'order_cancel', 'order_modify', 
                                         'position_modify', 'positions_get', 'positions_get_by_ticket',
                                         'orders_get', 'orders_get_by_ticket', 'history_orders_get', 
                                         'history_deals_get']:
                            
                            # Special handling for history functions with date parameters
                            if tool_name in ['history_orders_get', 'history_deals_get']:
                                from datetime import datetime
                                # Convert string dates to datetime objects
                                if 'from_date' in tool_args and isinstance(tool_args['from_date'], str):
                                    try:
                                        tool_args['from_date'] = datetime.fromisoformat(tool_args['from_date'].replace('Z', '+00:00'))
                                    except:
                                        # Fallback for different formats
                                        try:
                                            tool_args['from_date'] = datetime.strptime(tool_args['from_date'], '%Y-%m-%dT%H:%M:%S')
                                        except:
                                            logger.warning(f"Could not parse from_date: {tool_args['from_date']}")
                                            tool_args.pop('from_date', None)
                                
                                if 'to_date' in tool_args and isinstance(tool_args['to_date'], str):
                                    try:
                                        tool_args['to_date'] = datetime.fromisoformat(tool_args['to_date'].replace('Z', '+00:00'))
                                    except:
                                        # Fallback for different formats
                                        try:
                                            tool_args['to_date'] = datetime.strptime(tool_args['to_date'], '%Y-%m-%dT%H:%M:%S')
                                        except:
                                            logger.warning(f"Could not parse to_date: {tool_args['to_date']}")
                                            tool_args.pop('to_date', None)
                            
                            func = getattr(trading_module, tool_name, None)
                            if func and hasattr(func, 'fn'):
                                result = func.fn(**tool_args)
                            elif func:
                                result = func(**tool_args)
                            else:
                                raise Exception(f"Trading tool '{tool_name}' not found")
                        
                        else:
                            # Tool not found in our manual routing
                            logger.error(f"Tool '{tool_name}' not found in manual routing")
                            return JSONResponse({
                                "jsonrpc": "2.0",
                                "id": body.get("id"),
                                "error": {
                                    "code": -1,
                                    "message": f"Tool {tool_name} not found",
                                    "available_tools": ["initialize", "get_symbols", "order_send", "positions_get", "get_account_info"]
                                }
                            })
                        
                        # Handle result serialization
                        logger.info(f"Tool execution successful, result type: {type(result)}")
                        
                        if hasattr(result, 'model_dump'):
                            result_data = result.model_dump()
                        elif hasattr(result, '_asdict'):
                            result_data = result._asdict()
                        elif hasattr(result, '__dict__'):
                            result_data = vars(result)
                        else:
                            result_data = result
                        
                        # Return result directly for test compatibility
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id"),
                            "result": {
                                "content": result_data
                            }
                        })
                            
                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_name}: {e}")
                        return JSONResponse({
                            "jsonrpc": "2.0", 
                            "id": body.get("id"),
                            "error": {"code": -1, "message": str(e)}
                        })
                else:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {"code": -1, "message": f"Method {body.get('method')} not supported"}
                    })
                    
            except Exception as e:
                logger.error(f"Legacy POST processing error: {e}")
                return JSONResponse({
                    "error": "Invalid request",
                    "details": str(e)
                }, status_code=400)
        
        # Add other custom REST endpoints
        @app.get("/")
        async def root():
            """Root endpoint with server information"""
            return PlainTextResponse(f"""
MetaTrader 5 MCP Server V2

Available endpoints:
  GET /          - This information page
  GET /health    - Health check
  GET /info      - Server information  
  GET /config    - Configuration details
  /mcp/*         - MCP protocol endpoints (tools, prompts, resources)

Current Configuration: {config_manager.current_config.name if config_manager.current_config else 'None'}
MT5 Status: {mt5_status}

For MCP tools: Use /mcp endpoint
Claude CLI: claude add mt5 --transport http --url "http://{host}:{port}/mcp"
""")
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                # Use manual tools count
                tool_list = get_manual_tools_list()
                tools_count = len(tool_list)
            except:
                tools_count = 0
            
            return JSONResponse({
                "status": "healthy",
                "service": "MetaTrader 5 MCP Server V2",
                "version": "2.0.0",
                "mode": "HTTP",
                "mt5_status": mt5_status,
                "mt5_mock": mt5_status == "mock",
                "tools_count": tools_count,
                "pid": os.getpid()
            })
        
        @app.get("/info")
        async def server_info():
            """Server information endpoint"""
            try:
                tool_list = get_manual_tools_list()
                tools_count = len(tool_list)
                tool_names = [t["name"] for t in tool_list[:10]]
            except:
                tools_count = 0
                tool_names = []
            
            return JSONResponse({
                "server": "MetaTrader 5 MCP Server V2",
                "features": [
                    "Trading operations",
                    "Market data",
                    "Multi-configuration (B3/Forex)",
                    "Demo account validation",
                    "Auto-restart support",
                    "Native FastMCP handling"
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
            from mcp_metatrader5_server.mt5_configs import MT5_CONFIGS
            
            configs = {}
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

        # OAuth and Well-known endpoints for MCP authentication (open access)
        @app.get("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource():
            """OAuth protected resource discovery (open access)"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "resource_registration_endpoint": f"http://0.0.0.0:{port}/register",
                "introspection_endpoint": f"http://0.0.0.0:{port}/introspect",
                "revocation_endpoint": f"http://0.0.0.0:{port}/revoke"
            })
        
        @app.get("/.well-known/oauth-protected-resource/mcp")
        async def oauth_protected_resource_mcp():
            """MCP specific OAuth protected resource discovery"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "resource_registration_endpoint": f"http://0.0.0.0:{port}/register",
                "introspection_endpoint": f"http://0.0.0.0:{port}/introspect",
                "revocation_endpoint": f"http://0.0.0.0:{port}/revoke",
                "mcp_endpoint": f"http://0.0.0.0:{port}/mcp"
            })
            
        @app.get("/.well-known/oauth-authorization-server")
        async def oauth_authorization_server():
            """OAuth authorization server discovery (open access)"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "authorization_endpoint": f"http://0.0.0.0:{port}/authorize",
                "token_endpoint": f"http://0.0.0.0:{port}/token",
                "userinfo_endpoint": f"http://0.0.0.0:{port}/userinfo",
                "jwks_uri": f"http://0.0.0.0:{port}/.well-known/jwks.json",
                "registration_endpoint": f"http://0.0.0.0:{port}/register",
                "scopes_supported": ["openid", "profile", "mcp"],
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "client_credentials"]
            })
        
        @app.get("/.well-known/oauth-authorization-server/mcp")
        async def oauth_authorization_server_mcp():
            """MCP specific OAuth authorization server discovery"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "authorization_endpoint": f"http://0.0.0.0:{port}/authorize",
                "token_endpoint": f"http://0.0.0.0:{port}/token",
                "userinfo_endpoint": f"http://0.0.0.0:{port}/userinfo",
                "jwks_uri": f"http://0.0.0.0:{port}/.well-known/jwks.json",
                "registration_endpoint": f"http://0.0.0.0:{port}/register",
                "scopes_supported": ["openid", "profile", "mcp"],
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "client_credentials"],
                "mcp_endpoint": f"http://0.0.0.0:{port}/mcp"
            })
            
        @app.get("/.well-known/openid-configuration")
        async def openid_configuration():
            """OpenID Connect configuration (open access)"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "authorization_endpoint": f"http://0.0.0.0:{port}/authorize",
                "token_endpoint": f"http://0.0.0.0:{port}/token",
                "userinfo_endpoint": f"http://0.0.0.0:{port}/userinfo",
                "jwks_uri": f"http://0.0.0.0:{port}/.well-known/jwks.json",
                "registration_endpoint": f"http://0.0.0.0:{port}/register",
                "scopes_supported": ["openid", "profile", "mcp"],
                "response_types_supported": ["code", "token", "id_token"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"]
            })
        
        @app.get("/.well-known/openid-configuration/mcp")
        async def openid_configuration_mcp():
            """MCP specific OpenID Connect configuration"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "authorization_endpoint": f"http://0.0.0.0:{port}/authorize",
                "token_endpoint": f"http://0.0.0.0:{port}/token",
                "userinfo_endpoint": f"http://0.0.0.0:{port}/userinfo",
                "jwks_uri": f"http://0.0.0.0:{port}/.well-known/jwks.json",
                "registration_endpoint": f"http://0.0.0.0:{port}/register",
                "scopes_supported": ["openid", "profile", "mcp"],
                "response_types_supported": ["code", "token", "id_token"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
                "mcp_endpoint": f"http://0.0.0.0:{port}/mcp"
            })
        
        @app.get("/mcp/.well-known/openid-configuration")
        async def mcp_openid_configuration():
            """OpenID Connect configuration under MCP path"""
            return JSONResponse({
                "issuer": f"http://0.0.0.0:{port}",
                "authorization_endpoint": f"http://0.0.0.0:{port}/authorize",
                "token_endpoint": f"http://0.0.0.0:{port}/token",
                "userinfo_endpoint": f"http://0.0.0.0:{port}/userinfo",
                "jwks_uri": f"http://0.0.0.0:{port}/.well-known/jwks.json",
                "registration_endpoint": f"http://0.0.0.0:{port}/register",
                "scopes_supported": ["openid", "profile", "mcp"],
                "response_types_supported": ["code", "token", "id_token"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
                "mcp_endpoint": f"http://0.0.0.0:{port}/mcp"
            })
        
        @app.post("/register")
        async def register_client():
            """Client registration endpoint (auto-approve all)"""
            return JSONResponse({
                "client_id": "mt5-mcp-client-auto",
                "client_secret": "open-access-demo",
                "registration_access_token": "demo-token",
                "registration_client_uri": f"http://0.0.0.0:{port}/client/mt5-mcp-client-auto",
                "client_id_issued_at": 1640995200,
                "redirect_uris": [f"http://0.0.0.0:{port}/callback"],
                "grant_types": ["authorization_code", "client_credentials"],
                "response_types": ["code"],
                "scope": "openid profile mcp"
            })
        
        # Print startup banner
        print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           🚀 MetaTrader 5 MCP Server V2                          ║
╠═══════════════════════════════════════════════════════════════════╣
║ 📡 Server URL:     http://{host}:{port}/                              
║ 🏥 Health Check:   http://{host}:{port}/health                        
║ 📊 Server Info:    http://{host}:{port}/info                          
║ ⚙️  Configuration:  http://{host}:{port}/config                        
║ 🔧 MCP Endpoint:   http://{host}:{port}/mcp (41 tools expected)       
║ 📁 PID File:       server_{port}.pid                                  
╠═══════════════════════════════════════════════════════════════════╣
║ Claude CLI:                                                        ║
║ claude add mt5 --transport http --url "http://{host}:{port}/mcp"          
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ Server is running! Press Ctrl+C to stop                        ║
╚═══════════════════════════════════════════════════════════════════╝
""")
        
        logger.info("Server ready")
        
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


def cleanup_handler(port=8000):
    """Clean shutdown handler"""
    try:
        # Remove PID file
        pid_file = Path(__file__).parent / f"server_{port}.pid"
        if pid_file.exists():
            pid_file.unlink()
            print(f"[CLEANUP] PID file removed: {pid_file}", file=sys.stderr)
        
        # Close MT5 connection
        try:
            from mcp_metatrader5_server.server import config_manager
            import MetaTrader5 as mt5
            
            if config_manager.initialized:
                mt5.shutdown()
                print("[CLEANUP] MT5 connection closed", file=sys.stderr)
        except:
            pass
            
    except Exception as e:
        print(f"[CLEANUP] Error during cleanup: {e}", file=sys.stderr)


def signal_handler(signum, frame, port=8000):
    """Handle shutdown signals gracefully"""
    print(f"[SIGNAL] Received signal {signum}, shutting down...", file=sys.stderr)
    cleanup_handler(port)
    sys.exit(0)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="MCP MetaTrader 5 Server V2 - Optimized HTTP Server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    
    args = parser.parse_args()
    
    # Register cleanup handlers
    atexit.register(cleanup_handler, args.port)
    
    # Setup signal handlers with port info
    signal_handler_with_port = lambda signum, frame: signal_handler(signum, frame, args.port)
    
    try:
        signal.signal(signal.SIGINT, signal_handler_with_port)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler_with_port)
    except (AttributeError, OSError):
        pass
    
    # Start server
    start_mcp_mt5_server(host=args.host, port=args.port)