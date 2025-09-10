"""
MetaTrader 5 MCP Server - Trading Functions

This module contains tools and resources for trading operations in MetaTrader 5.
"""

import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
import os

# Import MT5 based on USE_MOCK environment variable
USE_MOCK = os.environ.get('USE_MOCK', 'false').lower() in ['true', '1', 'yes']

if USE_MOCK:
    from . import mt5_mock as mt5
else:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        from . import mt5_mock as mt5
import pandas as pd
import numpy as np
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import the main server instance
from mcp_metatrader5_server.server import mcp, OrderRequest, OrderResult, Position, HistoryOrder, Deal, config_manager

logger = logging.getLogger("mt5-mcp-server.trading")

# Log MT5 initialization status
try:
    terminal_info = mt5.terminal_info()
    if terminal_info:
        logger.info(f"[DEBUG] MT5 Trading module loaded. Terminal: {terminal_info.name}, Build: {terminal_info.build}")
    else:
        logger.warning("[DEBUG] MT5 Trading module loaded but terminal_info() returned None")
except Exception as e:
    logger.warning(f"[DEBUG] MT5 Trading module loaded with warning: {e}")

# Send order
@mcp.tool()
def order_send(request: OrderRequest) -> OrderResult:
    """
    Send an order to the trade server.
    
    Args:
        request: Order parameters
        
    Returns:
        OrderResult: Order execution result.
    """
    # Convert request to dictionary
    logger.info(f"[DEBUG] order_send called with request type: {type(request)}")
    logger.info(f"[DEBUG] order_send request content: {request}")
    
    if hasattr(request, 'model_dump'):
        request_dict = request.model_dump()
        logger.info("[DEBUG] Using model_dump() to convert request")
    elif isinstance(request, dict):
        request_dict = request
        logger.info("[DEBUG] Request is already a dict")
    else:
        request_dict = vars(request) if hasattr(request, '__dict__') else request
        logger.info(f"[DEBUG] Using vars() or direct assignment")
    
    logger.info(f"[DEBUG] Request dict to send: {request_dict}")
    
    # Check MT5 connection status before sending
    if not mt5.terminal_info():
        logger.error("[DEBUG] MT5 terminal not connected!")
        mt5_error = mt5.last_error()
        logger.error(f"[DEBUG] MT5 last error: {mt5_error}")
        raise ValueError(f"MT5 terminal not connected: {mt5_error}")
    
    # Send order
    logger.info("[DEBUG] Calling mt5.order_send()...")
    result = mt5.order_send(request_dict)
    logger.info(f"[DEBUG] mt5.order_send() returned: {result}")
    
    if result is None:
        mt5_error = mt5.last_error()
        logger.error(f"[DEBUG] Failed to send order, MT5 error: {mt5_error}")
        logger.error(f"[DEBUG] Request was: {request_dict}")
        
        # Try to get more detailed error info
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"[DEBUG] Account info: login={account_info.login}, balance={account_info.balance}, margin_free={account_info.margin_free}")
        
        symbol_info = mt5.symbol_info(request_dict.get('symbol'))
        if symbol_info:
            logger.info(f"[DEBUG] Symbol info: symbol={symbol_info.name}, bid={symbol_info.bid}, ask={symbol_info.ask}, trade_mode={symbol_info.trade_mode}")
        else:
            logger.error(f"[DEBUG] Symbol {request_dict.get('symbol')} not found or not selected!")
            
        raise ValueError(f"Failed to send order: {mt5_error}")
    
    # Convert named tuple to dictionary
    logger.info(f"[DEBUG] Converting result to dict, type: {type(result)}")
    result_dict = result._asdict()
    logger.info(f"[DEBUG] Result dict: {result_dict}")
    
    # Convert request named tuple to dictionary if needed
    if hasattr(result_dict.get('request'), '_asdict'):
        result_dict['request'] = result_dict['request']._asdict()
        logger.info(f"[DEBUG] Converted request to dict: {result_dict['request']}")
    
    logger.info(f"[DEBUG] Returning OrderResult with retcode: {result_dict.get('retcode')}")
    return OrderResult(**result_dict)

