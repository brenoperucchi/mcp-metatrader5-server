#!/usr/bin/env python3
"""
Servidor MCP MetaTrader 5 - Versão Simplificada

Versão simplificada que funciona diretamente sem dependências complexas.
"""

import sys
import os
import logging
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mt5-mcp-server-simple")

def test_imports():
    """Testa se todas as dependências necessárias estão disponíveis"""
    try:
        import MetaTrader5 as mt5
        logger.info("[OK] MetaTrader5 importado com sucesso")
        
        import pandas as pd
        logger.info("[OK] pandas importado com sucesso")
        
        import numpy as np
        logger.info("[OK] numpy importado com sucesso")
        
        import pydantic
        logger.info("[OK] pydantic importado com sucesso")
        
        import httpx
        logger.info("[OK] httpx importado com sucesso")
        
        import uvicorn
        logger.info("[OK] uvicorn importado com sucesso")
        
        return True
        
    except ImportError as e:
        logger.error(f"[X] Erro de importação: {e}")
        return False

def test_mt5_connection():
    """Testa a conexão com o MetaTrader 5"""
    try:
        import MetaTrader5 as mt5
        
        # Inicializar MT5
        if not mt5.initialize():
            logger.error("[X] Falha ao inicializar MetaTrader5")
            print(f"Erro: {mt5.last_error()}")
            return False
        
        logger.info("[OK] MetaTrader5 inicializado com sucesso")
        
        # Obter informações da versão
        version = mt5.version()
        logger.info(f"[OK] Versão MT5: {version}")
        
        # Obter alguns símbolos como teste
        symbols = mt5.symbols_get()
        if symbols:
            logger.info(f"[OK] {len(symbols)} símbolos disponíveis")
            logger.info(f"Exemplos: {[s.name for s in symbols[:5]]}")
        else:
            logger.warning("[WARN] Nenhum símbolo encontrado")
        
        # Fechar conexão
        mt5.shutdown()
        logger.info("[OK] Conexão MT5 fechada")
        
        return True
        
    except Exception as e:
        logger.error(f"[X] Erro ao testar MT5: {e}")
        return False

def main():
    """Função principal"""
    print("[TEST_TUBE] Teste de Dependências - MCP MetaTrader 5")
    print("=" * 50)
    
    # Teste 1: Importações
    print("\n[PACKAGE] Testando importações...")
    if not test_imports():
        print("[X] Falha nas importações. Instale as dependências:")
        print("pip install -r requirements.txt")
        return 1
    
    # Teste 2: MetaTrader 5
    print("\n[PLUG] Testando conexão MetaTrader 5...")
    if not test_mt5_connection():
        print("[X] Falha na conexão MT5. Verifique se:")
        print("• MetaTrader 5 está instalado")
        print("• MetaTrader 5 está aberto e logado")
        print("• Não há outro processo usando MT5")
        return 1
    
    print("\n[OK] Todos os testes passaram!")
    print("\n[ROCKET] Próximos passos:")
    print("1. Certifique-se que o MT5 está logado em uma conta")
    print("2. Execute o servidor MCP:")
    print("   python start_mcp_server.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
