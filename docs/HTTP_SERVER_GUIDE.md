# 🌐 Servidor HTTP - Guia de Uso

O fork_mcp agora suporte **2 modos de execução**:

## 🔄 **Modo STDIO (Padrão - Claude Desktop)**
```bash
python run_fork_mcp.py
```
- ✅ **Uso**: Integração com Claude Desktop
- ✅ **Protocolo**: JSON-RPC over STDIO
- ✅ **Produção**: Modo recomendado para uso real

## 🌐 **Modo HTTP (Testes e Desenvolvimento)**
```bash
python mcp_mt5_server.py --port 8000
```
- ✅ **Uso**: Testes, desenvolvimento, debugging
- ✅ **Protocolo**: HTTP REST API
- ✅ **Endpoints**: /health, /info, /config

---

## 📋 **Endpoints HTTP Disponíveis**

### 1. **Health Check**
```
GET http://127.0.0.1:8000/health
```
**Resposta:**
```json
{
  "status": "healthy",
  "service": "MetaTrader 5 MCP Server",
  "version": "1.0.0",
  "mode": "HTTP",
  "mt5_mock": true
}
```

### 2. **Informações do Servidor**
```
GET http://127.0.0.1:8000/info
```
**Resposta:**
```json
{
  "server": "MetaTrader 5 MCP Server (HTTP Mode)",
  "endpoints": {
    "health": "/health",
    "info": "/info",
    "config": "/config"
  },
  "features": [
    "Trading operations",
    "Market data", 
    "Multi-configuration (B3/Forex)",
    "Demo account validation",
    "Linux/WSL compatibility via mock"
  ],
  "current_config": {
    "name": "B3 - Ações Brasileiras",
    "market_type": "B3",
    "account": 72033102,
    "server": "XPMT5-DEMO",
    "initialized": false
  }
}
```

### 3. **Configurações Disponíveis**
```
GET http://127.0.0.1:8000/config
```
**Resposta:**
```json
{
  "available_configs": {
    "b3": {
      "name": "B3 - Ações Brasileiras",
      "market_type": "B3", 
      "account": 72033102,
      "server": "XPMT5-DEMO",
      "portable": true,
      "is_current": true
    },
    "forex": {
      "name": "Forex - Mercado Global",
      "market_type": "Forex",
      "account": 72033102,
      "server": "XPMT5-DEMO", 
      "portable": true,
      "is_current": false
    }
  },
  "current_config": "B3 - Ações Brasileiras"
}
```

### 4. **Página Inicial**
```
GET http://127.0.0.1:8000/
```
**Resposta**: Texto com informações básicas e links para endpoints

---

## 🚀 **Como Executar**

### Modo HTTP (para testes):
```bash
cd fork_mcp
source .venv/bin/activate  # Linux/WSL
python mcp_mt5_server.py --port 8000

# Servidor estará em: http://127.0.0.1:8000
```

### Modo STDIO (para Claude Desktop):
```bash  
cd fork_mcp
source .venv/bin/activate  # Linux/WSL
python run_fork_mcp.py

# Servidor estará em modo STDIO
```

---

## 🧪 **Testando os Endpoints**

### Via Python (requests):
```python
import requests

# Health check
response = requests.get('http://127.0.0.1:8000/health')
print(response.json())

# Configurações
response = requests.get('http://127.0.0.1:8000/config') 
print(response.json())
```

### Via curl (se disponível):
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/config
curl http://127.0.0.1:8000/info
```

### Via Browser:
Abra no navegador:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/config
- http://127.0.0.1:8000/info

---

## ⚡ **Logs de Inicialização HTTP**

Quando executar `python mcp_mt5_server.py --port 8000`, você verá:

```
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO - 🌐 Iniciando servidor HTTP MetaTrader 5 MCP
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Host: 127.0.0.1:8000
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Health: http://127.0.0.1:8000/health
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Info: http://127.0.0.1:8000/info
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Config: http://127.0.0.1:8000/config

2025-08-26 03:19:34 - mt5-mcp-http-server - INFO - 📊 Configuração MT5 Ativa:
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Nome: B3 - Ações Brasileiras
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    MT5_PATH: D:\Files\MetaTraders\MT5-Python\MetaTrader XPDEMO 82033102 Ticks
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Conta: 72033102
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Servidor: XPMT5-DEMO
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Mercado: B3
2025-08-26 03:19:34 - mt5-mcp-http-server - INFO -    Portable: True

2025-08-26 03:19:34 - mt5-mcp-http-server - INFO - ✅ Servidor HTTP pronto! (Ctrl+C para parar)
```

---

## 🔄 **Resumo**

| Aspecto | Modo STDIO | Modo HTTP |
|---------|------------|-----------|
| **Arquivo** | `run_fork_mcp.py` | `mcp_mt5_server.py` |
| **Uso** | Claude Desktop | Testes/Debug |
| **Protocolo** | JSON-RPC | HTTP REST |
| **Porta** | N/A | 8000 |
| **Endpoints** | MCP Tools | /health, /info, /config |

**🎯 Para uso normal**: Use `run_fork_mcp.py`  
**🧪 Para testes HTTP**: Use `mcp_mt5_server.py --port 8000`