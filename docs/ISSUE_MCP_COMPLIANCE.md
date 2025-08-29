# 🔧 [EPIC] Implementar Servidor MCP Compliant para Etapa 2 - Decisão de Swap

## 📋 **Resumo**

Transformar o servidor HTTP/JSON-RPC atual em um servidor MCP (Model Context Protocol) totalmente compliant para suportar a **ETAPA 2 - Decisão de Swap** com segurança e performance adequadas.

**Status atual**: ✅ 34 tools expostas, ❌ Protocolo MCP incompleto
**Meta**: 🎯 Servidor MCP 100% funcional para trading de arbitragem B3

---

## 🚀 **Objetivos Principais**

- [ ] **Protocolo MCP**: Implementar `tools/call` compliant 
- [ ] **Trading Seguro**: Validações robustas para conta demo
- [ ] **Performance**: Latência < 200ms para operações críticas
- [ ] **Auditoria**: Logging estruturado para compliance
- [ ] **Símbolos B3**: Suporte completo ITSA3/ITSA4 e outros pares ON/PN

---

## 📊 **Subtarefas por Prioridade**

### 🔴 **CRÍTICO - Protocolo MCP Core**

#### **Task 1: Implementar `tools/call` Method**
- [ ] **1.1** - Adicionar handler `tools/call` no servidor HTTP
- [ ] **1.2** - Mapear 34 tools existentes para `tools/call`
- [ ] **1.3** - Implementar estrutura de resposta MCP compliant:
  ```json
  {
    "content": [{"type": "text", "text": "JSON stringified result"}]
  }
  ```
- [ ] **1.4** - Testes unitários para `tools/call`

**Acceptance Criteria:**
```bash
# Deve funcionar:
curl -X POST http://localhost:8000/mcp \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", 
       "params": {"name": "get_account_info", "arguments": {}}}'
```

#### **Task 2: Estrutura de Erro Padronizada**
- [ ] **2.1** - Definir códigos de erro MCP:
  - `MT5_NOT_INITIALIZED`, `MT5_SYMBOL_NOT_FOUND`, `MT5_INSUFFICIENT_FUNDS`, etc.
- [ ] **2.2** - Implementar error handling consistente
- [ ] **2.3** - Documentar todos os códigos de erro

### 🟠 **ALTA - Ferramentas Críticas para Trading**

#### **Task 3: Cotações e Market Data**
- [ ] **3.1** - `get_symbol_info` com bid/ask/last/volume/time
- [ ] **3.2** - `get_symbol_info_tick` tempo real
- [ ] **3.3** - `copy_book_levels` (Level 2) com bids/asks
- [ ] **3.4** - Cache inteligente (100ms para cotações)
- [ ] **3.5** - Testes com símbolos ITSA3/ITSA4

#### **Task 4: Execução de Ordens** 
- [ ] **4.1** - `order_send` funcional em demo
- [ ] **4.2** - `order_check` com validações pré-envio
- [ ] **4.3** - `order_cancel` e `order_modify`
- [ ] **4.4** - `position_modify` para SL/TP
- [ ] **4.5** - Suporte a magic numbers e comentários

#### **Task 5: Gestão de Posições**
- [ ] **5.1** - `positions_get` com filtros por símbolo
- [ ] **5.2** - `positions_get_by_ticket` 
- [ ] **5.3** - `orders_get` (ordens pendentes)
- [ ] **5.4** - `history_orders_get` e `history_deals_get`

### 🟡 **MÉDIA - Segurança e Validações**

#### **Task 6: Validação de Conta Demo**
- [ ] **6.1** - `validate_demo_for_trading` obrigatório
- [ ] **6.2** - Bloqueio automático para contas REAL
- [ ] **6.3** - Warnings visuais para modo demo
- [ ] **6.4** - Configuração de bypass para desenvolvimento

#### **Task 7: Validação de Símbolos B3**
- [ ] **7.1** - Whitelist de símbolos permitidos:
  ```python
  ALLOWED_SYMBOLS = ["ITSA3", "ITSA4", "PETR3", "PETR4", "VALE3", "VALE5"]
  ```
- [ ] **7.2** - Validação automática em todas as operações
- [ ] **7.3** - Suporte a configuração dinâmica de símbolos

### 🟢 **BAIXA - Performance e Monitoring**

