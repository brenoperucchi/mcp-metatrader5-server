"""
MetaTrader 5 MCP Server - Core server functionality.

This module contains the main server instance and core functionality.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import os

# Force mock for validation testing
from . import mt5_mock as mt5
MT5_AVAILABLE = False
print("[DEBUG] Using MT5 mock - FORCED FOR TESTING")

import pandas as pd
import numpy as np
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from .mt5_configs import MT5Config, MT5_CONFIGS, get_config, list_configs

# Import logging utilities
from .logging_utils import setup_logging, create_structured_log_entry

# Global logger (will be configured by the runtime)
logger = None

# Global request counter for telemetry
_request_count = 0

# MT5 availability status (logged properly)
mt5_status = "mock"  # Forced for testing
print(f"[DEBUG] MT5 status: {mt5_status}, MT5_AVAILABLE: {MT5_AVAILABLE}")

# Create the MCP server
mcp = FastMCP("MetaTrader 5 MCP Server")

# Global configuration manager
class ConfigManager:
    """Manages MT5 configurations and switching between them"""
    
    def __init__(self):
        self.current_config: Optional[MT5Config] = None
        self.initialized = False
        # Set default config to B3
        self.current_config = MT5_CONFIGS["b3"]
    
    def switch_config(self, config_name: str) -> Dict[str, Any]:
        """Switch to a different MT5 configuration"""
        if config_name not in MT5_CONFIGS:
            return {
                "success": False,
                "error": f"Configuration '{config_name}' not found",
                "available_configs": list(MT5_CONFIGS.keys())
            }
        
        old_config_name = self.current_config.name if self.current_config else "None"
        
        # Shutdown current connection if active
        if self.initialized:
            mt5.shutdown()
            self.initialized = False
            logger.info(f"Disconnected from {old_config_name}")
        
        # Switch to new configuration
        self.current_config = MT5_CONFIGS[config_name]
        logger.info(f"Switched configuration from '{old_config_name}' to '{self.current_config.name}'")
        
        return {
            "success": True,
            "message": f"Switched from '{old_config_name}' to '{self.current_config.name}'",
            "current_config": {
                "name": self.current_config.name,
                "market_type": self.current_config.market_type,
                "account": self.current_config.account,
                "server": self.current_config.server
            }
        }
    
    def initialize_mt5(self) -> bool:
        """Initialize MT5 with current configuration"""
        if not self.current_config:
            logger.error("No configuration set")
            return False
        
        if not self.initialized:
            logger.info(f"Initializing MT5 with configuration: {self.current_config.name}")
            logger.info(f"MT5 Path: {self.current_config.mt5_path}")
            logger.info(f"Market: {self.current_config.market_type}")
            logger.info(f"MT5 status: {mt5_status}")
            
            # For mock MT5, always return success
            if mt5_status == "mock":
                logger.info("Using MT5 mock - initialization always successful")
                self.initialized = True
                return True
            
            # For real MT5, try normal initialization
            if mt5.initialize(path=self.current_config.mt5_path, portable=self.current_config.portable):
                self.initialized = True
                logger.info("MT5 initialization successful")
                return True
            else:
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
        
        return True
    
    def get_current_config_info(self) -> Dict[str, Any]:
        """Get current configuration information"""
        if not self.current_config:
            return {"error": "No configuration active"}
        
        return {
            "name": self.current_config.name,
            "market_type": self.current_config.market_type, 
            "account": self.current_config.account,
            "server": self.current_config.server,
            "mt5_path": self.current_config.mt5_path,
            "initialized": self.initialized
        }

# Global configuration manager instance
config_manager = ConfigManager()

# Models for request/response data
class SymbolInfo(BaseModel):
    """Information about a trading symbol"""
    name: str
    description: Optional[str] = None
    path: Optional[str] = None
    session_deals: Optional[int] = None
    session_buy_orders: Optional[int] = None
    session_sell_orders: Optional[int] = None
    volume: Optional[float] = None
    volumehigh: Optional[float] = None
    volumelow: Optional[float] = None
    time: Optional[int] = None
    digits: Optional[int] = None
    spread: Optional[int] = None
    spread_float: Optional[bool] = None
    trade_calc_mode: Optional[int] = None
    trade_mode: Optional[int] = None
    start_time: Optional[int] = None
    expiration_time: Optional[int] = None
    trade_stops_level: Optional[int] = None
    trade_freeze_level: Optional[int] = None
    trade_exemode: Optional[int] = None
    swap_mode: Optional[int] = None
    swap_rollover3days: Optional[int] = None
    margin_hedged_use_leg: Optional[bool] = None
    expiration_mode: Optional[int] = None
    filling_mode: Optional[int] = None
    order_mode: Optional[int] = None
    order_gtc_mode: Optional[int] = None
    option_mode: Optional[int] = None
    option_right: Optional[int] = None
    bid: Optional[float] = None
    bidhigh: Optional[float] = None
    bidlow: Optional[float] = None
    ask: Optional[float] = None
    askhigh: Optional[float] = None
    asklow: Optional[float] = None
    last: Optional[float] = None
    lasthigh: Optional[float] = None
    lastlow: Optional[float] = None
    point: Optional[float] = None
    tick_value: Optional[float] = None
    tick_value_profit: Optional[float] = None
    tick_value_loss: Optional[float] = None
    tick_size: Optional[float] = None
    contract_size: Optional[float] = None
    volume_min: Optional[float] = None
    volume_max: Optional[float] = None
    volume_step: Optional[float] = None
    swap_long: Optional[float] = None
    swap_short: Optional[float] = None
    margin_initial: Optional[float] = None
    margin_maintenance: Optional[float] = None
    # Additional tick data fields
    tick_bid: Optional[float] = None
    tick_ask: Optional[float] = None
    tick_last: Optional[float] = None
    tick_time: Optional[int] = None
    tick_volume: Optional[int] = None
    spread_value: Optional[float] = None
    spread_percent: Optional[float] = None
    # Alternative last price fields for debugging
    last_price: Optional[float] = None
    current_price: Optional[float] = None

class AccountInfo(BaseModel):
    """Trading account information"""
    login: int
    trade_mode: int
    leverage: int
    limit_orders: int
    margin_so_mode: int
    trade_allowed: bool
    trade_expert: bool
    margin_mode: int
    currency_digits: int
    fifo_close: bool
    balance: float
    credit: float
    profit: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    margin_so_call: float
    margin_so_so: float
    margin_initial: float
    margin_maintenance: float
    assets: float
    liabilities: float
    commission_blocked: float
    name: str
    server: str
    currency: str
    company: str

class OrderRequest(BaseModel):
    """Order request parameters"""
    action: int
    symbol: str
    volume: float
    type: int
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: Optional[int] = None
    magic: Optional[int] = None
    comment: Optional[str] = None
    type_time: Optional[int] = None
    type_filling: Optional[int] = None

class OrderResult(BaseModel):
    """Order execution result"""
    retcode: int
    deal: int
    order: int
    volume: float
    price: float
    bid: float
    ask: float
    comment: str
    request_id: int
    retcode_external: int
    request: Dict[str, Any]

class Position(BaseModel):
    """Trading position information"""
    ticket: int
    time: int
    time_msc: int
    time_update: int
    time_update_msc: int
    type: int
    magic: int
    identifier: int
    reason: int
    volume: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    swap: float
    profit: float
    symbol: str
    comment: str
    external_id: str

class HistoryOrder(BaseModel):
    """Historical order information"""
    ticket: int
    time_setup: int
    time_setup_msc: int
    time_expiration: int
    type: int
    type_time: int
    type_filling: int
    state: int
    magic: int
    position_id: int
    position_by_id: int
    reason: int
    volume_initial: float
    volume_current: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    price_stoplimit: float
    symbol: str
    comment: str
    external_id: str

class Deal(BaseModel):
    """Deal information"""
    ticket: int
    order: int
    time: int
    time_msc: int
    type: int
    entry: int
    magic: int
    position_id: int
    reason: int
    volume: float
    price: float
    commission: float
    swap: float
    profit: float
    fee: float
    symbol: str
    comment: str
    external_id: str

# Initialize MetaTrader 5 connection
@mcp.tool()
def initialize() -> bool:
    """
    Initialize the MetaTrader 5 terminal with current configuration.
    
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    return config_manager.initialize_mt5()

