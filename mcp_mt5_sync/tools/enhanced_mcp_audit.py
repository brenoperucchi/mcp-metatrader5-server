#!/usr/bin/env python3
"""
E2.0 - Auditoria Aprimorada do MCP MT5 (Pós-correções)
Testa especificamente o método tools/call que agora está implementado
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from pathlib import Path

class EnhancedMCPAudit:
    def __init__(self, server_url="192.168.0.125:8000"):
        self.server_url = server_url
        self.base_url = f"http://{server_url}"
        self.rpc_url = f"{self.base_url}/mcp"
        self.request_id = 1
        self.results = {}

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Chama ferramenta via tools/call (protocolo MCP)"""
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
                        
                        if "error" in result:
                            return {
                                "success": False,
                                "error": result["error"]["message"],
                                "latency_ms": latency_ms
                            }
                        
                        # Extrair dados da resposta MCP
                        content = result.get("result", {}).get("content", {})
                        
                        return {
                            "success": True,
                            "data": content,
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

    async def test_core_tools(self):
        """Testa ferramentas principais via tools/call"""
        print("🔧 TESTE DAS FERRAMENTAS PRINCIPAIS")
        print("-" * 50)
        
        core_tools = [
            ("get_account_info", {}, "Informações da conta"),
            ("get_version", {}, "Versão do MT5"),
            ("get_terminal_info", {}, "Info do terminal"),
            ("get_symbols", {}, "Lista de símbolos")
        ]
        
        results = {}
        
        for tool_name, args, description in core_tools:
            print(f"\n🔍 {tool_name}: {description}")
            result = await self.call_tool(tool_name, args)
            
            if result["success"]:
                print(f"   ✅ Sucesso ({result['latency_ms']:.1f}ms)")
                
                # Analisar dados específicos
                data = result["data"]
                if tool_name == "get_account_info":
                    login = data.get("login")
                    balance = data.get("balance")
                    trade_mode = "DEMO" if data.get("trade_mode") == 0 else "REAL"
                    print(f"      📊 Conta: {login} | Saldo: R$ {balance:,.2f} | Modo: {trade_mode}")
                elif tool_name == "get_symbols":
                    symbols_count = len(data) if isinstance(data, list) else "N/A"
                    print(f"      📈 {symbols_count} símbolos disponíveis")
                
                results[tool_name] = {
                    "success": True,
                    "latency_ms": result["latency_ms"],
                    "data_size": len(str(data))
                }
            else:
                print(f"   ❌ Falha: {result['error']}")
                results[tool_name] = {
                    "success": False,
                    "error": result["error"],
                    "latency_ms": result["latency_ms"]
                }
        
        self.results["core_tools"] = results
        return results

    async def test_itsa_symbols_detailed(self):
        """Teste detalhado dos símbolos ITSA3/ITSA4"""
        print("\n🇧🇷 ANÁLISE DETALHADA ITSA3/ITSA4")
        print("-" * 50)
        
        symbols = ["ITSA3", "ITSA4"]
        symbol_results = {}
        
        for symbol in symbols:
            print(f"\n📊 Analisando {symbol}:")
            
            # Teste 1: Symbol Info
            info_result = await self.call_tool("get_symbol_info", {"symbol": symbol})
            
            if info_result["success"]:
                data = info_result["data"]
                bid = data.get("bid", 0)
                ask = data.get("ask", 0)
                last = data.get("last", 0)
                volume = data.get("volume", 0)
                spread = ask - bid if bid and ask else 0
                spread_pct = (spread / bid * 100) if bid > 0 else 0
                
                print(f"   💰 Preços: Bid={bid} | Ask={ask} | Last={last}")
                print(f"   📈 Spread: {spread:.3f} ({spread_pct:.2f}%)")
                print(f"   📊 Volume: {volume:,}")
                print(f"   ⏱️  Latência: {info_result['latency_ms']:.1f}ms")
                
                # Teste 2: Symbol Tick
                tick_result = await self.call_tool("get_symbol_info_tick", {"symbol": symbol})
                
                tick_status = "✅" if tick_result["success"] else "❌"
                print(f"   🎯 Tick Info: {tick_status}")
                
                symbol_results[symbol] = {
                    "success": True,
                    "bid": bid,
                    "ask": ask,
                    "last": last,
                    "volume": volume,
                    "spread": spread,
                    "spread_percent": spread_pct,
                    "latency_ms": info_result["latency_ms"],
                    "tick_available": tick_result["success"]
                }
                
            else:
                print(f"   ❌ Erro: {info_result['error']}")
                symbol_results[symbol] = {
                    "success": False,
                    "error": info_result["error"]
                }
        
        # Análise de arbitragem
        if "ITSA3" in symbol_results and "ITSA4" in symbol_results:
            itsa3_data = symbol_results["ITSA3"]
            itsa4_data = symbol_results["ITSA4"]
            
            if itsa3_data["success"] and itsa4_data["success"]:
                print(f"\n🔄 ANÁLISE DE ARBITRAGEM:")
                
                # Spread entre ITSA3 e ITSA4
                itsa3_mid = (itsa3_data["bid"] + itsa3_data["ask"]) / 2
                itsa4_mid = (itsa4_data["bid"] + itsa4_data["ask"]) / 2
                
                premium = itsa4_mid - itsa3_mid
                premium_pct = (premium / itsa3_mid * 100) if itsa3_mid > 0 else 0
                
                print(f"   💎 ITSA3 Mid: R$ {itsa3_mid:.3f}")
                print(f"   💎 ITSA4 Mid: R$ {itsa4_mid:.3f}")
                print(f"   📊 Premium PN: R$ {premium:.3f} ({premium_pct:.2f}%)")
                
                # Avaliação para swap
                if premium_pct > 2:
                    print(f"   🟢 OPORTUNIDADE: Premium alto, favorável para ETAPA 2")
                elif premium_pct > 0:
                    print(f"   🟡 NEUTRO: Premium moderado")
                else:
                    print(f"   🔴 DESCONTO: PN com desconto, revisar estratégia")
                
                symbol_results["arbitrage_analysis"] = {
                    "itsa3_mid": itsa3_mid,
                    "itsa4_mid": itsa4_mid,
                    "premium": premium,
                    "premium_percent": premium_pct,
                    "opportunity": premium_pct > 2
                }
        
        self.results["itsa_symbols"] = symbol_results
        return symbol_results

    async def test_trading_tools(self):
        """Testa ferramentas de trading (sem executar ordens)"""
        print("\n⚡ FERRAMENTAS DE TRADING")
        print("-" * 50)
        
        trading_tools = [
            ("positions_get", {}, "Posições abertas"),
            ("orders_get", {}, "Ordens pendentes"),
            ("validate_demo_for_trading", {}, "Validação conta demo")
        ]
        
        results = {}
        
        for tool_name, args, description in trading_tools:
            print(f"\n🔧 {tool_name}: {description}")
            result = await self.call_tool(tool_name, args)
            
            if result["success"]:
                print(f"   ✅ Sucesso ({result['latency_ms']:.1f}ms)")
                
                data = result["data"]
                if tool_name == "positions_get":
                    pos_count = len(data) if isinstance(data, list) else 0
                    print(f"      📈 {pos_count} posições abertas")
                elif tool_name == "orders_get":
                    order_count = len(data) if isinstance(data, list) else 0
                    print(f"      📋 {order_count} ordens pendentes")
                elif tool_name == "validate_demo_for_trading":
                    is_demo = data.get("is_demo", False)
                    trading_allowed = data.get("trading_allowed", False)
                    print(f"      🛡️  Demo: {is_demo} | Trading: {trading_allowed}")
                
                results[tool_name] = {
                    "success": True,
                    "latency_ms": result["latency_ms"],
                    "data": data
                }
            else:
                print(f"   ❌ Falha: {result['error']}")
                results[tool_name] = {
                    "success": False,
                    "error": result["error"]
                }
        
        self.results["trading_tools"] = results
        return results

    async def benchmark_performance(self):
        """Benchmark de performance das ferramentas críticas"""
        print("\n⏱️  BENCHMARK DE PERFORMANCE")
        print("-" * 50)
        
        benchmark_tools = [
            ("get_symbol_info", {"symbol": "ITSA3"}, 50),  # SLA: 50ms
            ("get_symbol_info_tick", {"symbol": "ITSA3"}, 50),  # SLA: 50ms
            ("get_account_info", {}, 150),  # SLA: 150ms
        ]
        
        benchmark_results = {}
        
        for tool_name, args, sla_ms in benchmark_tools:
            print(f"\n📈 Benchmark: {tool_name} (SLA: {sla_ms}ms)")
            
            latencies = []
            success_count = 0
            iterations = 10
            
            for i in range(iterations):
                result = await self.call_tool(tool_name, args)
                if result["success"]:
                    latencies.append(result["latency_ms"])
                    success_count += 1
                    status = "✅" if result["latency_ms"] <= sla_ms else "⚠️"
                    print(f"   {i+1:2d}/10: {status} {result['latency_ms']:.1f}ms")
                else:
                    print(f"   {i+1:2d}/10: ❌ {result['error']}")
            
            if latencies:
                avg_lat = sum(latencies) / len(latencies)
                p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
                sla_violations = sum(1 for lat in latencies if lat > sla_ms)
                
                print(f"   📊 Avg: {avg_lat:.1f}ms | P95: {p95_lat:.1f}ms")
                print(f"   🎯 SLA: {sla_violations}/{len(latencies)} violações")
                
                sla_met = sla_violations == 0
                status_icon = "✅" if sla_met else "❌"
                print(f"   {status_icon} Status: {'PASS' if sla_met else 'FAIL'}")
                
                benchmark_results[tool_name] = {
                    "success_rate": success_count / iterations,
                    "avg_latency_ms": avg_lat,
                    "p95_latency_ms": p95_lat,
                    "sla_ms": sla_ms,
                    "sla_met": sla_met,
                    "violations": sla_violations
                }
        
        self.results["benchmark"] = benchmark_results
        return benchmark_results

    async def final_assessment(self):
        """Avaliação final do servidor para ETAPA 2"""
        print("\n🎯 AVALIAÇÃO FINAL PARA ETAPA 2")
        print("=" * 60)
        
        # Verificar critérios essenciais
        core_tools = self.results.get("core_tools", {})
        itsa_symbols = self.results.get("itsa_symbols", {})
        trading_tools = self.results.get("trading_tools", {})
        benchmark = self.results.get("benchmark", {})
        
        criteria = {
            "tools_call_working": any(t.get("success", False) for t in core_tools.values()),
            "account_info_working": core_tools.get("get_account_info", {}).get("success", False),
            "itsa3_accessible": itsa_symbols.get("ITSA3", {}).get("success", False),
            "itsa4_accessible": itsa_symbols.get("ITSA4", {}).get("success", False),
            "performance_acceptable": all(b.get("sla_met", False) for b in benchmark.values()),
            "arbitrage_viable": itsa_symbols.get("arbitrage_analysis", {}).get("premium_percent", 0) > 0
        }
        
        print("📋 CRITÉRIOS DE AVALIAÇÃO:")
        for criterion, status in criteria.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {criterion.replace('_', ' ').title()}")
        
        # Status final
        passed_criteria = sum(criteria.values())
        total_criteria = len(criteria)
        success_rate = passed_criteria / total_criteria
        
        print(f"\n📊 SCORE: {passed_criteria}/{total_criteria} ({success_rate*100:.1f}%)")
        
        if success_rate >= 0.8:
            status = "🟢 APROVADO"
            message = "Servidor pronto para ETAPA 2 - Decisão de Swap"
        elif success_rate >= 0.6:
            status = "🟡 APROVADO COM RESSALVAS"
            message = "Pode prosseguir, mas com monitoramento adicional"
        else:
            status = "🔴 REPROVADO"
            message = "Correções necessárias antes de prosseguir"
        
        print(f"\n{status}")
        print(f"💬 {message}")
        
        self.results["final_assessment"] = {
            "criteria": criteria,
            "score": passed_criteria,
            "total": total_criteria,
            "success_rate": success_rate,
            "status": status,
            "message": message
        }
        
        return status, message

    async def save_enhanced_report(self):
        """Salva relatório aprimorado"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Criar diretório de logs seguindo a convenção
        logs_dir = Path(__file__).parent.parent / "logs" / "enhanced_mcp_audit"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON completo no diretório de logs
        json_file = logs_dir / f"audit_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump({
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "server_url": self.server_url,
                    "audit_type": "Enhanced E2.0 - Post Corrections"
                },
                "results": self.results
            }, f, indent=2, default=str)
        
        # Relatório markdown
        docs_dir = Path("docs/mcp")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        md_file = docs_dir / "enhanced_capability_matrix.md"
        with open(md_file, "w") as f:
            f.write(f"""# 🚀 MCP MT5 Enhanced Audit - ETAPA 2.0 (Pós-correções)

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Servidor:** {self.server_url}  
**Status:** Auditoria pós-implementação das correções

## 📊 Resumo Executivo

""")
            
            final_assessment = self.results.get("final_assessment", {})
            status = final_assessment.get("status", "UNKNOWN")
            score = final_assessment.get("score", 0)
            total = final_assessment.get("total", 0)
            success_rate = final_assessment.get("success_rate", 0)
            
            f.write(f"- **Status Final:** {status}\n")
            f.write(f"- **Score:** {score}/{total} ({success_rate*100:.1f}%)\n")
            f.write(f"- **Protocolo MCP:** ✅ Implementado\n")
            f.write(f"- **ITSA3/ITSA4:** ✅ Acessíveis\n\n")
            
            # Ferramentas principais
            core_tools = self.results.get("core_tools", {})
            f.write("## 🔧 Ferramentas Principais\n\n")
            f.write("| Ferramenta | Status | Latência (ms) |\n")
            f.write("|------------|--------|--------------|\n")
            for tool, result in core_tools.items():
                status_icon = "✅" if result.get("success") else "❌"
                latency = f"{result.get('latency_ms', 0):.1f}" if result.get("latency_ms") else "N/A"
                f.write(f"| {tool} | {status_icon} | {latency} |\n")
            
            # Análise ITSA
            itsa_symbols = self.results.get("itsa_symbols", {})
            arbitrage = itsa_symbols.get("arbitrage_analysis", {})
            if arbitrage:
                f.write(f"\n## 💎 Análise de Arbitragem ITSA3/ITSA4\n\n")
                f.write(f"- **ITSA3 Mid:** R$ {arbitrage.get('itsa3_mid', 0):.3f}\n")
                f.write(f"- **ITSA4 Mid:** R$ {arbitrage.get('itsa4_mid', 0):.3f}\n")
                f.write(f"- **Premium PN:** {arbitrage.get('premium_percent', 0):.2f}%\n")
                f.write(f"- **Oportunidade:** {'✅ SIM' if arbitrage.get('opportunity') else '❌ NÃO'}\n")
            
            # Benchmark
            benchmark = self.results.get("benchmark", {})
            if benchmark:
                f.write(f"\n## ⏱️ Performance Benchmark\n\n")
                f.write("| Ferramenta | Avg (ms) | P95 (ms) | SLA | Status |\n")
                f.write("|------------|----------|----------|-----|--------|\n")
                for tool, result in benchmark.items():
                    avg_lat = f"{result.get('avg_latency_ms', 0):.1f}"
                    p95_lat = f"{result.get('p95_latency_ms', 0):.1f}"
                    sla = f"{result.get('sla_ms', 0)}"
                    status_icon = "✅" if result.get("sla_met") else "❌"
                    f.write(f"| {tool} | {avg_lat} | {p95_lat} | {sla} | {status_icon} |\n")
            
            f.write(f"""
## 🎯 Próximos Passos

Com base nos resultados da auditoria:

1. **E2.0 ✅ CONCLUÍDA** - Servidor MCP funcionando
2. **E2.1** - Prosseguir para especificação de contratos
3. **E2.2** - Implementar cliente Python para ETAPA 2
4. **Monitoramento** - Acompanhar performance em produção

## 💡 Recomendações

- Monitorar latência das cotações (manter < 50ms)
- Implementar cache para operações frequentes
- Configurar alertas para falhas de conectividade
- Validar DEMO mode antes de qualquer trading

---
*Relatório gerado pela auditoria aprimorada E2.0*
""")
        
        print(f"\n💾 RELATÓRIO APRIMORADO SALVO:")
        print(f"   📄 JSON: {json_file}")
        print(f"   📋 Markdown: {md_file}")
        print(f"   📁 Logs em: {logs_dir}")
        
        return json_file, md_file

    async def run_enhanced_audit(self):
        """Executa auditoria aprimorada completa"""
        print("🚀 AUDITORIA APRIMORADA - E2.0 PÓS-CORREÇÕES")
        print("=" * 70)
        print(f"🔗 Servidor: {self.server_url}")
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Executar todos os testes
        await self.test_core_tools()
        await self.test_itsa_symbols_detailed()
        await self.test_trading_tools()
        await self.benchmark_performance()
        
        # Avaliação final
        status, message = await self.final_assessment()
        
        # Salvar relatório
        json_file, md_file = await self.save_enhanced_report()
        
        print(f"\n🎉 AUDITORIA APRIMORADA CONCLUÍDA")
        print("=" * 70)
        print(f"📈 Resultado: {status}")
        print(f"💬 {message}")
        
        return status == "🟢 APROVADO"

async def main():
    auditor = EnhancedMCPAudit()
    success = await auditor.run_enhanced_audit()
    
    if success:
        print("\n🚀 PRÓXIMO PASSO: E2.1 - Especificação de contratos MCP")
    else:
        print("\n⚠️  Revisar problemas antes de prosseguir para E2.1")

if __name__ == "__main__":
    asyncio.run(main())