# 🚀 Guia do Cliente MCP MetaTrader 5

Agora você tem **3 formas** de usar o servidor MCP MT5:

## 🔧 **1. Uso Direto (Recomendado para Desenvolvimento)**

Execute: `python test_client.py`

### Exemplo Prático:
```python
import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mcp_metatrader5_server.server import config_manager
from mcp_metatrader5_server.mt5_mock import mt5_mock

# 1. Trocar configuração
result = config_manager.switch_config('forex')
print(f"Configuração: {result['current_config']['name']}")

# 2. Obter cotação atual
tick = mt5_mock.symbol_info_tick('EURUSD')
print(f"EURUSD: Bid={tick.bid}, Ask={tick.ask}")

# 3. Informações da conta
account = mt5_mock.account_info()
print(f"Saldo: ${account.balance:.2f}")

# 4. Dados históricos  
rates = mt5_mock.copy_rates_from_pos('EURUSD', 1, 0, 10)
print(f"Últimas 10 barras: {len(rates)} registros")

# 5. Lista de símbolos
symbols = mt5_mock.symbols_get()
print(f"Símbolos disponíveis: {[s.name for s in symbols[:5]]}")
```

## 📡 **2. Cliente MCP via STDIO (Produção)**

Execute: `python mcp_client_simple.py`

### Como usar:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json

async def use_mcp_client():
    server_params = StdioServerParameters(
        command="python",
        args=["run_fork_mcp.py"],
        cwd="."
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Chamar ferramenta
            result = await session.call_tool("get_current_config", {})
            config = json.loads(result.content[0].text)
            print(f"Configuração: {config['name']}")

asyncio.run(use_mcp_client())
```

## 🌐 **3. Cliente HTTP (Testes)**

Execute: `python mcp_mt5_server.py --port 8000` (em um terminal)

Execute: `python mcp_client.py` (em outro terminal)

### Como usar:
```python
import requests
import json

# Health check
response = requests.get('http://127.0.0.1:8000/health')
print(response.json())

# Configurações
response = requests.get('http://127.0.0.1:8000/config')
data = response.json()
print(f"Configuração atual: {data['current_config']}")
```

---

## 📋 **Funcionalidades Disponíveis**

### **🏦 Conta e Configuração**
- `config_manager.get_current_config_info()` - Configuração atual
- `config_manager.switch_config('forex')` - Trocar para Forex
- `config_manager.switch_config('b3')` - Trocar para B3
- `mt5_mock.account_info()` - Informações da conta

### **📊 Dados de Mercado**
- `mt5_mock.symbols_get()` - Lista de símbolos
- `mt5_mock.symbol_info('ITSA4')` - Informações do símbolo
- `mt5_mock.symbol_info_tick('ITSA4')` - Último tick
- `mt5_mock.copy_rates_from_pos(symbol, timeframe, start, count)` - Histórico

### **💼 Trading**
- `mt5_mock.positions_get()` - Posições abertas
- `mt5_mock.orders_get()` - Ordens ativas
- `mt5_mock.order_send(request)` - Enviar ordem
- `mt5_mock.order_check(request)` - Verificar ordem

### **🔧 Utilitários**
- `mt5_mock.terminal_info()` - Informações do terminal
- `mt5_mock.initialize()` - Inicializar MT5
- `mt5_mock.last_error()` - Último erro

---

## 🎯 **Casos de Uso Comuns**

### **Obter Cotações em Tempo Real**
```python
# Forex
config_manager.switch_config('forex')
tick = mt5_mock.symbol_info_tick('EURUSD')
print(f"EUR/USD: {tick.bid} / {tick.ask}")

# B3
config_manager.switch_config('b3') 
tick = mt5_mock.symbol_info_tick('ITSA4')
print(f"ITSA4: {tick.bid} / {tick.ask}")
```

### **Análise de Dados Históricos**
```python
# Obter últimas 100 barras de 5 minutos
rates = mt5_mock.copy_rates_from_pos('ITSA4', 5, 0, 100)

for rate in rates[-5:]:  # Últimas 5 barras
    print(f"Time: {rate[0]}, OHLC: {rate[1]:.2f}/{rate[2]:.2f}/{rate[3]:.2f}/{rate[4]:.2f}")
```

### **Monitoramento Multi-Mercados**
```python
markets = ['b3', 'forex']
symbols = {'b3': 'ITSA4', 'forex': 'EURUSD'}

for market in markets:
    config_manager.switch_config(market)
    tick = mt5_mock.symbol_info_tick(symbols[market])
    print(f"{market.upper()} - {symbols[market]}: {tick.last}")
```

### **Verificação de Conta e Segurança**
```python
# Verificar se é conta demo
account = mt5_mock.account_info()
is_demo = account.trade_mode == 0

if is_demo:
    print("✅ Conta DEMO - Trading permitido")
    # Suas operações aqui
else:
    print("🚨 Conta REAL - Cuidado!")
```

---

## 📊 **Status das Funcionalidades**

| Funcionalidade | Status | Observações |
|----------------|--------|-------------|
| **Multi-Configuração** | ✅ | B3 + Forex |
| **Dados em Tempo Real** | ✅ | Via mock realista |
| **Dados Históricos** | ✅ | OHLCV completo |
| **Informações da Conta** | ✅ | Saldo, equity, etc |
| **Trading Demo** | ✅ | Ordens simuladas |
| **Validação de Segurança** | ✅ | Apenas contas demo |
| **Compatibilidade Linux/WSL** | ✅ | Via mock completo |

---

## 🚀 **Próximos Passos**

1. **Desenvolver**: Use o modo direto (`test_client.py`)
2. **Integrar**: Use o cliente MCP (`mcp_client_simple.py`) 
3. **Testar HTTP**: Use o servidor HTTP (`mcp_mt5_server.py --port 8000`)
4. **Produção**: Configure com Claude Desktop

**🎯 O servidor está 100% funcional e pronto para uso!**