# Shutdown MetaTrader 5 connection
@mcp.tool()
def shutdown() -> bool:
    """
    Shut down the connection to the MetaTrader 5 terminal.
    
    Returns:
        bool: True if shutdown was successful.
    """
    mt5.shutdown()
    logger.info("MT5 connection shut down")
    return True

# Login to MetaTrader 5 account
@mcp.tool()
def login(login: int, password: str, server: str) -> bool:
    """
    Log in to the MetaTrader 5 trading account.
    
    Args:
        login: Trading account number
        password: Trading account password
        server: Trading server name
        
    Returns:
        bool: True if login was successful, False otherwise.
    """
    if not mt5.login(login=login, password=password, server=server):
        logger.error(f"MT5 login failed, error code: {mt5.last_error()}")
        return False
    
    logger.info(f"MT5 login successful to account #{login} on server {server}")
    return True

# Get account information
@mcp.tool()
def get_account_info() -> AccountInfo:
    """
    Get information about the current trading account.
    
    Returns:
        AccountInfo: Information about the trading account.
    """
    # Auto-initialize if not initialized
    if not config_manager.initialized:
        if not config_manager.initialize_mt5():
            raise ValueError("Failed to initialize MT5")
    
    account_info = mt5.account_info()
    if account_info is None:
        logger.error(f"Failed to get account info, error code: {mt5.last_error()}")
        raise ValueError("Failed to get account info")
    
    # Convert named tuple to dictionary
    account_dict = account_info._asdict()
    return AccountInfo(**account_dict)

