#!/usr/bin/env python3
"""
ETAPA 2.0 - Auditoria Completa do MCP MT5
Implementação da issue #9: Auditoria do MCP MT5: ferramentas, contratos e lacunas
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Usar o SimpleMCPClient que já está funcionando
import sys
sys.path.append('.')
from src.connectors.mt5_adapter import SimpleMCPClient

class MCPE20Auditor:
    """Auditor completo para ETAPA 2.0 - MCP MT5 Capability Matrix & Gap Analysis"""
    
    def __init__(self, server_url: str = "192.168.0.125:8000"):
        self.server_url = server_url
        self.client = SimpleMCPClient(server_url)
        self.results = {}
        self.start_time = time.time()
        
    async def initialize_audit(self):
        """Inicializar auditoria"""
        print("🚀 ETAPA 2.0 - Auditoria MCP MT5")
        print("=" * 60)
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Servidor: {self.server_url}")
        print()
        
        # Testar conectividade
        connection_result = await self.client.test_connection()
        self.results["connection"] = connection_result
        
        if connection_result.get("success"):
            print(f"✅ Conectividade: {connection_result.get('status')}")
        else:
            print(f"❌ Conectividade: {connection_result.get('error')}")
            return False
        return True

    async def audit_critical_tools_for_etapa2(self):
        """Auditar ferramentas críticas para ETAPA 2"""
        print("\n🎯 FERRAMENTAS CRÍTICAS PARA ETAPA 2")
        print("-" * 50)
        
        critical_tools = {
            # Market Data (CRÍTICO)
            "get_account_info": "Informações da conta de trading",
            "get_terminal_info": "Status do terminal MT5", 
            "get_version": "Versão do MT5",
            "get_symbol_info": "Informações do símbolo (bid/ask/volume)",
            "get_symbol_info_tick": "Tick atual do símbolo",
            
            # Symbols Management
            "get_symbols": "Lista todos os símbolos disponíveis",
            "symbol_select": "Adicionar símbolo ao Market Watch",
            
            # Order Book (Level 2) - CRÍTICO para spread analysis
            "copy_book_levels": "Profundidade do book de ofertas",
            "get_book_snapshot": "Snapshot completo bid/ask",
            
            # Trading Operations (CRÍTICO) 
            "order_send": "Enviar ordem de compra/venda",
            "order_check": "Validar ordem antes de enviar",
            "order_cancel": "Cancelar ordem pendente",
            "order_modify": "Modificar ordem pendente",
            
            # Position Management
            "positions_get": "Posições abertas",
            "positions_get_by_ticket": "Posição por ticket",
            "position_modify": "Modificar SL/TP da posição",
            
            # Orders Management
            "orders_get": "Ordens pendentes",
            "orders_get_by_ticket": "Ordem por ticket",
            
            # Historical Data
            "history_orders_get": "Histórico de ordens",
            "history_deals_get": "Histórico de negociações",
            
            # Safety & Validation
            "validate_demo_for_trading": "Validar conta demo"
        }
        
        results = {}
        
        for tool_name, description in critical_tools.items():
            print(f"\n🔍 Testando: {tool_name}")
            print(f"   Descrição: {description}")
            
            start_time = time.time()
            
            try:
                # Testar ferramenta com parâmetros apropriados
                if tool_name == "get_symbol_info":
                    result = await self._test_tool(tool_name, {"symbol": "ITSA3"})
                elif tool_name == "get_symbol_info_tick":
                    result = await self._test_tool(tool_name, {"symbol": "ITSA4"})
                elif tool_name == "copy_book_levels":
                    result = await self._test_tool(tool_name, {"symbol": "ITSA3"})
                elif tool_name == "symbol_select":
                    result = await self._test_tool(tool_name, {"symbol": "ITSA3", "visible": True})
                else:
                    result = await self._test_tool(tool_name, {})
                
                latency_ms = (time.time() - start_time) * 1000
                
                if result.get("success"):
                    print(f"   ✅ Sucesso ({latency_ms:.1f}ms)")
                    # Analisar estrutura da resposta
                    data = result.get("data", {})
                    if isinstance(data, dict) and data:
                        key_count = len(data.keys())
                        sample_keys = list(data.keys())[:3]
                        print(f"      📊 Dados: {key_count} campos, sample: {sample_keys}")
                else:
                    print(f"   ❌ Falha: {result.get('error', 'Unknown error')}")
                
                results[tool_name] = {
                    "success": result.get("success", False),
                    "latency_ms": latency_ms,
                    "error": result.get("error"),
                    "data_structure": self._analyze_data_structure(result.get("data", {})),
                    "description": description
                }
                
            except Exception as e:
                print(f"   💥 Exceção: {str(e)}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e),
                    "description": description
                }
        
        self.results["critical_tools"] = results
        return results

    async def _test_tool(self, tool_name: str, params: dict) -> dict:
        """Testar ferramenta específica via SimpleMCPClient"""
        # Mapear para métodos do SimpleMCPClient
        method_map = {
            "get_account_info": self.client.get_account_info,
            "get_terminal_info": self.client.get_terminal_info,
            "get_version": self.client.get_version,
            "get_symbol_info": self.client.get_symbol_info,
            "get_symbol_info_tick": self.client.get_symbol_info_tick,
            "get_symbols": self.client.get_symbols,
            "symbol_select": self.client.symbol_select,
            "copy_book_levels": self.client.copy_book_levels,
            "order_send": self.client.order_send,
            "order_check": self.client.order_check,
            "positions_get": self.client.positions_get,
            "orders_get": self.client.orders_get,
            "validate_demo_for_trading": self.client.validate_demo_for_trading
        }
        
        if tool_name in method_map:
            try:
                if params:
                    return await method_map[tool_name](**params)
                else:
                    return await method_map[tool_name]()
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Tool {tool_name} not mapped in SimpleMCPClient"}

    def _analyze_data_structure(self, data: Any) -> dict:
        """Analisar estrutura dos dados retornados"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "field_count": len(data),
                "fields": list(data.keys())[:10],  # Primeiros 10 campos
                "has_trading_fields": any(field in data for field in ["bid", "ask", "last", "volume", "balance", "equity"])
            }
        elif isinstance(data, list):
            return {
                "type": "array", 
                "length": len(data),
                "sample_item": self._analyze_data_structure(data[0]) if data else None
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100]  # Primeiros 100 chars
            }

    async def test_itsa3_itsa4_symbols(self):
        """Testar especificamente símbolos ITSA3/ITSA4"""
        print("\n🇧🇷 TESTE ESPECÍFICO: SÍMBOLOS ITSA3/ITSA4")
        print("-" * 50)
        
        symbols = ["ITSA3", "ITSA4"]
        results = {}
        
        for symbol in symbols:
            print(f"\n📊 Testando símbolo: {symbol}")
            
            # Teste 1: Informações básicas
            info_result = await self._test_tool("get_symbol_info", {"symbol": symbol})
            
            # Teste 2: Tick atual
            tick_result = await self._test_tool("get_symbol_info_tick", {"symbol": symbol})
            
            # Teste 3: Book de ofertas (se disponível)
            book_result = await self._test_tool("copy_book_levels", {"symbol": symbol})
            
            results[symbol] = {
                "symbol_info": info_result,
                "tick_info": tick_result, 
                "book_info": book_result
            }
            
            # Análise dos resultados
            if info_result.get("success"):
                data = info_result.get("data", {})
                bid = data.get("bid")
                ask = data.get("ask")
                last = data.get("last")
                volume = data.get("volume")
                
                print(f"   ✅ Info: bid={bid}, ask={ask}, last={last}, vol={volume}")
                
                # Verificar se tem dados de trading
                if bid and ask:
                    spread = ask - bid
                    spread_pct = (spread / bid) * 100 if bid > 0 else 0
                    print(f"      💰 Spread: {spread:.4f} ({spread_pct:.3f}%)")
            else:
                print(f"   ❌ Info: {info_result.get('error')}")
            
            if tick_result.get("success"):
                print(f"   ✅ Tick: OK")
            else:
                print(f"   ❌ Tick: {tick_result.get('error')}")
            
            if book_result.get("success"):
                print(f"   ✅ Book: OK")
            else:
                print(f"   ❌ Book: {book_result.get('error')}")
        
        self.results["itsa_symbols"] = results
        return results

    async def benchmark_latency(self):
        """Benchmark de latência das operações críticas"""
        print("\n⏱️  BENCHMARK DE LATÊNCIA")
        print("-" * 50)
        
        benchmark_tools = [
            ("get_version", {}),
            ("get_account_info", {}),
            ("get_symbol_info", {"symbol": "ITSA3"}),
            ("get_symbol_info_tick", {"symbol": "ITSA3"}),
        ]
        
        results = {}
        
        for tool_name, params in benchmark_tools:
            print(f"\n📈 Benchmark: {tool_name}")
            
            latencies = []
            success_count = 0
            iterations = 10
            
            for i in range(iterations):
                start_time = time.time()
                result = await self._test_tool(tool_name, params)
                latency_ms = (time.time() - start_time) * 1000
                
                if result.get("success"):
                    latencies.append(latency_ms)
                    success_count += 1
                    print(f"   {i+1:2d}/10: ✅ {latency_ms:.1f}ms")
                else:
                    print(f"   {i+1:2d}/10: ❌ {result.get('error', 'Failed')}")
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
                
                print(f"   📊 Resultados:")
                print(f"      Success Rate: {success_count}/{iterations} ({success_count/iterations*100:.1f}%)")
                print(f"      Avg: {avg_latency:.1f}ms | Min: {min_latency:.1f}ms | Max: {max_latency:.1f}ms | P95: {p95_latency:.1f}ms")
                
                # SLA Check (baseado nos requisitos da E2.0)
                sla_limits = {
                    "get_version": 100,
                    "get_account_info": 150,
                    "get_symbol_info": 150,
                    "get_symbol_info_tick": 150
                }
                
                sla_limit = sla_limits.get(tool_name, 200)
                sla_met = p95_latency <= sla_limit
                print(f"      SLA (P95 <= {sla_limit}ms): {'✅ PASS' if sla_met else '❌ FAIL'}")
                
                results[tool_name] = {
                    "success_rate": success_count/iterations,
                    "avg_latency_ms": avg_latency,
                    "p95_latency_ms": p95_latency,
                    "min_latency_ms": min_latency,
                    "max_latency_ms": max_latency,
                    "sla_met": sla_met,
                    "sla_limit_ms": sla_limit
                }
            else:
                print(f"      ❌ Todas as chamadas falharam")
                results[tool_name] = {"success_rate": 0}
        
        self.results["benchmark"] = results
        return results

    async def identify_gaps_for_etapa2(self):
        """Identificar gaps específicos para ETAPA 2"""
        print("\n🔍 ANÁLISE DE GAPS PARA ETAPA 2")
        print("-" * 50)
        
        gaps = []
        recommendations = []
        
        # Verificar se ferramentas críticas estão funcionando
        critical_tools = self.results.get("critical_tools", {})
        
        # Gap 1: Ferramentas que falharam
        failed_tools = [name for name, result in critical_tools.items() if not result.get("success")]
        if failed_tools:
            gap = f"🚨 CRÍTICO: {len(failed_tools)} ferramentas falharam: {failed_tools}"
            gaps.append(gap)
            print(gap)
            recommendations.append("Corrigir implementação dessas ferramentas no servidor MCP")
        
        # Gap 2: Latência alta
        benchmark_results = self.results.get("benchmark", {})
        high_latency_tools = [name for name, result in benchmark_results.items() 
                             if not result.get("sla_met", True)]
        if high_latency_tools:
            gap = f"⚡ PERFORMANCE: {len(high_latency_tools)} ferramentas com latência alta: {high_latency_tools}"
            gaps.append(gap)
            print(gap)
            recommendations.append("Otimizar performance dessas ferramentas (cache, async, etc.)")
        
        # Gap 3: Símbolos ITSA3/ITSA4
        itsa_results = self.results.get("itsa_symbols", {})
        for symbol in ["ITSA3", "ITSA4"]:
            if symbol in itsa_results:
                symbol_data = itsa_results[symbol]
                if not symbol_data.get("symbol_info", {}).get("success"):
                    gap = f"💰 TRADING: Símbolo {symbol} não acessível via get_symbol_info"
                    gaps.append(gap)
                    print(gap)
                    recommendations.append(f"Verificar disponibilidade do símbolo {symbol} no MT5")
        
        # Gap 4: Book de ofertas (Level 2)
        book_working = any(
            itsa_results.get(symbol, {}).get("book_info", {}).get("success", False)
            for symbol in ["ITSA3", "ITSA4"]
        )
        if not book_working:
            gap = "📊 LEVEL 2: Book de ofertas não funcional para ITSA3/ITSA4"
            gaps.append(gap)
            print(gap)
            recommendations.append("Configurar acesso ao book de ofertas (Level 2) no MT5")
        
        # Gap 5: Conta demo validation
        demo_validation = critical_tools.get("validate_demo_for_trading", {})
        if not demo_validation.get("success"):
            gap = "🛡️ SEGURANÇA: Validação de conta demo não funcional"
            gaps.append(gap)
            print(gap)
            recommendations.append("Implementar validação de conta demo para segurança")
        
        print(f"\n📋 RESUMO DOS GAPS:")
        print(f"   Total de gaps identificados: {len(gaps)}")
        print(f"   Recomendações: {len(recommendations)}")
        
        self.results["gaps"] = {
            "identified_gaps": gaps,
            "recommendations": recommendations,
            "severity": "HIGH" if any("CRÍTICO" in gap for gap in gaps) else "MEDIUM"
        }
        
        return gaps, recommendations

    async def save_results(self):
        """Salvar resultados da auditoria"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Criar diretório se não existir
        docs_dir = Path("docs/mcp")
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Capability Matrix
        capability_file = docs_dir / "capability_matrix.md"
        samples_dir = docs_dir / "samples"
        samples_dir.mkdir(exist_ok=True)
        
        # Salvar JSON completo
        json_file = f"mcp_e20_audit_{timestamp}.json"
        audit_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "server_url": self.server_url,
                "audit_duration_seconds": time.time() - self.start_time,
                "etapa": "2.0",
                "issue": "#9"
            },
            "results": self.results
        }
        
        with open(json_file, "w") as f:
            json.dump(audit_data, f, indent=2, default=str)
        
        # Gerar relatório em Markdown
        await self._generate_capability_matrix_md(capability_file)
        
        print(f"\n💾 RESULTADOS SALVOS:")
        print(f"   📄 JSON completo: {json_file}")
        print(f"   📋 Capability Matrix: {capability_file}")
        print(f"   📁 Samples: {samples_dir}/")
        
        return json_file, capability_file

    async def _generate_capability_matrix_md(self, filepath: Path):
        """Gerar relatório Capability Matrix em Markdown"""
        with open(filepath, "w") as f:
            f.write(f"""# MCP MT5 Capability Matrix - ETAPA 2.0

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Servidor:** {self.server_url}  
**Issue:** [E2.0] Auditoria do MCP MT5 (#9)

## 📊 Resumo Executivo

""")
            
            # Estatísticas gerais
            critical_tools = self.results.get("critical_tools", {})
            total_tools = len(critical_tools)
            working_tools = sum(1 for r in critical_tools.values() if r.get("success"))
            
            f.write(f"- **Ferramentas testadas:** {total_tools}\n")
            f.write(f"- **Funcionais:** {working_tools}/{total_tools} ({working_tools/total_tools*100:.1f}%)\n")
            f.write(f"- **Servidor:** {'🟢 Online' if self.results.get('connection', {}).get('success') else '🔴 Offline'}\n")
            
            # Gaps identificados
            gaps = self.results.get("gaps", {})
            gap_count = len(gaps.get("identified_gaps", []))
            severity = gaps.get("severity", "UNKNOWN")
            f.write(f"- **Gaps identificados:** {gap_count} (Severidade: {severity})\n\n")
            
            # Tabela de ferramentas
            f.write("## 🛠️ Status das Ferramentas Críticas\n\n")
            f.write("| Ferramenta | Status | Latência (ms) | Descrição |\n")
            f.write("|------------|--------|---------------|------------|\n")
            
            for tool_name, result in critical_tools.items():
                status = "✅" if result.get("success") else "❌"
                latency = f"{result.get('latency_ms', 0):.1f}" if result.get("latency_ms") else "N/A"
                description = result.get("description", "")
                f.write(f"| {tool_name} | {status} | {latency} | {description} |\n")
            
            # Benchmark
            f.write("\n## ⏱️ Benchmark de Performance\n\n")
            benchmark_results = self.results.get("benchmark", {})
            if benchmark_results:
                f.write("| Ferramenta | Success Rate | Avg (ms) | P95 (ms) | SLA |\n")
                f.write("|------------|--------------|----------|----------|-----|\n")
                for tool_name, result in benchmark_results.items():
                    success_rate = f"{result.get('success_rate', 0)*100:.1f}%"
                    avg_lat = f"{result.get('avg_latency_ms', 0):.1f}"
                    p95_lat = f"{result.get('p95_latency_ms', 0):.1f}" 
                    sla_status = "✅" if result.get("sla_met") else "❌"
                    f.write(f"| {tool_name} | {success_rate} | {avg_lat} | {p95_lat} | {sla_status} |\n")
            
            # Teste ITSA3/ITSA4
            f.write("\n## 🇧🇷 Status ITSA3/ITSA4\n\n")
            itsa_results = self.results.get("itsa_symbols", {})
            for symbol in ["ITSA3", "ITSA4"]:
                if symbol in itsa_results:
                    symbol_data = itsa_results[symbol]
                    info_ok = "✅" if symbol_data.get("symbol_info", {}).get("success") else "❌"
                    tick_ok = "✅" if symbol_data.get("tick_info", {}).get("success") else "❌"
                    book_ok = "✅" if symbol_data.get("book_info", {}).get("success") else "❌"
                    f.write(f"- **{symbol}**: Info {info_ok} | Tick {tick_ok} | Book {book_ok}\n")
            
            # Gaps
            f.write("\n## 🔍 Gaps Identificados\n\n")
            for gap in gaps.get("identified_gaps", []):
                f.write(f"- {gap}\n")
            
            f.write("\n## 💡 Recomendações\n\n")
            for rec in gaps.get("recommendations", []):
                f.write(f"1. {rec}\n")
            
            f.write(f"""
## 🎯 Próximos Passos

1. **Corrigir gaps críticos** identificados acima
2. **Implementar melhorias de performance** para ferramentas com latência alta
3. **Validar símbolos ITSA3/ITSA4** estão disponíveis no MT5
4. **Configurar Level 2 data** para análise de spread
5. **Prosseguir para E2.1** - Especificação de contratos MCP

---

*Auditoria realizada automaticamente pela ferramenta ETAPA 2.0*
""")

    async def run_complete_audit(self):
        """Executar auditoria completa"""
        if not await self.initialize_audit():
            return False
        
        # Executar todas as verificações
        await self.audit_critical_tools_for_etapa2()
        await self.test_itsa3_itsa4_symbols()
        await self.benchmark_latency()
        await self.identify_gaps_for_etapa2()
        
        # Salvar resultados
        json_file, md_file = await self.save_results()
        
        # Sumário final
        print(f"\n🎉 AUDITORIA E2.0 CONCLUÍDA")
        print("=" * 60)
        print(f"⏱️  Duração: {time.time() - self.start_time:.1f} segundos")
        print(f"📁 Resultados: {json_file}")
        print(f"📋 Relatório: {md_file}")
        
        # Status final
        gaps = self.results.get("gaps", {})
        gap_count = len(gaps.get("identified_gaps", []))
        severity = gaps.get("severity", "UNKNOWN")
        
        if gap_count == 0:
            print("✅ STATUS: Servidor MCP está pronto para ETAPA 2")
        elif severity == "HIGH":
            print("🚨 STATUS: Gaps críticos encontrados - correção necessária antes de prosseguir")
        else:
            print("⚠️  STATUS: Gaps menores encontrados - pode prosseguir com cuidado")
        
        return True

async def main():
    """Executar auditoria E2.0"""
    auditor = MCPE20Auditor()
    await auditor.run_complete_audit()

if __name__ == "__main__":
    asyncio.run(main())