#!/usr/bin/env python3
"""
[TEST_TUBE] Teste de Conectividade - MCP MetaTrader 5

Script para testar a conectividade entre Windows e macOS.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import httpx
    from client.mcp_mt5_client import MT5MCPClient
except ImportError as e:
    print(f"[X] Erro de importação: {e}")
    print("[IDEA] Execute: pip install -r client/requirements.txt")
    sys.exit(1)

async def test_basic_connectivity(host: str, port: int):
    """Teste básico de conectividade HTTP"""
    print(f"[PLUG] Testando conectividade básica para {host}:{port}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"http://{host}:{port}/health")
            print(f"[OK] Servidor respondeu: {response.status_code}")
            return True
    except Exception as e:
        print(f"[X] Erro de conectividade: {e}")
        return False

async def test_mcp_tools(host: str, port: int):
    """Teste das ferramentas MCP"""
    print(f"[SETUP] Testando ferramentas MCP...")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Testar listagem de ferramentas
            response = await client.post(
                f"http://{host}:{port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    tools = data["result"].get("tools", [])
                    print(f"[OK] {len(tools)} ferramentas MCP disponíveis:")
                    for tool in tools[:5]:  # Mostrar apenas as primeiras 5
                        print(f"   • {tool.get('name', 'N/A')}")
                    return True
            
            print(f"[X] Resposta inesperada: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[X] Erro ao testar ferramentas MCP: {e}")
        return False

async def test_mt5_functions(host: str, port: int):
    """Teste das funções específicas do MT5"""
    print(f"[DATA] Testando funções do MetaTrader 5...")
    
    try:
        async with MT5MCPClient(f"http://{host}:{port}") as client:
            
            # Teste 1: Conexão
            print("   [TOOL] Testando conexão...")
            try:
                result = await client.test_connection()
                print(f"   [OK] Conexão: {result}")
            except Exception as e:
                print(f"   [WARN] Conexão falhou: {e}")
            
            # Teste 2: Símbolos
            print("   [TRADE] Testando listagem de símbolos...")
            try:
                symbols_result = await client.list_symbols()
                if symbols_result.get("error"):
                    print(f"   [X] Erro nos símbolos: {symbols_result['error']}")
                    return False
                
                symbols = symbols_result.get('result', {}).get('content', [])
                print(f"   [OK] {len(symbols)} símbolos encontrados")
            except Exception as e:
                print(f"   [X] Erro nos símbolos: {e}")
                return False
            
            # Teste 3: Informações de conta
            print("   [MONEY] Testando informações da conta...")
            try:
                account = await client.get_account_info()
                if account.get("error"):
                    print(f"   [X] Erro na conta: {account['error']}")
                else:
                    account_data = account.get('result', {}).get('content', {})
                    print(f"   [OK] Conta: {account_data.get('login', 'N/A')}")
            except Exception as e:
                print(f"   [WARN] Conta não acessível: {e}")
            
            # Teste 4: Book L2 (se disponível)
            if symbols and len(symbols) > 0:
                test_symbol = symbols[0]  # Use first available symbol
                print(f"   📚 Testando book L2 para {test_symbol}...")
                try:
                    book = await client.get_book_l2(test_symbol)
                    if book.get("error"):
                        print(f"   [WARN] Book não disponível: {book['error']}")
                    else:
                        book_data = book.get('result', {}).get('content', [])
                        print(f"   [OK] Book L2: {len(book_data)} níveis")
                except Exception as e:
                    print(f"   [WARN] Book L2 não disponível: {e}")
            
            return True
            
    except Exception as e:
        print(f"[X] Erro geral nas funções MT5: {e}")
        return False

async def run_connectivity_tests():
    """Executa todos os testes de conectividade"""
    print("[TEST_TUBE] TESTE DE CONECTIVIDADE MCP MetaTrader 5")
    print("=" * 50)
    
    # Configurações padrão
    host = "192.168.0.125"  # Substitua pelo IP do Windows
    port = 50051
    
    print(f"[TP] Target: {host}:{port}")
    print("=" * 50)
    
    # Lista de testes
    tests = [
        ("Conectividade Básica", test_basic_connectivity(host, port)),
        ("Ferramentas MCP", test_mcp_tools(host, port)),
        ("Funções MT5", test_mt5_functions(host, port)),
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n[RUN] {test_name}")
        print("-" * 30)
        
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"[X] Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n[PHASE] RESUMO DOS TESTES")
    print("=" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "[OK] PASSOU" if result else "[X] FALHOU"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n[TP] Resultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("[SUCCESS] Todos os testes passaram! Sistema pronto para uso.")
    else:
        print("[WARN] Alguns testes falharam. Verifique a configuração.")
        print("\n[TOOL] DICAS DE TROUBLESHOOTING:")
        print("• Servidor MCP está rodando no Windows?")
        print("• Firewall liberado na porta 50051?")
        print("• MT5 logado e conectado?")
        print("• IP do Windows correto?")

def main():
    """Função principal"""
    try:
        asyncio.run(run_connectivity_tests())
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n[X] Erro fatal: {e}")

if __name__ == "__main__":
    # Verificar se está sendo executado do diretório correto
    if not Path("client/mcp_mt5_client.py").exists():
        print("[X] Execute este script do diretório raiz do projeto")
        print("[IDEA] cd mcp-metatrader5-server && python tests/integration/test_connectivity.py")
        sys.exit(1)
    
    main()