# Get terminal information
@mcp.tool()
def get_terminal_info() -> Dict[str, Any]:
    """
    Get information about the MetaTrader 5 terminal.
    
    Returns:
        Dict[str, Any]: Information about the terminal.
    """
    # Auto-initialize if not initialized
    if not config_manager.initialized:
        if not config_manager.initialize_mt5():
            raise ValueError("Failed to initialize MT5")
    
    terminal_info = mt5.terminal_info()
    if terminal_info is None:
        logger.error(f"Failed to get terminal info, error code: {mt5.last_error()}")
        raise ValueError("Failed to get terminal info")
    
    # Convert named tuple to dictionary
    return terminal_info._asdict()

# Get version information
@mcp.tool()
def get_version() -> Dict[str, Any]:
    """
    Get the MetaTrader 5 version.
    
    Returns:
        Dict[str, Any]: Version information.
    """
    version = mt5.version()
    if version is None:
        logger.error(f"Failed to get version, error code: {mt5.last_error()}")
        raise ValueError("Failed to get version")
    
    return {
        "version": version[0],
        "build": version[1],
        "date": version[2]
    }

# Validate demo account for trading
@mcp.tool()
def validate_demo_for_trading() -> Dict[str, Any]:
    """
    Validate if the connected account is a demo account before allowing trading operations.
    This is a safety feature to prevent accidental trading on real accounts.
    
    Returns:
        Dict[str, Any]: Validation result with account type information.
    """
    account_info = mt5.account_info()
    if account_info is None:
        logger.error(f"Failed to get account info, error code: {mt5.last_error()}")
        return {
            "allowed": False,
            "reason": "Account information not available",
            "account_type": "unknown"
        }
    
    # Check if account is demo using multiple indicators
    # 1. Check trade_mode (0 = demo, 1 = contest, 2 = real)
    trade_mode_demo = account_info.trade_mode == 0
    
    # 2. Check server name for demo indicators
    server_name = account_info.server.upper()
    server_demo = any(demo_indicator in server_name for demo_indicator in ['DEMO', 'TEST', 'TRIAL'])
    
    # 3. Combined validation - account is demo if either condition is true
    is_demo = trade_mode_demo or server_demo
    
    logger.info(f"Demo validation - trade_mode: {account_info.trade_mode}, server: {account_info.server}")
    logger.info(f"Demo validation result - trade_mode_demo: {trade_mode_demo}, server_demo: {server_demo}, final: {is_demo}")
    
    return {
        "allowed": is_demo,
        "reason": "Conta demo verificada" if is_demo else "Conta real detectada",
        "account_type": "demo" if is_demo else "real",
        "login": account_info.login,
        "server": account_info.server,
        "company": account_info.company
    }

