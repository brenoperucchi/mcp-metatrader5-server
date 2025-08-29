"""
Cliente Python para MT5 MCP Server

Este pacote fornece um cliente completo e amigável para interagir com o
fork_mcp (servidor MCP para MetaTrader 5).

Exemplo de uso básico:
    ```python
    import asyncio
    from datetime import datetime, timedelta
    from mt5_client import MT5Client, TimeframeType
    
    async def main():
        async with MT5Client() as client:
            await client.connect()
            
            # Obter informações da conta
            account = await client.get_account_info()
            print(f"Conta: {account.login} ({account.server})")
            
            # Obter últimos preços
            tick = await client.get_tick("EURUSD")
            print(f"EURUSD: Bid={tick.bid}, Ask={tick.ask}")
            
            # Obter dados históricos
            candles = await client.copy_rates_from(
                "EURUSD", TimeframeType.M1, datetime.now() - timedelta(hours=1)
            )
            print(f"Obtidas {len(candles)} velas")
    
    asyncio.run(main())
    ```
"""

from .client import MT5Client
from .mcp_client import MCPClient
from .models import (
    AccountInfo, SymbolInfo, TickData, CandleData, OrderInfo,
    PositionInfo, TradeInfo, BookTick, MCPResponse,
    OrderType, TradeAction, TimeframeType, CopyTicks,
    OrderState, DealType, PositionType
)
from .exceptions import (
    MT5ClientError, ConnectionError, TimeoutError, MCPError,
    RetryError, AuthenticationError, ValidationError,
    TradingError, MarketError, ConfigurationError
)

__version__ = "1.0.0"
__author__ = "MT5 MCP Team"
__email__ = "support@mt5mcp.com"
__description__ = "Cliente Python completo para fork_mcp (MetaTrader 5 MCP Server)"

# Classes principais
__all__ = [
    # Cliente principal
    "MT5Client",
    "MCPClient",
    
    # Modelos de dados
    "AccountInfo",
    "SymbolInfo", 
    "TickData",
    "CandleData",
    "OrderInfo",
    "PositionInfo",
    "TradeInfo",
    "BookTick",
    "MCPResponse",
    
    # Enums
    "OrderType",
    "TradeAction",
    "TimeframeType",
    "CopyTicks",
    "OrderState",
    "DealType",
    "PositionType",
    
    # Exceções
    "MT5ClientError",
    "ConnectionError",
    "TimeoutError",
    "MCPError",
    "RetryError",
    "AuthenticationError",
    "ValidationError",
    "TradingError",
    "MarketError",
    "ConfigurationError",
]
