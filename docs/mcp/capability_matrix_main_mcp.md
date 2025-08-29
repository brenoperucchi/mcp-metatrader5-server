# MCP MT5 Main_MCP Capability Matrix - Etapa 2

## 📋 Mapeamento Completo de Ferramentas (Main_MCP)

### 🎯 **Arquitetura Main_MCP**
- **Servidor Customizado**: Baseado em Starlette/FastAPI
- **Multi-Configuração**: B3 (50051) + Forex (50052)
- **Hot-Swap**: Troca de configuração sem reinicialização
- **Endpoints**: `/health` + `/mcp`

### 🔍 **Market Data Tools (4 ferramentas)**

| Ferramenta | Descrição | Input Schema | Output Schema | Status | Latência Alvo |
|------------|-----------|--------------|---------------|--------|---------------|
| `get_symbols` | Lista símbolos disponíveis | `{}` | `Array<string>` | ✅ | <100ms |
| `get_symbol_info` | Info detalhada do símbolo | `{symbol: string}` | `SymbolInfo` | ✅ | <150ms |
| `get_ticks` | Dados de ticks/barras | `{symbol, timeframe, count}` | `Array<Rate>` | ✅ | <200ms |
| `copy_book_levels` | Book de ofertas L2 | `{symbol, depth}` | `BookLevels` | ✅ | <300ms |

### 💼 **Trading Tools (8 ferramentas)**

| Ferramenta | Descrição | Input Schema | Output Schema | Status | Latência Alvo |
|------------|-----------|--------------|---------------|--------|---------------|
| `order_send` | Enviar ordem de mercado | `OrderRequest` | `OrderResult` | ✅ | <400ms |
| `order_send_limit` | Enviar ordem limitada | `OrderLimitRequest` | `OrderResult` | ✅ | <400ms |
| `order_modify` | Modificar ordem | `{ticket, price?, sl?, tp?}` | `ModifyResult` | ✅ | <300ms |
| `order_cancel` | Cancelar ordem | `{ticket}` | `CancelResult` | ✅ | <300ms |
| `order_close` | Fechar posição | `{ticket, volume?, deviation?}` | `CloseResult` | ✅ | <400ms |
| `position_modify` | Modificar SL/TP posição | `{ticket, sl?, tp?}` | `ModifyResult` | ✅ | <300ms |
| `get_positions` | Listar posições | `{symbol?}` | `Array<Position>` | ✅ | <100ms |
| `get_orders` | Listar ordens ativas | `{symbol?}` | `Array<Order>` | ✅ | <100ms |

### 🔧 **System & Configuration Tools (6 ferramentas)**

| Ferramenta | Descrição | Input Schema | Output Schema | Status | Multi-Config |
|------------|-----------|--------------|---------------|--------|--------------|
| `get_account_info` | Informações da conta | `{}` | `AccountInfo` | ✅ | ✅ |
| `validate_demo_for_trading` | Validar conta demo | `{}` | `ValidationResult` | ✅ | ✅ |
| `get_available_configs` | Listar configurações | `{}` | `Array<ConfigInfo>` | ✅ | ✅ |
| `get_current_config` | Configuração ativa | `{}` | `ConfigInfo` | ✅ | ✅ |
| `switch_config` | Trocar configuração | `{config_name}` | `SwitchResult` | ✅ | ✅ |
| `get_position_by_ticket` | Posição por ticket | `{ticket}` | `Position` | ✅ | ✅ |

## ✅ **Checklist de Verificação - Main_MCP**

### **Ferramentas Requeridas - Etapa 2**
- [x] **get_quotes** → `get_symbol_info` (bid/ask/last)
- [x] **get_ticks** → `get_ticks` (histórico de barras)
- [x] **get_positions** → `get_positions`
- [x] **get_orders** → `get_orders`
- [x] **place_order** → `order_send`
- [x] **cancel_order** → `order_cancel` ✨ **IMPLEMENTADO!**

### **Funcionalidades Únicas do Main_MCP**
- [x] **Hot-swap config** → `switch_config` (B3 ↔ Forex)
- [x] **Multi-broker** → Suporte simultâneo B3 + Forex
- [x] **Order Management** → Modify, Close, Cancel específicos
- [x] **Position Management** → Modify SL/TP
- [x] **Validation** → `validate_demo_for_trading`

### **Campos de Dados**
- [x] **bid/ask/last** → Presentes em `get_symbol_info`
- [x] **timestamp** → UTC em todos os dados
- [x] **volume** → Presente em ticks e posições
- [x] **spread** → Calculado dinamicamente
- [x] **timezone** → UTC consistente

### **Funcionalidades Técnicas**
- [x] **Transporte HTTP** → Starlette
- [x] **JSON-RPC 2.0** → Implementado
- [x] **CORS** → Habilitado
- [x] **Health Check** → `/health` endpoint
- [ ] **SSE/Streaming** → Não implementado
- [ ] **TLS** → Depende da configuração

