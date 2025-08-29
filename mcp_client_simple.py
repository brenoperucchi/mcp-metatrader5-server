#!/usr/bin/env python3
"""
MCP MetaTrader 5 Client - Robust STDIO Client with Retry Logic
Provides reliable connection to MCP server with Windows compatibility
"""

import asyncio
import sys
import json
import os
import time
import argparse
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Setup Windows STDIO compatibility early
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import logging utilities
from mcp_metatrader5_server.logging_utils import setup_logging, reconfigure_stdio_for_windows, LoggingScope

# Reconfigure STDIO for Windows
reconfigure_stdio_for_windows()

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"[ERROR] Failed to import MCP: {e}", file=sys.stderr)
    print("[ERROR] Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

class ConnectionTelemetry:
    """Track connection timing and metrics"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.spawn_start = None
        self.stdio_connected = None
        self.initialize_start = None
        self.initialize_done = None
        self.ping_ok = None
        self.list_tools_ok = None
        self.session_id = str(uuid.uuid4())[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "spawn_start": self.spawn_start,
            "stdio_connected": self.stdio_connected,
            "initialize_start": self.initialize_start,
            "initialize_done": self.initialize_done,
            "ping_ok": self.ping_ok,
            "list_tools_ok": self.list_tools_ok,
            "total_duration": (self.list_tools_ok - self.spawn_start) if (self.list_tools_ok and self.spawn_start) else None
        }

async def connect_with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    startup_timeout: float = 15.0,
    log_level: str = "INFO",
    logger = None
) -> Tuple[ClientSession, ConnectionTelemetry]:
    """
    Establish MCP STDIO connection with robust retry logic
    
    Args:
        max_retries: Maximum number of connection attempts
        base_delay: Base delay between retries (exponential backoff)
        startup_timeout: Timeout for server startup and initialization
        log_level: Logging level to pass to server
        logger: Logger instance
    
    Returns:
        Tuple of (connected session, telemetry data)
    
    Raises:
        ConnectionError: If all retries failed
    """
    telemetry = ConnectionTelemetry()
    python_exe = sys.executable
    server_script = str(Path(__file__).parent / "run_fork_mcp.py")
    
    for attempt in range(max_retries):
        telemetry.reset()
        telemetry.spawn_start = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "MCP_LOG_LEVEL": log_level,
            "MCPTransport": "stdio",
            "MCP_SESSION_ID": telemetry.session_id
        })
        
        # Setup server parameters with Windows-safe options
        server_params = StdioServerParameters(
            command=python_exe,
            args=["-u", server_script],  # Unbuffered mode
            cwd=str(Path(__file__).parent),
            env=env
        )
        
        if logger:
            logger.info(f"Connection attempt {attempt + 1}/{max_retries}", extra={
                "event": "connection_attempt",
                "context": {
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "session_id": telemetry.session_id,
                    "startup_timeout": startup_timeout
                }
            })
        
        try:
            async with stdio_client(server_params) as (read, write):
                telemetry.stdio_connected = time.time()
                
                if logger:
                    stdio_duration = telemetry.stdio_connected - telemetry.spawn_start
                    logger.debug(f"STDIO process spawned in {stdio_duration:.2f}s", extra={
                        "event": "stdio_spawned",
                        "context": {"duration": stdio_duration, "session_id": telemetry.session_id}
                    })
                
                async with ClientSession(read, write) as session:
                    # Initialize with timeout
                    telemetry.initialize_start = time.time()
                    
                    if logger:
                        logger.debug("Starting session initialization", extra={
                            "event": "session_init_start",
                            "context": {"session_id": telemetry.session_id}
                        })
                    
                    try:
                        await asyncio.wait_for(
                            session.initialize(),
                            timeout=startup_timeout
                        )
                        telemetry.initialize_done = time.time()
                        
                        # Validate connection with ping
                        ping_result = await asyncio.wait_for(
                            session.call_tool("ping", {}),
                            timeout=5.0
                        )
                        telemetry.ping_ok = time.time()
                        
                        # Validate tools list
                        tools = await asyncio.wait_for(
                            session.list_tools(),
                            timeout=5.0
                        )
                        telemetry.list_tools_ok = time.time()
                        
                        if logger:
                            total_duration = telemetry.list_tools_ok - telemetry.spawn_start
                            logger.info(f"Connection established successfully in {total_duration:.2f}s", extra={
                                "event": "connection_success",
                                "context": {
                                    "session_id": telemetry.session_id,
                                    "attempt": attempt + 1,
                                    "total_duration": total_duration,
                                    "tools_count": len(tools.tools)
                                }
                            })
                        
                        # Return successful session and telemetry
                        return session, telemetry
                        
                    except asyncio.TimeoutError as e:
                        error_msg = f"Timeout during initialization (attempt {attempt + 1})"
                        if logger:
                            logger.warning(error_msg, extra={
                                "event": "initialization_timeout",
                                "context": {
                                    "session_id": telemetry.session_id,
                                    "attempt": attempt + 1,
                                    "timeout": startup_timeout,
                                    "stage": "initialization" if telemetry.initialize_start else "session_setup"
                                }
                            })
                        raise ConnectionError(error_msg) from e
                        
        except Exception as e:
            error_duration = time.time() - telemetry.spawn_start
            error_msg = f"Connection failed (attempt {attempt + 1}): {str(e)}"
            
            if logger:
                logger.warning(error_msg, extra={
                    "event": "connection_failed",
                    "context": {
                        "session_id": telemetry.session_id,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration": error_duration,
                        "telemetry": telemetry.to_dict()
                    }
                })
            
            # Last attempt?
            if attempt == max_retries - 1:
                final_error = f"All {max_retries} connection attempts failed. Last error: {str(e)}"
                if logger:
                    logger.error(final_error, extra={
                        "event": "connection_exhausted",
                        "context": {
                            "session_id": telemetry.session_id,
                            "max_retries": max_retries,
                            "final_error": str(e),
                            "telemetry": telemetry.to_dict()
                        }
                    })
                raise ConnectionError(final_error) from e
            
            # Exponential backoff
            delay = base_delay * (2 ** attempt)
            if logger:
                logger.info(f"Retrying in {delay:.1f}s...", extra={
                    "event": "retry_delay",
                    "context": {"delay": delay, "next_attempt": attempt + 2}
                })
            await asyncio.sleep(delay)

async def main(
    retries: int = 3,
    startup_timeout: float = 15.0,
    log_level: str = "INFO",
    allow_real: bool = False
):
    """Main client function with comprehensive error handling and safety checks"""
    
    # Setup structured logging
    logger = setup_logging("mcp_client_simple", transport="stdio")
    
    logger.info("Starting MCP MetaTrader 5 Client", extra={
        "event": "client_startup",
        "context": {
            "retries": retries,
            "startup_timeout": startup_timeout,
            "log_level": log_level,
            "allow_real": allow_real
        }
    })
    
    try:
        with LoggingScope(logger, "mcp_connection"):
            # Connect with retry logic - the session is managed within connect_with_retry
            await run_demo_with_connection(
                max_retries=retries,
                startup_timeout=startup_timeout,
                log_level=log_level,
                allow_real=allow_real,
                logger=logger
            )
    except Exception as e:
        logger.error(f"Client error: {str(e)}", extra={
            "event": "client_error",
            "context": {"error": str(e), "type": type(e).__name__}
        })
        print(f"\n[ERROR] Client error: {e}", file=sys.stderr)
        raise
    
    finally:
        logger.info("Client session completed", extra={
            "event": "client_completed"
        })

async def run_demo_with_connection(
    max_retries: int,
    startup_timeout: float,
    log_level: str,
    allow_real: bool,
    logger
):
    """Run the demo within the connection context"""
    telemetry = ConnectionTelemetry()
    python_exe = sys.executable
    server_script = str(Path(__file__).parent / "run_fork_mcp.py")
    
    for attempt in range(max_retries):
        telemetry.reset()
        telemetry.spawn_start = time.time()
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "MCP_LOG_LEVEL": log_level,
            "MCPTransport": "stdio",
            "MCP_SESSION_ID": telemetry.session_id
        })
        
        # Setup server parameters with Windows-safe options
        server_params = StdioServerParameters(
            command=python_exe,
            args=["-u", server_script],  # Unbuffered mode
            cwd=str(Path(__file__).parent),
            env=env
        )
        
        logger.info(f"Connection attempt {attempt + 1}/{max_retries}", extra={
            "event": "connection_attempt",
            "context": {
                "attempt": attempt + 1,
                "max_retries": max_retries,
                "session_id": telemetry.session_id,
                "startup_timeout": startup_timeout
            }
        })
        
        try:
            async with stdio_client(server_params) as (read, write):
                telemetry.stdio_connected = time.time()
                
                stdio_duration = telemetry.stdio_connected - telemetry.spawn_start
                logger.debug(f"STDIO process spawned in {stdio_duration:.2f}s", extra={
                    "event": "stdio_spawned",
                    "context": {"duration": stdio_duration, "session_id": telemetry.session_id}
                })
                
                async with ClientSession(read, write) as session:
                    # Initialize with timeout
                    telemetry.initialize_start = time.time()
                    
                    logger.debug("Starting session initialization", extra={
                        "event": "session_init_start",
                        "context": {"session_id": telemetry.session_id}
                    })
                    
                    await asyncio.wait_for(
                        session.initialize(),
                        timeout=startup_timeout
                    )
                    telemetry.initialize_done = time.time()
                    
                    # Validate connection with ping
                    ping_result = await asyncio.wait_for(
                        session.call_tool("ping", {}),
                        timeout=5.0
                    )
                    telemetry.ping_ok = time.time()
                    
                    # Validate tools list
                    tools = await asyncio.wait_for(
                        session.list_tools(),
                        timeout=5.0
                    )
                    telemetry.list_tools_ok = time.time()
                    
                    total_duration = telemetry.list_tools_ok - telemetry.spawn_start
                    logger.info(f"Connection established successfully in {total_duration:.2f}s", extra={
                        "event": "connection_success",
                        "context": {
                            "session_id": telemetry.session_id,
                            "attempt": attempt + 1,
                            "total_duration": total_duration,
                            "tools_count": len(tools.tools)
                        }
                    })
                    
                    logger.info("Connection established, running client demo", extra={
                        "event": "demo_start",
                        "context": telemetry.to_dict()
                    })
                    
                    # Now run the demo while session is still active
                    await run_demo_operations(session, tools.tools, allow_real, logger)
                    return  # Success, exit function
                    
        except Exception as e:
            error_duration = time.time() - telemetry.spawn_start
            error_msg = f"Connection failed (attempt {attempt + 1}): {str(e)}"
            
            logger.warning(error_msg, extra={
                "event": "connection_failed",
                "context": {
                    "session_id": telemetry.session_id,
                    "attempt": attempt + 1,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": error_duration,
                    "telemetry": telemetry.to_dict()
                }
            })
            
            # Last attempt?
            if attempt == max_retries - 1:
                final_error = f"All {max_retries} connection attempts failed. Last error: {str(e)}"
                logger.error(final_error, extra={
                    "event": "connection_exhausted",
                    "context": {
                        "session_id": telemetry.session_id,
                        "max_retries": max_retries,
                        "final_error": str(e),
                        "telemetry": telemetry.to_dict()
                    }
                })
                raise ConnectionError(final_error) from e
            
            # Exponential backoff
            delay = 1.0 * (2 ** attempt)
            logger.info(f"Retrying in {delay:.1f}s...", extra={
                "event": "retry_delay",
                "context": {"delay": delay, "next_attempt": attempt + 2}
            })
            await asyncio.sleep(delay)

async def run_demo_operations(session, tools, allow_real: bool, logger):
    """Run demo operations within an active session"""
    try:
        # Show tool list
        print(f"\n=== MCP MetaTrader 5 Server Ready ===")
        print(f"Connected successfully! Found {len(tools)} tools:")
        
        for i, tool in enumerate(tools[:10], 1):
            print(f"  {i:2d}. {tool.name}")
        
        if len(tools) > 10:
            print(f"  ... and {len(tools) - 10} more tools")
        
        # Run diagnostic tools first
        logger.info("Running diagnostic tools", extra={"event": "diagnostics_start"})
        
        # 1. Transport info
        result = await session.call_tool("transport_info", {})
        transport_info = json.loads(result.content[0].text)
        logger.debug("Transport info retrieved", extra={
            "event": "transport_info",
            "context": transport_info
        })
        
        # 2. Health check
        result = await session.call_tool("health", {})
        health_info = json.loads(result.content[0].text)
        print(f"\nServer Health: {health_info['status'].upper()}")
        print(f"MT5 Status: {health_info['mt5_status']} ({health_info['details']})")
        
        logger.info(f"Server health: {health_info['status']}", extra={
            "event": "health_check",
            "context": health_info
        })
        
        # 3. Connection status with account safety check
        result = await session.call_tool("connection_status", {})
        conn_status = json.loads(result.content[0].text)
        
        if conn_status.get('initialized'):
            account_type = conn_status.get('trade_mode', 'unknown')
            account_login = conn_status.get('login', 'N/A')
            
            # Safety banner for account type
            print(f"\n{'='*60}")
            if account_type == 'demo':
                print(f"[OK] DEMO ACCOUNT DETECTED - SAFE FOR TRADING")
            else:
                print(f"[WARN] REAL ACCOUNT DETECTED - TRADING RESTRICTED")
            print(f"Account: {account_login} | Server: {conn_status.get('server', 'N/A')}")
            print(f"Company: {conn_status.get('company', 'N/A')}")
            print(f"Balance: ${conn_status.get('balance', 0):.2f}")
            print(f"{'='*60}")
            
            logger.info(f"Account status: {account_type}", extra={
                "event": "account_status",
                "context": {
                    "login": account_login,
                    "trade_mode": account_type,
                    "server": conn_status.get('server'),
                    "company": conn_status.get('company'),
                    "balance": conn_status.get('balance')
                }
            })
            
            # Trading safety validation
            result = await session.call_tool("validate_demo_for_trading", {})
            trading_validation = json.loads(result.content[0].text)
            trading_allowed = trading_validation.get('allowed', False)
            
            if not trading_allowed and not allow_real:
                print("\n[WARN] TRADING DISABLED: Real account detected")
                print("   To enable real trading, use: --allow-real")
                print("   Or set environment: MCP_ALLOW_REAL=1")
                
                logger.warning("Real trading blocked by policy", extra={
                    "event": "real_trading_blocked",
                    "context": trading_validation
                })
            else:
                print(f"\n[OK] Trading: {'ENABLED' if trading_allowed else 'DISABLED'}")
                logger.info(f"Trading validation: {'allowed' if trading_allowed else 'blocked'}", extra={
                    "event": "trading_validation",
                    "context": trading_validation
                })
        
        # 4. Configuration management demo
        print("\n--- Configuration Management Demo ---")
        
        # Current config
        result = await session.call_tool("get_current_config", {})
        config = json.loads(result.content[0].text)
        print(f"Current: {config.get('name', 'N/A')} ({config.get('market_type', 'N/A')})")
        
        # Available configs
        result = await session.call_tool("get_available_configs", {})
        configs = json.loads(result.content[0].text)
        available = list(configs.get('available_configs', {}).keys())
        print(f"Available: {', '.join(available)}")
        
        # Optional: Config switch demo (only if multiple configs)
        if len(available) > 1:
            print("\n--- Config Switch Demo ---")
            for config_name in available:
                if config_name != config.get('name', '').lower():
                    print(f"Switching to {config_name}...")
                    result = await session.call_tool("switch_config", {"config_name": config_name})
                    switch_result = json.loads(result.content[0].text)
                    if switch_result.get('success'):
                        print(f"[OK] Switched to: {switch_result['current_config']['name']}")
                        # Switch back
                        await session.call_tool("switch_config", {"config_name": "b3"})
                        print("[OK] Switched back to B3")
                        break
                    else:
                        print(f"[ERROR] {switch_result.get('error')}")
        
        print("\n" + "="*60)
        print("[SUCCESS] MCP CLIENT COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("Next steps:")
        print("   - Integrate with your trading applications")
        print("   - Use tools via Claude CLI: claude mcp list")
        print("   - Check logs in: logs/mcp_client_simple/")
        print("   - Server logs in: logs/run_fork_mcp/")
        
    except Exception as e:
        logger.error(f"Error during demo: {str(e)}", extra={
            "event": "demo_error",
            "context": {"error": str(e), "type": type(e).__name__}
        })
        print(f"\n[ERROR] Demo failed: {e}")
        raise

# CLI argument parsing
def parse_args():
    parser = argparse.ArgumentParser(
        description="MCP MetaTrader 5 Client - Connect to MCP server with retry logic"
    )
    parser.add_argument(
        "--retries", 
        type=int, 
        default=3,
        help="Maximum connection retry attempts (default: 3)"
    )
    parser.add_argument(
        "--startup-timeout", 
        type=float,
        default=15.0,
        help="Server startup timeout in seconds (default: 15.0)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARN", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--allow-real",
        action="store_true",
        help="Allow trading on real accounts (use with caution)"
    )
    return parser.parse_args()

# Utility functions for specific tool demonstrations
async def demo_specific_tool(tool_name: str, logger=None, **kwargs):
    """
    Demonstrate calling a specific tool with new connection
    """
    if logger:
        logger.info(f"Demonstrating tool: {tool_name}", extra={
            "event": "tool_demo",
            "context": {"tool_name": tool_name, "kwargs": kwargs}
        })
    
    try:
        session, telemetry = await connect_with_retry(max_retries=1, logger=logger)
        result = await session.call_tool(tool_name, kwargs)
        
        if result.content:
            data = json.loads(result.content[0].text)
            print(f"\n✅ {tool_name} result:")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"✅ {tool_name} executed (no return data)")
            return None
            
    except Exception as e:
        error_msg = f"❌ {tool_name} failed: {e}"
        print(error_msg)
        if logger:
            logger.error(error_msg, extra={
                "event": "tool_demo_error",
                "context": {"tool_name": tool_name, "error": str(e)}
            })
        raise

# Example usage functions
async def example_get_quotes(symbol: str = "ITSA4", logger=None):
    """Example: Get real-time quotes"""
    return await demo_specific_tool("symbol_info_tick", logger=logger, symbol=symbol)

async def example_get_historical_data(symbol: str = "ITSA4", count: int = 10, logger=None):
    """Example: Get historical data"""
    return await demo_specific_tool(
        "copy_rates_from_pos",
        logger=logger,
        symbol=symbol,
        timeframe=1,
        start_pos=0,
        count=count
    )

async def example_switch_market(market: str = "forex", logger=None):
    """Example: Switch market configuration"""
    return await demo_specific_tool("switch_config", logger=logger, config_name=market)

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Set environment for real trading if requested
    if args.allow_real:
        os.environ["MCP_ALLOW_REAL"] = "1"
    
    # Main execution
    try:
        asyncio.run(main(
            retries=args.retries,
            startup_timeout=args.startup_timeout,
            log_level=args.log_level,
            allow_real=args.allow_real
        ))
    except KeyboardInterrupt:
        print("\n[INFO] Client stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Client failed: {e}", file=sys.stderr)
        sys.exit(1)
