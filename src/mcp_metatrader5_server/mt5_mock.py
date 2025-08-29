"""
Mock do MetaTrader5 para desenvolvimento em ambiente Linux/WSL
"""

import time
import random
from datetime import datetime

class MockMT5:
    """Mock da biblioteca MetaTrader5 para desenvolvimento"""
    
    # Constants
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_MODIFY = 7
    TRADE_ACTION_REMOVE = 8
    
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 2
    
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    
    # Constantes para copy_ticks
    COPY_TICKS_ALL = 0
    COPY_TICKS_INFO = 1
    COPY_TICKS_TRADE = 2
    
    def __init__(self):
        self.initialized = False
        self.last_error_code = 0
        
    def initialize(self, path=None, login=None, password=None, server=None, timeout=None, portable=False):
        """Mock initialize"""
        print(f"🔄 [MOCK] MT5 initialize(path={path}, portable={portable})")
        self.initialized = True
        return True
        
    def shutdown(self):
        """Mock shutdown"""
        print("🔄 [MOCK] MT5 shutdown()")
        self.initialized = False
        
    def login(self, login, password, server):
        """Mock login"""
        print(f"🔄 [MOCK] MT5 login({login}, ***, {server})")
        return True
        
    def terminal_info(self):
        """Mock terminal info"""
        class TerminalInfo:
            def __init__(self):
                self.name = "MetaTrader 5 (Mock)"
                self.path = "/mock/mt5"
                self.data_path = "/mock/data"
                self.commondata_path = "/mock/common"
                self.language = 1033  # English
                self.company = "Mock Company"
                self.build = 4000
                self.maxbars = 100000
                self.codepage = 1252
            
            def _asdict(self):
                return {
                    'name': self.name,
                    'path': self.path,
                    'data_path': self.data_path,
                    'commondata_path': self.commondata_path,
                    'language': self.language,
                    'company': self.company,
                    'build': self.build,
                    'maxbars': self.maxbars,
                    'codepage': self.codepage
                }
                
        return TerminalInfo()
        
    def account_info(self):
        """Mock account info"""
        from collections import namedtuple
        
        AccountInfo = namedtuple('AccountInfo', [
            'login', 'trade_mode', 'leverage', 'limit_orders', 'margin_so_mode',
            'trade_allowed', 'trade_expert', 'margin_mode', 'currency_digits', 
            'fifo_close', 'balance', 'credit', 'profit', 'equity', 'margin', 
            'margin_free', 'margin_level', 'margin_so_call', 'margin_so_so',
            'margin_initial', 'margin_maintenance', 'assets', 'liabilities',
            'commission_blocked', 'name', 'server', 'currency', 'company'
        ])
        
        return AccountInfo(
            login=123456789,
            trade_mode=0,  # Demo
            leverage=100,
            limit_orders=200,
            margin_so_mode=0,
            trade_allowed=True,
            trade_expert=True,
            margin_mode=0,
            currency_digits=2,
            fifo_close=False,
            balance=10000.0,
            credit=0.0,
            profit=125.50,
            equity=10125.50,
            margin=0.0,
            margin_free=10125.50,
            margin_level=0.0,
            margin_so_call=0.0,
            margin_so_so=0.0,
            margin_initial=0.0,
            margin_maintenance=0.0,
            assets=10125.50,
            liabilities=0.0,
            commission_blocked=0.0,
            name="Mock Account",
            server="Mock-Server",
            currency="USD",
            company="Mock Broker"
        )
        
    def symbols_total(self):
        """Mock symbols total"""
        return 1000
        
    def symbols_get(self, group="*"):
        """Mock symbols get"""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "PETR4", "ITSA4", "VALE3"]
        
        class SymbolInfo:
            def __init__(self, symbol):
                self.name = symbol
                self.description = f"Mock {symbol}"
                self.path = f"Mock\\{symbol}"
                self.country = "Mock"
                self.sector = "Mock"
                self.industry = "Mock"
                self.currency_base = symbol[:3] if len(symbol) > 3 else symbol
                self.currency_profit = symbol[3:] if len(symbol) > 3 else "USD"
                self.currency_margin = symbol[3:] if len(symbol) > 3 else "USD"
                self.digits = 5 if "USD" in symbol else 2
                self.point = 0.00001 if "USD" in symbol else 0.01
                self.spread = 2
                self.trade_contract_size = 100000.0 if "USD" in symbol else 1.0
                
        return [SymbolInfo(s) for s in symbols]
        
    def symbol_info(self, symbol):
        """Mock symbol info"""
        # Support for ITSA3 and ITSA4 specifically
        if symbol in ["ITSA3", "ITSA4"]:
            base_price = 31.04 if symbol == "ITSA4" else 30.87
            
            class SymbolInfo:
                def __init__(self):
                    self.name = symbol
                    self.description = f"ITAUSA PN ({symbol})"
                    self.point = 0.01
                    self.digits = 2
                    self.spread = 2
                    self.trade_contract_size = 1.0
                    self.bid = base_price
                    self.ask = base_price + 0.02
                    self.last = base_price + 0.01
                    self.volume = random.randint(1000, 10000)
                    self.time = int(time.time())
                
                def _asdict(self):
                    return {
                        'name': self.name,
                        'description': self.description,
                        'point': self.point,
                        'digits': self.digits,
                        'spread': self.spread,
                        'trade_contract_size': self.trade_contract_size,
                        'bid': self.bid,
                        'ask': self.ask,
                        'last': self.last,
                        'volume': self.volume,
                        'time': self.time
                    }
                    
            return SymbolInfo()
        else:
            # Generic symbol handling
            class SymbolInfo:
                def __init__(self):
                    self.name = symbol
                    self.description = f"Mock {symbol}"
                    self.point = 0.01 if symbol.endswith("4") else 0.00001
                    self.digits = 2 if symbol.endswith("4") else 5
                    self.spread = 2
                    self.trade_contract_size = 1.0 if symbol.endswith("4") else 100000.0
                    self.bid = 31.04 if symbol.endswith("4") else 1.08950
                    self.ask = 31.06 if symbol.endswith("4") else 1.08970
                    self.last = 31.05 if symbol.endswith("4") else 1.08960
                    self.volume = random.randint(1000, 10000)
                    self.time = int(time.time())
                
                def _asdict(self):
                    return vars(self)
                    
            return SymbolInfo()
        
    def symbol_info_tick(self, symbol):
        """Mock symbol tick"""
        # Support for ITSA3 and ITSA4 specifically
        if symbol in ["ITSA3", "ITSA4"]:
            base_price = 31.04 if symbol == "ITSA4" else 30.87
            
            class TickInfo:
                def __init__(self):
                    self.time = int(time.time())
                    self.bid = base_price
                    self.ask = base_price + 0.02
                    self.last = base_price + 0.01
                    self.volume = random.randint(100, 1000)
                    self.time_msc = int(time.time() * 1000)
                    self.flags = 6
                    self.volume_real = float(self.volume)
                
                def _asdict(self):
                    return {
                        'time': self.time,
                        'bid': self.bid,
                        'ask': self.ask,
                        'last': self.last,
                        'volume': self.volume,
                        'time_msc': self.time_msc,
                        'flags': self.flags,
                        'volume_real': self.volume_real
                    }
                    
            return TickInfo()
        else:
            # Generic symbol handling
            class TickInfo:
                def __init__(self):
                    self.time = int(time.time())
                    self.bid = 31.04 if symbol.endswith("4") else 1.08950
                    self.ask = 31.06 if symbol.endswith("4") else 1.08970
                    self.last = 31.05 if symbol.endswith("4") else 1.08960
                    self.volume = random.randint(100, 1000)
                    self.time_msc = int(time.time() * 1000)
                    self.flags = 6
                    self.volume_real = float(self.volume)
                
                def _asdict(self):
                    return vars(self)
                    
            return TickInfo()
        
    def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        """Mock rates"""
        import numpy as np
        
        # Gerar dados mock
        base_time = int(time.time())
        base_price = 31.05 if symbol.endswith("4") else 1.08960
        
        rates = []
        for i in range(count):
            # Variação de preço simulada
            variation = random.uniform(-0.02, 0.02)
            price = base_price + variation
            
            rate_tuple = (
                base_time - (count - i) * timeframe * 60,  # time
                price - random.uniform(0, 0.01),  # open
                price + random.uniform(0, 0.01),  # high
                price - random.uniform(0, 0.01),  # low
                price,  # close
                random.randint(100, 1000),  # tick_volume
                random.randint(1, 5),  # spread
                random.randint(100, 1000),  # real_volume
            )
            rates.append(rate_tuple)
            
        return np.array(rates, dtype=[
            ('time', 'u8'),
            ('open', 'f8'),
            ('high', 'f8'), 
            ('low', 'f8'),
            ('close', 'f8'),
            ('tick_volume', 'u8'),
            ('spread', 'i4'),
            ('real_volume', 'u8')
        ])
        
    def copy_ticks_from_pos(self, symbol, start_pos, count):
        """Mock ticks"""
        import numpy as np
        
        base_time = int(time.time())
        base_price = 31.05 if symbol.endswith("4") else 1.08960
        
        ticks = []
        for i in range(count):
            variation = random.uniform(-0.01, 0.01)
            bid = base_price + variation
            ask = bid + random.uniform(0.001, 0.005)
            
            tick_tuple = (
                base_time - (count - i) * 60,  # time
                bid,  # bid
                ask,  # ask
                bid + random.uniform(0, ask-bid),  # last
                random.randint(1, 100),  # volume
                int((base_time - (count - i) * 60) * 1000),  # time_msc
                6,  # flags
                float(random.randint(1, 100))  # volume_real
            )
            ticks.append(tick_tuple)
            
        return np.array(ticks, dtype=[
            ('time', 'u8'),
            ('bid', 'f8'),
            ('ask', 'f8'),
            ('last', 'f8'),
            ('volume', 'u8'),
            ('time_msc', 'u8'),
            ('flags', 'u4'),
            ('volume_real', 'f8')
        ])
        
    def positions_get(self, symbol=None, group=None, ticket=None):
        """Mock positions"""
        # Retornar lista vazia (sem posições abertas)
        return ()
        
    def orders_get(self, symbol=None, group=None, ticket=None):
        """Mock orders"""
        # Retornar lista vazia (sem ordens pendentes)
        return ()
        
    def order_send(self, request):
        """Mock order send"""
        class OrderResult:
            def __init__(self):
                self.retcode = 10009  # TRADE_RETCODE_DONE
                self.deal = random.randint(1000000, 9999999)
                self.order = random.randint(1000000, 9999999)
                self.volume = request.get('volume', 0.01)
                self.price = request.get('price', 1.0)
                self.bid = self.price - 0.00010
                self.ask = self.price + 0.00010
                self.comment = "Mock order"
                self.request_id = random.randint(1, 999999)
                self.retcode_external = 0
                
        print(f"🔄 [MOCK] Order sent: {request}")
        return OrderResult()
        
    def order_check(self, request):
        """Mock order check"""
        class CheckResult:
            def __init__(self):
                self.retcode = 10009  # TRADE_RETCODE_DONE
                self.balance = 10000.0
                self.equity = 10125.50
                self.profit = 125.50
                self.margin = 0.0
                self.margin_free = 10125.50
                self.margin_level = 0.0
                self.comment = "Mock check OK"
                self.request = request  # Include the original request
                
            def _asdict(self):
                return {
                    'retcode': self.retcode,
                    'balance': self.balance,
                    'equity': self.equity,
                    'profit': self.profit,
                    'margin': self.margin,
                    'margin_free': self.margin_free,
                    'margin_level': self.margin_level,
                    'comment': self.comment,
                    'request': self.request
                }
                
        return CheckResult()
        
    def last_error(self):
        """Mock last error"""
        return (self.last_error_code, "Mock: No error" if self.last_error_code == 0 else "Mock error")
    
    def history_orders_get(self, **kwargs):
        """Mock history orders"""
        # Retornar lista vazia (sem ordens históricas)
        return ()
        
    def history_deals_get(self, **kwargs):
        """Mock history deals"""
        # Retornar lista vazia (sem deals históricos)
        return ()
    
    # Constantes adicionais necessárias
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_CONTEST = 1  
    ACCOUNT_TRADE_MODE_REAL = 2
    
    TRADE_ACTION_SLTP = 2
    TRADE_ACTION_CLOSE_BY = 10
    
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7
    ORDER_TYPE_CLOSE_BY = 8
    
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    
    ORDER_TIME_GTC = 0
    ORDER_TIME_DAY = 1  
    ORDER_TIME_SPECIFIED = 2
    ORDER_TIME_SPECIFIED_DAY = 3
        
    def market_book_add(self, symbol):
        """Mock market book add"""
        return True
        
    def market_book_get(self, symbol):
        """Mock market book get"""
        class BookItem:
            def __init__(self, type_, price, volume):
                self.type = type_  # 0=buy, 1=sell
                self.price = price
                self.volume = volume
                self.volume_real = float(volume)
                
        base_price = 31.05 if symbol.endswith("4") else 1.08960
        
        return [
            BookItem(0, base_price - 0.01, 1000),  # Buy
            BookItem(0, base_price - 0.02, 1500),
            BookItem(1, base_price + 0.01, 1200),  # Sell
            BookItem(1, base_price + 0.02, 800),
        ]
        
    def market_book_release(self, symbol):
        """Mock market book release"""
        return True
    
    def symbol_select(self, symbol, visible=True):
        """Mock symbol select"""
        print(f"🔄 [MOCK] Symbol select: {symbol}, visible={visible}")
        return True