### **Controle de Erro & Segurança**
- [x] **Demo-only validation** → `validate_demo_for_trading`
- [x] **Error messages** → Descritivas em português
- [x] **Force_real flag** → Proteção adicional
- [ ] **Request timeout** → Não configurável
- [ ] **Rate limiting** → Não implementado

## 🔥 **Vantagens do Main_MCP vs Fork_MCP**

### ✅ **Implementado no Main_MCP (não no Fork)**
1. **order_cancel** → Ferramenta específica
2. **order_modify** → Modificar ordens pendentes  
3. **order_close** → Fechar posições específicas
4. **position_modify** → Modificar SL/TP de posições
5. **switch_config** → Hot-swap B3 ↔ Forex
6. **validate_demo_for_trading** → Validação de segurança

### 🎯 **Multi-Configuração (Exclusivo)**
- **B3 Server**: `http://localhost:50051/mcp`
- **Forex Server**: `http://localhost:50052/mcp`
- **Hot-swap**: Trocar mercado sem reiniciar
- **Dual-operation**: Operar ambos simultaneamente

## 📊 **Schemas de Dados - Main_MCP**

### **SymbolInfo (Enhanced)**
```json
{
  "symbol": "PETR4",
  "description": "PETROBRAS PN",
  "point": 0.01,
  "digits": 2,
  "spread": 2,
  "tick_bid": 31.04,
  "tick_ask": 31.06,
  "tick_last": 31.05,
  "tick_time": 1704067200,
  "tick_volume": 1234567,
  "tick_error": null
}
```

### **OrderRequest (Complete)**
```json
{
  "action": 0,
  "symbol": "PETR4",
  "volume": 100,
  "price": 31.05,
  "sl": 30.50,
  "tp": 32.00,
  "deviation": 20,
  "magic": 123456,
  "comment": "Main MCP Order",
  "type_time": 0,
  "expiration": 0,
  "force_real": false
}
```

### **ConfigInfo (Unique)**
```json
{
  "name": "B3 Stocks (Brazilian Market)",
  "account": 72033102,
  "server": "XPMT5-DEMO", 
  "market_type": "stocks",
  "mt5_path": "D:\\...\\terminal64.exe",
  "initialized": true
}
```

## 🚨 **Gaps Identificados - Main_MCP**

### **Resolvidos (vs Fork_MCP)**
- ✅ **Cancel Order**: `order_cancel` implementado
- ✅ **Order Management**: Modify, Close específicos
- ✅ **Multi-Config**: Hot-swap B3/Forex

### **Ainda Pendentes**
1. **Idempotência**: Sem `client_id`/`idempotency_key`
2. **Streaming/SSE**: Sem dados em tempo real
3. **Rate Limiting**: Sem controle de taxa
4. **Request/Trace ID**: Sem debugging avançado

### **Limitações Técnicas**
1. **Timeouts**: Não configuráveis (fixo 30s)
2. **Retry Logic**: Não implementado
3. **Circuit Breaker**: Não implementado
4. **Metrics**: Sem métricas de performance

## 🎯 **Comparação Direta: Main_MCP vs Fork_MCP**

| Aspecto | Main_MCP | Fork_MCP | Vencedor |
|---------|----------|----------|----------|
| **Ferramentas** | 18 tools | 30 tools | Fork_MCP |
| **Trading Advanced** | ✅ (8 tools) | ❌ (básico) | **Main_MCP** |
| **Multi-Config** | ✅ (B3+Forex) | ❌ | **Main_MCP** |
| **Cancel Order** | ✅ | ❌ | **Main_MCP** |
| **Order Modify** | ✅ | ❌ | **Main_MCP** |
| **Market Data** | ❌ (4 tools) | ✅ (16 tools) | Fork_MCP |
| **Resources** | ❌ | ✅ (7 resources) | Fork_MCP |
| **Prompts** | ❌ | ✅ (5 prompts) | Fork_MCP |
| **FastMCP** | ❌ | ✅ | Fork_MCP |

## 🎯 **Decisão para Etapa 2**

### **Recomendação**: ⚠️ **HÍBRIDO**

1. **Para Trading Avançado**: **Main_MCP**
   - Order management completo
   - Multi-configuração
   - Hot-swap B3/Forex
   
2. **Para Market Data**: **Fork_MCP**  
   - Mais ferramentas (16 vs 4)
   - Resources educativos
   - Prompts para IA

### **Status Main_MCP**: ✅ **70% dos Requisitos Atendidos**

**Pontos Fortes**:
- ✅ Trading avançado (100%)
- ✅ Multi-configuração (100%) 
- ✅ Cancel/Modify orders (100%)
- ❌ Market data limitado (25%)

**Próximos Passos**:
1. Implementar mais market data tools no Main_MCP
2. Ou usar Fork_MCP para market data + Main_MCP para trading
3. Benchmark de performance real

---

**Status**: ⚠️ **Aprovado com Restrições** - Especializado em Trading
**Uso Recomendado**: Trading avançado multi-mercado
**Gap Principal**: Market data limitado vs Fork_MCP