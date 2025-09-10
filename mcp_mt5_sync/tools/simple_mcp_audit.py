#!/usr/bin/env python3
"""
E2.0 - Auditoria Simplificada do MCP MT5
Baseada em chamadas HTTP diretas ao servidor
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from pathlib import Path

class SimpleMCPAudit:
    def __init__(self, server_url="192.168.0.125:8000"):
        self.server_url = server_url
        self.base_url = f"http://{server_url}"
        self.rpc_url = f"{self.base_url}/mcp"
        self.request_id = 1
        self.results = {}

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Chama ferramenta via tools/call (protocolo MCP correto)"""
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }
        self.request_id += 1
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "data": result,
                            "latency_ms": latency_ms
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "latency_ms": latency_ms
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    async def call_method(self, method: str, params: dict = None):
        """Chama método MCP direto (para tools/list, etc)"""
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        self.request_id += 1
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "data": result,
                            "latency_ms": latency_ms
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "latency_ms": latency_ms
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }

    async def audit_tools_list(self):
        """Lista todas as ferramentas disponíveis"""
        print("🔍 Listando ferramentas disponíveis...")
        result = await self.call_method("tools/list")
        
        if result["success"]:
            tools_data = result["data"].get("result", {})
            tools = tools_data.get("tools", [])
            
            print(f"✅ {len(tools)} ferramentas encontradas")
            
            # Categorizar ferramentas
            categories = {
                "connection": [],
                "market_data": [],
                "trading": [],
                "positions": [],
                "history": [],
                "other": []
            }
            
            for tool in tools:
                name = tool["name"]
                desc = tool["description"]
                
                if name in ["initialize", "shutdown", "login", "get_account_info", "get_terminal_info", "get_version", "validate_demo_for_trading"]:
                    categories["connection"].append((name, desc))
                elif "symbol" in name or "tick" in name or "rates" in name or "book" in name:
                    categories["market_data"].append((name, desc))
                elif "order" in name and ("send" in name or "check" in name or "cancel" in name or "modify" in name):
                    categories["trading"].append((name, desc))
                elif "position" in name or "orders_get" in name:
                    categories["positions"].append((name, desc))
                elif "history" in name:
                    categories["history"].append((name, desc))
                else:
                    categories["other"].append((name, desc))
            
            print("\n📋 Ferramentas por categoria:")
            for category, tool_list in categories.items():
                if tool_list:
                    print(f"\n   {category.upper()}: {len(tool_list)} ferramentas")
                    for name, desc in tool_list[:3]:  # Mostrar apenas 3 primeiras
                        print(f"     - {name}: {desc[:60]}...")
            
            self.results["tools_list"] = {
                "total": len(tools),
                "categories": {k: len(v) for k, v in categories.items()},
                "tools": tools
            }
            
            return tools
        else:
            print(f"❌ Erro ao listar ferramentas: {result['error']}")
            return []

    async def test_mcp_tools(self):
        """Testa ferramentas via protocolo MCP correto"""
        print("\n🧪 Testando ferramentas via tools/call...")
        
        tools_to_test = [
            "get_version",
            "get_terminal_info", 
            "get_account_info",
            "get_symbols"
        ]
        
        results = {}
        
        for tool_name in tools_to_test:
            print(f"\n   Testando: {tool_name}")
            result = await self.call_tool(tool_name)
            
            if result["success"]:
                data = result["data"]
                if "error" in data:
                    print(f"     ❌ {data['error']['message']}")
                    results[tool_name] = {"success": False, "error": data["error"]}
                else:
                    # Extrair dados da resposta MCP
                    content = data.get("result", {}).get("content", {})
                    print(f"     ✅ Sucesso ({result['latency_ms']:.1f}ms)")
                    results[tool_name] = {"success": True, "latency_ms": result["latency_ms"], "data": content}
            else:
                print(f"     ❌ {result['error']}")
                results[tool_name] = {"success": False, "error": result["error"]}
        
        self.results["mcp_tools"] = results
        return results

    async def test_symbol_operations(self):
        """Testa operações com símbolos ITSA3/ITSA4"""
        print("\n🇧🇷 Testando símbolos ITSA3/ITSA4...")
        
        symbols = ["ITSA3", "ITSA4"]
        symbol_results = {}
        
        for symbol in symbols:
            print(f"\n   📊 Símbolo: {symbol}")
            
            # Teste get_symbol_info
            result = await self.call_tool("get_symbol_info", {"symbol": symbol})
            
            if result["success"]:
                data = result["data"]
                if "error" not in data:
                    content = data.get("result", {}).get("content", {})
                    bid = content.get("bid", "N/A")
                    ask = content.get("ask", "N/A")
                    print(f"     ✅ get_symbol_info: OK (Bid: {bid}, Ask: {ask})")
                    symbol_results[symbol] = {"success": True, "bid": bid, "ask": ask}
                    
                    # Se der certo, tenta get_symbol_info_tick
                    tick_result = await self.call_tool("get_symbol_info_tick", {"symbol": symbol})
                    if tick_result["success"] and "error" not in tick_result["data"]:
                        print(f"     ✅ get_symbol_info_tick: OK")
                        symbol_results[symbol]["tick_success"] = True
                    else:
                        print(f"     ❌ get_symbol_info_tick: Failed")
                        symbol_results[symbol]["tick_success"] = False
                else:
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    print(f"     ❌ get_symbol_info: {error_msg}")
                    symbol_results[symbol] = {"success": False, "error": error_msg}
            else:
                print(f"     ❌ get_symbol_info: {result['error']}")
                symbol_results[symbol] = {"success": False, "error": result["error"]}
        
        self.results["symbol_tests"] = symbol_results
        return symbol_results

    async def analyze_gaps(self):
        """Analisa gaps encontrados"""
        print("\n🔍 ANÁLISE DE GAPS")
        print("-" * 50)
        
        gaps = []
        recommendations = []
        
        # Gap 1: Ferramentas MCP que falharam
        mcp_tools = self.results.get("mcp_tools", {})
        failed_tools = [name for name, result in mcp_tools.items() if not result.get("success")]
        
        if failed_tools:
            gap = f"🚨 FERRAMENTAS MCP: {len(failed_tools)} ferramentas falham - {failed_tools}"
            gaps.append(gap)
            print(gap)
            recommendations.append("Verificar implementação das ferramentas que falharam")
        
        # Gap 2: Símbolos ITSA3/ITSA4
        symbol_tests = self.results.get("symbol_tests", {})
        failed_symbols = [symbol for symbol, result in symbol_tests.items() if not result.get("success")]
        
        if failed_symbols:
            gap = f"💰 SÍMBOLOS B3: {len(failed_symbols)} símbolos inacessíveis - {failed_symbols}"
            gaps.append(gap)
            print(gap)
            recommendations.append("Configurar símbolos B3 no MT5 e verificar Market Watch")
        
        # Verificar sucesso geral
        tools_available = self.results.get("tools_list", {}).get("total", 0)
        successful_tools = len([name for name, result in mcp_tools.items() if result.get("success")])
        
        if successful_tools == 0 and tools_available > 0:
            gap = "⚡ PROTOCOLO: Nenhuma ferramenta funcionando apesar de estarem listadas"
            gaps.append(gap)
            print(gap)
            recommendations.append("Verificar implementação do protocolo MCP tools/call")
        
        print(f"\n📋 RESUMO: {len(gaps)} gaps identificados")
        for i, gap in enumerate(gaps, 1):
            print(f"   {i}. {gap}")
        
        print(f"\n💡 RECOMENDAÇÕES:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        self.results["gaps"] = {
            "total": len(gaps),
            "items": gaps,
            "recommendations": recommendations,
            "severity": "HIGH" if any("CRÍTICO" in gap for gap in gaps) else "MEDIUM"
        }

    async def generate_report(self):
        """Gera relatório completo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Criar diretório de logs seguindo a convenção
        logs_dir = Path(__file__).parent.parent / "logs" / "simple_mcp_audit"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar diretórios para compatibilidade
        docs_dir = Path("docs/mcp")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar JSON no diretório de logs
        json_file = logs_dir / f"audit_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump({
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "server_url": self.server_url,
                    "audit_type": "E2.0 - Simplified MCP Audit"
                },
                "results": self.results
            }, f, indent=2)
        
        # Gerar Markdown
        md_file = docs_dir / "capability_matrix.md"
        with open(md_file, "w") as f:
            f.write(f"""# MCP MT5 Capability Matrix - ETAPA 2.0

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Servidor:** {self.server_url}  
**Issue:** [E2.0] Auditoria do MCP MT5 (#9)

## 📊 Resumo Executivo

""")
            
            tools_total = self.results.get("tools_list", {}).get("total", 0)
            gaps_total = self.results.get("gaps", {}).get("total", 0)
            severity = self.results.get("gaps", {}).get("severity", "UNKNOWN")
            
            f.write(f"- **Ferramentas disponíveis:** {tools_total}\n")
            f.write(f"- **Gaps identificados:** {gaps_total} (Severidade: {severity})\n")
            f.write(f"- **Status do servidor:** {'🟢 Online' if tools_total > 0 else '🔴 Offline'}\n\n")
            
            # Ferramentas por categoria
            categories = self.results.get("tools_list", {}).get("categories", {})
            if categories:
                f.write("## 🛠️ Ferramentas por Categoria\n\n")
                f.write("| Categoria | Quantidade |\n")
                f.write("|-----------|------------|\n")
                for cat, count in categories.items():
                    f.write(f"| {cat.title()} | {count} |\n")
                f.write("\n")
            
            # Status das ferramentas MCP
            mcp_tools = self.results.get("mcp_tools", {})
            if mcp_tools:
                f.write("## 🛠️ Status das Ferramentas MCP\n\n")
                f.write("| Ferramenta | Status | Latência (ms) |\n")
                f.write("|------------|--------|--------------|\n")
                for tool_name, result in mcp_tools.items():
                    status = "✅" if result.get("success") else "❌"
                    latency = f"{result.get('latency_ms', 0):.1f}" if result.get("latency_ms") else "N/A"
                    f.write(f"| {tool_name} | {status} | {latency} |\n")
                f.write("\n")
            
            # Teste de símbolos
            symbol_tests = self.results.get("symbol_tests", {})
            if symbol_tests:
                f.write("## 🇧🇷 Status Símbolos ITSA3/ITSA4\n\n")
                for symbol, result in symbol_tests.items():
                    status = "✅" if result.get("success") else "❌"
                    f.write(f"- **{symbol}**: {status}\n")
                f.write("\n")
            
            # Gaps
            gaps = self.results.get("gaps", {})
            if gaps.get("items"):
                f.write("## 🔍 Gaps Identificados\n\n")
                for i, gap in enumerate(gaps["items"], 1):
                    f.write(f"{i}. {gap}\n")
                f.write("\n")
            
            if gaps.get("recommendations"):
                f.write("## 💡 Recomendações\n\n")
                for i, rec in enumerate(gaps["recommendations"], 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")
            
            f.write(f"""## 🎯 Conclusão para ETAPA 2

**Status:** {'🚨 BLOQUEIO' if severity == 'HIGH' else '⚠️ ATENÇÃO' if severity == 'MEDIUM' else '✅ APROVADO'}

### Próximos Passos:
1. **Corrigir protocolo MCP** no servidor (implementar tools/call)
2. **Validar símbolos B3** estão disponíveis no MT5  
3. **Configurar Market Watch** para ITSA3/ITSA4
4. **Testar execução de ordens** em conta demo
5. **Prosseguir para E2.1** após correções

---
*Relatório gerado automaticamente para issue #9*
""")
        
        print(f"\n💾 RELATÓRIO SALVO:")
        print(f"   📄 JSON: {json_file}")
        print(f"   📋 Markdown: {md_file}")
        print(f"   📁 Logs em: {logs_dir}")
        
        return json_file, md_file

    async def run_audit(self):
        """Executa auditoria completa"""
        print("🚀 ETAPA 2.0 - Auditoria MCP MT5 Simplificada")
        print("=" * 60)
        print(f"🔗 Servidor: {self.server_url}")
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Executar testes
        tools = await self.audit_tools_list()
        if not tools:
            print("❌ Não foi possível listar ferramentas. Servidor pode estar offline.")
            return
        
        await self.test_mcp_tools()
        await self.test_symbol_operations()
        await self.analyze_gaps()
        
        # Gerar relatório
        json_file, md_file = await self.generate_report()
        
        # Status final
        print(f"\n🎉 AUDITORIA E2.0 CONCLUÍDA")
        print("=" * 60)
        
        gaps_total = self.results.get("gaps", {}).get("total", 0)
        severity = self.results.get("gaps", {}).get("severity", "UNKNOWN")
        
        if gaps_total == 0:
            print("✅ STATUS: Servidor MCP pronto para ETAPA 2")
        elif severity == "HIGH":
            print("🚨 STATUS: Gaps críticos - correção obrigatória antes de prosseguir")
        else:
            print("⚠️  STATUS: Gaps menores - pode prosseguir com cautela")
        
        print(f"\n📁 Relatórios disponíveis em:")
        print(f"   - {json_file}")
        print(f"   - {md_file}")

async def main():
    auditor = SimpleMCPAudit()
    await auditor.run_audit()

if __name__ == "__main__":
    asyncio.run(main())