#### **Task 8: Performance e Latência**
- [ ] **8.1** - SLAs obrigatórios implementados:
  - `get_symbol_info`: < 50ms
  - `order_send`: < 200ms
  - `positions_get`: < 100ms
- [ ] **8.2** - Timeouts configuráveis (default: 5s)
- [ ] **8.3** - Cache estratégico (cotações 100ms, posições 500ms)
- [ ] **8.4** - Métricas de performance

#### **Task 9: Logging e Auditoria**
- [ ] **9.1** - Logging estruturado com `structlog`
- [ ] **9.2** - Session IDs para rastreamento
- [ ] **9.3** - Métricas de duração de calls
- [ ] **9.4** - Log de todas as operações de trading

#### **Task 10: Configuração Flexível**
- [ ] **10.1** - Arquivo `mcp_server_config.yaml`
- [ ] **10.2** - Override de parâmetros via env vars
- [ ] **10.3** - Hot-reload de configurações não-críticas

---

## 🎯 **Testes de Validação**

### **Teste 1: MCP Protocol Compliance**
```bash
# Tools/call básico
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", 
       "params": {"name": "get_account_info", "arguments": {}}}'

# Resposta esperada:
{
  "jsonrpc": "2.0", "id": 1,
  "result": {"content": [{"type": "text", "text": "{\"login\": 123456, ...}"}]}
}
```

### **Teste 2: Cotações B3**
```bash
# ITSA3 real-time
curl -X POST http://192.168.0.125:8000/mcp \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/call",
       "params": {"name": "get_symbol_info_tick", "arguments": {"symbol": "ITSA3"}}}'

# Resposta esperada: bid/ask/last/volume/time
```

### **Teste 3: Validação de Trading**
```bash
# Order check
curl -X POST http://192.168.0.125:8000/mcp \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
       "params": {"name": "order_check", 
                  "arguments": {"request": {"symbol": "ITSA3", "volume": 100, "type": 0}}}}'

# Resposta esperada: retcode=0, margin info, validation OK
```

### **Teste 4: Performance**
```bash
# Latência < 200ms para operações críticas
time curl -X POST http://192.168.0.125:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "order_send", ...}}'
```

---

## ✅ **Definition of Done**

### **Requisitos Funcionais:**
- [ ] ✅ `tools/call` funcionando para todas 34 ferramentas
- [ ] ✅ Cotações ITSA3/ITSA4 retornando bid/ask/last/volume em tempo real
- [ ] ✅ `order_send`/`order_check` funcionais em conta demo 
- [ ] ✅ `positions_get` e gestão de posições completa
- [ ] ✅ Validação automática de conta demo ativa

### **Requisitos Não-Funcionais:**
- [ ] 🚀 Latência < 200ms para operações críticas
- [ ] 📊 Logs estruturados para auditoria completa
- [ ] 🔒 Validações de segurança ativas (demo-only)
- [ ] 📈 Métricas de performance coletadas
- [ ] 🔧 Configuração flexível via YAML

### **Testes:**
- [ ] ✅ 100% cobertura para `tools/call`
- [ ] ✅ Testes de integração com MT5 demo
- [ ] ✅ Testes de performance/latência
- [ ] ✅ Testes de segurança (bloqueio conta real)

---

## 📚 **Recursos e Referências**

- **Prompt Técnico**: `fork_mcp/mcp_server_corrections_prompt.md`
- **Capability Matrix**: `docs/mcp/capability_matrix.md` 
- **Servidor Atual**: `fork_mcp/run_http_server.py`
- **MCP Spec**: https://modelcontextprotocol.io/

---

## 🏷️ **Labels**

`epic` `mcp` `trading` `b3` `performance` `security` `etapa-2`

---

## 👥 **Assignees**

@brenoperucchi

---

## ⏱️ **Timeline**

- **Sprint 1** (Semana 1): Tasks 1-2 (Protocolo MCP Core)
- **Sprint 2** (Semana 2): Tasks 3-5 (Ferramentas Trading)  
- **Sprint 3** (Semana 3): Tasks 6-7 (Segurança)
- **Sprint 4** (Semana 4): Tasks 8-10 (Performance/Monitoring)

**Prazo Final**: 4 semanas para MVP completo

---

*Este servidor MCP compliant permitirá implementar a **ETAPA 2 - Decisão de Swap** com segurança, performance e auditoria adequadas para trading de arbitragem no mercado B3.*