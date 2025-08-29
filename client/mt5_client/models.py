"""
Modelos Pydantic para o cliente MT5 MCP
Baseado nas 37+ ferramentas disponíveis no fork_mcp
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import IntEnum

# Enums para tipos de dados MT5
class TradeAction(IntEnum):
    """Ações de trading disponíveis"""
    DEAL = 1
    PENDING = 5
    SLTP = 6
    MODIFY = 7
    REMOVE = 8
    CLOSE_BY = 10

class OrderType(IntEnum):
    """Tipos de ordem"""
    BUY = 0
    SELL = 1
    BUY_LIMIT = 2
    SELL_LIMIT = 3
    BUY_STOP = 4
    SELL_STOP = 5
    BUY_STOP_LIMIT = 6
    SELL_STOP_LIMIT = 7
    CLOSE_BY = 8

class OrderFilling(IntEnum):
    """Tipos de preenchimento de ordem"""
    FOK = 0  # Fill or Kill
    IOC = 1  # Immediate or Cancel
    RETURN = 2  # Return

class OrderTime(IntEnum):
    """Tipos de tempo de ordem"""
    GTC = 0  # Good Till Cancel
    DAY = 1  # Good Till Day
    SPECIFIED = 2  # Good Till Specified
    SPECIFIED_DAY = 3  # Good Till Specified Day

# Modelos principais
class AccountInfo(BaseModel):
    """Informações da conta de trading"""
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
    
    @property
    def is_demo(self) -> bool:
        """Verifica se a conta é demo"""
        return "demo" in self.server.lower() or self.trade_mode == 0

class SymbolInfo(BaseModel):
    """Informações detalhadas do símbolo"""
    name: str
    description: Optional[str] = None
    path: Optional[str] = None
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
    
    # Campos de tick atuais
    tick_bid: Optional[float] = None
    tick_ask: Optional[float] = None
    tick_last: Optional[float] = None
    tick_time: Optional[int] = None
    tick_volume: Optional[int] = None
    spread_value: Optional[float] = None
    spread_percent: Optional[float] = None

class TickInfo(BaseModel):
    """Informações de tick (cotação atual)"""
    time: int = Field(..., description="Timestamp do tick")
    bid: float = Field(..., description="Preço de compra")
    ask: float = Field(..., description="Preço de venda")
    last: float = Field(..., description="Último preço negociado")
    volume: int = Field(..., description="Volume do tick")
    flags: Optional[int] = Field(None, description="Flags do tick")
    
    @property
    def spread(self) -> float:
        """Calcula o spread"""
        return self.ask - self.bid
    
    @property
    def datetime(self) -> datetime:
        """Converte timestamp para datetime"""
        return datetime.fromtimestamp(self.time)

class RateInfo(BaseModel):
    """Informações de barra/candle"""
    time: int = Field(..., description="Timestamp da barra")
    open: float = Field(..., description="Preço de abertura")
    high: float = Field(..., description="Preço máximo")
    low: float = Field(..., description="Preço mínimo")
    close: float = Field(..., description="Preço de fechamento")
    tick_volume: int = Field(..., description="Volume de ticks")
    spread: Optional[int] = Field(None, description="Spread")
    real_volume: Optional[int] = Field(None, description="Volume real")
    
    @property
    def datetime(self) -> datetime:
        """Converte timestamp para datetime"""
        return datetime.fromtimestamp(self.time)

class OrderRequest(BaseModel):
    """Request para envio de ordem"""
    action: TradeAction = Field(..., description="Ação de trading")
    symbol: str = Field(..., description="Símbolo")
    volume: float = Field(..., description="Volume em lotes")
    type: OrderType = Field(..., description="Tipo de ordem")
    price: float = Field(..., description="Preço da ordem")
    sl: Optional[float] = Field(None, description="Stop Loss")
    tp: Optional[float] = Field(None, description="Take Profit")
    deviation: Optional[int] = Field(None, description="Desvio máximo permitido")
    magic: Optional[int] = Field(None, description="Número mágico")
    comment: Optional[str] = Field(None, description="Comentário")
    type_time: Optional[OrderTime] = Field(None, description="Tipo de tempo")
    type_filling: Optional[OrderFilling] = Field(None, description="Tipo de preenchimento")
    expiration: Optional[int] = Field(None, description="Timestamp de expiração")

class OrderResult(BaseModel):
    """Resultado da execução de ordem"""
    retcode: int = Field(..., description="Código de retorno")
    deal: int = Field(..., description="ID do deal")
    order: int = Field(..., description="ID da ordem")
    volume: float = Field(..., description="Volume executado")
    price: float = Field(..., description="Preço de execução")
    bid: float = Field(..., description="Preço bid no momento")
    ask: float = Field(..., description="Preço ask no momento")
    comment: str = Field(..., description="Comentário do resultado")
    request_id: int = Field(..., description="ID da requisição")
    retcode_external: int = Field(..., description="Código de retorno externo")
    request: Dict[str, Any] = Field(..., description="Requisição original")
    
    @property
    def is_successful(self) -> bool:
        """Verifica se a ordem foi executada com sucesso"""
        return self.retcode == 10009  # TRADE_RETCODE_DONE

class Position(BaseModel):
    """Informações de posição aberta"""
    ticket: int = Field(..., description="Ticket da posição")
    time: int = Field(..., description="Timestamp de abertura")
    time_msc: int = Field(..., description="Timestamp em milissegundos")
    time_update: int = Field(..., description="Timestamp da última atualização")
    time_update_msc: int = Field(..., description="Timestamp de atualização (ms)")
    type: int = Field(..., description="Tipo de posição (0=buy, 1=sell)")
    magic: int = Field(..., description="Número mágico")
    identifier: int = Field(..., description="Identificador da posição")
    reason: int = Field(..., description="Razão de abertura")
    volume: float = Field(..., description="Volume da posição")
    price_open: float = Field(..., description="Preço de abertura")
    sl: float = Field(..., description="Stop Loss")
    tp: float = Field(..., description="Take Profit")
    price_current: float = Field(..., description="Preço atual")
    swap: float = Field(..., description="Swap")
    profit: float = Field(..., description="Lucro atual")
    symbol: str = Field(..., description="Símbolo")
    comment: str = Field(..., description="Comentário")
    external_id: str = Field(..., description="ID externo")
    
    @property
    def is_buy(self) -> bool:
        """Verifica se é posição comprada"""
        return self.type == 0
    
    @property
    def is_sell(self) -> bool:
        """Verifica se é posição vendida"""
        return self.type == 1
    
    @property
    def datetime_open(self) -> datetime:
        """Data/hora de abertura da posição"""
        return datetime.fromtimestamp(self.time)

class Order(BaseModel):
    """Informações de ordem pendente"""
    ticket: int = Field(..., description="Ticket da ordem")
    time_setup: int = Field(..., description="Timestamp de criação")
    time_setup_msc: int = Field(..., description="Timestamp de criação (ms)")
    time_expiration: int = Field(..., description="Timestamp de expiração")
    type: int = Field(..., description="Tipo de ordem")
    type_time: int = Field(..., description="Tipo de tempo")
    type_filling: int = Field(..., description="Tipo de preenchimento")
    state: int = Field(..., description="Estado da ordem")
    magic: int = Field(..., description="Número mágico")
    position_id: int = Field(..., description="ID da posição relacionada")
    position_by_id: int = Field(..., description="ID da posição oposta")
    reason: int = Field(..., description="Razão de criação")
    volume_initial: float = Field(..., description="Volume inicial")
    volume_current: float = Field(..., description="Volume atual")
    price_open: float = Field(..., description="Preço de abertura")
    sl: float = Field(..., description="Stop Loss")
    tp: float = Field(..., description="Take Profit")
    price_current: float = Field(..., description="Preço atual")
    price_stoplimit: float = Field(..., description="Preço stop limit")
    symbol: str = Field(..., description="Símbolo")
    comment: str = Field(..., description="Comentário")
    external_id: str = Field(..., description="ID externo")
    
    @property
    def datetime_setup(self) -> datetime:
        """Data/hora de criação da ordem"""
        return datetime.fromtimestamp(self.time_setup)

class Deal(BaseModel):
    """Informações de deal (transação)"""
    ticket: int = Field(..., description="Ticket do deal")
    order: int = Field(..., description="Ordem relacionada")
    time: int = Field(..., description="Timestamp do deal")
    time_msc: int = Field(..., description="Timestamp (ms)")
    type: int = Field(..., description="Tipo de deal")
    entry: int = Field(..., description="Entrada/saída")
    magic: int = Field(..., description="Número mágico")
    position_id: int = Field(..., description="ID da posição")
    reason: int = Field(..., description="Razão do deal")
    volume: float = Field(..., description="Volume")
    price: float = Field(..., description="Preço")
    commission: float = Field(..., description="Comissão")
    swap: float = Field(..., description="Swap")
    profit: float = Field(..., description="Lucro")
    fee: float = Field(..., description="Taxa")
    symbol: str = Field(..., description="Símbolo")
    comment: str = Field(..., description="Comentário")
    external_id: str = Field(..., description="ID externo")
    
    @property
    def datetime(self) -> datetime:
        """Data/hora do deal"""
        return datetime.fromtimestamp(self.time)

class BookLevel(BaseModel):
    """Nível do book de ofertas (Level 2)"""
    type: int = Field(..., description="Tipo (0=buy, 1=sell)")
    price: float = Field(..., description="Preço")
    volume: int = Field(..., description="Volume")

class BookSnapshot(BaseModel):
    """Snapshot completo do book de ofertas"""
    symbol: str = Field(..., description="Símbolo")
    time: int = Field(..., description="Timestamp")
    bids: List[BookLevel] = Field(..., description="Níveis de compra")
    asks: List[BookLevel] = Field(..., description="Níveis de venda")
    
    @property
    def datetime(self) -> datetime:
        """Data/hora do snapshot"""
        return datetime.fromtimestamp(self.time)

class TerminalInfo(BaseModel):
    """Informações do terminal MT5"""
    community_account: bool
    community_connection: bool
    connected: bool
    dlls_allowed: bool
    trade_allowed: bool
    tradeapi_disabled: bool
    email_enabled: bool
    ftp_enabled: bool
    notifications_enabled: bool
    mqid: bool
    build: int
    maxbars: int
    codepage: int
    ping_last: int
    community_balance: int
    retransmission: float
    company: str
    name: str
    language: int
    path: str
    data_path: str
    commondata_path: str

class ConfigInfo(BaseModel):
    """Informações de configuração (B3/Forex)"""
    name: str = Field(..., description="Nome da configuração")
    description: str = Field(..., description="Descrição")
    symbols: List[str] = Field(..., description="Símbolos disponíveis")
    timeframes: List[int] = Field(..., description="Timeframes suportados")
    market_hours: Dict[str, str] = Field(..., description="Horários de mercado")
    active: bool = Field(False, description="Se está ativa")

# Modelos de resposta para recursos
class TimeframeInfo(BaseModel):
    """Informações sobre timeframes"""
    name: str
    value: int
    description: str

class TickFlagInfo(BaseModel):
    """Informações sobre flags de tick"""
    name: str
    value: int
    description: str

class ErrorInfo(BaseModel):
    """Informações de erro do MT5"""
    code: int = Field(..., description="Código do erro")
    description: str = Field(..., description="Descrição do erro")

# Modelos de resposta MCP
class MCPResponse(BaseModel):
    """Resposta padrão do MCP"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPToolList(BaseModel):
    """Lista de ferramentas MCP"""
    tools: List[Dict[str, Any]]

class MCPResourceList(BaseModel):
    """Lista de recursos MCP"""
    resources: List[Dict[str, Any]]

# Modelos para validação
class DemoValidationResult(BaseModel):
    """Resultado da validação de conta demo"""
    is_demo: bool = Field(..., description="Se a conta é demo")
    account_type: str = Field(..., description="Tipo de conta")
    server: str = Field(..., description="Servidor")
    safe_for_trading: bool = Field(..., description="Se é segura para trading")
    warnings: List[str] = Field(default_factory=list, description="Avisos")
