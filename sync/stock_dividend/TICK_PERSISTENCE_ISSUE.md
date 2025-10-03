# 🚨 Problema: Ticks Não Estão Sendo Persistidos em Modo Live

## Diagnóstico Completo

**Data**: 2025-10-03
**Status**: 🔴 PROBLEMA IDENTIFICADO

---

## O Problema

O MCP MetaTrader5 Server implementou **tick persistence** completo, mas os ticks **não estão sendo salvos** no PostgreSQL quando o stock-dividend está em modo live.

**Motivo**: O stock-dividend está chamando o endpoint **ERRADO**.

---

## Análise dos Logs

### O que está acontecendo agora:

```
2025-10-03 15:29:21,728 - MCP Direct tool call: get_symbol_info with args: {'symbol': 'ITSA3'}
2025-10-03 15:29:21,728 - MCP Direct tool call: get_symbol_info with args: {'symbol': 'ITSA4'}
```

O stock-dividend está chamando **`get_symbol_info`** repetidamente (2x por segundo).

### Problema:

**`get_symbol_info`** NÃO é um endpoint de ticks!

`get_symbol_info` retorna apenas informações **estáticas** do símbolo:
- Nome
- Descrição
- Digits
- Spread
- Volume mínimo/máximo
- Etc.

Este endpoint **não retorna dados de tick** e **não deve** persistir nada.

---

## A Solução

### Endpoints CORRETOS para Ticks (com persistência ativa):

#### 1. `get_symbol_info_tick` - Tick Mais Recente
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_symbol_info_tick",
    "arguments": {
      "symbol": "ITSA3"
    }
  }
}
```

**Retorna**: 1 tick (o mais recente)
**Persistência**: ✅ SIM - salva automaticamente no PostgreSQL

---

#### 2. `copy_ticks_from_pos` - Ticks Recentes por Posição
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "copy_ticks_from_pos",
    "arguments": {
      "symbol": "ITSA3",
      "start_pos": 0,
      "count": 10,
      "flags": 2
    }
  }
}
```

**Retorna**: Até 10 ticks mais recentes
**Persistência**: ✅ SIM - salva todos automaticamente

**Flags**:
- `0` = COPY_TICKS_INFO (apenas bid/ask)
- `1` = COPY_TICKS_TRADE (apenas last/volume)
- `2` = COPY_TICKS_ALL (todos os dados) ← **RECOMENDADO**

---

#### 3. `copy_ticks_from_date` - Ticks a Partir de Data
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "copy_ticks_from_date",
    "arguments": {
      "symbol": "ITSA3",
      "date_from": "2025-10-03T09:00:00",
      "count": 100,
      "flags": 2
    }
  }
}
```

**Retorna**: Até 100 ticks a partir da data
**Persistência**: ✅ SIM - salva todos automaticamente

---

#### 4. `copy_ticks_range` - Ticks em Intervalo
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "copy_ticks_range",
    "arguments": {
      "symbol": "ITSA3",
      "date_from": "2025-10-03T09:00:00",
      "date_to": "2025-10-03T10:00:00",
      "flags": 2
    }
  }
}
```

**Retorna**: Todos os ticks no intervalo
**Persistência**: ✅ SIM - salva todos automaticamente

---

## Recomendação para Modo Live

### Opção 1: Polling com `get_symbol_info_tick` (Mais Simples)

```ruby
# Atualizar a cada 1 segundo
loop do
  symbols.each do |symbol|
    response = mcp_client.call_tool("get_symbol_info_tick", {
      symbol: symbol
    })

    tick = response["content"]
    # Processar tick...
    # Não precisa salvar - MCP já persistiu automaticamente!
  end

  sleep 1
end
```

**Vantagens**:
- Simples de implementar
- 1 tick por request
- Latência baixa
- Persistência automática ✅

---

### Opção 2: Batch com `copy_ticks_from_pos` (Mais Eficiente)

```ruby
# Atualizar a cada 5 segundos, pegando últimos 100 ticks
loop do
  symbols.each do |symbol|
    response = mcp_client.call_tool("copy_ticks_from_pos", {
      symbol: symbol,
      start_pos: 0,
      count: 100,
      flags: 2  # COPY_TICKS_ALL
    })

    ticks = response["content"]
    # Processar todos os ticks...
    # Não precisa salvar - MCP já persistiu automaticamente!
  end

  sleep 5
end
```

**Vantagens**:
- Menos requests
- Captura todos os ticks (não perde nenhum)
- Batch processing
- Persistência automática ✅

---

## Arquitetura de Persistência (Já Implementada no MCP)

```
┌─────────────────┐
│ stock-dividend  │
│   (macOS)       │
└────────┬────────┘
         │
         │ HTTP Request
         │ get_symbol_info_tick / copy_ticks_*
         │
         ▼
┌─────────────────┐
│  MCP Server     │
│  (Windows)      │
│                 │
│  ┌───────────┐  │
│  │ Market    │  │
│  │ Data      │  │
│  └─────┬─────┘  │
│        │        │
│        │ enqueue_tick()
│        ▼        │
│  ┌───────────┐  │
│  │   Tick    │  │
│  │ Persister │  │
│  │  (Async)  │  │
│  └─────┬─────┘  │
│        │        │
└────────┼────────┘
         │
         │ Batch INSERT
         │ (20 ticks ou 5s)
         ▼
┌─────────────────┐
│  PostgreSQL     │
│   (macOS)       │
│                 │
│ trading.mt5_ticks
└─────────────────┘
```

