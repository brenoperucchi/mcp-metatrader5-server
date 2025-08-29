# 🚀 MetaTrader 5 MCP Server - Guia dos Servidores

## 📋 Servidores Disponíveis

### ✅ **`run_fork_mcp.py`** - Servidor STDIO (Principal)
```bash
python run_fork_mcp.py
```
- **Uso:** Claude Desktop (local)
- **Protocolo:** STDIO + JSON-RPC
- **Ferramentas:** 41 MCP tools
- **Status:** ✅ Funcional

### ✅ **`run_http_server.py`** - Servidor HTTP Híbrido
```bash
python run_http_server.py --host 0.0.0.0 --port 8000
```
- **Uso:** REST endpoints + MCP status
- **Protocolo:** HTTP REST + MCP info
- **Ferramentas:** 41 MCP tools info + REST endpoints
- **Endpoints:**
  - `GET /` - Info do servidor
  - `GET /health` - Status de saúde
  - `GET /info` - Detalhes técnicos
  - `GET /config` - Configurações B3/Forex
  - `GET /mcp` - Status MCP + info das tools
- **Status:** ✅ Funcional (REST endpoints)

### ✅ **`run_mcp_only.py`** - Servidor MCP Puro (Claude CLI)
```bash
python run_mcp_only.py --host 0.0.0.0 --port 8001
```
- **Uso:** Claude CLI (remoto MCP puro)
- **Protocolo:** HTTP MCP nativo (FastMCP)
- **Ferramentas:** 41 MCP tools nativas
- **Endpoints:** Protocolo MCP completo
- **Status:** ✅ Funcional (MCP protocolo)

## 🔧 Como Conectar

### Claude Desktop (STDIO):
```json
{
  "mcpServers": {
    "mcp-metatrader5": {
      "command": "python",
      "args": ["run_fork_mcp.py"],
      "cwd": "/caminho/para/fork_mcp"
    }
  }
}
```

### Claude CLI (HTTP):
```bash
# Para MCP puro (recomendado)
claude add mt5 --transport http --url "http://192.168.0.125:8001"

# Para servidor híbrido (REST + MCP info)  
curl http://192.168.0.125:8000/mcp  # Ver status MCP
```

## 🧪 Testes Rápidos

### Testar STDIO:
```bash
python run_fork_mcp.py &
python test_stdio_simple.py
```

### Testar HTTP:
```bash
python run_http_server.py &
curl http://localhost:8000/health
curl http://localhost:8000/info
curl http://localhost:8000/config
```

## ⚡ Correções Aplicadas

### ✅ Datetime (Python 3.13):
- ❌ `datetime.now(datetime.UTC)` 
- ✅ `datetime.now(timezone.utc)`

### ✅ FastMCP Integration:
- ❌ Usar `mcp.http_app()` diretamente (retorna Starlette)
- ✅ Criar FastAPI app + mount MCP app em `/mcp`

### ✅ Imports Completos:
```python
# Garante todas as 41 ferramentas
import mcp_metatrader5_server.market_data  # 16 tools
import mcp_metatrader5_server.trading      # 11 tools
```

## 🎯 Arquivos Finais

| Arquivo | Status | Uso |
|---------|--------|-----|
| `run_fork_mcp.py` | ✅ Principal | STDIO (Claude Desktop) |
| `run_http_server.py` | ✅ Corrigido | HTTP (Claude CLI) |
| ~~outros run_*.py~~ | ❌ Obsoletos | Remover |

## 🔥 41 Ferramentas MCP Disponíveis

### Server (14):
- `initialize`, `shutdown`, `login`, `ping`, `health`
- `get_account_info`, `get_terminal_info`, `get_version`
- `validate_demo_for_trading`, `get_available_configs`
- `get_current_config`, `switch_config`
- `transport_info`, `connection_status`

### Market Data (16):
- `get_symbols`, `get_symbols_by_group`, `get_symbol_info`
- `get_symbol_info_tick`, `symbol_select`
- `copy_rates_from_pos`, `copy_rates_from_date`, `copy_rates_range`
- `copy_ticks_from_pos`, `copy_ticks_from_date`, `copy_ticks_range`
- `get_last_error`, `copy_book_levels`
- `subscribe_market_book`, `unsubscribe_market_book`, `get_book_snapshot`

### Trading (11):
- `order_send`, `order_check`, `order_cancel`, `order_modify`
- `position_modify`, `positions_get`, `positions_get_by_ticket`
- `orders_get`, `orders_get_by_ticket`
- `history_orders_get`, `history_deals_get`

**Total: 41 ferramentas MCP + 4 endpoints REST**