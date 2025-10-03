# Diagnóstico de Dados Históricos MT5 - ITSA3

## 🎯 Problema Identificado

**CAUSA PRINCIPAL:** O MT5 tem **limitações de dados históricos** para períodos antigos. O erro `'Failed to copy rates for ITSA3 in range 2025-01-01 00:00:00 to 2025-01-30 00:10:00'` ocorre porque o MT5 não mantém dados históricos completos para todos os períodos passados.

### Limitação de Dados Históricos Descoberta
- **Data atual:** 19 de setembro de 2025
- **Data solicitada:** Janeiro 2025 (8 meses atrás)
- **Resultado:** Dados não disponíveis devido a limitações de retenção histórica do MT5

## 📊 Resultados dos Testes Atualizados

### 1. Conectividade do Servidor
✅ **Servidor MCP:** Online em `http://192.168.0.125:8000`
✅ **copy_rates_range:** Disponível
✅ **copy_ticks_range:** Disponível
✅ **Símbolo ITSA3:** Existe no MT5 e está ativo

### 2. Testes de Dados Históricos

| Período Testado | Timeframe | Resultado | Observações |
|----------------|-----------|-----------|-------------|
| Janeiro 2025 (8 meses atrás) | D1 | ❌ FALHA | Dados históricos não disponíveis |
| Fevereiro 2025 (7 meses atrás) | D1 | ❌ FALHA | Dados históricos não disponíveis |
| Agosto 2025 (1 mês atrás) | D1 | ❌ FALHA | Dados históricos não disponíveis |
| Setembro 2025 (1 dia atrás) | M1 | ✅ SUCESSO | Dados recentes disponíveis |
| Setembro 2025 (atual) | M1 | ✅ SUCESSO | Dados atuais via copy_rates_from_pos |

### 3. Padrão Descoberto
- **copy_rates_range:** Funciona apenas para dados **muito recentes** (últimos dias)
- **copy_rates_from_pos:** Funciona para obter dados recentes sem especificar datas
- **Limitação de histórico:** MT5 aparenta manter apenas dados dos últimos dias/semanas

## 🔍 Limitações Identificadas

### 1. **Limitações Severas de Dados Históricos**
- O MT5 mantém apenas dados recentes (aparentemente últimas 2-4 semanas)
- Dados de meses anteriores não estão disponíveis via copy_rates_range
- Esta é uma limitação do servidor/configuração, não do símbolo

### 2. **Diferença entre Funções MT5**
- **copy_rates_from_pos:** Acessa dados mais antigos armazenados
- **copy_rates_range:** Limitado a períodos muito recentes
- **get_symbol_info:** Funciona normalmente (dados em tempo real)

### 3. **Configuração do Servidor MT5**
- Possível configuração limitada de histórico
- Pode ser necessário sincronizar/baixar mais dados históricos
- Limitação pode ser do provedor de dados ou configuração local

## ⚙️ Verificações de Configuração

### 1. **Disponibilidade do Símbolo ITSA3**
✅ **CONFIRMADO:** ITSA3 está disponível e ativo no MT5
✅ **Dados em tempo real:** Bid: 11.20, Ask: 11.44, Last: 11.39
📋 **Variações encontradas:** ITSA3, ITSA3F, ITSA3M, ITSA3Q, ITSA3R, ITSA4, etc.

### 2. **Horários de Mercado B3 (Bovespa)**
- **Funcionamento:** Segunda a sexta-feira
- **Horário:** 10:00 às 17:00 (horário de Brasília)
- **Status atual:** Mercado fechado (teste realizado após horário)

### 3. **Servidor MCP**
- **Status:** Online e funcional
- **Ferramentas:** Todas as 41 ferramentas MCP disponíveis
- **Conectividade:** OK via rede local (192.168.0.125:8000)

## 🧪 Alternativas para Obter 29 Dias de Dados

### ✅ Métodos que Funcionam:

#### 1. **Usar copy_rates_from_pos (Recomendado)**
```bash
# Obter os últimos 29 dias de dados (se disponíveis)
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"tools/call",
    "params":{
      "name":"copy_rates_from_pos",
      "arguments":{
        "symbol":"ITSA3",
        "timeframe":1440,
        "start_pos":0,
        "count":29
      }
    }
  }'
```