# Instância global do mock
mt5_mock = MockMT5()

# Exportar todas as funções e constantes para compatibilidade
initialize = mt5_mock.initialize
shutdown = mt5_mock.shutdown
login = mt5_mock.login
terminal_info = mt5_mock.terminal_info
account_info = mt5_mock.account_info
symbols_total = mt5_mock.symbols_total
symbols_get = mt5_mock.symbols_get
symbol_info = mt5_mock.symbol_info
symbol_info_tick = mt5_mock.symbol_info_tick
symbol_select = mt5_mock.symbol_select
copy_rates_from_pos = mt5_mock.copy_rates_from_pos
copy_ticks_from_pos = mt5_mock.copy_ticks_from_pos
positions_get = mt5_mock.positions_get
orders_get = mt5_mock.orders_get
order_send = mt5_mock.order_send
order_check = mt5_mock.order_check
last_error = mt5_mock.last_error
market_book_add = mt5_mock.market_book_add
market_book_get = mt5_mock.market_book_get
market_book_release = mt5_mock.market_book_release
history_orders_get = mt5_mock.history_orders_get
history_deals_get = mt5_mock.history_deals_get

# Export constants
TRADE_ACTION_DEAL = MockMT5.TRADE_ACTION_DEAL
TRADE_ACTION_PENDING = MockMT5.TRADE_ACTION_PENDING
TRADE_ACTION_MODIFY = MockMT5.TRADE_ACTION_MODIFY
TRADE_ACTION_REMOVE = MockMT5.TRADE_ACTION_REMOVE
TRADE_ACTION_SLTP = MockMT5.TRADE_ACTION_SLTP
TRADE_ACTION_CLOSE_BY = MockMT5.TRADE_ACTION_CLOSE_BY

