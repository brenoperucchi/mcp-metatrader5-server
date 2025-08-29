#!/usr/bin/env python3
"""
MCP MT5 Capability Tester - Etapa 2
Mapeia e testa todas as ferramentas do servidor MCP MT5
"""

import asyncio
import json
import time
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

class MCPCapabilityTester:
    """Testador de capacidades do servidor MCP MT5"""
    
    def __init__(self, server_url: str = "http://localhost:50051"):
        self.server_url = server_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = {
            "tools": {},
            "resources": {},
            "latency": {},
            "errors": [],
            "samples": {}
        }
        self.samples_dir = Path("samples")
        self.samples_dir.mkdir(exist_ok=True)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def measure_latency(self, func, *args, **kwargs):
        """Mede latência de uma chamada"""
        latencies = []
        for _ in range(10):  # 10 amostras
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                latency = (time.perf_counter() - start) * 1000  # ms
                latencies.append(latency)
            except Exception as e:
                self.results["errors"].append(str(e))
                
        if latencies:
            latencies.sort()
            return {
                "min": latencies[0],
                "p50": latencies[len(latencies)//2],
                "p95": latencies[int(len(latencies)*0.95)],
                "p99": latencies[min(int(len(latencies)*0.99), len(latencies)-1)],
                "max": latencies[-1]
            }
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chama uma ferramenta MCP"""
        try:
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
        except Exception as e:
            return {"error": str(e)}
    
    async def list_tools(self) -> List[str]:
        """Lista todas as ferramentas disponíveis"""
        try:
            response = await self.client.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 1
                }
            )
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                return result["result"]["tools"]
            return []
        except Exception as e:
            self.results["errors"].append(f"list_tools error: {e}")
            return []
    
    async def list_resources(self) -> List[str]:
        """Lista todos os resources disponíveis"""
        try:
            response = await self.client.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "resources/list",
                    "params": {},
                    "id": 1
                }
            )
            result = response.json()
            if "result" in result and "resources" in result["result"]:
                return result["result"]["resources"]
            return []
        except Exception as e:
            self.results["errors"].append(f"list_resources error: {e}")
            return []
    
    async def test_get_quotes(self):
        """Testa obtenção de cotações"""
        print("📊 Testando get_quotes...")
        
        # Testar com PETR4
        result = await self.call_tool("get_symbol_info", {"symbol": "PETR4"})
        self.results["samples"]["get_quotes_PETR4"] = result
        
        # Salvar amostra
        with open(self.samples_dir / "get_quotes_PETR4.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Medir latência
        latency = await self.measure_latency(
            self.call_tool, "get_symbol_info", {"symbol": "PETR4"}
        )
        self.results["latency"]["get_quotes"] = latency
        
        return result
    
    async def test_get_ticks(self):
        """Testa obtenção de ticks"""
        print("📈 Testando get_ticks...")
        
        # Testar com PETR4
        result = await self.call_tool("copy_ticks_from", {
            "symbol": "PETR4",
            "date_from": "2024-01-01",
            "count": 10
        })
        self.results["samples"]["get_ticks_PETR4"] = result
        
        # Salvar amostra
        with open(self.samples_dir / "get_ticks_PETR4.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Medir latência
        latency = await self.measure_latency(
            self.call_tool, "copy_ticks_from", 
            {"symbol": "PETR4", "date_from": "2024-01-01", "count": 10}
        )
        self.results["latency"]["get_ticks"] = latency
        
        return result
    
    async def test_get_positions(self):
        """Testa obtenção de posições"""
        print("💼 Testando get_positions...")
        
        result = await self.call_tool("positions_get")
        self.results["samples"]["get_positions"] = result
        
        # Salvar amostra
        with open(self.samples_dir / "get_positions.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Medir latência
        latency = await self.measure_latency(self.call_tool, "positions_get")
        self.results["latency"]["get_positions"] = latency
        
        return result
    
    async def test_get_orders(self):
        """Testa obtenção de ordens"""
        print("📋 Testando get_orders...")
        
        result = await self.call_tool("orders_get")
        self.results["samples"]["get_orders"] = result
        
        # Salvar amostra
        with open(self.samples_dir / "get_orders.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Medir latência
        latency = await self.measure_latency(self.call_tool, "orders_get")
        self.results["latency"]["get_orders"] = latency
        
        return result
    
    async def test_place_order(self):
        """Testa envio de ordem (simulado)"""
        print("🎯 Testando place_order...")
        
        # Ordem de teste (não será enviada realmente)
        order_request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": "PETR4",
            "volume": 100,
            "type": 0,  # ORDER_TYPE_BUY
            "price": 30.00,
            "deviation": 20,
            "magic": 123456,
            "comment": "Test order MCP"
        }
        
        result = await self.call_tool("order_check", {"request": order_request})
        self.results["samples"]["place_order_check"] = result
        
        # Salvar amostra
        with open(self.samples_dir / "place_order_check.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Medir latência
        latency = await self.measure_latency(
            self.call_tool, "order_check", {"request": order_request}
        )
        self.results["latency"]["place_order"] = latency
        
        return result
    
    async def run_full_test(self):
        """Executa todos os testes"""
        print("🚀 Iniciando teste completo de capacidades MCP MT5")
        print("=" * 60)
        
        # 1. Listar ferramentas
        print("\n📦 Listando ferramentas disponíveis...")
        tools = await self.list_tools()
        self.results["tools"]["available"] = tools
        print(f"   Encontradas: {len(tools)} ferramentas")
        
        # 2. Listar resources
        print("\n📚 Listando resources disponíveis...")
        resources = await self.list_resources()
        self.results["resources"]["available"] = resources
        print(f"   Encontrados: {len(resources)} resources")
        
        # 3. Testar ferramentas principais
        print("\n🧪 Testando ferramentas principais...")
        
        # Testar cada ferramenta
        await self.test_get_quotes()
        await self.test_get_ticks()
        await self.test_get_positions()
        await self.test_get_orders()
        await self.test_place_order()
        
        # 4. Gerar relatório
        print("\n📊 Gerando relatório de capacidades...")
        self.generate_capability_matrix()
        self.generate_benchmark_report()
        
        print("\n✅ Teste completo finalizado!")
        print(f"   Amostras salvas em: {self.samples_dir}")
        print(f"   Relatórios gerados em: docs/mcp/")
        
        return self.results
    
    def generate_capability_matrix(self):
        """Gera matriz de capacidades"""
        matrix = """# MCP MT5 Capability Matrix

## 📋 Ferramentas Disponíveis

| Ferramenta | Status | Schema Input | Schema Output | Latência P95 |
|------------|--------|--------------|---------------|--------------|
"""
        
        # Adicionar ferramentas testadas
        for tool_name in ["get_quotes", "get_ticks", "get_positions", "get_orders", "place_order"]:
            sample = self.results["samples"].get(tool_name, {})
            latency = self.results["latency"].get(tool_name, {})
            
            status = "✅" if not sample.get("error") else "❌"
            p95 = f"{latency.get('p95', 0):.2f}ms" if latency else "N/A"
            
            matrix += f"| {tool_name} | {status} | Documentado | Documentado | {p95} |\n"
        
        # Salvar matriz
        with open("capability_matrix.md", "w") as f:
            f.write(matrix)
    
    def generate_benchmark_report(self):
        """Gera relatório de benchmark"""
        report = f"""# Benchmark Report - Etapa 2

## 📊 Resultados de Latência

Data: {datetime.now().isoformat()}

### Métricas de Performance

| Operação | Min (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) |
|----------|----------|----------|----------|----------|----------|
"""
        
        for op, latency in self.results["latency"].items():
            if latency:
                report += f"| {op} | {latency['min']:.2f} | {latency['p50']:.2f} | {latency['p95']:.2f} | {latency['p99']:.2f} | {latency['max']:.2f} |\n"
        
        # Adicionar análise
        report += "\n## ✅ Critérios Atendidos\n\n"
        report += "- [x] P95 < 150ms para quotes\n" if self.results["latency"].get("get_quotes", {}).get("p95", 999) < 150 else "- [ ] P95 < 150ms para quotes\n"
        report += "- [x] P95 < 400ms para place_order\n" if self.results["latency"].get("place_order", {}).get("p95", 999) < 400 else "- [ ] P95 < 400ms para place_order\n"
        
        # Salvar relatório
        with open("benchmark_etapa2.md", "w") as f:
            f.write(report)

async def main():
    """Função principal"""
    async with MCPCapabilityTester() as tester:
        await tester.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())