# Multi-configuration tools
@mcp.tool()
def get_available_configs() -> Dict[str, Any]:
    """
    Get all available MT5 configurations (B3, Forex, etc.).
    
    Returns:
        Dict[str, Any]: Available configurations with details.
    """
    configs = {}
    for key, config in MT5_CONFIGS.items():
        configs[key] = {
            "name": config.name,
            "market_type": config.market_type,
            "account": config.account,
            "server": config.server,
            "is_current": config_manager.current_config and config.name == config_manager.current_config.name
        }
    
    return {
        "available_configs": configs,
        "current_config": config_manager.current_config.name if config_manager.current_config else None
    }

@mcp.tool() 
def get_current_config() -> Dict[str, Any]:
    """
    Get information about the currently active MT5 configuration.
    
    Returns:
        Dict[str, Any]: Current configuration details.
    """
    return config_manager.get_current_config_info()

@mcp.tool()
def switch_config(config_name: str) -> Dict[str, Any]:
    """
    Switch between different MT5 configurations (B3, Forex, etc.).
    
    Args:
        config_name: Name of the configuration to switch to ("b3" or "forex")
        
    Returns:
        Dict[str, Any]: Switch operation result.
    """
    global _request_count
    _request_count += 1
    if logger:
        logger.info(f"Switching to config: {config_name}", extra={"event": "config_switch", "context": {"config_name": config_name}})
    return config_manager.switch_config(config_name)

# DIAGNOSTIC TOOLS FOR STDIO TROUBLESHOOTING

@mcp.tool()
def ping() -> Dict[str, Any]:
    """
    Simple ping to verify MCP server connectivity and measure round-trip time.
    
    Returns:
        Dict with ok status and timestamp
    """
    global _request_count
    _request_count += 1
    
    from datetime import datetime
    response = {
        "ok": True,
        "time": datetime.utcnow().isoformat() + "Z",
        "mt5_available": MT5_AVAILABLE,
        "mt5_status": mt5_status
    }
    
    if logger:
        logger.debug("Ping received", extra={"event": "ping", "context": response})
    
    return response

@mcp.tool()
def health() -> Dict[str, Any]:
    """
    Comprehensive health check including MT5 connection state.
    
    Returns:
        Dict with status, MT5 availability, and configuration details
    """
    global _request_count
    _request_count += 1
    
    # Determine overall status
    if not config_manager.current_config:
        status = "down"
        details = "No configuration active"
    elif not config_manager.initialized:
        status = "degraded" 
        details = "Configuration set but not initialized"
    else:
        status = "ok"
        details = "MT5 initialized and ready"
    
    health_info = {
        "status": status,
        "details": details,
        "mt5_available": MT5_AVAILABLE,
        "mt5_status": mt5_status,
        "initialized": config_manager.initialized,
        "requests_served": _request_count,
        "config": config_manager.get_current_config_info() if config_manager.current_config else None
    }
    
    if logger:
        logger.info(f"Health check: {status}", extra={"event": "health_check", "context": health_info})
    
    return health_info

@mcp.tool()
def transport_info() -> Dict[str, Any]:
    """
    Information about the current transport being used.
    
    Returns:
        Dict with transport type and related info
    """
    global _request_count
    _request_count += 1
    
    transport_type = os.environ.get("MCPTransport", "unknown")
    
    info = {
        "transport": transport_type,
        "pid": os.getpid(),
        "mt5_available": MT5_AVAILABLE,
        "mt5_status": mt5_status
    }
    
    if logger:
        logger.debug(f"Transport info requested", extra={"event": "transport_info", "context": info})
    
    return info

