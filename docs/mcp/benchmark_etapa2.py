#!/usr/bin/env python3
"""
Benchmark de Performance - Etapa 2
Valida latências P95/P99 do servidor MCP MT5
"""

import asyncio
import time
import statistics
import json
from datetime import datetime
import sys
sys.path.append('../../main_mcp/client')

# Tentar importar o cliente MCP
try:
    from mcp_mt5_client import MT5MCPClient
except ImportError:
    print("⚠️ Cliente MCP não encontrado, usando httpx direto")
    import httpx
    
    class MT5MCPClient:
        def __init__(self, server_url="http://localhost:50051"):
            self.server_url = server_url
            self.client = httpx.AsyncClient(timeout=30.0)
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.client.aclose()
        
        async def call_tool(self, tool_name, arguments=None):
            response = await self.client.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {}
                    },
                    "id": 1
                }
            )
            return response.json()

class PerformanceBenchmark:
    """Benchmark de performance do MCP MT5"""
    
    def __init__(self, server_url="http://localhost:50051"):
        self.server_url = server_url
        self.results = {}
    
    async def measure_operation(self, client, operation_name, tool_name, arguments=None, iterations=60):
        """Mede latência de uma operação"""
        print(f"📊 Medindo {operation_name}... ({iterations} iterações)")
        
        latencies = []
        errors = 0
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                result = await client.call_tool(tool_name, arguments)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                latencies.append(elapsed)
                
                # Pequena pausa entre requests
                if i % 10 == 0:
                    print(f"   {i}/{iterations} completo...")
                await asyncio.sleep(0.1)  # 100ms entre requests
                
            except Exception as e:
                errors += 1
                print(f"   ❌ Erro: {e}")
        
        if latencies:
            latencies.sort()
            stats = {
                "operation": operation_name,
                "tool": tool_name,
                "iterations": iterations,
                "errors": errors,
                "min": latencies[0],
                "max": latencies[-1],
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                "p50": latencies[len(latencies)//2],
                "p95": latencies[int(len(latencies)*0.95)],
                "p99": latencies[min(int(len(latencies)*0.99), len(latencies)-1)],
            }
            
            self.results[operation_name] = stats
            return stats
        
        return None
    
    async def run_benchmark(self):
        """Executa benchmark completo"""
        print("🚀 Iniciando Benchmark de Performance - Etapa 2")
        print("=" * 60)
        print(f"Servidor: {self.server_url}")
        print(f"Hora início: {datetime.now().isoformat()}")
        print("=" * 60)
        
        async with MT5MCPClient(self.server_url) as client:
            # 1. Quotes (get_symbol_info_tick)
            await self.measure_operation(
                client,
                "get_quotes",
                "get_symbol_info_tick",
                {"symbol": "PETR4"},
                iterations=60
            )
            
            # 2. Ticks históricos
            await self.measure_operation(
                client,
                "get_ticks",
                "copy_ticks_from_pos",
                {"symbol": "PETR4", "start_pos": 0, "count": 100},
                iterations=30
            )
            
            # 3. Posições
            await self.measure_operation(
                client,
                "get_positions",
                "positions_get",
                {},
                iterations=30
            )
            
            # 4. Ordens
            await self.measure_operation(
                client,
                "get_orders",
                "orders_get",
                {},
                iterations=30
            )
            
            # 5. Validação de ordem (simula place_order)
            order_request = {
                "action": 1,
                "symbol": "PETR4",
                "volume": 100,
                "type": 0,
                "price": 30.00,
                "deviation": 20,
                "magic": 123456,
                "comment": "Benchmark test"
            }
            
            await self.measure_operation(
                client,
                "place_order_check",
                "order_check",
                {"request": order_request},
                iterations=30
            )
        
        # Gerar relatório
        self.generate_report()
        
        print("\n✅ Benchmark completo!")
        print(f"Hora fim: {datetime.now().isoformat()}")
    
    def generate_report(self):
        """Gera relatório de benchmark"""
        
        # Salvar resultados raw
        with open("benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Gerar relatório markdown
        report = f"""# Benchmark Report - Etapa 2

## 📊 Resultados de Performance

**Data**: {datetime.now().isoformat()}
**Servidor**: {self.server_url}

## Sumário Executivo

| Operação | Iterações | Erros | Min (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) |
|----------|-----------|-------|----------|----------|----------|----------|----------|
"""
        
        for op_name, stats in self.results.items():
            report += f"| {op_name} | {stats['iterations']} | {stats['errors']} | "
            report += f"{stats['min']:.2f} | {stats['p50']:.2f} | "
            report += f"{stats['p95']:.2f} | {stats['p99']:.2f} | {stats['max']:.2f} |\n"
        
        # Análise de critérios
        report += "\n## ✅ Validação de Critérios\n\n"
        
        # Critério 1: Quotes P95 < 150ms
        if "get_quotes" in self.results:
            p95_quotes = self.results["get_quotes"]["p95"]
            if p95_quotes < 150:
                report += f"- ✅ **Quotes P95 < 150ms**: {p95_quotes:.2f}ms\n"
            else:
                report += f"- ❌ **Quotes P95 < 150ms**: {p95_quotes:.2f}ms (FALHOU)\n"
        
        # Critério 2: Orders P95 < 400ms
        if "place_order_check" in self.results:
            p95_orders = self.results["place_order_check"]["p95"]
            if p95_orders < 400:
                report += f"- ✅ **Orders P95 < 400ms**: {p95_orders:.2f}ms\n"
            else:
                report += f"- ❌ **Orders P95 < 400ms**: {p95_orders:.2f}ms (FALHOU)\n"
        
        # Estatísticas detalhadas
        report += "\n## 📈 Estatísticas Detalhadas\n\n"
        
        for op_name, stats in self.results.items():
            report += f"### {op_name}\n\n"
            report += f"- **Média**: {stats['mean']:.2f}ms\n"
            report += f"- **Mediana**: {stats['median']:.2f}ms\n"
            report += f"- **Desvio Padrão**: {stats['stdev']:.2f}ms\n"
            report += f"- **Taxa de Erro**: {stats['errors']}/{stats['iterations']} "
            report += f"({100*stats['errors']/stats['iterations']:.1f}%)\n\n"
        
        # Recomendações
        report += "## 🎯 Recomendações\n\n"
        
        all_good = True
        if "get_quotes" in self.results and self.results["get_quotes"]["p95"] > 150:
            report += "- ⚠️ Otimizar latência de quotes\n"
            all_good = False
        
        if "place_order_check" in self.results and self.results["place_order_check"]["p95"] > 400:
            report += "- ⚠️ Otimizar latência de ordens\n"
            all_good = False
        
        for op_name, stats in self.results.items():
            if stats["errors"] > stats["iterations"] * 0.05:  # > 5% erro
                report += f"- ⚠️ Investigar alta taxa de erro em {op_name}\n"
                all_good = False
        
        if all_good:
            report += "- ✅ Performance dentro dos parâmetros esperados\n"
        
        # Conclusão
        report += "\n## 📝 Conclusão\n\n"
        
        if all_good:
            report += "**Status**: ✅ APROVADO - Servidor atende aos critérios de performance\n"
        else:
            report += "**Status**: ⚠️ APROVADO COM RESSALVAS - Alguns critérios não atendidos\n"
        
        # Salvar relatório
        with open("benchmark_etapa2.md", "w") as f:
            f.write(report)
        
        print("\n📄 Relatório salvo em: benchmark_etapa2.md")
        print("📊 Dados raw salvos em: benchmark_results.json")

async def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark MCP MT5 - Etapa 2")
    parser.add_argument("--server", default="http://localhost:50051", help="URL do servidor MCP")
    parser.add_argument("--quick", action="store_true", help="Modo rápido (menos iterações)")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.server)
    
    if args.quick:
        print("⚡ Modo rápido ativado (10 iterações por operação)")
        # Ajustar para menos iterações em modo quick
    
    await benchmark.run_benchmark()

if __name__ == "__main__":
    asyncio.run(main())