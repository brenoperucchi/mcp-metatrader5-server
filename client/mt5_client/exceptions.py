"""
Exceções customizadas para o cliente MT5 MCP
"""

from typing import Optional, Dict, Any


class MT5ClientError(Exception):
    """Exceção base para erros do cliente MT5"""
    
    def __init__(self, message: str, error_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConnectionError(MT5ClientError):
    """Erro de conexão com o servidor MCP"""
    pass


class AuthenticationError(MT5ClientError):
    """Erro de autenticação"""
    pass


class TimeoutError(MT5ClientError):
    """Erro de timeout"""
    pass


class MCPError(MT5ClientError):
    """Erro específico do protocolo MCP"""
    
    def __init__(self, message: str, mcp_error_code: Optional[int] = None, mcp_error_data: Optional[Dict[str, Any]] = None):
        self.mcp_error_code = mcp_error_code
        self.mcp_error_data = mcp_error_data or {}
        super().__init__(message, mcp_error_code, mcp_error_data)


class MT5Error(MT5ClientError):
    """Erro específico do MetaTrader 5"""
    
    # Códigos de erro comuns do MT5
    MT5_ERROR_CODES = {
        0: "Success",
        1: "No error returned",
        2: "Common error",
        3: "Invalid trade parameters",
        4: "Trade server is busy",
        5: "Old version of the client terminal",
        6: "No connection with trade server",
        7: "Not enough rights",
        8: "Too frequent requests",
        9: "Malfunctioning trade operation",
        10: "Account disabled",
        11: "Invalid account",
        64: "Account disabled",
        65: "Invalid account",
        128: "Trade timeout",
        129: "Invalid price",
        130: "Invalid stops",
        131: "Invalid trade volume",
        132: "Market is closed",
        133: "Trade is disabled",
        134: "Not enough money",
        135: "Price changed",
        136: "Off quotes",
        137: "Broker is busy",
        138: "Requote",
        139: "Order is locked",
        140: "Long positions only allowed",
        141: "Too many requests",
        145: "Modification denied because order too close to market",
        146: "Trade context is busy",
        147: "Expirations are denied by broker",
        148: "Amount of open and pending orders has reached the limit",
        149: "Hedging is prohibited",
        150: "Prohibited by FIFO rules",
        10004: "Requote",
        10006: "Request rejected",
        10007: "Request canceled by trader",
        10008: "Order placed",
        10009: "Request completed",
        10010: "Only part of the request was completed",
        10011: "Request processing error",
        10012: "Request canceled by timeout",
        10013: "Invalid request",
        10014: "Invalid volume in the request",
        10015: "Invalid price in the request",
        10016: "Invalid stops in the request",
        10017: "Trade is disabled",
        10018: "Market is closed",
        10019: "There is not enough money to complete the request",
        10020: "Prices changed",
        10021: "There are no quotes to process the request",
        10022: "Invalid order expiration date in the request",
        10023: "Order state changed",
        10024: "Too frequent requests",
        10025: "No changes in request",
        10026: "Autotrading disabled by server",
        10027: "Autotrading disabled by client terminal",
        10028: "Request locked for processing",
        10029: "Order or position frozen",
        10030: "Invalid order filling type",
        10031: "No connection with the trade server",
        10032: "Operation is allowed only for live accounts",
        10033: "The number of pending orders has reached the limit",
        10034: "The volume of orders and positions for the symbol has reached the limit",
        10035: "Incorrect or prohibited order type",
        10036: "Position with the specified POSITION_IDENTIFIER has already been closed"
    }
    
    def __init__(self, message: str, mt5_error_code: Optional[int] = None):
        self.mt5_error_code = mt5_error_code
        
        # Enriquecer mensagem com descrição do erro MT5
        if mt5_error_code and mt5_error_code in self.MT5_ERROR_CODES:
            mt5_description = self.MT5_ERROR_CODES[mt5_error_code]
            enhanced_message = f"{message} (MT5: {mt5_description})"
        else:
            enhanced_message = message
            
        super().__init__(enhanced_message, mt5_error_code)


class TradingError(MT5Error):
    """Erro específico de operações de trading"""
    pass


class MarketDataError(MT5Error):
    """Erro específico de dados de mercado"""
    pass


class ConfigurationError(MT5ClientError):
    """Erro de configuração"""
    pass


class ValidationError(MT5ClientError):
    """Erro de validação de dados"""
    pass


class DemoAccountError(MT5ClientError):
    """Erro relacionado à validação de conta demo"""
    pass


class RetryError(MT5ClientError):
    """Erro após esgotar tentativas de retry"""
    
    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        self.attempts = attempts
        self.last_error = last_error
        enhanced_message = f"{message} (após {attempts} tentativas)"
        if last_error:
            enhanced_message += f": {str(last_error)}"
        super().__init__(enhanced_message)


class SymbolError(MarketDataError):
    """Erro relacionado a símbolos"""
    pass


class OrderError(TradingError):
    """Erro relacionado a ordens"""
    pass


class PositionError(TradingError):
    """Erro relacionado a posições"""
    pass
