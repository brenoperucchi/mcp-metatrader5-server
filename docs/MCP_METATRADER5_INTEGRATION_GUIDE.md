# MCP MetaTrader 5 Server - Guia Completo de Integração

## Índice
1. [Visão Geral](#visão-geral)
2. [Instalação e Configuração](#instalação-e-configuração)
3. [Protocolos de Conexão](#protocolos-de-conexão)
4. [API Reference - Métodos Disponíveis](#api-reference---métodos-disponíveis)
5. [Exemplos de Uso](#exemplos-de-uso)
6. [Testes Completos](#testes-completos)
7. [Tratamento de Erros](#tratamento-de-erros)
8. [Melhores Práticas](#melhores-práticas)
9. [Troubleshooting](#troubleshooting)

---

## Visão Geral

O **MCP MetaTrader 5 Server** é uma implementação completa do protocolo MCP (Model Context Protocol) que permite integração com a plataforma MetaTrader 5 para trading automatizado e análise de mercado. Suporta dois protocolos de comunicação:

- **MCP Direto**: Comunicação via STDIO/pipes (alta performance)
- **HTTP API**: Comunicação via REST API (flexibilidade e acesso remoto)

### Características Principais

✅ **Trading Completo**: Ordens a mercado, limitadas, stop-loss, take-profit
✅ **Dados de Mercado**: Preços em tempo real, históricos, book de ofertas  
✅ **Gestão de Posições**: Abrir, modificar, fechar posições
✅ **Gestão de Ordens**: Criar, modificar, cancelar ordens pendentes
✅ **Validação de Segurança**: Verificação obrigatória de conta demo
✅ **Logging Completo**: Sistema de logs estruturado com timestamps

---

## Instalação e Configuração

### 1. Pré-requisitos

- Python 3.11+
- MetaTrader 5 instalado e configurado
- Conta demo ativa (obrigatório para trading)

### 2. Instalação

```bash
# Clone o repositório
git clone https://github.com/your-repo/mcp-metatrader5-server
cd mcp-metatrader5-server

# Instale dependências
pip install -r requirements.txt

# Ou usando uv (recomendado)
uv sync
```

### 3. Configuração do MetaTrader 5

```python
# Configuração básica no seu projeto
import MetaTrader5 as mt5

# Configurar caminho do MT5 (opcional)
MT5_PATH = r"D:\Files\MetaTraders\MT5-Python\MetaTrader XPDEMO 82033102 Ticks"

# Inicializar com configurações
if not mt5.initialize(path=MT5_PATH, portable=True):
    print("Falha na inicialização do MT5")
    exit()

# Login (substitua pelos seus dados)
login = 72033102
password = "sua_senha"
server = "XPMT5-DEMO"

if not mt5.login(login=login, password=password, server=server):
    print("Falha no login")
    exit()
```

---

## Protocolos de Conexão

### MCP Direto (STDIO)

**Vantagens**: Alta performance, baixa latência, protocolo otimizado
**Uso**: Integração direta em aplicações Python

#### Configuração para Claude Desktop

```json
{
  "mcpServers": {
    "mcp-metatrader5": {
      "command": "python",
      "args": ["-m", "mcp_metatrader5_server"],
      "env": {
        "MT5_LOGIN": "72033102",
        "MT5_PASSWORD": "sua_senha",
        "MT5_SERVER": "XPMT5-DEMO"
      }
    }
  }
}
```

#### Cliente Python MCP Direto

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def connect_mcp_direct():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_metatrader5_server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Obter informações da conta
            result = await session.call_tool("mcp__mt5__get_account_info")
            print(f"Conta: {result}")
            
            # Executar ordem
            order_request = {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": 0,  # ORDER_TYPE_BUY
                "type_filling": 2
            }
            
            trade_result = await session.call_tool("mcp__mt5__order_send", {"request": order_request})
            print(f"Resultado: {trade_result}")
```

### HTTP API

**Vantagens**: Acesso remoto, cross-platform, escalável
**Uso**: APIs web, microserviços, integração multi-linguagem

#### Iniciando o Servidor HTTP

```bash
# Método 1: Servidor direto
python run_http_server.py

# Método 2: Auto-restart (recomendado para desenvolvimento)
# No Windows:
python watch_server.py --port 8000

# No WSL/Linux (para restart):
python restart_server.py --port 8000
```

#### Verificando Status do Servidor

```bash
# Verificar se servidor está rodando
curl -s http://localhost:8000/mcp

# Ou usando IP da rede local
curl -s http://192.168.0.125:8000/mcp

# Resposta esperada:
{
  "protocol": "MCP",
  "version": "1.0.0",
  "server": "MetaTrader 5 MCP Server V2",
  "transport": "HTTP", 
  "status": "available",
  "mt5_status": "real",
  "current_config": "B3 - Ações Brasileiras"
}
```

#### Comandos de Restart

```bash
# Zerar arquivo PID para reiniciar
echo "" > server_8000.pid

# Ou do WSL/Linux
python restart_server.py --port 8000
```

#### Cliente HTTP Python

```python
import aiohttp
import asyncio

class MetaTrader5HTTPClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        
    async def call_tool(self, tool_name, params=None):
        """Chamada genérica para qualquer ferramenta MCP"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params or {}
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload) as response:
                result = await response.json()
                if "error" in result:
                    raise Exception(f"Erro MCP: {result['error']}")
                return result["result"]["content"][0]["text"]

# Exemplo de uso
async def main():
    client = MetaTrader5HTTPClient("http://192.168.0.125:8000")
    
    # Obter informações da conta
    account_info = await client.call_tool("mcp__mt5__get_account_info")
    print(f"Conta: {account_info}")
    
    # Validar conta demo (obrigatório antes de trading)
    validation = await client.call_tool("mcp__mt5__validate_demo_for_trading")
    print(f"Validação: {validation}")
    
    if '"allowed": true' in validation:
        # Executar ordem de compra
        order_params = {
            "request": {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": 0,  # ORDER_TYPE_BUY
                "type_filling": 2
            }
        }
        
        result = await client.call_tool("mcp__mt5__order_send", order_params)
        print(f"Ordem executada: {result}")

asyncio.run(main())
```

#### Cliente HTTP JavaScript/Node.js

```javascript
class MetaTrader5HTTPClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async callTool(toolName, params = {}) {
        const payload = {
            jsonrpc: '2.0',
            id: 1,
            method: 'tools/call',
            params: {
                name: toolName,
                arguments: params
            }
        };
        
        const response = await fetch(this.baseUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        if (result.error) {
            throw new Error(`Erro MCP: ${JSON.stringify(result.error)}`);
        }
        
        return JSON.parse(result.result.content[0].text);
    }
}

// Exemplo de uso
const client = new MetaTrader5HTTPClient('http://192.168.0.125:8000');

// Obter informações da conta
const accountInfo = await client.callTool('mcp__mt5__get_account_info');
console.log('Conta:', accountInfo);

// Executar ordem
const orderParams = {
    request: {
        action: 1,  // TRADE_ACTION_DEAL
        symbol: 'EURUSD',
        volume: 0.1,
        type: 0,    // ORDER_TYPE_BUY
        type_filling: 2
    }
};

const tradeResult = await client.callTool('mcp__mt5__order_send', orderParams);
console.log('Resultado:', tradeResult);
```

---

## API Reference - Métodos Disponíveis

### Métodos de Conexão e Informações

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__initialize` | Inicializa conexão MT5 | - |
| `mcp__mt5__shutdown` | Encerra conexão MT5 | - |
| `mcp__mt5__login` | Login na conta | `login`, `password`, `server` |
| `mcp__mt5__get_account_info` | Informações da conta | - |
| `mcp__mt5__get_terminal_info` | Informações do terminal | - |
| `mcp__mt5__get_version` | Versão do MT5 | - |
| `mcp__mt5__validate_demo_for_trading` | **Valida conta demo (obrigatório)** | - |

### Métodos de Símbolos e Market Data

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__get_symbols` | Lista todos os símbolos | - |
| `mcp__mt5__get_symbols_by_group` | Símbolos por grupo | `group` |
| `mcp__mt5__get_symbol_info` | Informações do símbolo | `symbol` |
| `mcp__mt5__get_symbol_info_tick` | Último tick do símbolo | `symbol` |
| `mcp__mt5__symbol_select` | Adicionar/remover símbolo do Market Watch | `symbol`, `visible` |

### Métodos de Dados Históricos

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__copy_rates_from_pos` | Barras a partir de posição | `symbol`, `timeframe`, `start_pos`, `count` |
| `mcp__mt5__copy_rates_from_date` | Barras a partir de data | `symbol`, `timeframe`, `date_from`, `count` |
| `mcp__mt5__copy_rates_range` | Barras em intervalo de datas | `symbol`, `timeframe`, `date_from`, `date_to` |
| `mcp__mt5__copy_ticks_from_pos` | Ticks a partir de posição | `symbol`, `start_pos`, `count`, `flags?` |
| `mcp__mt5__copy_ticks_from_date` | Ticks a partir de data | `symbol`, `date_from`, `count`, `flags?` |
| `mcp__mt5__copy_ticks_range` | Ticks em intervalo | `symbol`, `date_from`, `date_to`, `flags?` |

### Métodos de Book de Ofertas (Level II)

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__copy_book_levels` | Níveis do book | `symbol`, `depth?` |
| `mcp__mt5__subscribe_market_book` | Subscrever book | `symbol` |
| `mcp__mt5__unsubscribe_market_book` | Cancelar subscrição | `symbol` |
| `mcp__mt5__get_book_snapshot` | Snapshot completo do book | `symbol`, `depth?` |

### Métodos de Trading

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__order_send` | **Enviar ordem** | `request` |
| `mcp__mt5__order_check` | Verificar ordem | `request` |
| `mcp__mt5__order_cancel` | Cancelar ordem pendente | `ticket` |
| `mcp__mt5__order_modify` | Modificar ordem pendente | `ticket`, `price?`, `sl?`, `tp?` |
| `mcp__mt5__position_modify` | Modificar posição (SL/TP) | `ticket`, `sl?`, `tp?` |

### Métodos de Consulta

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__positions_get` | Posições abertas | `symbol?`, `group?` |
| `mcp__mt5__positions_get_by_ticket` | Posição por ticket | `ticket` |
| `mcp__mt5__orders_get` | Ordens pendentes | `symbol?`, `group?` |
| `mcp__mt5__orders_get_by_ticket` | Ordem por ticket | `ticket` |
| `mcp__mt5__history_orders_get` | Histórico de ordens | `from_date?`, `to_date?`, `symbol?`, `group?`, `ticket?` |
| `mcp__mt5__history_deals_get` | Histórico de deals | `from_date?`, `to_date?`, `symbol?`, `group?`, `ticket?` |

### Métodos Utilitários

| Método | Descrição | Parâmetros |
|--------|-----------|------------|
| `mcp__mt5__get_last_error` | Último erro MT5 | - |

---

## Exemplos de Uso

### Exemplo 1: Trading Básico (Ordem a Mercado)

```python
import asyncio
import aiohttp

async def exemplo_trading_basico():
    client = MetaTrader5HTTPClient("http://localhost:8000")
    
    # 1. Validar conta demo (OBRIGATÓRIO)
    validation = await client.call_tool("mcp__mt5__validate_demo_for_trading")
    if '"allowed": false' in validation:
        print("❌ Trading não permitido - apenas contas demo são aceitas")
        return
    
    print("✅ Conta demo validada - trading autorizado")
    
    # 2. Obter informações do símbolo
    symbol_info = await client.call_tool("mcp__mt5__get_symbol_info", {"symbol": "EURUSD"})
    print(f"Símbolo: {symbol_info}")
    
    # 3. Executar ordem de compra a mercado
    order_request = {
        "request": {
            "action": 1,          # TRADE_ACTION_DEAL
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": 0,            # ORDER_TYPE_BUY
            "type_filling": 2,    # ORDER_FILLING_IOC
            "comment": "Compra via MCP"
        }
    }
    
    result = await client.call_tool("mcp__mt5__order_send", order_request)
    print(f"Resultado da ordem: {result}")
    
    # 4. Verificar posições abertas
    positions = await client.call_tool("mcp__mt5__positions_get")
    print(f"Posições: {positions}")

asyncio.run(exemplo_trading_basico())
```

### Exemplo 2: Ordem Limitada com Stop Loss e Take Profit

```python
async def exemplo_ordem_limitada():
    client = MetaTrader5HTTPClient("http://localhost:8000")
    
    # Validar conta demo
    validation = await client.call_tool("mcp__mt5__validate_demo_for_trading")
    assert '"allowed": true' in validation, "Trading não permitido"
    
    # Obter preço atual
    tick = await client.call_tool("mcp__mt5__get_symbol_info_tick", {"symbol": "EURUSD"})
    current_price = eval(tick)['ask']  # Converter string JSON para dict
    
    # Calcular preços para ordem limitada
    entry_price = current_price - 0.0020  # 20 pips abaixo
    stop_loss = entry_price - 0.0030     # 30 pips de SL
    take_profit = entry_price + 0.0050   # 50 pips de TP
    
    # Criar ordem limitada de compra
    order_request = {
        "request": {
            "action": 0,                    # TRADE_ACTION_PENDING
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": 2,                      # ORDER_TYPE_BUY_LIMIT
            "price": round(entry_price, 5),
            "sl": round(stop_loss, 5),
            "tp": round(take_profit, 5),
            "type_filling": 1,              # ORDER_FILLING_FOK
            "comment": "Ordem limitada via MCP"
        }
    }
    
    result = await client.call_tool("mcp__mt5__order_send", order_request)
    print(f"Ordem limitada criada: {result}")
    
    # Obter ticket da ordem
    result_dict = eval(result)
    if result_dict.get('retcode') == 10009:  # TRADE_RETCODE_DONE
        order_ticket = result_dict.get('order')
        print(f"✅ Ordem #{order_ticket} criada com sucesso")
        
        # Listar ordens pendentes
        pending_orders = await client.call_tool("mcp__mt5__orders_get")
        print(f"Ordens pendentes: {pending_orders}")
    else:
        print(f"❌ Falha na criação da ordem: {result}")

asyncio.run(exemplo_ordem_limitada())
```

### Exemplo 3: Modificação de Posição (Stop Loss / Take Profit)

```python
async def exemplo_modificar_posicao():
    client = MetaTrader5HTTPClient("http://localhost:8000")
    
    # Validar conta demo
    validation = await client.call_tool("mcp__mt5__validate_demo_for_trading")
    assert '"allowed": true' in validation, "Trading não permitido"
    
    # Obter posições abertas
    positions = await client.call_tool("mcp__mt5__positions_get", {"symbol": "EURUSD"})
    positions_list = eval(positions)
    
    if not positions_list:
        print("❌ Nenhuma posição aberta encontrada")
        return
    
    # Selecionar primeira posição
    position = positions_list[0]
    ticket = position['ticket']
    entry_price = position['price_open']
    position_type = position['type']  # 0=BUY, 1=SELL
    
    print(f"📍 Modificando posição #{ticket} (tipo: {position_type}, entrada: {entry_price})")
    
    # Calcular novos níveis
    if position_type == 0:  # Posição de compra
        new_sl = round(entry_price - 0.0030, 5)  # SL 30 pips abaixo
        new_tp = round(entry_price + 0.0050, 5)  # TP 50 pips acima
    else:  # Posição de venda
        new_sl = round(entry_price + 0.0030, 5)  # SL 30 pips acima
        new_tp = round(entry_price - 0.0050, 5)  # TP 50 pips abaixo
    
    # Modificar posição
    modify_params = {
        "ticket": ticket,
        "sl": new_sl,
        "tp": new_tp
    }
    
    result = await client.call_tool("mcp__mt5__position_modify", modify_params)
    print(f"Resultado modificação: {result}")
    
    # Verificar modificação
    updated_position = await client.call_tool("mcp__mt5__positions_get_by_ticket", {"ticket": ticket})
    print(f"Posição atualizada: {updated_position}")

asyncio.run(exemplo_modificar_posicao())
```

### Exemplo 4: Análise de Market Data

```python
async def exemplo_market_data():
    client = MetaTrader5HTTPClient("http://localhost:8000")
    
    symbol = "EURUSD"
    
    # 1. Informações básicas do símbolo
    symbol_info = await client.call_tool("mcp__mt5__get_symbol_info", {"symbol": symbol})
    print(f"Informações do símbolo: {symbol_info}")
    
    # 2. Último tick
    tick = await client.call_tool("mcp__mt5__get_symbol_info_tick", {"symbol": symbol})
    print(f"Último tick: {tick}")
    
    # 3. Dados históricos (últimas 100 barras H1)
    rates_params = {
        "symbol": symbol,
        "timeframe": 16385,  # TIMEFRAME_H1
        "start_pos": 0,
        "count": 100
    }
    
    rates = await client.call_tool("mcp__mt5__copy_rates_from_pos", rates_params)
    rates_data = eval(rates)
    print(f"Barras históricas obtidas: {len(rates_data)} barras")
    print(f"Última barra: {rates_data[-1] if rates_data else 'N/A'}")
    
    # 4. Book de ofertas (se disponível)
    try:
        # Subscrever ao book
        await client.call_tool("mcp__mt5__subscribe_market_book", {"symbol": symbol})
        
        # Obter snapshot do book
        book = await client.call_tool("mcp__mt5__get_book_snapshot", {
            "symbol": symbol,
            "depth": 10
        })
        print(f"Book de ofertas: {book}")
        
        # Cancelar subscrição
        await client.call_tool("mcp__mt5__unsubscribe_market_book", {"symbol": symbol})
        
    except Exception as e:
        print(f"Book de ofertas não disponível: {e}")

asyncio.run(exemplo_market_data())
```

---

## Testes Completos

### Estrutura de Teste Baseada em `test_complete_b3_http.py`

```python
import asyncio
import aiohttp
import json
import time
from datetime import datetime

class CompleteTradingTest:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.test_results = []
        self.test_symbol = None
        
    async def call_tool(self, tool_name, params=None):
        """Método base para chamadas MCP"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params or {}
            }
        }
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.server_url, json=payload) as response:
                    result = await response.json()
                    
            duration = (time.time() - start_time) * 1000
            
            if "error" in result:
                self.test_results.append({
                    "test": tool_name,
                    "success": False,
                    "duration_ms": duration,
                    "error": result["error"],
                    "timestamp": datetime.now().isoformat()
                })
                return None
            
            content = result["result"]["content"][0]["text"]
            self.test_results.append({
                "test": tool_name,
                "success": True,
                "duration_ms": duration,
                "data": json.loads(content) if content.startswith('{') else content,
                "timestamp": datetime.now().isoformat()
            })
            
            return content
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append({
                "test": tool_name,
                "success": False,
                "duration_ms": duration,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return None
    
    async def test_connectivity(self):
        """Teste 1: Conectividade básica"""
        print("[TEST] Testando conectividade...")
        result = await self.call_tool("mcp__mt5__get_symbols")
        if result:
            symbols_count = len(json.loads(result))
            print(f"✅ Conectividade OK - {symbols_count} símbolos disponíveis")
            return True
        else:
            print("❌ Falha na conectividade")
            return False
    
    async def test_account_validation(self):
        """Teste 2: Validação de conta"""
        print("[TEST] Validando conta...")
        
        # Obter informações da conta
        account_info = await self.call_tool("mcp__mt5__get_account_info")
        if not account_info:
            print("❌ Falha ao obter informações da conta")
            return False
            
        # Validar conta demo
        validation = await self.call_tool("mcp__mt5__validate_demo_for_trading")
        if validation and '"allowed": true' in validation:
            print("✅ Conta demo validada - trading autorizado")
            return True
        else:
            print("❌ Trading não autorizado - apenas contas demo")
            return False
    
    async def find_suitable_symbol(self):
        """Encontrar símbolo adequado para testes"""
        print("[TEST] Procurando símbolo adequado...")
        
        # Lista de símbolos preferenciais (B3)
        preferred_symbols = ["PETR4", "VALE3", "BBAS3", "ITUB4", "ABEV3", "MGLU3"]
        
        symbols_result = await self.call_tool("mcp__mt5__get_symbols")
        if not symbols_result:
            return None
            
        all_symbols = json.loads(symbols_result)
        
        # Tentar símbolos preferenciais primeiro
        for symbol in preferred_symbols:
            if symbol in all_symbols:
                symbol_info = await self.call_tool("mcp__mt5__get_symbol_info", {"symbol": symbol})
                if symbol_info:
                    info = json.loads(symbol_info)
                    if info.get('trade_mode') == 4:  # SYMBOL_TRADE_MODE_FULL
                        self.test_symbol = symbol
                        print(f"✅ Símbolo selecionado: {symbol}")
                        return symbol
        
        # Fallback: procurar qualquer símbolo negociável
        for symbol in all_symbols[:50]:  # Testar apenas os primeiros 50
            symbol_info = await self.call_tool("mcp__mt5__get_symbol_info", {"symbol": symbol})
            if symbol_info:
                info = json.loads(symbol_info)
                if (info.get('trade_mode') == 4 and 
                    info.get('volume_min', 0) <= 1.0 and
                    info.get('ask', 0) > 0):
                    self.test_symbol = symbol
                    print(f"✅ Símbolo alternativo selecionado: {symbol}")
                    return symbol
        
        print("❌ Nenhum símbolo adequado encontrado")
        return None
    
    async def test_market_data(self):
        """Teste 3: Dados de mercado"""
        if not self.test_symbol:
            return False
            
        print(f"[TEST] Testando dados de mercado para {self.test_symbol}...")
        
        # Informações do símbolo
        symbol_info = await self.call_tool("mcp__mt5__get_symbol_info", {"symbol": self.test_symbol})
        if not symbol_info:
            return False
        
        # Último tick
        tick = await self.call_tool("mcp__mt5__get_symbol_info_tick", {"symbol": self.test_symbol})
        if not tick:
            return False
        
        # Dados históricos
        rates = await self.call_tool("mcp__mt5__copy_rates_from_pos", {
            "symbol": self.test_symbol,
            "timeframe": 16385,  # H1
            "start_pos": 0,
            "count": 10
        })
        
        print("✅ Dados de mercado obtidos com sucesso")
        return bool(rates)
    
    async def test_full_trading_cycle(self):
        """Teste 4: Ciclo completo de trading"""
        if not self.test_symbol:
            return False
            
        print(f"[TEST] Executando ciclo completo de trading com {self.test_symbol}...")
        
        # 1. Ordem a mercado (compra)
        order_request = {
            "request": {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": self.test_symbol,
                "volume": 1.0,
                "type": 0,    # ORDER_TYPE_BUY
                "type_filling": 2,
                "comment": "Teste MCP Completo"
            }
        }
        
        buy_result = await self.call_tool("mcp__mt5__order_send", order_request)
        if not buy_result or '"retcode": 10009' not in buy_result:
            print("❌ Falha na ordem de compra")
            return False
        
        buy_data = json.loads(buy_result)
        print(f"✅ Compra executada - Deal: {buy_data.get('deal')}")
        
        # Aguardar posição aparecer
        await asyncio.sleep(2)
        
        # 2. Buscar posição criada
        positions = await self.call_tool("mcp__mt5__positions_get", {"symbol": self.test_symbol})
        if not positions:
            print("❌ Posição não encontrada")
            return False
        
        positions_list = json.loads(positions)
        if not positions_list:
            print("❌ Nenhuma posição aberta")
            return False
        
        position = positions_list[0]
        position_ticket = position['ticket']
        entry_price = position['price_open']
        
        print(f"✅ Posição encontrada - Ticket: {position_ticket}")
        
        # 3. Modificar posição (adicionar SL/TP)
        sl_price = round(entry_price * 0.98, 5)  # SL 2% abaixo
        tp_price = round(entry_price * 1.03, 5)  # TP 3% acima
        
        modify_result = await self.call_tool("mcp__mt5__position_modify", {
            "ticket": position_ticket,
            "sl": sl_price,
            "tp": tp_price
        })
        
        if modify_result and '"retcode": 10009' in modify_result:
            print(f"✅ SL/TP adicionados - SL: {sl_price}, TP: {tp_price}")
        
        # Aguardar modificação
        await asyncio.sleep(1)
        
        # 4. Fechar posição
        close_request = {
            "request": {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": self.test_symbol,
                "volume": 1.0,
                "type": 1,    # ORDER_TYPE_SELL
                "position": position_ticket,
                "type_filling": 2,
                "comment": "Fechamento Teste MCP"
            }
        }
        
        close_result = await self.call_tool("mcp__mt5__order_send", close_request)
        if close_result and '"retcode": 10009' in close_result:
            close_data = json.loads(close_result)
            print(f"✅ Posição fechada - Deal: {close_data.get('deal')}")
            return True
        else:
            print("❌ Falha ao fechar posição")
            return False
    
    async def test_pending_orders(self):
        """Teste 5: Ordens pendentes"""
        if not self.test_symbol:
            return False
            
        print(f"[TEST] Testando ordens pendentes com {self.test_symbol}...")
        
        # Obter preço atual
        tick = await self.call_tool("mcp__mt5__get_symbol_info_tick", {"symbol": self.test_symbol})
        if not tick:
            return False
        
        tick_data = json.loads(tick)
        current_price = tick_data.get('ask', 0)
        
        # Criar ordem limitada abaixo do mercado
        limit_price = round(current_price * 0.95, 5)  # 5% abaixo
        
        limit_order = {
            "request": {
                "action": 0,  # TRADE_ACTION_PENDING
                "symbol": self.test_symbol,
                "volume": 1.0,
                "type": 2,    # ORDER_TYPE_BUY_LIMIT
                "price": limit_price,
                "type_filling": 1,
                "comment": "Ordem Limitada Teste MCP"
            }
        }
        
        order_result = await self.call_tool("mcp__mt5__order_send", limit_order)
        if not order_result or '"retcode": 10009' not in order_result:
            print("❌ Falha na criação da ordem limitada")
            return False
        
        order_data = json.loads(order_result)
        order_ticket = order_data.get('order')
        print(f"✅ Ordem limitada criada - Ticket: {order_ticket}")
        
        # Aguardar ordem aparecer
        await asyncio.sleep(1)
        
        # Modificar ordem
        new_price = round(limit_price * 0.99, 5)  # Reduzir preço em 1%
        
        modify_result = await self.call_tool("mcp__mt5__order_modify", {
            "ticket": order_ticket,
            "price": new_price
        })
        
        if modify_result and '"retcode": 10009' in modify_result:
            print(f"✅ Ordem modificada - Novo preço: {new_price}")
        
        # Cancelar ordem
        cancel_result = await self.call_tool("mcp__mt5__order_cancel", {"ticket": order_ticket})
        if cancel_result and '"retcode": 10009' in cancel_result:
            print("✅ Ordem cancelada com sucesso")
            return True
        else:
            print("❌ Falha ao cancelar ordem")
            return False
    
    async def run_complete_test(self):
        """Executar bateria completa de testes"""
        print("🚀 INICIANDO TESTE COMPLETO MCP METATRADER 5")
        print("=" * 50)
        
        start_time = time.time()
        
        # Bateria de testes
        tests = [
            ("Conectividade", self.test_connectivity),
            ("Validação de Conta", self.test_account_validation),
            ("Busca de Símbolo", self.find_suitable_symbol),
            ("Dados de Mercado", self.test_market_data),
            ("Trading Completo", self.test_full_trading_cycle),
            ("Ordens Pendentes", self.test_pending_orders)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n[TEST] {test_name}...")
            try:
                result = await test_func()
                if result:
                    print(f"✅ {test_name} - PASSOU")
                    passed += 1
                else:
                    print(f"❌ {test_name} - FALHOU")
            except Exception as e:
                print(f"❌ {test_name} - ERRO: {e}")
        
        # Relatório final
        duration = time.time() - start_time
        success_rate = (passed / total) * 100
        
        print("\n" + "=" * 50)
        print("📊 RELATÓRIO FINAL")
        print("=" * 50)
        print(f"✅ Testes aprovados: {passed}/{total}")
        print(f"📊 Taxa de sucesso: {success_rate:.1f}%")
        print(f"⏱️  Duração total: {duration:.2f}s")
        
        if self.test_symbol:
            print(f"📈 Símbolo testado: {self.test_symbol}")
        
        # Salvar relatório JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_complete_mcp_{timestamp}.json"
        
        report_data = {
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "success_rate": success_rate,
                "duration_seconds": round(duration, 2),
                "test_symbol": self.test_symbol
            },
            "detailed_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Relatório salvo: {report_file}")
        
        return success_rate == 100.0

# Executar teste
async def main():
    tester = CompleteTradingTest("http://192.168.0.125:8000")
    success = await tester.run_complete_test()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
```

---

## Tratamento de Erros

### Códigos de Retorno MT5 Comuns

```python
TRADE_RETCODES = {
    10004: "REQUOTE - Preço mudou",
    10006: "REJECTED - Solicitação rejeitada",
    10007: "CANCEL - Solicitação cancelada",
    10008: "PLACED - Ordem colocada",
    10009: "DONE - Sucesso completo",
    10010: "DONE_PARTIAL - Preenchimento parcial",
    10011: "ERROR - Erro comum",
    10012: "TIMEOUT - Timeout",
    10013: "INVALID - Solicitação inválida",
    10014: "INVALID_VOLUME - Volume inválido",
    10015: "INVALID_PRICE - Preço inválido",
    10016: "INVALID_STOPS - Stops inválidos",
    10017: "TRADE_DISABLED - Trading desabilitado",
    10018: "MARKET_CLOSED - Mercado fechado",
    10019: "NO_MONEY - Fundos insuficientes",
    10020: "PRICE_CHANGED - Preço mudou",
    10021: "PRICE_OFF - Preço fora do mercado",
    10022: "INVALID_EXPIRATION - Expiração inválida",
    10023: "ORDER_CHANGED - Estado da ordem mudou",
    10024: "TOO_MANY_REQUESTS - Muitas solicitações",
    10025: "NO_CHANGES - Nenhuma mudança",
    10026: "SERVER_DISABLES_AT - Auto-trading desabilitado pelo servidor",
    10027: "CLIENT_DISABLES_AT - Auto-trading desabilitado pelo cliente",
    10028: "LOCKED - Operação bloqueada",
    10029: "FROZEN - Ordem congelada",
    10030: "INVALID_FILL - Tipo de preenchimento inválido"
}

def interpret_retcode(retcode):
    """Interpretar código de retorno MT5"""
    return TRADE_RETCODES.get(retcode, f"Código desconhecido: {retcode}")
```

### Tratamento de Erros na Aplicação

```python
import logging

class MT5ErrorHandler:
    @staticmethod
    def handle_order_error(result):
        """Tratar erros de ordens"""
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                return False, "Erro ao interpretar resultado"
        
        retcode = result.get('retcode')
        
        if retcode == 10009:  # TRADE_RETCODE_DONE
            return True, "Ordem executada com sucesso"
        elif retcode == 10019:  # TRADE_RETCODE_NO_MONEY
            return False, "Fundos insuficientes"
        elif retcode == 10018:  # TRADE_RETCODE_MARKET_CLOSED
            return False, "Mercado fechado"
        elif retcode == 10017:  # TRADE_RETCODE_TRADE_DISABLED
            return False, "Trading desabilitado para este símbolo"
        else:
            return False, interpret_retcode(retcode)
    
    @staticmethod
    def handle_connection_error(error):
        """Tratar erros de conexão"""
        error_msg = str(error).lower()
        
        if "connection refused" in error_msg:
            return "Servidor MCP não está rodando - verifique se o servidor está ativo"
        elif "timeout" in error_msg:
            return "Timeout na conexão - verifique a rede e o servidor"
        elif "unauthorized" in error_msg:
            return "Acesso não autorizado - verifique as credenciais"
        else:
            return f"Erro de conexão: {error}"

# Exemplo de uso
async def safe_order_execution(client, order_request):
    try:
        result = await client.call_tool("mcp__mt5__order_send", {"request": order_request})
        
        success, message = MT5ErrorHandler.handle_order_error(result)
        
        if success:
            logging.info(f"✅ Ordem executada: {message}")
            return json.loads(result)
        else:
            logging.error(f"❌ Falha na ordem: {message}")
            return None
            
    except Exception as e:
        error_msg = MT5ErrorHandler.handle_connection_error(e)
        logging.error(f"❌ Erro de conexão: {error_msg}")
        return None
```

---

## Melhores Práticas

### 1. Validação de Segurança

```python
async def ensure_demo_account(client):
    """SEMPRE validar conta demo antes de trading"""
    validation = await client.call_tool("mcp__mt5__validate_demo_for_trading")
    
    if not validation or '"allowed": false' in validation:
        raise Exception("❌ TRADING BLOQUEADO: Apenas contas demo são permitidas")
    
    print("✅ Conta demo validada - trading autorizado")
    return True
```

### 2. Gestão de Riscos

```python
def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss):
    """Calcular tamanho da posição baseado no risco"""
    risk_amount = account_balance * (risk_percent / 100)
    price_diff = abs(entry_price - stop_loss)
    
    if price_diff == 0:
        return 0
    
    position_size = risk_amount / price_diff
    return round(position_size, 2)

# Exemplo de uso
account_info = await client.call_tool("mcp__mt5__get_account_info")
balance = json.loads(account_info)['balance']

position_size = calculate_position_size(
    account_balance=balance,
    risk_percent=1.0,  # Riscar 1% do saldo
    entry_price=1.1000,
    stop_loss=1.0950
)

print(f"Tamanho calculado da posição: {position_size}")
```

### 3. Logging Estruturado

```python
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'mcp_trading_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

def log_trade_operation(operation, symbol, volume, price, result):
    """Log estruturado para operações de trading"""
    logging.info(f"TRADE | {operation} | {symbol} | Vol: {volume} | Price: {price} | Result: {result}")

# Exemplo de uso
log_trade_operation("BUY", "EURUSD", 0.1, 1.1000, "SUCCESS")
```

### 4. Retry Logic

```python
import asyncio
from functools import wraps

def retry_on_failure(max_retries=3, delay=1.0):
    """Decorator para tentar novamente em caso de falha"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:  # Última tentativa
                        raise e
                    
                    logging.warning(f"Tentativa {attempt + 1} falhou: {e}. Tentando novamente em {delay}s...")
                    await asyncio.sleep(delay)
            
            return None
        return wrapper
    return decorator

# Exemplo de uso
@retry_on_failure(max_retries=3, delay=2.0)
async def robust_order_send(client, order_request):
    result = await client.call_tool("mcp__mt5__order_send", {"request": order_request})
    
    if not result or '"retcode": 10009' not in result:
        raise Exception("Ordem falhou")
    
    return result
```

---

## Troubleshooting

### Problemas Comuns e Soluções

#### 1. Servidor MCP não inicia

**Problema**: `Connection refused` ou servidor não responde

**Soluções**:
```bash
# Verificar se o MT5 está rodando
tasklist | findstr "MetaTrader"

# Verificar porta disponível
netstat -an | findstr :8000

# Iniciar servidor com debug
python run_http_server.py --debug

# Verificar logs
tail -f logs/run_http_server/run_http_server_*.log
```

#### 2. Login no MT5 falha

**Problema**: `LOGIN_FAIL` ou credenciais rejeitadas

**Soluções**:
```python
# Verificar credenciais
login_result = await client.call_tool("mcp__mt5__login", {
    "login": 72033102,
    "password": "sua_senha",
    "server": "XPMT5-DEMO"
})

# Verificar conta ativa no MT5
account_info = await client.call_tool("mcp__mt5__get_account_info")

# Reinitilaizar conexão
await client.call_tool("mcp__mt5__shutdown")
await client.call_tool("mcp__mt5__initialize")
```

#### 3. Ordens rejeitadas

**Problema**: `TRADE_RETCODE_REJECTED` ou ordens não executam

**Soluções**:
```python
# Verificar informações do símbolo
symbol_info = await client.call_tool("mcp__mt5__get_symbol_info", {"symbol": "EURUSD"})
info = json.loads(symbol_info)

# Verificar se trading está habilitado
if info.get('trade_mode') != 4:
    print("Trading não habilitado para este símbolo")

# Verificar volume mínimo/máximo
volume_min = info.get('volume_min', 0.01)
volume_max = info.get('volume_max', 1000)

# Verificar spread e liquidez
spread = info.get('spread', 0)
if spread > 50:  # Spread muito alto
    print("Spread muito alto, aguardar melhores condições")

# Usar order_check antes de enviar
check_result = await client.call_tool("mcp__mt5__order_check", {"request": order_request})
```

#### 4. Problemas de serialização

**Problema**: `'dict' object has no attribute 'model_dump'`

**Solução**: Atualizar servidor para versão mais recente que inclui correções de serialização.

#### 5. Timeout na conexão

**Problema**: Operações demoram muito ou timeout

**Soluções**:
```python
# Aumentar timeout do cliente HTTP
timeout = aiohttp.ClientTimeout(total=30)
async with aiohttp.ClientSession(timeout=timeout) as session:
    # suas operações

# Verificar latência de rede
import time

start = time.time()
result = await client.call_tool("mcp__mt5__get_account_info")
duration = time.time() - start
print(f"Latência: {duration:.2f}s")

# Usar connection pooling
connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
session = aiohttp.ClientSession(connector=connector)
```

---

## Conclusão

Este guia fornece uma base completa para integração com o MCP MetaTrader 5 Server. Lembre-se sempre de:

1. ✅ **Validar conta demo** antes de qualquer operação de trading
2. 🔒 **Implementar gestão de riscos** adequada
3. 📝 **Usar logging estruturado** para debugging
4. 🔄 **Implementar retry logic** para operações críticas
5. 🧪 **Testar completamente** antes de usar em produção

Para suporte adicional, consulte os logs do servidor em `logs/run_http_server/` e os testes de exemplo em `tests/integration/`.

**Aviso Legal**: Este sistema é destinado apenas para contas demo. O uso em contas reais requer implementação adicional de medidas de segurança e validações.