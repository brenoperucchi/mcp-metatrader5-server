"""
MetaTrader 5 MCP Server - Market Data Functions

This module contains tools and resources for accessing market data from MetaTrader 5.
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
from fastmcp.utilities.types import Image
from pydantic import BaseModel, Field

# Import the main server instance and config manager
from mcp_metatrader5_server.server import mcp, config_manager

# Configuration management for verbose logging
def is_verbose_enabled(port=8000):
    """Check if verbose mode is enabled in JSON config"""
    try:
        import sys
        from pathlib import Path
        
        # Add parent directory to path to import server_config
        parent_dir = Path(__file__).parent.parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        from server_config import server_config
        config = server_config.get_server_config(port)
        return config.get("verbose", False)
    except:
        return True  # Default to verbose if config not available

logger = logging.getLogger("mt5-mcp-server.market_data")

# Helper function for tick persistence
async def _persist_tick_async(symbol: str, tick_data: Any):
    """Helper to persist tick asynchronously without blocking"""
    try:
        from mcp_metatrader5_server.tick_persister_registry import get_tick_persister

        persister = get_tick_persister()
        if persister:
            from datetime import datetime, timezone
            tick_dict = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc),
                'bid': getattr(tick_data, 'bid', 0),
                'ask': getattr(tick_data, 'ask', 0),
                'last': getattr(tick_data, 'last', 0),
                'volume': getattr(tick_data, 'volume', 0)
            }
            await persister.enqueue_tick(tick_dict)
            if is_verbose_enabled():
                logger.info(f"✅ Enqueued tick for {symbol}: bid={tick_dict['bid']}, ask={tick_dict['ask']}")
        else:
            if is_verbose_enabled():
                logger.debug(f"⚠️  Tick persister not available - skipping persistence for {symbol}")
    except Exception as e:
        # Log error but don't break the API
        logger.error(f"❌ Tick persistence error for {symbol}: {e}")

async def _persist_ticks_batch_async(symbol: str, ticks_list: List[Dict[str, Any]]):
    """Helper to persist multiple ticks asynchronously without blocking"""
    try:
        from mcp_metatrader5_server.tick_persister_registry import get_tick_persister

        persister = get_tick_persister()
        if persister:
            from datetime import datetime, timezone
            for tick in ticks_list:
                # Convert tick timestamp to datetime if needed
                if 'time' in tick and isinstance(tick['time'], (int, float)):
                    tick_time = datetime.fromtimestamp(tick['time'], tz=timezone.utc)
                elif 'time' in tick and isinstance(tick['time'], str):
                    # Already ISO format, use current time
                    tick_time = datetime.now(timezone.utc)
                else:
                    tick_time = datetime.now(timezone.utc)

                await persister.enqueue_tick({
                    'symbol': symbol,
                    'timestamp': tick_time,
                    'bid': tick.get('bid', 0),
                    'ask': tick.get('ask', 0),
                    'last': tick.get('last', 0),
                    'volume': tick.get('volume', 0)
                })
            if is_verbose_enabled() and len(ticks_list) > 0:
                logger.info(f"✅ Enqueued {len(ticks_list)} ticks for {symbol}")
    except Exception as e:
        # Log error but don't break the API
        logger.error(f"❌ Batch tick persistence error for {symbol}: {e}")

# Get symbols
@mcp.tool()
def get_symbols() -> List[str]:
    """
    Get all available symbols (financial instruments) from the MetaTrader 5 terminal.
    
    Returns:
        List[str]: List of symbol names.
    """
    symbols = mt5.symbols_get()
    if symbols is None:
        logger.error(f"Failed to get symbols, error code: {mt5.last_error()}")
        raise ValueError("Failed to get symbols")
    
    return [symbol.name for symbol in symbols]

# Get symbols by group
@mcp.tool()
def get_symbols_by_group(group: str) -> List[str]:
    """
    Get symbols that match a specific group or pattern.
    
    Args:
        group: Filter for arranging a group of symbols (e.g., "*", "EUR*", etc.)
        
    Returns:
        List[str]: List of symbol names that match the group.
    """
    symbols = mt5.symbols_get(group=group)
    if symbols is None:
        logger.error(f"Failed to get symbols for group {group}, error code: {mt5.last_error()}")
        return []
    
    return [symbol.name for symbol in symbols]

# Get symbol information
@mcp.tool()
def get_symbol_info(symbol: str) -> Dict[str, Any]:
    """
    Get information about a specific symbol.
    
    Args:
        symbol: Symbol name
        
    Returns:
        Dict[str, Any]: Information about the symbol.
    """
    # Try to use existing connection first, only initialize if absolutely needed
    if not config_manager.initialized:
        logger.warning("MT5 not initialized, attempting lazy initialization")
        if not config_manager.initialize_mt5():
            logger.warning("MT5 initialization failed, attempting to use cached data if available")
            # Don't raise error immediately - try to get symbol data anyway
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        error_code = mt5.last_error()
        logger.error(f"Failed to get info for symbol {symbol}, error code: {error_code}")
        
        # Try to provide fallback data or at least meaningful error
        if error_code == (-10003,):  # Market closed error
            logger.warning(f"Market appears to be closed for {symbol}, but data should still be available")
        
        raise ValueError(f"Failed to get info for symbol {symbol} (error: {error_code})")
    
    # Convert named tuple to dictionary
    symbol_dict = symbol_info._asdict()
    
    # DEBUG: Log original dict from MT5 (only if verbose enabled)
    if is_verbose_enabled():
        logger.info(f"ORIGINAL MT5 DICT for {symbol}: 'last' = {symbol_dict.get('last', 'NOT_FOUND')}")
        logger.info(f"ORIGINAL MT5 DICT keys: {list(symbol_dict.keys())}")
        logger.info(f"'last' in original dict: {'last' in symbol_dict}")
    
    # Enrich with tick data to ensure we have the latest 'last' price
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            # FORCE the last field - try multiple approaches
            symbol_dict['last'] = tick.last
            symbol_dict['last_price'] = tick.last  # Alternative field
            symbol_dict['current_price'] = tick.last  # Another alternative
            symbol_dict['price_last'] = tick.last  # Yet another alternative
            symbol_dict['recent_price'] = tick.last  # Non-"last" alternative
            symbol_dict['trade_price'] = tick.last  # Another non-"last" alternative
            
            # Update other fields
            symbol_dict['bid'] = tick.bid
            symbol_dict['ask'] = tick.ask
            symbol_dict['tick_bid'] = tick.bid
            symbol_dict['tick_ask'] = tick.ask
            symbol_dict['tick_last'] = tick.last
            symbol_dict['tick_time'] = tick.time
            symbol_dict['tick_volume'] = tick.volume
            
            # Calculate spread information
            if tick.bid and tick.ask:
                symbol_dict['spread_value'] = tick.ask - tick.bid
                symbol_dict['spread_percent'] = ((tick.ask - tick.bid) / tick.bid) * 100 if tick.bid > 0 else 0
                
            # Debug log to see what's happening (only if verbose enabled)
            if is_verbose_enabled():
                logger.info(f"DEBUG {symbol}: setting last={tick.last}, dict_last={symbol_dict.get('last')}")
                logger.info(f"DEBUG {symbol}: dict keys: {list(symbol_dict.keys())}")
                logger.info(f"DEBUG {symbol}: 'last' in dict: {'last' in symbol_dict}")
        else:
            logger.warning(f"Could not get tick data for {symbol}, using symbol_info only")
    except Exception as e:
        logger.warning(f"Error getting tick data for {symbol}: {e}, using symbol_info only")
    
    # Final debug before return (only if verbose enabled)
    if is_verbose_enabled():
        logger.info(f"FINAL DEBUG {symbol}: returning dict with keys: {list(symbol_dict.keys())}")
        logger.info(f"FINAL DEBUG {symbol}: last={symbol_dict.get('last')}, tick_last={symbol_dict.get('tick_last')}")
    
    return symbol_dict  # Return dict directly instead of SymbolInfo

# Get symbol tick information
@mcp.tool()
async def get_symbol_info_tick(symbol: str) -> Dict[str, Any]:
    """
    Get the latest tick data for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        Dict[str, Any]: Latest tick data for the symbol.
    """
    # Auto-initialize if not initialized
    if not config_manager.initialized:
        if not config_manager.initialize_mt5():
            raise ValueError("Failed to initialize MT5")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Failed to get tick for symbol {symbol}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to get tick for symbol {symbol}")

    # Persist tick asynchronously (non-blocking)
    await _persist_tick_async(symbol, tick)

    # Convert named tuple to dictionary
    return tick._asdict()

# Select symbol in Market Watch
@mcp.tool()
def symbol_select(symbol: str, visible: bool = True) -> bool:
    """
    Select a symbol in the Market Watch window or remove a symbol from it.
    
    Args:
        symbol: Symbol name
        visible: Symbol visibility flag
            - True: Make the symbol visible in Market Watch
            - False: Hide the symbol from Market Watch
        
    Returns:
        bool: True if the symbol is selected successfully, False otherwise.
    """
    result = mt5.symbol_select(symbol, visible)
    if not result:
        logger.error(f"Failed to select symbol {symbol}, error code: {mt5.last_error()}")
    
    return result

# Copy rates from position
@mcp.tool()
def copy_rates_from_pos(
    symbol: str, 
    timeframe: int, 
    start_pos: int, 
    count: int
) -> List[Dict[str, Any]]:
    """
    Get bars from a specified symbol and timeframe starting from the specified position.
    
    Args:
        symbol: Symbol name
        timeframe: Timeframe as specified in TIMEFRAME_* constants:
            - 1: TIMEFRAME_M1 (1 minute)
            - 5: TIMEFRAME_M5 (5 minutes)
            - 15: TIMEFRAME_M15 (15 minutes)
            - 30: TIMEFRAME_M30 (30 minutes)
            - 60: TIMEFRAME_H1 (1 hour)
            - 240: TIMEFRAME_H4 (4 hours)
            - 1440: TIMEFRAME_D1 (1 day)
            - 10080: TIMEFRAME_W1 (1 week)
            - 43200: TIMEFRAME_MN1 (1 month)
        start_pos: Initial position for bar retrieval
        count: Number of bars to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of bars with time, open, high, low, close, tick_volume, spread, and real_volume.
    """
    rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
    if rates is None:
        logger.error(f"Failed to copy rates for {symbol}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy rates for {symbol}")
    
    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(rates)
    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return df.to_dict('records')

# Copy rates from date
@mcp.tool()
def copy_rates_from_date(
    symbol: str, 
    timeframe: int, 
    date_from: datetime, 
    count: int
) -> List[Dict[str, Any]]:
    """
    Get bars from a specified symbol and timeframe starting from the specified date.
    
    Args:
        symbol: Symbol name
        timeframe: Timeframe (use TIMEFRAME_* constants)
        date_from: Start date for bar retrieval
        count: Number of bars to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of bars with time, open, high, low, close, tick_volume, spread, and real_volume.
    """
    # Convert datetime to timestamp
    date_from_timestamp = int(date_from.timestamp())
    
    rates = mt5.copy_rates_from_date(symbol, timeframe, date_from_timestamp, count)
    if rates is None:
        logger.error(f"Failed to copy rates for {symbol} from date {date_from}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy rates for {symbol} from date {date_from}")
    
    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(rates)
    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return df.to_dict('records')

# Copy rates range
@mcp.tool()
def copy_rates_range(
    symbol: str, 
    timeframe: int, 
    date_from: datetime, 
    date_to: datetime
) -> List[Dict[str, Any]]:
    """
    Get bars from a specified symbol and timeframe within the specified date range.
    
    Args:
        symbol: Symbol name
        timeframe: Timeframe (use TIMEFRAME_* constants)
        date_from: Start date for bar retrieval
        date_to: End date for bar retrieval
        
    Returns:
        List[Dict[str, Any]]: List of bars with time, open, high, low, close, tick_volume, spread, and real_volume.
    """
    # Convert datetime to timestamp
    date_from_timestamp = int(date_from.timestamp())
    date_to_timestamp = int(date_to.timestamp())
    
    rates = mt5.copy_rates_range(symbol, timeframe, date_from_timestamp, date_to_timestamp)
    if rates is None:
        logger.error(f"Failed to copy rates for {symbol} in range {date_from} to {date_to}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy rates for {symbol} in range {date_from} to {date_to}")
    
    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(rates)
    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return df.to_dict('records')

# Copy ticks from position
@mcp.tool()
async def copy_ticks_from_pos(
    symbol: str,
    start_pos: int,
    count: int,
    flags: int = mt5.COPY_TICKS_ALL
) -> List[Dict[str, Any]]:
    """
    Get ticks from a specified symbol starting from the specified position.

    Args:
        symbol: Symbol name
        start_pos: Initial position for tick retrieval
        count: Number of ticks to retrieve
        flags: Type of requested ticks:
            - mt5.COPY_TICKS_ALL: All ticks (default)
            - mt5.COPY_TICKS_INFO: Ticks containing bid and/or ask price changes
            - mt5.COPY_TICKS_TRADE: Ticks containing last price and volume changes

    Returns:
        List[Dict[str, Any]]: List of ticks.
    """
    ticks = mt5.copy_ticks_from(symbol, start_pos, count, flags)
    if ticks is None:
        logger.error(f"Failed to copy ticks for {symbol}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy ticks for {symbol}")

    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(ticks)

    # Store original time values before conversion for persistence
    ticks_records = []
    for idx, row in df.iterrows():
        tick_dict = {
            'time': row.get('time'),  # Keep as timestamp
            'bid': row.get('bid', 0),
            'ask': row.get('ask', 0),
            'last': row.get('last', 0),
            'volume': row.get('volume', 0),
            'flags': row.get('flags', 0)
        }
        ticks_records.append(tick_dict)

    # Persist ticks asynchronously (non-blocking)
    await _persist_ticks_batch_async(symbol, ticks_records)

    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    if 'time_msc' in df.columns:
        df['time_msc'] = pd.to_datetime(df['time_msc'], unit='ms').dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return df.to_dict('records')

# Copy ticks from date
@mcp.tool()
async def copy_ticks_from_date(
    symbol: str,
    date_from: datetime,
    count: int,
    flags: int = mt5.COPY_TICKS_ALL
) -> List[Dict[str, Any]]:
    """
    Get ticks from a specified symbol starting from the specified date.

    Args:
        symbol: Symbol name
        date_from: Start date for tick retrieval
        count: Number of ticks to retrieve
        flags: Type of requested ticks

    Returns:
        List[Dict[str, Any]]: List of ticks.
    """
    # MT5 copy_ticks_from expects datetime object, not timestamp
    # Ensure datetime object is timezone-naive as required by MT5
    if date_from.tzinfo is not None:
        date_from = date_from.replace(tzinfo=None)

    ticks = mt5.copy_ticks_from(symbol, date_from, count, flags)
    if ticks is None:
        logger.error(f"Failed to copy ticks for {symbol} from date {date_from}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy ticks for {symbol} from date {date_from}")

    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(ticks)

    # Store original time values before conversion for persistence
    ticks_records = []
    for idx, row in df.iterrows():
        tick_dict = {
            'time': row.get('time'),  # Keep as timestamp
            'bid': row.get('bid', 0),
            'ask': row.get('ask', 0),
            'last': row.get('last', 0),
            'volume': row.get('volume', 0),
            'flags': row.get('flags', 0)
        }
        ticks_records.append(tick_dict)

    # Persist ticks asynchronously (non-blocking)
    await _persist_ticks_batch_async(symbol, ticks_records)

    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    if 'time_msc' in df.columns:
        df['time_msc'] = pd.to_datetime(df['time_msc'], unit='ms').dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return df.to_dict('records')

# Copy ticks range
@mcp.tool()
async def copy_ticks_range(
    symbol: str,
    date_from: datetime,
    date_to: datetime,
    flags: int = mt5.COPY_TICKS_ALL
) -> List[Dict[str, Any]]:
    """
    Get ticks from a specified symbol within the specified date range.

    Args:
        symbol: Symbol name
        date_from: Start date for tick retrieval
        date_to: End date for tick retrieval
        flags: Type of requested ticks

    Returns:
        List[Dict[str, Any]]: List of ticks.
    """
    # MT5 copy_ticks_range expects datetime objects, not timestamps
    # Ensure datetime objects are timezone-naive as required by MT5
    if date_from.tzinfo is not None:
        date_from = date_from.replace(tzinfo=None)
    if date_to.tzinfo is not None:
        date_to = date_to.replace(tzinfo=None)

    # VERBOSE LOGGING for debugging
    logger.info(f"🔍 copy_ticks_range called: symbol={symbol}, from={date_from}, to={date_to}, flags={flags}")

    # Try to select symbol first (ensure it's in Market Watch)
    try:
        mt5.symbol_select(symbol, True)
        logger.info(f"   Symbol {symbol} selected in Market Watch")
    except Exception as e:
        logger.warning(f"   Could not select symbol: {e}")

    ticks = mt5.copy_ticks_range(symbol, date_from, date_to, flags)

    # VERBOSE LOGGING for result
    if ticks is not None:
        logger.info(f"✅ MT5 returned {len(ticks)} ticks")
    else:
        error = mt5.last_error()
        logger.error(f"❌ MT5 returned None, error code: {error}")

    if ticks is None:
        logger.error(f"Failed to copy ticks for {symbol} in range {date_from} to {date_to}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to copy ticks for {symbol} in range {date_from} to {date_to}")

    # Convert numpy array to list of dictionaries
    df = pd.DataFrame(ticks)

    # Store original time values before conversion for persistence
    ticks_records = []
    for idx, row in df.iterrows():
        tick_dict = {
            'time': row.get('time'),  # Keep as timestamp
            'bid': row.get('bid', 0),
            'ask': row.get('ask', 0),
            'last': row.get('last', 0),
            'volume': row.get('volume', 0),
            'flags': row.get('flags', 0)
        }
        ticks_records.append(tick_dict)

    # Persist ticks asynchronously (non-blocking)
    await _persist_ticks_batch_async(symbol, ticks_records)

    # Convert time to ISO string for JSON serialization
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    if 'time_msc' in df.columns:
        df['time_msc'] = pd.to_datetime(df['time_msc'], unit='ms').dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return df.to_dict('records')

# Get last error
@mcp.tool()
def get_last_error() -> Dict[str, Any]:
    """
    Get the last error code and description.
    
    Returns:
        Dict[str, Any]: Last error code and description.
    """
    error_code = mt5.last_error()
    
    error_descriptions = {
        mt5.RES_S_OK: "OK",
        mt5.RES_E_FAIL: "Generic fail",
        mt5.RES_E_INVALID_PARAMS: "Invalid parameters",
        mt5.RES_E_NO_MEMORY: "No memory",
        mt5.RES_E_NOT_FOUND: "Not found",
        mt5.RES_E_INVALID_VERSION: "Invalid version",
        mt5.RES_E_AUTH_FAILED: "Authorization failed",
        mt5.RES_E_UNSUPPORTED: "Unsupported method",
        mt5.RES_E_AUTO_TRADING_DISABLED: "Auto-trading disabled",
        mt5.RES_E_INTERNAL_FAIL: "Internal failure",
        mt5.RES_E_DONE: "Request completed",
        mt5.RES_E_CANCELED: "Request canceled",
    }
    
    error_description = error_descriptions.get(error_code, "Unknown error")
    
    return {
        "code": error_code,
        "description": error_description
    }

# Resource for timeframe constants
@mcp.resource("mt5://timeframes")
def get_timeframes() -> str:
    """
    Get information about available timeframes in MetaTrader 5.
    
    Returns:
        str: Information about available timeframes.
    """
    timeframes = {
        "TIMEFRAME_M1": 1,
        "TIMEFRAME_M2": 2,
        "TIMEFRAME_M3": 3,
        "TIMEFRAME_M4": 4,
        "TIMEFRAME_M5": 5,
        "TIMEFRAME_M6": 6,
        "TIMEFRAME_M10": 10,
        "TIMEFRAME_M12": 12,
        "TIMEFRAME_M15": 15,
        "TIMEFRAME_M20": 20,
        "TIMEFRAME_M30": 30,
        "TIMEFRAME_H1": 60,
        "TIMEFRAME_H2": 120,
        "TIMEFRAME_H3": 180,
        "TIMEFRAME_H4": 240,
        "TIMEFRAME_H6": 360,
        "TIMEFRAME_H8": 480,
        "TIMEFRAME_H12": 720,
        "TIMEFRAME_D1": 1440,
        "TIMEFRAME_W1": 10080,
        "TIMEFRAME_MN1": 43200
    }
    
    result = "Available timeframes in MetaTrader 5:\n\n"
    for name, value in timeframes.items():
        result += f"{name}: {value}\n"
    
    return result

# Resource for tick flag constants
@mcp.resource("mt5://tick_flags")
def get_tick_flags() -> str:
    """
    Get information about tick flags in MetaTrader 5.
    
    Returns:
        str: Information about tick flags.
    """
    tick_flags = {
        "COPY_TICKS_ALL": mt5.COPY_TICKS_ALL,
        "COPY_TICKS_INFO": mt5.COPY_TICKS_INFO,
        "COPY_TICKS_TRADE": mt5.COPY_TICKS_TRADE
    }
    
    result = "Available tick flags in MetaTrader 5:\n\n"
    for name, value in tick_flags.items():
        result += f"{name}: {value}\n"
    
    return result

# Book Level 2 Data (Order Book) Functions
class BookLevel(BaseModel):
    """Order book level data"""
    type: int  # 0-buy, 1-sell
    price: float
    volume: float
    volume_real: float

@mcp.tool()
def copy_book_levels(symbol: str, depth: int = 10) -> List[Dict[str, Any]]:
    """
    Get Level 2 market data (order book) for a specified symbol.
    
    Args:
        symbol: Symbol name (e.g., "EURUSD", "WINM25", etc.)
        depth: Number of price levels to retrieve (default: 10, max: 20)
        
    Returns:
        List[Dict[str, Any]]: List of order book levels with price, volume and type information.
        Each level contains:
        - type: 0 for buy orders, 1 for sell orders
        - price: Price level
        - volume: Volume at this price level
        - volume_real: Real volume at this price level
    """
    # Validate depth parameter
    if depth <= 0 or depth > 20:
        raise ValueError("Depth must be between 1 and 20")
    
    # Get market book data
    book = mt5.market_book_get(symbol)
    if book is None:
        logger.error(f"Failed to get market book for {symbol}, error code: {mt5.last_error()}")
        raise ValueError(f"Failed to get market book for symbol {symbol}")
    
    # Convert to list of dictionaries, limiting by depth
    book_levels = []
    for i, level in enumerate(book[:depth]):
        book_levels.append({
            "type": level.type,
            "price": level.price,
            "volume": level.volume,
            "volume_real": level.volume_real
        })
    
    logger.info(f"Retrieved {len(book_levels)} book levels for {symbol}")
    return book_levels

@mcp.tool()
def subscribe_market_book(symbol: str) -> bool:
    """
    Subscribe to market book (Level 2) data for a symbol.
    
    Args:
        symbol: Symbol name
        
    Returns:
        bool: True if subscription successful, False otherwise.
    """
    result = mt5.market_book_add(symbol)
    if not result:
        logger.error(f"Failed to subscribe to market book for {symbol}, error code: {mt5.last_error()}")
        return False
    
    logger.info(f"Successfully subscribed to market book for {symbol}")
    return True

@mcp.tool()
def unsubscribe_market_book(symbol: str) -> bool:
    """
    Unsubscribe from market book (Level 2) data for a symbol.
    
    Args:
        symbol: Symbol name
        
    Returns:
        bool: True if unsubscription successful, False otherwise.
    """
    result = mt5.market_book_release(symbol)
    if not result:
        logger.error(f"Failed to unsubscribe from market book for {symbol}, error code: {mt5.last_error()}")
        return False
    
    logger.info(f"Successfully unsubscribed from market book for {symbol}")
    return True

@mcp.tool()
def get_book_snapshot(symbol: str, depth: int = 5) -> Dict[str, Any]:
    """
    Get a complete order book snapshot with bid/ask levels separated.
    
    Args:
        symbol: Symbol name
        depth: Number of levels on each side (default: 5)
        
    Returns:
        Dict[str, Any]: Order book snapshot with separated bid/ask levels and summary.
    """
    if depth <= 0 or depth > 10:
        raise ValueError("Depth must be between 1 and 10")
    
    # Get current tick for reference
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(f"Failed to get tick data for {symbol}")
    
    # Get book data
    book = mt5.market_book_get(symbol)
    if book is None:
        raise ValueError(f"Failed to get market book for {symbol}")
    
    # Separate bid and ask levels
    bids = []
    asks = []
    
    for level in book:
        level_data = {
            "price": level.price,
            "volume": level.volume,
            "volume_real": level.volume_real
        }
        
        if level.type == 0:  # Buy orders (bids)
            bids.append(level_data)
        else:  # Sell orders (asks)
            asks.append(level_data)
    
    # Limit to requested depth
    bids = bids[:depth]
    asks = asks[:depth]
    
    # Calculate spreads and totals
    best_bid = bids[0]["price"] if bids else 0
    best_ask = asks[0]["price"] if asks else 0
    spread = best_ask - best_bid if best_bid and best_ask else 0
    
    total_bid_volume = sum(level["volume"] for level in bids)
    total_ask_volume = sum(level["volume"] for level in asks)
    
    return {
        "symbol": symbol,
        "timestamp": tick.time,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "bids": bids,
        "asks": asks,
        "total_bid_volume": total_bid_volume,
        "total_ask_volume": total_ask_volume,
        "bid_levels": len(bids),
        "ask_levels": len(asks)
    }