@mcp.tool()
def connection_status() -> Dict[str, Any]:
    """
    Current connection status including account details and trading mode.
    
    Returns:
        Dict with login, server, company, trade_mode (demo/real), initialized flag
    """
    global _request_count
    _request_count += 1
    
    if not config_manager.initialized:
        status = {
            "initialized": False,
            "reason": "MT5 not initialized",
            "config": config_manager.get_current_config_info() if config_manager.current_config else None
        }
    else:
        try:
            account_info = mt5.account_info()
            if account_info:
                is_demo = account_info.trade_mode == (getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0))
                status = {
                    "initialized": True,
                    "login": account_info.login,
                    "server": account_info.server,
                    "company": account_info.company,
                    "trade_mode": "demo" if is_demo else "real",
                    "balance": account_info.balance,
                    "config": config_manager.get_current_config_info()
                }
            else:
                status = {
                    "initialized": True,
                    "error": "Account info not available",
                    "last_error": mt5.last_error() if hasattr(mt5, 'last_error') else None
                }
        except Exception as e:
            status = {
                "initialized": True,
                "error": f"Failed to get account info: {str(e)}",
                "config": config_manager.get_current_config_info()
            }
    
    if logger:
        logger.info("Connection status requested", extra={"event": "connection_status", "context": status})
    
    return status

# DEMO/REAL ACCOUNT SAFETY GUARD

def require_demo_or_allowed() -> Dict[str, Any]:
    """
    Safety guard to ensure trading operations only proceed on DEMO accounts
    or when explicitly allowed on REAL accounts.
    
    Returns:
        Dict with allowed status and reason
    """
    if not config_manager.initialized:
        return {
            "allowed": False,
            "reason": "MT5 not initialized",
            "account_type": "unknown"
        }
    
    try:
        account_info = mt5.account_info()
        if not account_info:
            return {
                "allowed": False,
                "reason": "Account information not available",
                "account_type": "unknown"
            }
        
        is_demo = account_info.trade_mode == (getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0))
        account_type = "demo" if is_demo else "real"
        
        if is_demo:
            # Demo accounts always allowed
            return {
                "allowed": True,
                "reason": "Demo account verified",
                "account_type": account_type,
                "login": account_info.login,
                "server": account_info.server
            }
        else:
            # Real accounts only allowed with explicit permission
            allow_real = os.environ.get("MCP_ALLOW_REAL") == "1"
            
            result = {
                "allowed": allow_real,
                "reason": "Real trading enabled by MCP_ALLOW_REAL=1" if allow_real else "Real trading disabled by policy",
                "account_type": account_type,
                "login": account_info.login,
                "server": account_info.server
            }
            
            if logger and not allow_real:
                logger.warning(f"Real trading blocked for account {account_info.login}", extra={
                    "event": "real_trading_blocked",
                    "context": {
                        "login": account_info.login,
                        "server": account_info.server,
                        "company": account_info.company
                    }
                })
            
            return result
            
    except Exception as e:
        return {
            "allowed": False,
            "reason": f"Error checking account: {str(e)}",
            "account_type": "unknown"
        }

# Helper to log MT5 connection events
def log_mt5_connection_event():
    """
    Log structured MT5 connection event for audit trail
    """
    if logger and config_manager.initialized:
        try:
            account_info = mt5.account_info()
            if account_info:
                is_demo = account_info.trade_mode == (getattr(mt5, 'ACCOUNT_TRADE_MODE_DEMO', 0))
                logger.info("MT5 connected successfully", extra={
                    "event": "mt5_connected",
                    "context": {
                        "login": account_info.login,
                        "server": account_info.server,
                        "company": account_info.company,
                        "trade_mode": "demo" if is_demo else "real",
                        "balance": account_info.balance,
                        "config_name": config_manager.current_config.name
                    }
                })
        except Exception as e:
            logger.error(f"Failed to log MT5 connection: {str(e)}", extra={
                "event": "mt5_log_failed",
                "context": {"error": str(e)}
            })
