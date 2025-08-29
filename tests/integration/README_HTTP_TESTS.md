# Testes HTTP MCP - fork_mcp

Este diretório contém testes específicos para o servidor HTTP MCP implementado em `fork_mcp/run_http_server.py`.

## 🌐 Servidor HTTP MCP

O servidor HTTP MCP permite acesso remoto às ferramentas MetaTrader 5 via protocolo HTTP usando JSON-RPC 2.0, compatível com Claude CLI.

### Iniciando o Servidor
```bash
# Servidor HTTP MCP na porta 8000
python fork_mcp/run_http_server.py --port 8000

# Verificar se está funcionando
curl http://localhost:8000/health
```

## 🧪 Testes Disponíveis

### 1. Teste Básico HTTP (`test_http_mcp_basic.py`)
```bash
python fork_mcp/tests/integration/test_http_mcp_basic.py
```

**O que testa:**
- ✅ Status do servidor (/health endpoint)
- ✅ Conectividade HTTP (protocolo JSON-RPC 2.0)
- ✅ Listagem de ferramentas (34 tools disponíveis)
- ✅ Estrutura de resposta MCP (formato compliant)
- ⚠️ Tratamento de erro (pequeno ajuste necessário)

**Status atual:** 80% funcional (4/5 testes passam)

### 2. Teste Completo B3 HTTP (`test_complete_b3_http.py`)
```bash
python fork_mcp/tests/integration/test_complete_b3_http.py
```

**O que testa:**
- Conectividade com símbolos B3
- Validação de conta demo
- Dados de mercado em tempo real
- Posições e ordens
- Histórico de trading
- **Operações de trading completas** (compra, venda, modificação, cancelamento)

**Diferenças do teste original:**
- Usa protocolo HTTP MCP ao invés de servidor dedicado
- Conecta na porta 8000 ao invés de 50051
- Utiliza JSON-RPC 2.0 com `tools/call` ao invés de chamadas diretas
- Compatível com `fork_mcp/run_http_server.py`

### 3. Teste Completo B3 Original (`test_complete_b3.py`)
```bash
python fork_mcp/tests/integration/test_complete_b3.py
```

Este é o teste original que funciona com o servidor dedicado na porta 50051.

## 📊 Status dos Sistemas

### ✅ Servidor Dedicado (50051) - 100% FUNCIONAL
```bash
# Terminal 1: Iniciar servidor
python main_mcp/dedicated_server.py --config b3 --port 50051

# Terminal 2: Executar teste
python main_mcp/tests/integration/test_complete_b3.py
# Resultado: 16/16 testes passaram (100%)
```

### ⚠️ Servidor HTTP MCP (8000) - 80% FUNCIONAL
```bash
# Terminal 1: Iniciar servidor HTTP
python fork_mcp/run_http_server.py --port 8000

# Terminal 2: Executar testes
python fork_mcp/tests/integration/test_http_mcp_basic.py
# Resultado: 4/5 testes básicos passaram (80%)

python fork_mcp/tests/integration/test_complete_b3_http.py
# Aguarda MT5 conectado em conta demo
```

## 🚀 Uso com Claude CLI

### Configuração Remota
```bash
# Adicionar servidor MCP HTTP
claude mcp add mt5 --transport http http://192.168.0.125:8000/

# Testar conexão
claude mcp test mt5

# Listar ferramentas disponíveis
claude mcp list-tools mt5

# Usar com Claude
claude chat --mcp mt5
```

## 🔧 Dependências dos Testes

### Requisitos Python
```bash
pip install aiohttp asyncio json pathlib
```

### Requisitos MetaTrader 5
- MetaTrader 5 instalado e conectado
- Conta demo B3 configurada (para testes de trading)
- Símbolos B3 disponíveis (PETR4, VALE3, ITUB4, etc.)

## 📁 Estrutura dos Arquivos

```
fork_mcp/tests/integration/
├── README_HTTP_TESTS.md         # Este arquivo
├── test_http_mcp_basic.py       # Teste básico HTTP (80% passa)
├── test_complete_b3_http.py     # Teste completo B3 via HTTP
├── test_complete_b3.py          # Teste original (servidor dedicado)
├── test_complete_forex.py       # Teste Forex
├── test_connectivity.py         # Teste conectividade
└── test_forex_market.py         # Teste mercado Forex
```

## 🎯 Próximos Passos

### Para desenvolvimento HTTP:
1. **Ajustar tratamento de erro** (teste #5 falhando)
2. **Testar com MT5 conectado** em conta demo
3. **Verificar validação de segurança** demo vs real

### Para uso em produção:
1. **Use servidor dedicado** (100% funcional)
2. **Aguarde correções HTTP** (80% → 100%)
3. **Configure Claude CLI** quando HTTP estiver pronto

## 📚 Referências

- **Task Completions**: ../TASK_1_COMPLETION.md até TASK_6_COMPLETION.md
- **Servidor Original**: main_mcp/dedicated_server.py
- **Servidor HTTP**: fork_mcp/run_http_server.py
- **Cliente MCP**: main_mcp/client/mcp_mt5_client.py
