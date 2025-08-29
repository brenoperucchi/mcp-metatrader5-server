"""
Cliente MT5 de alto nível com API amigável para todas as ferramentas
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, date
from decimal import Decimal

from .mcp_client import MCPClient
from .models import (
    AccountInfo, SymbolInfo, TickData, CandleData, OrderInfo,
    PositionInfo, TradeInfo, BookTick, OrderType, TradeAction,
    TimeframeType, CopyTicks
)
from .exceptions import MT5ClientError, ValidationError, TradingError

logger = logging.getLogger(__name__)


class MT5Client:
    """
    Cliente MT5 de alto nível que fornece uma API amigável para todas as funcionalidades
    """
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:50051",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        log_dir: Optional[str] = None,
        demo_only: bool = True
    ):
        """
        Inicializa o cliente MT5
        
        Args:
            base_url: URL base do servidor MCP
            timeout: Timeout para requisições
            max_retries: Máximo de tentativas de retry
            retry_delay: Delay entre tentativas
            log_dir: Diretório para logs
            demo_only: Só permite contas demo (segurança)
        """
        self._mcp_client = MCPClient(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            log_dir=log_dir
        )
        self.demo_only = demo_only
        self._account_info: Optional[AccountInfo] = None
        self._symbols_cache: Dict[str, SymbolInfo] = {}
        
    async def __aenter__(self):
        """Context manager entry"""
        await self._mcp_client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self._mcp_client.disconnect()
    
    # ========== CONNECTION & INFO ==========
    
    async def connect(self) -> bool:
        """Conectar ao MT5 terminal"""
        try:
            result = await self._mcp_client.call_tool("initialize")
            success = result.get("content", [{}])[0].get("result", False)
            
            if success:
                logger.info("Conectado ao MT5 terminal com sucesso")
                # Obter info da conta para validação
                await self._load_account_info()
            
            return success
        except Exception as e:
            logger.error(f"Erro ao conectar ao MT5: {e}")
            raise MT5ClientError(f"Falha na conexão com MT5: {str(e)}")
    
    async def disconnect(self) -> None:
        """Desconectar do MT5 terminal"""
        try:
            await self._mcp_client.call_tool("shutdown")
            self._account_info = None
            self._symbols_cache.clear()
            logger.info("Desconectado do MT5 terminal")
        except Exception as e:
            logger.warning(f"Erro ao desconectar: {e}")
    
    async def _load_account_info(self):
        """Carregar informações da conta e validar"""
        try:
            account_data = await self.get_account_info()
            
            # Validar se é conta demo quando necessário
            if self.demo_only and not account_data.is_demo:
                raise ValidationError(
                    "Apenas contas demo são permitidas. Configure demo_only=False para contas reais."
                )
            
            self._account_info = account_data
            logger.info(f"Conta carregada: {account_data.login} ({'DEMO' if account_data.is_demo else 'REAL'})")
            
        except Exception as e:
            logger.error(f"Erro ao carregar informações da conta: {e}")
            raise
    
    async def get_account_info(self) -> AccountInfo:
        """Obter informações da conta"""
        result = await self._mcp_client.call_tool("account_info")
        data = result.get("content", [{}])[0]
        return AccountInfo.from_mt5_dict(data)
    
    async def get_terminal_info(self) -> Dict[str, Any]:
        """Obter informações do terminal"""
        result = await self._mcp_client.call_tool("terminal_info")
        return result.get("content", [{}])[0]
    
    async def get_version(self) -> Dict[str, Any]:
        """Obter versão do MT5"""
        result = await self._mcp_client.call_tool("version")
        return result.get("content", [{}])[0]
    
    # ========== SYMBOLS & MARKET DATA ==========
    
    async def get_symbols(self, group: Optional[str] = None) -> List[SymbolInfo]:
        """
        Obter lista de símbolos
        
        Args:
            group: Filtro de grupo (ex: "EURUSD*", "*.F")
            
        Returns:
            Lista de informações dos símbolos
        """
        args = {}
        if group:
            args["group"] = group
            
        result = await self._mcp_client.call_tool("symbols_get", args)
        symbols_data = result.get("content", [{}])[0].get("symbols", [])
        
        symbols = [SymbolInfo.from_mt5_dict(data) for data in symbols_data]
        
        # Atualizar cache
        for symbol in symbols:
            self._symbols_cache[symbol.name] = symbol
        
        return symbols
    
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        Obter informações de um símbolo específico
        
        Args:
            symbol: Nome do símbolo (ex: "EURUSD")
            
        Returns:
            Informações do símbolo
        """
        # Verificar cache primeiro
        if symbol in self._symbols_cache:
            return self._symbols_cache[symbol]
        
        result = await self._mcp_client.call_tool("symbol_info", {"symbol": symbol})
        data = result.get("content", [{}])[0]
        
        if not data:
            raise ValidationError(f"Símbolo '{symbol}' não encontrado")
        
        symbol_info = SymbolInfo.from_mt5_dict(data)
        self._symbols_cache[symbol] = symbol_info
        
        return symbol_info
    
    async def select_symbol(self, symbol: str, enable: bool = True) -> bool:
        """
        Selecionar/deselecionar símbolo no Market Watch
        
        Args:
            symbol: Nome do símbolo
            enable: True para selecionar, False para deselecionar
            
        Returns:
            Sucesso da operação
        """
        result = await self._mcp_client.call_tool("symbol_select", {
            "symbol": symbol,
            "enable": enable
        })
        return result.get("content", [{}])[0].get("result", False)
    
    async def get_tick(self, symbol: str) -> TickData:
        """
        Obter último tick de um símbolo
        
        Args:
            symbol: Nome do símbolo
            
        Returns:
            Dados do tick
        """
        result = await self._mcp_client.call_tool("symbol_info_tick", {"symbol": symbol})
        data = result.get("content", [{}])[0]
        
        if not data:
            raise ValidationError(f"Tick não encontrado para símbolo '{symbol}'")
        
        return TickData.from_mt5_dict(data)
    
    async def copy_ticks_from(
        self,
        symbol: str,
        date_from: Union[datetime, date],
        count: int = 100,
        flags: CopyTicks = CopyTicks.ALL
    ) -> List[TickData]:
        """
        Copiar ticks históricos a partir de uma data
        
        Args:
            symbol: Nome do símbolo
            date_from: Data/hora inicial
            count: Número de ticks
            flags: Tipo de ticks
            
        Returns:
            Lista de ticks
        """
        # Converter data para timestamp se necessário
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        
        result = await self._mcp_client.call_tool("copy_ticks_from", {
            "symbol": symbol,
            "date_from": date_from.isoformat(),
            "count": count,
            "flags": flags.value
        })
        
        ticks_data = result.get("content", [{}])[0].get("ticks", [])
        return [TickData.from_mt5_dict(data) for data in ticks_data]
    
    async def copy_ticks_range(
        self,
        symbol: str,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date],
        flags: CopyTicks = CopyTicks.ALL
    ) -> List[TickData]:
        """
        Copiar ticks históricos em um intervalo
        
        Args:
            symbol: Nome do símbolo
            date_from: Data/hora inicial
            date_to: Data/hora final
            flags: Tipo de ticks
            
        Returns:
            Lista de ticks
        """
        # Converter datas para timestamp se necessário
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        result = await self._mcp_client.call_tool("copy_ticks_range", {
            "symbol": symbol,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "flags": flags.value
        })
        
        ticks_data = result.get("content", [{}])[0].get("ticks", [])
        return [TickData.from_mt5_dict(data) for data in ticks_data]
    
    async def copy_rates_from(
        self,
        symbol: str,
        timeframe: TimeframeType,
        date_from: Union[datetime, date],
        count: int = 100
    ) -> List[CandleData]:
        """
        Copiar rates (velas) históricos a partir de uma data
        
        Args:
            symbol: Nome do símbolo
            timeframe: Timeframe (M1, M5, H1, etc.)
            date_from: Data/hora inicial
            count: Número de velas
            
        Returns:
            Lista de velas
        """
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        
        result = await self._mcp_client.call_tool("copy_rates_from", {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "date_from": date_from.isoformat(),
            "count": count
        })
        
        rates_data = result.get("content", [{}])[0].get("rates", [])
        return [CandleData.from_mt5_dict(data) for data in rates_data]
    
    async def copy_rates_range(
        self,
        symbol: str,
        timeframe: TimeframeType,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date]
    ) -> List[CandleData]:
        """
        Copiar rates (velas) históricos em um intervalo
        
        Args:
            symbol: Nome do símbolo
            timeframe: Timeframe
            date_from: Data/hora inicial
            date_to: Data/hora final
            
        Returns:
            Lista de velas
        """
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        result = await self._mcp_client.call_tool("copy_rates_range", {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        })
        
        rates_data = result.get("content", [{}])[0].get("rates", [])
        return [CandleData.from_mt5_dict(data) for data in rates_data]
    
    async def market_book_add(self, symbol: str) -> bool:
        """Adicionar símbolo ao Market Book (DOM)"""
        result = await self._mcp_client.call_tool("market_book_add", {"symbol": symbol})
        return result.get("content", [{}])[0].get("result", False)
    
    async def market_book_get(self, symbol: str) -> List[BookTick]:
        """Obter Market Book (DOM) de um símbolo"""
        result = await self._mcp_client.call_tool("market_book_get", {"symbol": symbol})
        book_data = result.get("content", [{}])[0].get("book", [])
        return [BookTick.from_mt5_dict(data) for data in book_data]
    
    async def market_book_release(self, symbol: str) -> bool:
        """Remover símbolo do Market Book"""
        result = await self._mcp_client.call_tool("market_book_release", {"symbol": symbol})
        return result.get("content", [{}])[0].get("result", False)
    
    # ========== ORDERS & TRADING ==========
    
    async def order_send(
        self,
        symbol: str,
        action: TradeAction,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        deviation: Optional[int] = None,
        order_type: Optional[OrderType] = None,
        type_filling: Optional[str] = None,
        type_time: Optional[str] = None,
        expiration: Optional[datetime] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
        position: Optional[int] = None,
        position_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Enviar ordem de trading
        
        Args:
            symbol: Símbolo para trading
            action: Tipo de ação (buy, sell, etc.)
            volume: Volume da ordem
            price: Preço (para ordens limitadas/stop)
            sl: Stop Loss
            tp: Take Profit
            deviation: Desvio permitido em pontos
            order_type: Tipo da ordem
            type_filling: Tipo de preenchimento
            type_time: Tipo de tempo
            expiration: Data de expiração
            comment: Comentário
            magic: Número mágico
            position: ID da posição
            position_by: ID da posição contrária
            
        Returns:
            Resultado da ordem
        """
        # Validar se conta é demo quando necessário
        if self.demo_only and self._account_info and not self._account_info.is_demo:
            raise TradingError("Trading só é permitido em contas demo")
        
        # Preparar request
        request = {
            "symbol": symbol,
            "action": action.value,
            "volume": volume
        }
        
        # Adicionar parâmetros opcionais
        if price is not None:
            request["price"] = price
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp
        if deviation is not None:
            request["deviation"] = deviation
        if order_type is not None:
            request["type"] = order_type.value
        if type_filling is not None:
            request["type_filling"] = type_filling
        if type_time is not None:
            request["type_time"] = type_time
        if expiration is not None:
            request["expiration"] = expiration.isoformat()
        if comment is not None:
            request["comment"] = comment
        if magic is not None:
            request["magic"] = magic
        if position is not None:
            request["position"] = position
        if position_by is not None:
            request["position_by"] = position_by
        
        result = await self._mcp_client.call_tool("order_send", {"request": request})
        response = result.get("content", [{}])[0]
        
        # Verificar se houve erro
        if response.get("retcode", 0) != 10009:  # TRADE_RETCODE_DONE
            error_msg = response.get("comment", "Erro desconhecido na ordem")
            raise TradingError(f"Falha na ordem: {error_msg}")
        
        return response
    
    async def order_calc_margin(
        self,
        action: TradeAction,
        symbol: str,
        volume: float,
        price: float
    ) -> float:
        """
        Calcular margem necessária para uma ordem
        
        Args:
            action: Ação de trading
            symbol: Símbolo
            volume: Volume
            price: Preço
            
        Returns:
            Margem necessária
        """
        result = await self._mcp_client.call_tool("order_calc_margin", {
            "action": action.value,
            "symbol": symbol,
            "volume": volume,
            "price": price
        })
        
        return result.get("content", [{}])[0].get("margin", 0.0)
    
    async def order_calc_profit(
        self,
        action: TradeAction,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float
    ) -> float:
        """
        Calcular profit de uma ordem
        
        Args:
            action: Ação de trading
            symbol: Símbolo
            volume: Volume
            price_open: Preço de abertura
            price_close: Preço de fechamento
            
        Returns:
            Profit calculado
        """
        result = await self._mcp_client.call_tool("order_calc_profit", {
            "action": action.value,
            "symbol": symbol,
            "volume": volume,
            "price_open": price_open,
            "price_close": price_close
        })
        
        return result.get("content", [{}])[0].get("profit", 0.0)
    
    async def order_check(
        self,
        symbol: str,
        action: TradeAction,
        volume: float,
        price: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Verificar ordem antes de enviar
        
        Args:
            symbol: Símbolo
            action: Ação
            volume: Volume
            price: Preço
            **kwargs: Outros parâmetros da ordem
            
        Returns:
            Resultado da verificação
        """
        request = {
            "symbol": symbol,
            "action": action.value,
            "volume": volume
        }
        
        if price is not None:
            request["price"] = price
        
        request.update(kwargs)
        
        result = await self._mcp_client.call_tool("order_check", {"request": request})
        return result.get("content", [{}])[0]
    
    async def orders_get(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> List[OrderInfo]:
        """
        Obter ordens ativas
        
        Args:
            symbol: Filtrar por símbolo
            ticket: Obter ordem específica
            
        Returns:
            Lista de ordens
        """
        args = {}
        if symbol:
            args["symbol"] = symbol
        if ticket:
            args["ticket"] = ticket
        
        result = await self._mcp_client.call_tool("orders_get", args if args else None)
        orders_data = result.get("content", [{}])[0].get("orders", [])
        return [OrderInfo.from_mt5_dict(data) for data in orders_data]
    
    async def orders_total(self) -> int:
        """Obter total de ordens ativas"""
        result = await self._mcp_client.call_tool("orders_total")
        return result.get("content", [{}])[0].get("total", 0)
    
    # ========== POSITIONS ==========
    
    async def positions_get(self, symbol: Optional[str] = None, ticket: Optional[int] = None) -> List[PositionInfo]:
        """
        Obter posições abertas
        
        Args:
            symbol: Filtrar por símbolo
            ticket: Obter posição específica
            
        Returns:
            Lista de posições
        """
        args = {}
        if symbol:
            args["symbol"] = symbol
        if ticket:
            args["ticket"] = ticket
        
        result = await self._mcp_client.call_tool("positions_get", args if args else None)
        positions_data = result.get("content", [{}])[0].get("positions", [])
        return [PositionInfo.from_mt5_dict(data) for data in positions_data]
    
    async def positions_total(self) -> int:
        """Obter total de posições abertas"""
        result = await self._mcp_client.call_tool("positions_total")
        return result.get("content", [{}])[0].get("total", 0)
    
    # ========== HISTORY ==========
    
    async def history_orders_get(
        self,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date],
        group: Optional[str] = None,
        ticket: Optional[int] = None,
        position: Optional[int] = None
    ) -> List[OrderInfo]:
        """
        Obter ordens do histórico
        
        Args:
            date_from: Data inicial
            date_to: Data final
            group: Filtro de grupo
            ticket: Ticket específico
            position: Posição específica
            
        Returns:
            Lista de ordens históricas
        """
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        args = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        
        if group:
            args["group"] = group
        if ticket:
            args["ticket"] = ticket
        if position:
            args["position"] = position
        
        result = await self._mcp_client.call_tool("history_orders_get", args)
        orders_data = result.get("content", [{}])[0].get("orders", [])
        return [OrderInfo.from_mt5_dict(data) for data in orders_data]
    
    async def history_orders_total(
        self,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date]
    ) -> int:
        """Obter total de ordens no histórico"""
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        result = await self._mcp_client.call_tool("history_orders_total", {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        })
        return result.get("content", [{}])[0].get("total", 0)
    
    async def history_deals_get(
        self,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date],
        group: Optional[str] = None,
        ticket: Optional[int] = None,
        position: Optional[int] = None
    ) -> List[TradeInfo]:
        """
        Obter negociações do histórico
        
        Args:
            date_from: Data inicial
            date_to: Data final
            group: Filtro de grupo
            ticket: Ticket específico
            position: Posição específica
            
        Returns:
            Lista de negociações
        """
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        args = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        }
        
        if group:
            args["group"] = group
        if ticket:
            args["ticket"] = ticket
        if position:
            args["position"] = position
        
        result = await self._mcp_client.call_tool("history_deals_get", args)
        deals_data = result.get("content", [{}])[0].get("deals", [])
        return [TradeInfo.from_mt5_dict(data) for data in deals_data]
    
    async def history_deals_total(
        self,
        date_from: Union[datetime, date],
        date_to: Union[datetime, date]
    ) -> int:
        """Obter total de negociações no histórico"""
        if isinstance(date_from, date):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, date):
            date_to = datetime.combine(date_to, datetime.max.time())
        
        result = await self._mcp_client.call_tool("history_deals_total", {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat()
        })
        return result.get("content", [{}])[0].get("total", 0)
    
    # ========== UTILITY METHODS ==========
    
    async def get_last_error(self) -> int:
        """Obter último código de erro"""
        result = await self._mcp_client.call_tool("last_error")
        return result.get("content", [{}])[0].get("error", 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do cliente"""
        return {
            **self._mcp_client.get_stats(),
            "account_info": self._account_info.model_dump() if self._account_info else None,
            "symbols_cached": len(self._symbols_cache),
            "demo_only": self.demo_only
        }
    
    @property
    def is_connected(self) -> bool:
        """Verificar se está conectado"""
        return self._mcp_client.is_connected
    
    @property
    def account_info(self) -> Optional[AccountInfo]:
        """Informações da conta"""
        return self._account_info
    
    # ========== HELPER METHODS ==========
    
    async def buy(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Abrir posição de compra (market order)"""
        return await self.order_send(
            symbol=symbol,
            action=TradeAction.BUY,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=comment or "Buy order"
        )
    
    async def sell(
        self,
        symbol: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Abrir posição de venda (market order)"""
        return await self.order_send(
            symbol=symbol,
            action=TradeAction.SELL,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=comment or "Sell order"
        )
    
    async def close_position(self, position_id: int, comment: Optional[str] = None) -> Dict[str, Any]:
        """Fechar posição por ID"""
        positions = await self.positions_get(ticket=position_id)
        
        if not positions:
            raise TradingError(f"Posição {position_id} não encontrada")
        
        position = positions[0]
        
        # Determinar ação contrária
        close_action = TradeAction.SELL if position.type == 0 else TradeAction.BUY  # 0 = buy, 1 = sell
        
        return await self.order_send(
            symbol=position.symbol,
            action=close_action,
            volume=position.volume,
            position=position_id,
            comment=comment or f"Close position {position_id}"
        )
    
    async def close_all_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fechar todas as posições (opcionalmente filtradas por símbolo)"""
        positions = await self.positions_get(symbol=symbol)
        results = []
        
        for position in positions:
            try:
                result = await self.close_position(
                    position.ticket,
                    f"Close all positions - {position.symbol}"
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Erro ao fechar posição {position.ticket}: {e}")
                results.append({"error": str(e), "ticket": position.ticket})
        
        return results
    
    async def ping_server(self) -> float:
        """Testar latência com servidor"""
        return await self._mcp_client.ping()
