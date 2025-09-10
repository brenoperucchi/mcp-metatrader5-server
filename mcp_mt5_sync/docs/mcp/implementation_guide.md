# 🚀 GUIA DE IMPLEMENTAÇÃO - Correções do Servidor MCP MT5

## 📊 **STATUS ATUAL vs NECESSÁRIO**

| Componente | Status Atual | Necessário | Prioridade |
|------------|--------------|------------|------------|
| **Protocolo MCP** | ❌ Não implementa `tools/call` | ✅ Implementar método `tools/call` | 🔴 CRÍTICA |
| **Ferramentas** | ✅ 41 ferramentas listadas | ✅ Todas funcionais via `tools/call` | 🔴 CRÍTICA |
| **Símbolos B3** | ❌ ITSA3/ITSA4 não acessíveis | ✅ Configurar no Market Watch | 🟡 ALTA |
| **Formato Resposta** | ❌ JSON direto | ✅ MCP format (content array) | 🔴 CRÍTICA |
| **Segurança** | ❓ Não validado | ✅ Validação conta DEMO | 🟡 ALTA |

---

## 🔧 **IMPLEMENTAÇÃO PASSO A PASSO**

### **PASSO 1: Adicionar Método tools/call** (CRÍTICO)

```python
# No servidor MCP, adicionar handler para tools/call
async def handle_request(self, request):
    method = request.get("method")
    params = request.get("params", {})
    
    if method == "tools/call":
        return await self.handle_tools_call(params)
    elif method == "tools/list":
        return self.list_available_tools()
    else:
        return {"error": {"code": -32601, "message": f"Method {method} not found"}}

async def handle_tools_call(self, params):
    """Implementa tools/call conforme padrão MCP"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    # Mapear ferramentas para métodos internos
    tool_map = {
        "initialize": self.mt5_initialize,
        "shutdown": self.mt5_shutdown,
        "login": self.mt5_login,
        "get_account_info": self.mt5_get_account_info,
        "get_terminal_info": self.mt5_get_terminal_info,
        "get_version": self.mt5_get_version,
        "get_symbols": self.mt5_get_symbols,
        "get_symbol_info": self.mt5_get_symbol_info,
        "get_symbol_info_tick": self.mt5_get_symbol_info_tick,
        "order_send": self.mt5_order_send,
        "order_check": self.mt5_order_check,
        "positions_get": self.mt5_positions_get,
        # ... mapear todas as 41 ferramentas
    }
    
    if tool_name not in tool_map:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": f"Tool {tool_name} not found"
                })
            }]
        }
    
    try:
        # Executar ferramenta
        result = await tool_map[tool_name](**arguments)
        
        # Formatar resposta MCP
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "data": result
                })
            }]
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": str(e)
                })
            }]
        }
```

### **PASSO 2: Implementar Ferramentas Críticas**

#### 2.1 Market Data (ITSA3/ITSA4)

```python
async def mt5_get_symbol_info(self, symbol: str):
    """Retorna informações do símbolo"""
    import MetaTrader5 as mt5
    
    # Garantir que símbolo está no Market Watch
    if not mt5.symbol_select(symbol, True):
        raise Exception(f"Failed to select {symbol}")
    
    info = mt5.symbol_info(symbol)
    if info is None:
        raise Exception(f"Symbol {symbol} not found")
    
    tick = mt5.symbol_info_tick(symbol)
    
    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "volume": tick.volume,
        "time": tick.time,
        "spread": info.spread,
        "digits": info.digits
    }
```

#### 2.2 Account Info

```python
async def mt5_get_account_info(self):
    """Retorna informações da conta"""
    import MetaTrader5 as mt5
    
    account = mt5.account_info()
    if account is None:
        raise Exception("Failed to get account info")
    
    return {
        "login": account.login,
        "trade_mode": "DEMO" if account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "margin_free": account.margin_free,
        "currency": account.currency,
        "server": account.server,
        "company": account.company
    }
```

#### 2.3 Order Execution

```python
async def mt5_order_send(self, request: dict):
    """Envia ordem para o MT5"""
    import MetaTrader5 as mt5
    
    # Validar conta DEMO
    account = mt5.account_info()
    if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise Exception("Trading only allowed in DEMO mode during development")
    
    # Preparar requisição
    mt5_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request["symbol"],
        "volume": request["volume"],
        "type": mt5.ORDER_TYPE_BUY if request.get("type") == "buy" else mt5.ORDER_TYPE_SELL,
        "price": request.get("price", 0),
        "sl": request.get("sl", 0),
        "tp": request.get("tp", 0),
        "deviation": 20,
        "magic": 234000,
        "comment": request.get("comment", "MCP Order"),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    
    # Enviar ordem
    result = mt5.order_send(mt5_request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise Exception(f"Order failed: {result.comment}")
    
    return {
        "retcode": result.retcode,
        "deal": result.deal,
        "order": result.order,
        "volume": result.volume,
        "price": result.price,
        "bid": result.bid,
        "ask": result.ask,
        "comment": result.comment
    }
```

### **PASSO 3: Configurar MT5 para B3**

