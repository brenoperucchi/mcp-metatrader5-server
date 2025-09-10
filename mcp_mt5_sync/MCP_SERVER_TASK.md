# 🚨 TASK para MCP Server (Windows WSL)

## Objetivo
Corrigir 5 falhas críticas no servidor MCP MT5 identificadas pela validação E2.1

## Arquivos Fornecidos
- `validate_contracts.py` - Script de validação que você deve executar
- `contract_validation_20250828_165536.json` - Relatório detalhado das falhas

## Falhas Críticas Encontradas

### 1. `get_account_info` ❌
**Erro:** "Failed to get account info"  
**SLA:** 150ms  
**Crítico:** Sim - necessário para validação DEMO

### 2. `get_terminal_info` ❌  
**Erro:** "Failed to get terminal info"  
**SLA:** 100ms  
**Crítico:** Sim - status do terminal

### 3. `get_symbol_info` ❌
**Erro:** "Failed to get info for symbol ITSA3/ITSA4"  
**SLA:** 50ms  
**Crítico:** Sim - cotações essenciais para arbitragem

### 4. `get_symbol_info_tick` ❌
**Erro:** "Failed to get tick for symbol ITSA3/ITSA4"  
**SLA:** 50ms  
**Crítico:** Sim - dados de tick

### 5. `order_check` ❌
**Erro:** "Invalid 'volume' argument"  
**SLA:** 200ms  
**Crítico:** Sim - validação de ordens

## ✅ Funcionando
- `initialize` - OK (3.1ms)
- `validate_demo_for_trading` - OK (1.7ms) 
- `symbol_select` - OK para ITSA3/ITSA4

## Comandos para Execução

1. **Executar validação:**
```bash
python3 validate_contracts.py
```

2. **Testar tools individuais:**
```bash
curl -X POST http://192.168.0.125:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_account_info", "arguments": {}}}'
```

## Meta
**Target:** 9/9 testes passando (100%)  
**Atual:** 3/9 testes passando (33.3%)  
**Blocker:** E2.2 não pode iniciar até 100% dos testes críticos passarem

## Retorno Esperado
Quando corrigido, execute `validate_contracts.py` novamente e coloque o novo relatório JSON no sync_folder/ com nome: `contract_validation_FIXED_YYYYMMDD_HHMMSS.json`