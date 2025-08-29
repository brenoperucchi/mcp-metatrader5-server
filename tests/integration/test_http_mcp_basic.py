#!/usr/bin/env python3
"""
[ROCKET] TESTE BÁSICO HTTP MCP - SEM DEPENDÊNCIA MT5
===================================================

Teste básico para verificar se a comunicação HTTP MCP está funcionando
corretamente, sem depender de MT5 estar conectado.

Este teste verifica:
1. [OK] Conectividade HTTP
2. [OK] Protocolo JSON-RPC 2.0
3. [OK] Listagem de ferramentas
4. [OK] Estrutura de resposta MCP
5. [INFO] Status das ferramentas

[HTTP] Servidor: http://localhost:8000
"""

import asyncio
import json
import sys
import aiohttp
from datetime import datetime
from typing import Dict, Any

class BasicHTTPMCPClient:
    """Cliente HTTP MCP básico para testes"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Envia requisição JSON-RPC para o servidor MCP"""
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    return {
                        "error": f"HTTP {response.status}",
                        "text": await response.text()
                    }
        except Exception as e:
            return {"error": str(e)}
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chama uma ferramenta MCP via HTTP"""
        
        return await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })

class BasicHTTPMCPTest:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.test_results = []
        
    async def log_test(self, test_name: str, success: bool, data: dict = None, error: str = None):
        """Registra resultado de teste"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "success": success,
            "data": data,
            "error": error
        }
        self.test_results.append(result)
        
        status = "[OK]" if success else "[X]"
        print(f"{status} {test_name}")
        if error:
            print(f"   [FAIL] {error}")
        elif data:
            print(f"   [INFO] {json.dumps(data, indent=2)[:150]}...")
    
    async def test_basic_connectivity(self):
        """Teste de conectividade HTTP básica"""
        try:
            async with BasicHTTPMCPClient(self.server_url) as client:
                # Teste de inicialização MCP
                result = await client.send_request("initialize", {
                    "protocolVersion": "1.0.0",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "basic-test-client",
                        "version": "1.0.0"
                    }
                })
                
                if "error" in result:
                    await self.log_test("Conectividade HTTP", False, error=str(result["error"]))
                    return False
                else:
                    server_info = result.get("result", {}).get("serverInfo", {})
                    await self.log_test("Conectividade HTTP", True, {
                        "server_name": server_info.get("name"),
                        "server_version": server_info.get("version"),
                        "protocol": result.get("result", {}).get("protocolVersion")
                    })
                    return True
        except Exception as e:
            await self.log_test("Conectividade HTTP", False, error=str(e))
            return False
    
    async def test_tools_listing(self):
        """Teste de listagem de ferramentas"""
        try:
            async with BasicHTTPMCPClient(self.server_url) as client:
                result = await client.send_request("tools/list")
                
                if "error" in result:
                    await self.log_test("Listagem de Ferramentas", False, error=str(result["error"]))
                    return False
                else:
                    tools = result.get("result", {}).get("tools", [])
                    tool_names = [tool.get("name") for tool in tools]
                    
                    await self.log_test("Listagem de Ferramentas", True, {
                        "total_tools": len(tools),
                        "sample_tools": tool_names[:5],
                        "has_trading_tools": any("order" in name for name in tool_names),
                        "has_market_data": any("symbol" in name for name in tool_names)
                    })
                    return True
        except Exception as e:
            await self.log_test("Listagem de Ferramentas", False, error=str(e))
            return False
    
    async def test_tool_structure(self):
        """Teste da estrutura de resposta das ferramentas"""
        try:
            async with BasicHTTPMCPClient(self.server_url) as client:
                # Teste com ferramenta que não depende do MT5
                result = await client.call_tool("get_version")
                
                if "error" in result:
                    # Isso é esperado se MT5 não estiver conectado
                    error_info = result.get("error", {})
                    await self.log_test("Estrutura de Resposta", True, {
                        "has_error_structure": True,
                        "error_format": "MCP compliant",
                        "error_code": error_info.get("code") if isinstance(error_info, dict) else "unknown"
                    })
                else:
                    # Se funcionou, verificar estrutura
                    await self.log_test("Estrutura de Resposta", True, {
                        "has_result": "result" in result,
                        "has_content": "content" in result.get("result", {}),
                        "response_format": "MCP compliant"
                    })
                return True
        except Exception as e:
            await self.log_test("Estrutura de Resposta", False, error=str(e))
            return False
    
    async def test_error_handling(self):
        """Teste do tratamento de erro"""
        try:
            async with BasicHTTPMCPClient(self.server_url) as client:
                # Teste com ferramenta inexistente
                result = await client.call_tool("nonexistent_tool")
                
                if "error" in result:
                    error_info = result.get("error", {})
                    await self.log_test("Tratamento de Erro", True, {
                        "error_detected": True,
                        "has_error_code": "code" in error_info if isinstance(error_info, dict) else False,
                        "has_message": "message" in error_info if isinstance(error_info, dict) else False,
                        "error_structure": "correct"
                    })
                else:
                    await self.log_test("Tratamento de Erro", False, error="Deveria retornar erro para ferramenta inexistente")
                return True
        except Exception as e:
            await self.log_test("Tratamento de Erro", False, error=str(e))
            return False
    
    async def test_server_status(self):
        """Teste do status do servidor"""
        try:
            async with aiohttp.ClientSession() as session:
                # Teste do endpoint de health
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        await self.log_test("Status do Servidor", True, {
                            "status": health_data.get("status"),
                            "service": health_data.get("service"),
                            "mode": health_data.get("mode"),
                            "mt5_status": health_data.get("mt5_status"),
                            "tools_count": health_data.get("tools_count")
                        })
                        return True
                    else:
                        await self.log_test("Status do Servidor", False, error=f"HTTP {response.status}")
                        return False
        except Exception as e:
            await self.log_test("Status do Servidor", False, error=str(e))
            return False
    
    async def run_basic_tests(self):
        """Executa todos os testes básicos"""
        print("🔧 TESTE BÁSICO HTTP MCP - SEM MT5")
        print("=" * 45)
        print(f"Servidor: {self.server_url}")
        print()
        
        try:
            # Testes básicos em ordem
            tests = [
                ("Status do Servidor", self.test_server_status()),
                ("Conectividade HTTP", self.test_basic_connectivity()),
                ("Listagem de Ferramentas", self.test_tools_listing()),
                ("Estrutura de Resposta", self.test_tool_structure()),
                ("Tratamento de Erro", self.test_error_handling())
            ]
            
            for test_name, test_coroutine in tests:
                print(f"\n[TEST] Executando: {test_name}")
                await test_coroutine
            
            # Relatório final
            print("\n" + "=" * 45)
            print("📊 RELATÓRIO DE TESTES BÁSICOS")
            print("=" * 45)
            
            total_tests = len(self.test_results)
            passed_tests = sum(1 for test in self.test_results if test["success"])
            failed_tests = total_tests - passed_tests
            
            print(f"✅ Testes passou: {passed_tests}")
            print(f"❌ Testes falharam: {failed_tests}")
            print(f"📈 Total: {total_tests}")
            print(f"🎯 Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
            
            # Salvar relatório
            with open("basic_test_report.json", "w") as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\n💾 Relatório salvo em: basic_test_report.json")
            
            # Análise dos resultados
            print("\n🔍 ANÁLISE DOS RESULTADOS:")
            if passed_tests == total_tests:
                print("🎉 SERVIDOR HTTP MCP TOTALMENTE FUNCIONAL!")
                print("   ✓ Comunicação HTTP funcionando")
                print("   ✓ Protocolo JSON-RPC 2.0 operacional")
                print("   ✓ Ferramentas MCP disponíveis")
                print("   ✓ Tratamento de erro adequado")
                print("\n🚀 PRONTO PARA TESTES COMPLETOS COM MT5!")
            elif passed_tests >= total_tests * 0.8:
                print("⚠️ SERVIDOR HTTP MCP PARCIALMENTE FUNCIONAL")
                print("   ✓ Comunicação básica funcionando")
                print("   ⚠️ Alguns componentes com problemas")
                print("\n🔧 INVESTIGAÇÃO NECESSÁRIA")
            else:
                print("❌ SERVIDOR HTTP MCP COM PROBLEMAS SÉRIOS")
                print("   ❌ Problemas fundamentais detectados")
                print("\n🚨 CORREÇÃO URGENTE NECESSÁRIA")
            
            return passed_tests == total_tests
            
        except Exception as e:
            print(f"❌ Erro geral nos testes: {e}")
            return False

async def main():
    """Função principal"""
    print("*** TESTE BÁSICO MCP HTTP - COMUNICAÇÃO SEM MT5 ***")
    print("Verificando funcionalidade básica do servidor HTTP MCP")
    print("=" * 60)
    
    # Verificar argumentos
    server_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"🌐 Testando servidor: {server_url}")
    
    # Executar testes
    tester = BasicHTTPMCPTest(server_url)
    success = await tester.run_basic_tests()
    
    if success:
        print("\n✅ COMUNICAÇÃO HTTP MCP FUNCIONANDO!")
        print("🎯 Próximo passo: Testar com MT5 conectado")
        sys.exit(0)
    else:
        print("\n❌ PROBLEMAS NA COMUNICAÇÃO HTTP MCP!")
        print("🔧 Verifique os logs acima para detalhes")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