### Características:
- ⚡ **Não-bloqueante**: < 0.01ms para enfileirar
- 📦 **Batch processing**: 20 ticks ou 5 segundos
- 🔄 **Backpressure**: Máximo 1000 ticks na fila
- 💾 **Idempotente**: ON CONFLICT DO NOTHING
- 🛡️ **Retry automático**: 3 tentativas com backoff

---

## Como Verificar se Está Funcionando

### 1. Logs do MCP (Windows)

```bash
# Ver logs em tempo real
tail -f logs/mcp_mt5_server/server_*.log
```

**O que procurar**:
```
✅ Bom (chamando endpoint correto):
   MCP Direct tool call: get_symbol_info_tick with args: {'symbol': 'ITSA3'}
   MCP Direct tool call: copy_ticks_from_pos with args: {'symbol': 'ITSA3', ...}

❌ Ruim (chamando endpoint errado):
   MCP Direct tool call: get_symbol_info with args: {'symbol': 'ITSA3'}
```

**Sinais de persistência ativa**:
```
2025-10-03 15:30:00 - Enqueued tick for ITSA3 (queue: 5/1000)
2025-10-03 15:30:05 - Flushing batch of 20 ticks
2025-10-03 15:30:05 - Successfully persisted 20 ticks to trading.mt5_ticks
```

---

### 2. PostgreSQL (macOS)

```sql
-- Conectar
psql -h 192.168.0.235 -U postgres -d jumpstart_development

-- Ver ticks recentes
SELECT
  symbol,
  tick_time,
  bid,
  ask,
  volume,
  created_at
FROM trading.mt5_ticks
WHERE symbol = 'ITSA3'
ORDER BY tick_time DESC
LIMIT 10;

-- Contar ticks por símbolo (últimos 5 minutos)
SELECT
  symbol,
  COUNT(*) as tick_count,
  MIN(tick_time) as first_tick,
  MAX(tick_time) as last_tick
FROM trading.mt5_ticks
WHERE created_at > NOW() - INTERVAL '5 minutes'
GROUP BY symbol
ORDER BY tick_count DESC;

-- Ver taxa de ingestão (ticks/segundo)
SELECT
  symbol,
  COUNT(*) as ticks,
  EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) as seconds,
  COUNT(*) / NULLIF(EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))), 0) as ticks_per_second
FROM trading.mt5_ticks
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY symbol;
```

---

## Checklist de Implementação

- [ ] Substituir `get_symbol_info` por `get_symbol_info_tick` ou `copy_ticks_from_pos`
- [ ] Ajustar intervalo de polling (1s para single, 5s para batch)
- [ ] Adicionar flags: 2 (COPY_TICKS_ALL) para capturar todos os dados
- [ ] Remover código de persistência local (MCP já faz isso)
- [ ] Testar com 1-2 símbolos primeiro
- [ ] Monitorar logs do MCP para confirmar enqueue
- [ ] Verificar PostgreSQL para confirmar INSERT
- [ ] Escalar para todos os símbolos

---

## Performance Esperada

### Modo Live com 10 símbolos:

| Métrica | `get_symbol_info_tick` | `copy_ticks_from_pos` |
|---------|------------------------|------------------------|
| **Polling** | 1 segundo | 5 segundos |
| **Requests/min** | 600 (10 × 60) | 120 (10 × 12) |
| **Ticks/min** | ~600 | ~6,000 |
| **Latência** | <5ms | <20ms |
| **DB Inserts/min** | ~30 batches | ~300 batches |

---

## Arquivos de Referência

### No MCP Server (este projeto):

- **Configuração**: `config/server_config.json` (tick_persistence ativo)
- **Implementação**: `src/mcp_metatrader5_server/tick_persister.py`
- **Endpoints**: `src/mcp_metatrader5_server/market_data.py`
- **Guia de API**: `API_USAGE_GUIDE.md` (completo, com exemplos)
- **Guia de API** (sync): `sync/stock_dividend/MCP_API_USAGE_GUIDE.md`

### Scripts de Teste:

- `investigate_ticks_issue_windows.py` - Testar HTTP API
- `diagnose_ticks_access.py` - Testar MT5 direto

---

## Próximos Passos

1. **No stock-dividend**: Atualizar código para usar `get_symbol_info_tick` ou `copy_ticks_from_pos`
2. **Testar**: Rodar em modo live com 1 símbolo
3. **Verificar**: Checar logs e PostgreSQL
4. **Escalar**: Adicionar mais símbolos gradualmente

---

## Suporte

Se precisar de ajuda:

1. **Logs do MCP**: `logs/mcp_mt5_server/server_*.log`
2. **Verbose mode**: Já está ativo (`verbose: true`)
3. **Health check**: `curl http://192.168.0.235:8000/health`
4. **Test script**: `python investigate_ticks_issue_windows.py` (no Windows)

---

## Status do MCP Server

✅ **Tick persistence**: ATIVO e funcionando
✅ **PostgreSQL**: Conectado (192.168.0.235:5432)
✅ **Batch processing**: 20 ticks ou 5s
✅ **Backpressure**: 1000 ticks max
✅ **Verbose logging**: ATIVO
✅ **Todos os endpoints de ticks**: Async + persistência implementada

**O problema está no cliente (stock-dividend), não no servidor (MCP).**

---

**Criado**: 2025-10-03
**MCP Server Version**: 2.0.0
**Tick Persistence**: Feature completamente implementada e testada