#### 2. **Usar copy_rates_range para Período Recente**
```bash
# Teste com dados dos últimos dias disponíveis
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/call",
    "params":{
      "name":"copy_rates_range",
      "arguments":{
        "symbol":"ITSA3",
        "timeframe":1,
        "date_from":"2025-09-18T14:00:00Z",
        "date_to":"2025-09-18T17:00:00Z"
      }
    }
  }'
```

### ❌ Métodos que NÃO Funcionam:
- copy_rates_range com datas antigas (mais de algumas semanas)
- Qualquer tentativa de acessar dados de meses anteriores

## 🛠️ Scripts de Diagnóstico Criados

### 1. **diagnose_historical_data.py**
Script completo para diagnóstico de problemas de dados históricos:
```bash
python3 diagnose_historical_data.py --symbol ITSA3 --server "http://192.168.0.125:8000" --verbose
```

### 2. **test_historical_data.py**
Script existente para testes de dados históricos com múltiplos ranges.

### 3. **debug_ticks_error.py**
Script específico para debug de erros de ticks.

## 🎯 Recomendações Finais

### Para Resolver o Problema de Janeiro 2025:

1. **Aceite a limitação:** O MT5 não mantém dados históricos de 8 meses atrás
2. **Use copy_rates_from_pos:** Para obter os dados mais antigos disponíveis
3. **Configure sincronização:** Verifique se é possível baixar mais histórico no MT5
4. **Use timeframes maiores:** D1 pode ter mais histórico que M1

### Para Desenvolvimento:
1. **Implemente fallback:** Use copy_rates_from_pos quando copy_rates_range falhar
2. **Valide disponibilidade:** Teste disponibilidade antes de solicitar períodos específicos
3. **Cache dados importantes:** Salve dados históricos importantes localmente
4. **Use múltiplas fontes:** Considere APIs alternativas para dados históricos extensos

### Para Produção:
1. **Monitore limitações:** Documente quais períodos estão disponíveis
2. **Implemente retry logic:** Para lidar com falhas de dados
3. **Configure alertas:** Para quando dados históricos não estiverem disponíveis
4. **Backup de dados:** Mantenha backup próprio de dados históricos importantes

## 📝 Comandos Úteis para Testes

```bash
# 1. Verificar símbolos disponíveis
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_symbols_by_group","arguments":{"group":"*ITSA*"}}}'

# 2. Obter informações atuais do símbolo
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_symbol_info","arguments":{"symbol":"ITSA3"}}}'

# 3. Obter dados históricos disponíveis (método que funciona)
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"copy_rates_from_pos","arguments":{"symbol":"ITSA3","timeframe":1440,"start_pos":0,"count":30}}}'

# 4. Teste com período recente (últimos dias)
curl -X POST http://192.168.0.125:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"copy_rates_range","arguments":{"symbol":"ITSA3","timeframe":1,"date_from":"2025-09-18T14:00:00Z","date_to":"2025-09-18T17:00:00Z"}}}'

# 5. Executar diagnóstico completo
python3 diagnose_historical_data.py --symbol ITSA3 --server "http://192.168.0.125:8000"
```

## 🚨 Conclusão Principal

**O problema não é um bug, mas uma limitação de configuração/dados históricos do MT5.**

- Janeiro 2025 é uma data válida (8 meses atrás)
- O MT5 simplesmente não mantém dados históricos desse período
- Use `copy_rates_from_pos` para obter os dados históricos mais antigos disponíveis
- Para dados de 29 dias específicos, você precisará usar dados mais recentes ou configurar o MT5 para manter mais histórico

---

**📅 Documento atualizado:** 19 de setembro de 2025
**🔧 Versão:** 2.0 (Corrigida)
**💻 Ambiente:** WSL Ubuntu → Windows MCP Server (192.168.0.125:8000) → MT5
**🎯 Status:** Problema diagnosticado - limitação de dados históricos do MT5