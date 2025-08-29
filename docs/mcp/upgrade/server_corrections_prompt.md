# 🔧 PROMPT PARA CORREÇÃO DO SERVIDOR MCP MT5

**Objetivo:** Transformar o servidor HTTP/JSON-RPC atual em um servidor MCP compliant para suportar a ETAPA 2 - Decisão de Swap.

---

## 📋 ESPECIFICAÇÕES TÉCNICAS COMPLETAS

### 1. **PROTOCOLO MCP - IMPLEMENTAÇÃO OBRIGATÓRIA**

O servidor atual **NÃO implementa o padrão MCP**. Você deve adicionar:

#### 1.1 Suporte ao método `tools/call`
```python
def handle_tools_call(self, params):
    """
    Implementa o método tools/call conforme especificação MCP
    
    Input:
    {
        "name": "get_account_info",
        "arguments": {}
    }
    
    Output:
    {
        "content": [
            {
                "type": "text", 
                "text": "JSON stringified result"
            }
        ]
    }
    """
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    # Mapear para método interno existente
    if tool_name == "get_account_info":
        result = self.mt5_get_account_info()
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result)
                }
            ]
        }
    
    # Repetir para todas as 34 ferramentas...
```

#### 1.2 Estrutura de resposta MCP
```python
# ATUAL (INCORRETO):
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {...}
}

# DEVE SER (MCP COMPLIANT):
{
    "jsonrpc": "2.0", 
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "JSON stringified data"
            }
        ]
    }
}
```

### 2. **FERRAMENTAS CRÍTICAS PARA ETAPA 2**

Estas ferramentas devem funcionar perfeitamente via `tools/call`:

#### 2.1 **Cotações e Market Data**
```python
# get_symbol_info
params: {"symbol": "ITSA3"}
response: {
    "bid": 8.45,
    "ask": 8.47, 
    "last": 8.46,
    "volume": 15420,
    "time": "2025-01-25T10:30:00.000Z"
}

# get_symbol_info_tick  
params: {"symbol": "ITSA4"}
response: {
    "bid": 9.18,
    "ask": 9.20,
    "last": 9.19, 
    "volume": 8750,
    "time": "2025-01-25T10:30:01.000Z"
}

# copy_book_levels (Level 2)
params: {"symbol": "ITSA3", "depth": 5}
response: {
    "bids": [
        {"price": 8.45, "volume": 1000},
        {"price": 8.44, "volume": 2500}
    ],
    "asks": [
        {"price": 8.47, "volume": 800},
        {"price": 8.48, "volume": 1200}
    ]
}
```

#### 2.2 **Execução de Ordens**
```python
# order_send
params: {
    "request": {
        "action": "TRADE_ACTION_DEAL",
        "symbol": "ITSA3",
        "volume": 100,
        "type": "ORDER_TYPE_BUY", 
        "price": 8.46,
        "sl": 8.20,
        "tp": 8.70,
        "comment": "Swap ITSA3->ITSA4",
        "magic": 12345
    }
}
response: {
    "retcode": 10009,  # TRADE_RETCODE_DONE
    "deal": 123456789,
    "order": 987654321, 
    "volume": 100,
    "price": 8.46,
    "bid": 8.45,
    "ask": 8.47,
    "comment": "Executed successfully"
}

# order_check (validação antes de enviar)
params: {"request": {...}}
response: {
    "retcode": 0,
    "balance": 95420.50,
    "equity": 95420.50, 
    "profit": 0.0,
    "margin": 2538.00,
    "margin_free": 92882.50,
    "comment": "Valid order"
}
```

#### 2.3 **Gestão de Posições**
```python
# positions_get
params: {"symbol": "ITSA3"}
response: [
    {
        "ticket": 123456789,
        "symbol": "ITSA3", 
        "volume": 100,
        "type": "POSITION_TYPE_BUY",
        "price_open": 8.46,
        "price_current": 8.48,
        "profit": 2.00,
        "time": "2025-01-25T10:25:00.000Z"
    }
]

# orders_get (ordens pendentes)
params: {}
response: [
    {
        "ticket": 987654321,
        "symbol": "ITSA4",
        "volume": 100, 
        "type": "ORDER_TYPE_BUY_LIMIT",
        "price_open": 9.15,
        "time_setup": "2025-01-25T10:30:00.000Z",
        "state": "ORDER_STATE_PLACED"
    }
]
```

#### 2.4 **Informações de Conta**
```python
# get_account_info
params: {}
response: {
    "login": 123456789,
    "trade_mode": "DEMO", # ou "REAL"
    "balance": 100000.00,
    "equity": 100000.00,
    "margin": 0.00,
    "margin_free": 100000.00,
    "currency": "BRL",
    "server": "XP-Demo",
    "company": "XP Investimentos"
}
```

### 3. **ESTRUTURA DE ERRO PADRONIZADA**