ORDER_TYPE_BUY = MockMT5.ORDER_TYPE_BUY
ORDER_TYPE_SELL = MockMT5.ORDER_TYPE_SELL
ORDER_TYPE_BUY_LIMIT = MockMT5.ORDER_TYPE_BUY_LIMIT
ORDER_TYPE_SELL_LIMIT = MockMT5.ORDER_TYPE_SELL_LIMIT
ORDER_TYPE_BUY_STOP = MockMT5.ORDER_TYPE_BUY_STOP
ORDER_TYPE_SELL_STOP = MockMT5.ORDER_TYPE_SELL_STOP
ORDER_TYPE_BUY_STOP_LIMIT = MockMT5.ORDER_TYPE_BUY_STOP_LIMIT
ORDER_TYPE_SELL_STOP_LIMIT = MockMT5.ORDER_TYPE_SELL_STOP_LIMIT
ORDER_TYPE_CLOSE_BY = MockMT5.ORDER_TYPE_CLOSE_BY

ORDER_TIME_GTC = MockMT5.ORDER_TIME_GTC
ORDER_TIME_DAY = MockMT5.ORDER_TIME_DAY
ORDER_TIME_SPECIFIED = MockMT5.ORDER_TIME_SPECIFIED
ORDER_TIME_SPECIFIED_DAY = MockMT5.ORDER_TIME_SPECIFIED_DAY