# Check order
@mcp.tool()
def order_check(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if an order can be placed with the specified parameters.
    
    Args:
        request: Dictionary with order parameters including:
            - action: Trade action (1 for DEAL, 2 for PENDING)
            - symbol: Trading symbol (e.g., "ITSA3")
            - volume: Volume to trade (integer or float)
            - type: Order type (0 for BUY, 1 for SELL)
            - price: Price for the order
            - comment: Optional comment
            - magic: Optional magic number
        
    Returns:
        Dict[str, Any]: Order check result.
    """
    # Auto-initialize if not initialized
    if not config_manager.initialized:
        if not config_manager.initialize_mt5():
            raise ValueError("Failed to initialize MT5")
    
    logger.info(f"[DEBUG] order_check called with request type: {type(request)}")
    
    # Ensure request is a dictionary
    if not isinstance(request, dict):
        raise ValueError("Request must be a dictionary")
    
    # Validate and convert volume to float
    if 'volume' in request:
        try:
            request['volume'] = float(request['volume'])
            logger.info(f"[DEBUG] Converted volume to float: {request['volume']}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid 'volume' argument: {request['volume']} - must be a number")
    
    logger.info(f"[DEBUG] order_check request dict: {request}")
    
    # Check order
    result = mt5.order_check(request)
    logger.info(f"[DEBUG] mt5.order_check() returned: {result}")
    
    if result is None:
        mt5_error = mt5.last_error()
        logger.error(f"[DEBUG] Failed to check order, MT5 error: {mt5_error}")
        logger.error(f"[DEBUG] Request was: {request}")
        raise ValueError(f"Failed to check order: {mt5_error}")
    
    # Convert named tuple to dictionary
    result_dict = result._asdict()
    
    # Convert request named tuple to dictionary if needed
    if hasattr(result_dict.get('request'), '_asdict'):
        result_dict['request'] = result_dict['request']._asdict()
    
    return result_dict

# Cancel order
@mcp.tool()
def order_cancel(ticket: int) -> Dict[str, Any]:
    """
    Cancel a pending order.
    
    Args:
        ticket: Order ticket to cancel
        
    Returns:
        Dict[str, Any]: Order cancellation result.
    """
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": ticket,
    }
    
    result = mt5.order_send(request)
    if result is None:
        logger.error(f"Failed to cancel order {ticket}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to cancel order {ticket}")
    
    # Convert named tuple to dictionary
    result_dict = result._asdict()
    
    return result_dict

# Modify order
@mcp.tool()
def order_modify(ticket: int, price: Optional[float] = None, sl: Optional[float] = None, tp: Optional[float] = None) -> Dict[str, Any]:
    """
    Modify an existing pending order.
    
    Args:
        ticket: Order ticket to modify
        price: New price (optional, keeps current if not specified)
        sl: New stop loss (optional, keeps current if not specified) 
        tp: New take profit (optional, keeps current if not specified)
        
    Returns:
        Dict[str, Any]: Order modification result.
    """
    # Get current order info
    orders = mt5.orders_get(ticket=ticket)
    if not orders or len(orders) == 0:
        logger.error(f"Order {ticket} not found")
        raise ValueError(f"Order {ticket} not found")
    
    current_order = orders[0]
    
    # Build request with current values or new ones
    request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "order": ticket,
        "price": price if price is not None else current_order.price_open,
        "sl": sl if sl is not None else current_order.sl,
        "tp": tp if tp is not None else current_order.tp,
    }
    
    result = mt5.order_send(request)
    if result is None:
        logger.error(f"Failed to modify order {ticket}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to modify order {ticket}")
    
    # Convert named tuple to dictionary
    result_dict = result._asdict()
    
    return result_dict

# Position modify (Stop Loss / Take Profit)
@mcp.tool()  
def position_modify(ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> Dict[str, Any]:
    """
    Modify Stop Loss and Take Profit of an open position.
    
    Args:
        ticket: Position ticket to modify
        sl: New stop loss (optional, keeps current if not specified)
        tp: New take profit (optional, keeps current if not specified)
        
    Returns:
        Dict[str, Any]: Position modification result.
    """
    # Get current position info
    positions = mt5.positions_get(ticket=ticket)
    if not positions or len(positions) == 0:
        logger.error(f"Position {ticket} not found")
        raise ValueError(f"Position {ticket} not found")
    
    current_position = positions[0]
    
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": current_position.symbol,
        "position": ticket,
        "sl": sl if sl is not None else current_position.sl,
        "tp": tp if tp is not None else current_position.tp,
    }
    
    result = mt5.order_send(request)
    if result is None:
        logger.error(f"Failed to modify position {ticket}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to modify position {ticket}")
    
    # Convert named tuple to dictionary
    result_dict = result._asdict()
    
    return result_dict

# Get positions
@mcp.tool()
def positions_get(symbol: Optional[str] = None, group: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get open positions.
    
    Args:
        symbol: Symbol name. If specified, only positions for this symbol will be returned.
        group: Filter for arranging a group of positions (e.g., "*", "USD*", etc.)
        
    Returns:
        List[Dict[str, Any]]: List of open positions.
    """
    if symbol is not None:
        positions = mt5.positions_get(symbol=symbol)
    elif group is not None:
        positions = mt5.positions_get(group=group)
    else:
        positions = mt5.positions_get()
    
    if positions is None:
        logger.error(f"Failed to get positions, error code: {mt5.last_error()}")
        return []
    
    result = []
    for position in positions:
        # Convert named tuple to dictionary
        position_dict = position._asdict()
        result.append(position_dict)
    
    return result

# Get position by ticket
@mcp.tool()
def positions_get_by_ticket(ticket: int) -> Optional[Dict[str, Any]]:
    """
    Get an open position by its ticket.
    
    Args:
        ticket: Position ticket
        
    Returns:
        Optional[Dict[str, Any]]: Position information or None if not found.
    """
    position = mt5.positions_get(ticket=ticket)
    if position is None or len(position) == 0:
        logger.error(f"Failed to get position with ticket {ticket}, error code: {mt5.last_error()}")
        return None
    
    # Convert named tuple to dictionary
    position_dict = position[0]._asdict()
    return position_dict

# Get orders
@mcp.tool()
def orders_get(symbol: Optional[str] = None, group: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active orders.
    
    Args:
        symbol: Symbol name. If specified, only orders for this symbol will be returned.
        group: Filter for arranging a group of orders (e.g., "*", "USD*", etc.)
        
    Returns:
        List[Dict[str, Any]]: List of active orders.
    """
    if symbol is not None:
        orders = mt5.orders_get(symbol=symbol)
    elif group is not None:
        orders = mt5.orders_get(group=group)
    else:
        orders = mt5.orders_get()
    
    if orders is None:
        logger.error(f"Failed to get orders, error code: {mt5.last_error()}")
        return []
    
    result = []
    for order in orders:
        # Convert named tuple to dictionary
        order_dict = order._asdict()
        result.append(order_dict)
    
    return result

# Get order by ticket
@mcp.tool()
def orders_get_by_ticket(ticket: int) -> Optional[Dict[str, Any]]:
    """
    Get an active order by its ticket.
    
    Args:
        ticket: Order ticket
        
    Returns:
        Optional[Dict[str, Any]]: Order information or None if not found.
    """
    order = mt5.orders_get(ticket=ticket)
    if order is None or len(order) == 0:
        logger.error(f"Failed to get order with ticket {ticket}, error code: {mt5.last_error()}")
        return None
    
    # Convert named tuple to dictionary
    return order[0]._asdict()

# Get history orders
@mcp.tool()
def history_orders_get(
    symbol: Optional[str] = None,
    group: Optional[str] = None,
    ticket: Optional[int] = None,
    position: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[HistoryOrder]:
    """
    Get orders from history within the specified date range.
    
    Args:
        symbol: Symbol name
        group: Filter for arranging a group of orders
        ticket: Order ticket
        position: Position ticket
        from_date: Start date for order retrieval
        to_date: End date for order retrieval
        
    Returns:
        List[HistoryOrder]: List of historical orders.
    """
    # Convert datetime to timestamp
    from_timestamp = int(from_date.timestamp()) if from_date else None
    to_timestamp = int(to_date.timestamp()) if to_date else None
    
    # Prepare request
    request = {}
    if symbol is not None:
        request["symbol"] = symbol
    if group is not None:
        request["group"] = group
    if ticket is not None:
        request["ticket"] = ticket
    if position is not None:
        request["position"] = position
    if from_timestamp is not None:
        request["date_from"] = from_timestamp
    if to_timestamp is not None:
        request["date_to"] = to_timestamp
    
    # Get history orders
    if request:
        orders = mt5.history_orders_get(**request)
    else:
        orders = mt5.history_orders_get()
    
    if orders is None:
        logger.error(f"Failed to get history orders, error code: {mt5.last_error()}")
        return []
    
    result = []
    for order in orders:
        # Convert named tuple to dictionary
        order_dict = order._asdict()
        result.append(HistoryOrder(**order_dict))
    
    return result

# Get history deals
@mcp.tool()
def history_deals_get(
    symbol: Optional[str] = None,
    group: Optional[str] = None,
    ticket: Optional[int] = None,
    position: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[Deal]:
    """
    Get deals from history within the specified date range.
    
    Args:
        symbol: Symbol name
        group: Filter for arranging a group of deals
        ticket: Deal ticket
        position: Position ticket
        from_date: Start date for deal retrieval
        to_date: End date for deal retrieval
        
    Returns:
        List[Deal]: List of historical deals.
    """
    # Convert datetime to timestamp
    from_timestamp = int(from_date.timestamp()) if from_date else None
    to_timestamp = int(to_date.timestamp()) if to_date else None
    
    # Prepare request
    request = {}
    if symbol is not None:
        request["symbol"] = symbol
    if group is not None:
        request["group"] = group
    if ticket is not None:
        request["ticket"] = ticket
    if position is not None:
        request["position"] = position
    if from_timestamp is not None:
        request["date_from"] = from_timestamp
    if to_timestamp is not None:
        request["date_to"] = to_timestamp
    
    # Get history deals
    if request:
        deals = mt5.history_deals_get(**request)
    else:
        deals = mt5.history_deals_get()
    
    if deals is None:
        logger.error(f"Failed to get history deals, error code: {mt5.last_error()}")
        return []
    
    result = []
    for deal in deals:
        # Convert named tuple to dictionary
        deal_dict = deal._asdict()
        result.append(Deal(**deal_dict))
    
    return result

# Resource for order types
@mcp.resource("mt5://order_types")
def get_order_types() -> str:
    """
    Get information about order types in MetaTrader 5.
    
    Returns:
        str: Information about order types.
    """
    order_types = {
        "ORDER_TYPE_BUY": mt5.ORDER_TYPE_BUY,
        "ORDER_TYPE_SELL": mt5.ORDER_TYPE_SELL,
        "ORDER_TYPE_BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
        "ORDER_TYPE_SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
        "ORDER_TYPE_BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
        "ORDER_TYPE_SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
        "ORDER_TYPE_BUY_STOP_LIMIT": mt5.ORDER_TYPE_BUY_STOP_LIMIT,
        "ORDER_TYPE_SELL_STOP_LIMIT": mt5.ORDER_TYPE_SELL_STOP_LIMIT,
        "ORDER_TYPE_CLOSE_BY": mt5.ORDER_TYPE_CLOSE_BY
    }
    
    result = "Available order types in MetaTrader 5:\n\n"
    for name, value in order_types.items():
        result += f"{name}: {value}\n"
    
    return result

# Resource for order filling types
@mcp.resource("mt5://order_filling_types")
def get_order_filling_types() -> str:
    """
    Get information about order filling types in MetaTrader 5.
    
    Returns:
        str: Information about order filling types.
    """
    filling_types = {
        "ORDER_FILLING_FOK": mt5.ORDER_FILLING_FOK,
        "ORDER_FILLING_IOC": mt5.ORDER_FILLING_IOC,
        "ORDER_FILLING_RETURN": mt5.ORDER_FILLING_RETURN
    }
    
    result = "Available order filling types in MetaTrader 5:\n\n"
    for name, value in filling_types.items():
        result += f"{name}: {value}\n"
    
    return result

# Resource for order time types
@mcp.resource("mt5://order_time_types")
def get_order_time_types() -> str:
    """
    Get information about order time types in MetaTrader 5.
    
    Returns:
        str: Information about order time types.
    """
    time_types = {
        "ORDER_TIME_GTC": mt5.ORDER_TIME_GTC,
        "ORDER_TIME_DAY": mt5.ORDER_TIME_DAY,
        "ORDER_TIME_SPECIFIED": mt5.ORDER_TIME_SPECIFIED,
        "ORDER_TIME_SPECIFIED_DAY": mt5.ORDER_TIME_SPECIFIED_DAY
    }
    
    result = "Available order time types in MetaTrader 5:\n\n"
    for name, value in time_types.items():
        result += f"{name}: {value}\n"
    
    return result

# Resource for trade request actions
@mcp.resource("mt5://trade_actions")
def get_trade_actions() -> str:
    """
    Get information about trade request actions in MetaTrader 5.
    
    Returns:
        str: Information about trade request actions.
    """
    actions = {
        "TRADE_ACTION_DEAL": mt5.TRADE_ACTION_DEAL,
        "TRADE_ACTION_PENDING": mt5.TRADE_ACTION_PENDING,
        "TRADE_ACTION_SLTP": mt5.TRADE_ACTION_SLTP,
        "TRADE_ACTION_MODIFY": mt5.TRADE_ACTION_MODIFY,
        "TRADE_ACTION_REMOVE": mt5.TRADE_ACTION_REMOVE,
        "TRADE_ACTION_CLOSE_BY": mt5.TRADE_ACTION_CLOSE_BY
    }
    
    result = "Available trade request actions in MetaTrader 5:\n\n"
    for name, value in actions.items():
        result += f"{name}: {value}\n"
    
    return result
