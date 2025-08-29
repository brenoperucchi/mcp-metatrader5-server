# Fork MCP - MetaTrader 5 MCP Server (Enhanced)

Esta é a versão aprimorada do MetaTrader 5 MCP Server, baseada no FastMCP com funcionalidades adicionais de trading e multi-configuração.

## 🚀 Características

- **Porta padrão**: 8000 ou 8080 
- **Implementação**: FastMCP com extensões personalizadas
- **Multi-configuração**: Suporte para B3 (ações brasileiras) e Forex
- **Funcionalidades**: 37+ ferramentas MT5 completas
- **Segurança**: Validação de conta demo para operações de trading
- **Compatibilidade**: Funciona no Linux/WSL com mock do MT5

## 📊 Funcionalidades Implementadas

### 🔧 Ferramentas de Trading
- ✅ **order_send** - Enviar ordens ao mercado
- ✅ **order_cancel** - Cancelar ordens pendentes  
- ✅ **order_modify** - Modificar ordens existentes
- ✅ **order_check** - Verificar viabilidade de ordens
- ✅ **position_modify** - Modificar Stop Loss e Take Profit
- ✅ **positions_get** - Obter posições abertas
- ✅ **orders_get** - Obter ordens ativas
- ✅ **history_orders_get** - Histórico de ordens
- ✅ **history_deals_get** - Histórico de negociações

### 📈 Dados de Mercado
- ✅ **symbols_get** - Lista de símbolos disponíveis
- ✅ **symbol_info** - Informações detalhadas do símbolo
- ✅ **symbol_info_tick** - Último tick do símbolo
- ✅ **copy_rates_from_pos** - Dados históricos de preços
- ✅ **copy_ticks_from** - Dados de ticks
- ✅ **market_book_add/get/release** - Book de ofertas (Nível II)

### 🏦 Informações da Conta
- ✅ **get_account_info** - Informações da conta
- ✅ **get_terminal_info** - Informações do terminal
- ✅ **validate_demo_for_trading** - Validação de segurança

### ⚙️ Multi-Configuração
- ✅ **get_available_configs** - Listar configurações (B3/Forex)
- ✅ **get_current_config** - Configuração ativa atual
- ✅ **switch_config** - Alternar entre configurações
- ✅ **initialize** - Inicializar com configuração ativa

### 📚 Recursos Informativos
- ✅ Constantes de tipos de ordem (ORDER_TYPE_*)
- ✅ Constantes de preenchimento (ORDER_FILLING_*)
- ✅ Constantes de tempo (ORDER_TIME_*)  
- ✅ Constantes de ações (TRADE_ACTION_*)

## 🏗️ Estrutura do Projeto

```
fork_mcp/
├── src/
│   └── mcp_metatrader5_server/
│       ├── __init__.py
│       ├── server.py          # Servidor principal + multi-config
│       ├── trading.py         # Ferramentas de trading 
│       ├── market_data.py     # Dados de mercado
│       ├── mt5_configs.py     # Configurações B3/Forex
│       └── mt5_mock.py        # Mock para desenvolvimento
├── .venv/                     # Ambiente virtual
├── pyproject.toml            # Dependências e configuração
├── run_fork_mcp.py           # Script de execução
├── setup_claude_desktop.py   # Configuração do Claude Desktop
└── README.md
```

## 🛠️ Instalação e Configuração

### 1. Ambiente Virtual
```bash
cd fork_mcp
python -m venv .venv

# Linux/WSL
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Instalar Dependências
```bash
pip install -e .
```

### 3. Configurar Claude Desktop (Opcional)
```bash
python setup_claude_desktop.py
```

### 4. Executar Servidor

**🔄 Modo STDIO (Claude Desktop - Recomendado):**
```bash
python run_fork_mcp.py
```

**🌐 Modo HTTP (Testes e Desenvolvimento):**
```bash
python mcp_mt5_server.py --port 8000
```

**Diferenças:**
- **STDIO**: Para uso com Claude Desktop (protocolo MCP padrão)
- **HTTP**: Para testes via browser/curl (endpoints REST: /health, /info, /config)

## 🔧 Multi-Configuração B3/Forex

O servidor suporte duas configurações pré-definidas:

### B3 - Ações Brasileiras
```python
"b3": {
    "name": "B3 - Ações Brasileiras",
    "market_type": "B3", 
    "account": 123456789,
    "server": "XP-Demo"
}
```

### Forex - Mercado Global  
```python
"forex": {
    "name": "Forex - Mercado Global",
    "market_type": "Forex",
    "account": 987654321, 
    "server": "MetaQuotes-Demo"
}
```

### Como Alternar
```python
# Via ferramentas MCP
switch_config("forex")  # Muda para Forex
switch_config("b3")     # Volta para B3

# Verificar configuração atual
get_current_config()    

# Listar todas as configurações
get_available_configs()
```

## 🔒 Segurança

O servidor inclui validação automática de conta demo para operações de trading:

- ✅ Operações só são permitidas em contas demo
- ✅ Validação automática antes de cada operação de trading
- ✅ Logs de segurança para todas as tentativas

## 🐧 Compatibilidade Linux/WSL

O servidor funciona perfeitamente no Linux/WSL através do sistema de mock:

- ✅ Mock completo da biblioteca MetaTrader5 
- ✅ Dados simulados realistas para desenvolvimento
- ✅ Todas as funcionalidades testáveis sem MT5 real
- ✅ Logs informativos sobre o uso do mock

## 📋 Exemplo de Uso no Claude Desktop

```json
{
  "mcpServers": {
    "mcp-metatrader5": {
      "command": "python",
      "args": ["/caminho/para/fork_mcp/run_fork_mcp.py"],
      "cwd": "/caminho/para/fork_mcp"
    }
  }
}
```

## ✅ Status do Projeto

- 🟢 **Etapa 2 Concluída**: 100% dos requisitos implementados
- 🟢 **37+ ferramentas MCP** funcionais
- 🟢 **Multi-configuração** B3/Forex operacional  
- 🟢 **Segurança** com validação de conta demo
- 🟢 **Compatibilidade** Linux/WSL via mock
- 🟢 **Integração** Claude Desktop configurada

## 📈 Próximos Passos

- [ ] Implementar WebSocket para dados em tempo real
- [ ] Adicionar mais configurações de broker
- [ ] Expandir funcionalidades de análise técnica
- [ ] Implementar sistema de alertas

---

**Baseado no fork original**: https://github.com/Qoyyuum/mcp-metatrader5-server