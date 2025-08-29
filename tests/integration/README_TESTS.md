# MCP MetaTrader 5 - Testes Completos

Este diretório contém testes completos para validar o funcionamento dos servidores MCP MetaTrader 5 em diferentes configurações de mercado.

## Testes Disponíveis

### 1. `test_complete_b3.py` - Teste Mercado B3 (Bolsa Brasileira)

**Servidor:** `http://192.168.0.125:50051`  
**Configuração:** B3 - Bolsa de Valores Brasileira  
**Símbolos testados:** PETR4, VALE3, ITUB4, BBDC4, MGLU3, WEGE3  

Este teste valida:
- ✅ Conectividade com servidor B3
- ✅ Validação de conta demo (segurança)
- ✅ Dados de mercado de ações brasileiras
- ✅ Posições e ordens existentes
- ✅ **Histórico de ordens e deals (últimos 30 dias)**
- ✅ Operações de trading completas (compra, modificação, fechamento)
- ✅ Ordens limitadas e modificações

**Como executar:**
```bash
# Via Python diretamente
python tests/integration/test_complete_b3.py

# Via VS Code Task
Ctrl+Shift+P > Tasks: Run Task > Test Complete B3 Flow
```

### 2. `test_complete_forex.py` - Teste Mercado Forex (Darwinex)

**Servidor:** `http://192.168.0.125:50052`  
**Configuração:** Forex - Darwinex Demo  
**Conta:** 3000064180  
**Servidor MT5:** Darwinex-Demo  
**Símbolos testados:** EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD  

Este teste valida:
- ✅ Conectividade com servidor Forex
- ✅ Validação de conta demo Darwinex (segurança)
- ✅ Dados de mercado de pares de moedas
- ✅ Posições e ordens existentes
- ✅ **Histórico de ordens e deals Forex (últimos 30 dias)**
- ✅ Operações de trading Forex (com pips, spreads)
- ✅ Stop Loss e Take Profit em pips
- ✅ Ordens limitadas com precisão de 5 decimais

**Como executar:**
```bash
# Via Python diretamente
python tests/integration/test_complete_forex.py

# Via VS Code Task
Ctrl+Shift+P > Tasks: Run Task > Test Complete Forex Flow
```

## Funcionalidades de Histórico

### 📋 **Histórico de Ordens (`get_history_orders`)**
- **Função:** Busca ordens históricas (executadas e canceladas)
- **Período:** Últimos 30 dias por padrão
- **Filtros:** Por símbolo, data, ticket específico
- **Dados:** Ticket, tipo, volume, preço, estado, comentário

### 💰 **Histórico de Deals (`get_history_deals`)**
- **Função:** Busca transações executadas (deals)
- **Período:** Últimos 30 dias por padrão  
- **Filtros:** Por símbolo, data, ticket, posição
- **Dados:** Ticket, preço, volume, profit, comissão, swap
- **Análise:** Cálculo automático de P&L total, estatísticas

### 📊 **Estatísticas Calculadas**
```
📈 B3 (Ações):
• Lucro total em R$
• Comissão total em R$
• Volume total em ações/lotes
• Análise por ação específica

💱 Forex (Pares):
• Lucro total em USD
• Comissão total em USD  
• Swap total em USD
• Volume total em lotes
• Análise por par específico
```

## Relatórios Gerados

Cada teste gera um relatório JSON detalhado:

- `test_report.json` - Resultado do teste B3
- `test_report_forex.json` - Resultado do teste Forex

## Segurança

🔒 **IMPORTANTE:** Ambos os testes incluem validação de segurança que:

1. **Verifica se a conta é DEMO** antes de qualquer operação de trading
2. **Bloqueia automaticamente** operações em contas reais
3. **Usa volumes mínimos** para testes seguros
4. **Fecha automaticamente** todas as posições abertas durante o teste

## Pré-requisitos

1. **Servidores MCP ativos:**
   - B3: `http://192.168.0.125:50051`
   - Forex: `http://192.168.0.125:50052`

2. **MetaTrader 5 configurado** com contas demo:
   - Conta B3 demo ativa
   - Conta Darwinex demo (3000064180)

3. **Cliente MCP funcionando:**
   ```bash
   pip install -r client/requirements.txt
   ```

## Interpretação dos Resultados

### Códigos de Retorno MT5

- `10009` - ✅ **DONE** - Operação executada com sucesso
- `10015` - ❌ **INVALID_PRICE** - Preço inválido
- `10017` - ❌ **INVALID_VOLUME** - Volume inválido
- `10018` - ⚠️ **MARKET_CLOSED** - Mercado fechado
- `10019` - ❌ **NO_MONEY** - Saldo insuficiente
- `10020` - ⚠️ **PRICE_CHANGED** - Preço mudou (requote)
- `10021` - ❌ **TRADE_DISABLED** - Trading desabilitado

### Taxa de Sucesso

- **100%** - ✅ Todos os testes passaram
- **90-99%** - ⚠️ Alguns problemas menores (mercado fechado, etc)
- **<90%** - ❌ Problemas sérios que precisam investigação

## Troubleshooting

### Erro de Conectividade
```bash
# Verificar se o servidor está rodando
curl -X POST http://192.168.0.125:50051/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Conta não é Demo
- Verificar se está conectado à conta demo correta no MT5
- Para B3: conta deve estar configurada como demo
- Para Forex: deve ser conta Darwinex-Demo (3000064180)

### Símbolos não encontrados
- **B3:** Verificar se ações brasileiras estão disponíveis
- **Forex:** Verificar se pares de moedas estão ativos

### Mercado fechado
- **B3:** Funciona em horário comercial brasileiro (9h-18h)
- **Forex:** Mercado 24h, mas pode ter pouca liquidez aos fins de semana