```python
# Quando tool falha:
{
    "jsonrpc": "2.0",
    "id": 1, 
    "result": {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "success": false,
                    "error": {
                        "code": "MT5_ERROR_1",
                        "message": "Symbol ITSA3 not found",
                        "details": "Check if symbol is available in Market Watch"
                    }
                })
            }
        ]
    }
}

# Códigos de erro obrigatórios:
- MT5_NOT_INITIALIZED: Terminal não inicializado
- MT5_SYMBOL_NOT_FOUND: Símbolo não encontrado
- MT5_INSUFFICIENT_FUNDS: Margem insuficiente  
- MT5_TRADE_DISABLED: Trading desabilitado
- MT5_INVALID_REQUEST: Parâmetros inválidos
- MT5_CONNECTION_LOST: Conexão perdida
- MT5_TIMEOUT: Timeout na operação
```

### 4. **VALIDAÇÕES DE SEGURANÇA**

#### 4.1 **Validação de Conta Demo**
```python
# validate_demo_for_trading
params: {}
response: {
    "is_demo": true,
    "account_type": "DEMO",
    "trading_allowed": true,
    "warning": "Trading operations are in DEMO mode"
}

# CRÍTICO: Bloquear trading em conta REAL durante desenvolvimento
if account_info["trade_mode"] == "REAL" and not explicitly_authorized:
    return error("REAL trading blocked for safety")
```

#### 4.2 **Validação de Símbolos B3**
```python
# Apenas símbolos brasileiros permitidos:
ALLOWED_SYMBOLS = [
    "ITSA3", "ITSA4",  # Itaúsa ON/PN
    "PETR3", "PETR4",  # Petrobras ON/PN  
    "VALE3", "VALE5",  # Vale ON/PNA
    # ... outros pares ON/PN
]

def validate_symbol(symbol):
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError(f"Symbol {symbol} not allowed for arbitrage")
```

### 5. **PERFORMANCE E LATÊNCIA**

#### 5.1 **SLAs Obrigatórios**
```python
# Latências máximas:
- get_symbol_info: < 50ms
- get_symbol_info_tick: < 50ms  
- order_send: < 200ms
- order_check: < 100ms
- positions_get: < 100ms

# Implementar timeout configurável:
DEFAULT_TIMEOUT = 5000  # 5 segundos
```

#### 5.2 **Cache Inteligente**
```python
# Cache cotações por 100ms (10 FPS)
@cache(ttl=0.1) 
def get_symbol_tick_cached(symbol):
    return mt5.symbol_info_tick(symbol)

# Cache posições por 500ms
@cache(ttl=0.5)
def get_positions_cached():
    return mt5.positions_get()
```

### 6. **LOGGING E AUDITORIA**

#### 6.1 **Log Estruturado**
```python
import structlog
logger = structlog.get_logger()

def handle_tools_call(self, params):
    tool_name = params.get("name")
    start_time = time.time()
    
    logger.info("mcp_tool_call", 
        tool=tool_name, 
        params=params,
        session_id=self.session_id
    )
    
    try:
        result = self._execute_tool(tool_name, params)
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info("mcp_tool_success",
            tool=tool_name,
            duration_ms=duration_ms,
            session_id=self.session_id
        )
        
        return result
        
    except Exception as e:
        logger.error("mcp_tool_error",
            tool=tool_name, 
            error=str(e),
            session_id=self.session_id
        )
        raise
```

### 7. **CONFIGURAÇÃO FLEXÍVEL**

#### 7.1 **Arquivo de Configuração**
```yaml
# mcp_server_config.yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

mt5:
  login: 123456789
  password: "demo_password"
  server: "XP-Demo" 
  path: "C:\\Program Files\\XP Investimentos\\MetaTrader 5\\terminal64.exe"

trading:
  demo_only: true
  allowed_symbols: ["ITSA3", "ITSA4", "PETR3", "PETR4"]
  max_volume_per_order: 1000
  
cache:
  quotes_ttl_ms: 100
  positions_ttl_ms: 500
  
timeouts:
  default_ms: 5000
  order_send_ms: 10000
```

### 8. **TRANSPORTE OPCIONAL - SSE**

```python
# Adicionar suporte a Server-Sent Events para streaming
@app.route('/mcp/stream')
async def mcp_stream():
    async def event_generator():
        while True:
            # Stream de cotações em tempo real
            quotes = get_realtime_quotes(["ITSA3", "ITSA4"])
            yield f"data: {json.dumps(quotes)}\n\n"
            await asyncio.sleep(0.1)  # 10 FPS
            
    return Response(event_generator(), mimetype='text/event-stream')
```

---

## ✅ **CHECKLIST DE VALIDAÇÃO**

Após implementação, testar:

### Teste 1: Protocolo MCP
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_account_info", "arguments": {}}}'
```

### Teste 2: Cotações ITSA3/ITSA4
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_symbol_info", "arguments": {"symbol": "ITSA3"}}}'
```

### Teste 3: Validação de Ordem
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "order_check", "arguments": {"request": {"symbol": "ITSA3", "volume": 100, "type": 0}}}}'
```

---

## 🎯 **RESULTADO ESPERADO**

Após implementação:

1. ✅ **tools/call** funcionando para todas as 34 ferramentas
2. ✅ **Cotações ITSA3/ITSA4** retornando bid/ask/last/volume
3. ✅ **order_send/order_check** funcionais em conta demo
4. ✅ **Latência < 200ms** para operações críticas
5. ✅ **Logs estruturados** para auditoria
6. ✅ **Validação de segurança** ativa

**Este servidor corrigido permitirá implementar a ETAPA 2 - Decisão de Swap com segurança e performance adequadas.**