```python
# Ao inicializar MT5
async def mt5_initialize(self):
    """Inicializa MT5 com configuração B3"""
    import MetaTrader5 as mt5
    
    if not mt5.initialize():
        raise Exception("MT5 initialization failed")
    
    # Adicionar símbolos B3 ao Market Watch
    b3_symbols = ["ITSA3", "ITSA4", "PETR3", "PETR4", "VALE3"]
    
    for symbol in b3_symbols:
        if not mt5.symbol_select(symbol, True):
            print(f"Warning: Could not select {symbol}")
    
    return {"success": True, "message": "MT5 initialized with B3 symbols"}
```

### **PASSO 4: Adicionar Cache e Performance**

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedData:
    def __init__(self, data, ttl_ms):
        self.data = data
        self.expiry = datetime.now() + timedelta(milliseconds=ttl_ms)
    
    def is_valid(self):
        return datetime.now() < self.expiry

# Cache para cotações (100ms)
quote_cache = {}

async def mt5_get_symbol_info_cached(self, symbol: str):
    """Versão com cache de get_symbol_info"""
    if symbol in quote_cache:
        cached = quote_cache[symbol]
        if cached.is_valid():
            return cached.data
    
    # Buscar novo dado
    data = await self.mt5_get_symbol_info(symbol)
    quote_cache[symbol] = CachedData(data, ttl_ms=100)
    return data
```

### **PASSO 5: Logging e Monitoramento**

```python
import logging
import time

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

async def handle_tools_call_with_logging(self, params):
    """Versão com logging do handle_tools_call"""
    tool_name = params.get("name")
    start_time = time.time()
    
    logger.info(f"Tool call started: {tool_name}", extra={
        "tool": tool_name,
        "params": params
    })
    
    try:
        result = await self.handle_tools_call(params)
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Tool call success: {tool_name}", extra={
            "tool": tool_name,
            "duration_ms": duration_ms
        })
        
        # Verificar SLA
        sla_limits = {
            "get_symbol_info": 50,
            "get_symbol_info_tick": 50,
            "order_send": 200
        }
        
        if tool_name in sla_limits and duration_ms > sla_limits[tool_name]:
            logger.warning(f"SLA violation: {tool_name} took {duration_ms}ms (limit: {sla_limits[tool_name]}ms)")
        
        return result
        
    except Exception as e:
        logger.error(f"Tool call failed: {tool_name}", extra={
            "tool": tool_name,
            "error": str(e)
        })
        raise
```

---

## 🧪 **TESTES DE VALIDAÇÃO**

### **Teste 1: Verificar tools/call**
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_version", "arguments": {}}}'

# Resposta esperada:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"success\": true, \"data\": {\"version\": \"5.0.36\", \"build\": 3220}}"
    }]
  }
}
```

### **Teste 2: Verificar ITSA3**
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_symbol_info", "arguments": {"symbol": "ITSA3"}}}'

# Resposta esperada:
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"success\": true, \"data\": {\"symbol\": \"ITSA3\", \"bid\": 8.45, \"ask\": 8.47, \"last\": 8.46, \"volume\": 15420}}"
    }]
  }
}
```

### **Teste 3: Verificar Account Info**
```bash
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_account_info", "arguments": {}}}'
```

---

## ✅ **CHECKLIST DE IMPLEMENTAÇÃO**

### **Fase 1: Protocolo MCP** (HOJE)
- [ ] Implementar método `tools/call`
- [ ] Converter formato de resposta para MCP (content array)
- [ ] Mapear todas as 41 ferramentas
- [ ] Adicionar tratamento de erros padronizado

### **Fase 2: Ferramentas Críticas** (HOJE)
- [ ] `get_account_info` funcionando
- [ ] `get_symbol_info` para ITSA3/ITSA4
- [ ] `get_symbol_info_tick` para ITSA3/ITSA4
- [ ] `positions_get` retornando posições

### **Fase 3: Trading** (AMANHÃ)
- [ ] `order_send` com validação DEMO
- [ ] `order_check` validando margem
- [ ] `order_cancel` e `order_modify`
- [ ] `position_modify` para SL/TP

### **Fase 4: Otimizações** (OPCIONAL)
- [ ] Cache de cotações (100ms TTL)
- [ ] Cache de posições (500ms TTL)
- [ ] Logging estruturado
- [ ] Monitoramento de SLAs

---

## 🎯 **COMANDO PARA TESTAR APÓS IMPLEMENTAÇÃO**

```bash
# Script de validação completo
python3 tools/simple_mcp_audit.py

# Se todos os testes passarem, prosseguir para E2.1
```

---

## 📈 **MÉTRICAS DE SUCESSO**

1. **tools/call funcionando**: 41/41 ferramentas respondem
2. **ITSA3/ITSA4 acessíveis**: bid/ask/last retornando valores
3. **Latência adequada**: P95 < 150ms para cotações
4. **Segurança**: Apenas conta DEMO permitida
5. **Logs**: Todas as operações registradas

Com essas correções implementadas, o servidor estará **100% pronto** para a ETAPA 2 - Decisão de Swap!