ORDER_FILLING_FOK = MockMT5.ORDER_FILLING_FOK
ORDER_FILLING_IOC = MockMT5.ORDER_FILLING_IOC
ORDER_FILLING_RETURN = MockMT5.ORDER_FILLING_RETURN

ACCOUNT_TRADE_MODE_DEMO = MockMT5.ACCOUNT_TRADE_MODE_DEMO
ACCOUNT_TRADE_MODE_CONTEST = MockMT5.ACCOUNT_TRADE_MODE_CONTEST
ACCOUNT_TRADE_MODE_REAL = MockMT5.ACCOUNT_TRADE_MODE_REAL

TIMEFRAME_M1 = MockMT5.TIMEFRAME_M1
TIMEFRAME_M5 = MockMT5.TIMEFRAME_M5
TIMEFRAME_M15 = MockMT5.TIMEFRAME_M15
TIMEFRAME_M30 = MockMT5.TIMEFRAME_M30
TIMEFRAME_H1 = MockMT5.TIMEFRAME_H1
TIMEFRAME_H4 = MockMT5.TIMEFRAME_H4
TIMEFRAME_D1 = MockMT5.TIMEFRAME_D1

COPY_TICKS_ALL = MockMT5.COPY_TICKS_ALL
COPY_TICKS_INFO = MockMT5.COPY_TICKS_INFO
COPY_TICKS_TRADE = MockMT5.COPY_TICKS_TRADE