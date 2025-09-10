# 🔧 Sistema de Configuração Persistente

## **Visão Geral**

Sistema que permite configurar o servidor MT5 com modo verbose (`--info`) e outras opções que **persistem entre restarts**.

- ✅ **Sem variáveis de ambiente** (export/set)
- ✅ **Configuração por porta** - Múltiplos servidores
- ✅ **Persistência automática** em JSON
- ✅ **Compatível com restart automático**

## **📁 Estrutura**

```
mcp-metatrader5-server/
├── config/
│   └── server_config.json          # Configurações persistentes
├── server_config.py                # Gerenciador de configuração
├── watch_server.py                 # Watcher com --info
├── restart_server.py               # Restart que respeita config
└── test_config.py                  # Testes do sistema
```

## **🚀 Como Usar**

### **1. Ativar modo verbose e iniciar servidor:**
```bash
# Primeiro ativar verbose no JSON
python server_config.py --port 8000 --verbose

# Depois iniciar servidor (carregará verbose do JSON)
python watch_server.py --port 8000
```

### **2. Verificar configuração salva:**
```bash
python server_config.py --port 8000 --show
```

### **3. Reiniciar (respeitará configuração JSON):**
```bash
python restart_server.py --port 8000
```

### **4. Desativar verbose:**
```bash
python server_config.py --port 8000 --no-verbose
```

## **⚙️ Comandos Disponíveis**

### **watch_server.py**
```bash
# Servidor (usa configuração do JSON)
python watch_server.py --port 8000

# Para diferentes portas (cada uma usa sua configuração JSON)
python watch_server.py --port 8001  # Verbose se configurado no JSON
python watch_server.py --port 8002  # Normal se não configurado
```

### **restart_server.py**
```bash
# Restart respeitando configuração salva
python restart_server.py --port 8000

# Mostra configuração atual antes de reiniciar
# Exemplo de output:
# 📊 Modo verbose: ✅ ATIVO
# 🔧 Host: 0.0.0.0  
# ⚙️ Config MT5: b3
```

### **server_config.py**
```bash
# Mostrar configuração atual
python server_config.py --port 8000 --show

# Ativar verbose manualmente
python server_config.py --port 8000 --verbose

# Desativar verbose
python server_config.py --port 8000 --no-verbose

# Reset total da configuração
python server_config.py --port 8000 --reset
```

## **📊 Arquivo de Configuração**

**Localização:** `config/server_config.json`

**Exemplo:**
```json
{
  "servers": {
    "8000": {
      "port": 8000,
      "verbose": true,
      "host": "0.0.0.0",
      "mt5_config": "b3",
      "created": "2025-09-08T18:33:23.942529",
      "last_updated": "2025-09-08T18:35:12.123456"
    },
    "8001": {
      "port": 8001,
      "verbose": false,
      "host": "0.0.0.0",
      "mt5_config": "forex",
      "created": "2025-09-08T18:40:00.000000",
      "last_updated": "2025-09-08T18:40:15.123456"
    }
  },
  "global": {
    "created": "2025-09-08T18:33:23.940000",
    "version": "2.0.0",
    "last_updated": "2025-09-08T18:35:12.123456"
  }
}
```

## **🔄 Fluxo Completo**

### **Cenário 1: Desenvolvimento verbose**
```bash
# 1. Ativar verbose via JSON
python server_config.py --port 8000 --verbose

# 2. Iniciar servidor
python watch_server.py --port 8000

# 3. Fazer mudanças no código...

# 4. Reiniciar (mantém verbose automaticamente)
python restart_server.py --port 8000

# 5. Servidor reinicia com --info ativo ✅
```

### **Cenário 2: Produção normal**
```bash  
# 1. Iniciar normal
python watch_server.py --port 8000

# 2. Reiniciar (mantém modo normal)
python restart_server.py --port 8000

# 3. Servidor reinicia sem verbose ✅
```

### **Cenário 3: Alternar modos**
```bash
# Ativar verbose posteriormente
python server_config.py --port 8000 --verbose

# Reiniciar (agora com verbose)
python restart_server.py --port 8000

# Desativar verbose
python server_config.py --port 8000 --no-verbose

# Reiniciar (volta ao normal)
python restart_server.py --port 8000
```

## **🎯 Funcionalidades Principais**

### ✅ **Persistência Automática**
- Configurações salvam automaticamente
- Sobrevivem a restarts do sistema
- Arquivo JSON legível e editável

### ✅ **Configuração por Porta**
- Múltiplos servidores com configs diferentes
- Cada porta tem suas próprias configurações
- Não há conflitos entre servidores

### ✅ **Integração Completa**
- `watch_server.py` salva configurações
- `restart_server.py` respeita configurações
- Comandos CLI para gerenciar configs

### ✅ **Extensibilidade**
- Fácil adicionar novas configurações
- Estrutura JSON flexível
- Versionamento da configuração

## **🧪 Testes**

```bash
# Testar sistema completo
python test_config.py

# Resultado esperado:
# ✅ Flag --info presente/removida conforme config
# ✅ Arquivo de configuração criado/atualizado
# ✅ Persistência funcionando
```

## **🔧 Troubleshooting**

### **Config não persiste:**
```bash
# Verificar se arquivo foi criado
ls -la config/server_config.json

# Verificar permissões
chmod 644 config/server_config.json

# Reset total se necessário
python server_config.py --port 8000 --reset
```

### **Verbose não ativa:**
```bash
# Verificar configuração atual
python server_config.py --port 8000 --show

# Forçar ativação
python server_config.py --port 8000 --verbose
```

### **Múltiplas portas confusas:**
```bash
# Listar todas as configurações
python server_config.py --show

# Reset tudo se necessário  
rm config/server_config.json
```

---

## **📋 Resumo de Comandos**

| Ação | Comando |
|------|---------|
| **Ativar verbose** | `python server_config.py --port 8000 --verbose` |
| **Desativar verbose** | `python server_config.py --port 8000 --no-verbose` |
| **Iniciar servidor** | `python watch_server.py --port 8000` |
| **Reiniciar** | `python restart_server.py --port 8000` |
| **Ver config** | `python server_config.py --port 8000 --show` |
| **Reset config** | `python server_config.py --port 8000 --reset` |
| **Testar sistema** | `python test_config.py` |

✅ **Sistema pronto para uso!**