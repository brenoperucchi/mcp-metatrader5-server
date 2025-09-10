#!/usr/bin/env python3
"""
Script para testar o protocolo MCP e auditar as ferramentas disponíveis
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List

class MCPProtocolTester:
    def __init__(self, server_url: str):
        self.server_url = server_url.replace('http://', '').replace('https://', '')
        self.base_url = f"http://{self.server_url}"
        self.rpc_url = f"{self.base_url}/mcp"
        self.request_id = 1

    async def call_method(self, method: str, params: dict = None) -> Dict[str, Any]:
        """Call MCP method directly"""
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        self.request_id += 1
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.post(
                    self.rpc_url, 
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True, 
                            "data": result,
                            "latency_ms": latency_ms,
                            "status": response.status
                        }
                    else:
                        text = await response.text()
                        return {
                            "success": False, 
                            "error": f"HTTP {response.status}: {text}",
                            "latency_ms": latency_ms,
                            "status": response.status
                        }
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "latency_ms": 0,
                "status": 0
            }

    async def audit_capabilities(self) -> Dict[str, Any]:
        """Audit MCP server capabilities"""
        results = {}
        
        # Test 1: List tools
        print("🔍 Testing tools/list...")
        tools_result = await self.call_method("tools/list")
        results["tools_list"] = tools_result
        
        if tools_result["success"]:
            tools = tools_result["data"].get("result", {}).get("tools", [])
            print(f"✅ Found {len(tools)} tools")
            for tool in tools[:5]:  # Show first 5
                print(f"  - {tool['name']}: {tool['description']}")
        else:
            print(f"❌ Failed: {tools_result['error']}")
            return results
        
        # Test 2: Try different methods for calling tools
        test_methods = [
            "get_account_info",
            "get_terminal_info", 
            "get_version",
            "get_symbols"
        ]
        
        for method in test_methods:
            print(f"\n🧪 Testing direct method: {method}")
            result = await self.call_method(method)
            results[f"direct_{method}"] = result
            
            if result["success"]:
                print(f"✅ {method}: Success (latency: {result['latency_ms']:.1f}ms)")
            else:
                print(f"❌ {method}: {result['error']}")
        
        # Test 3: Try to get symbol info for ITSA3/ITSA4
        symbols_to_test = ["ITSA3", "ITSA4"]
        for symbol in symbols_to_test:
            print(f"\n📊 Testing symbol info: {symbol}")
            result = await self.call_method("get_symbol_info", {"symbol": symbol})
            results[f"symbol_{symbol}"] = result
            
            if result["success"]:
                data = result["data"].get("result", {})
                print(f"✅ {symbol}: Found symbol data")
                if isinstance(data, dict):
                    for key in ["bid", "ask", "last", "volume"]:
                        if key in data:
                            print(f"  {key}: {data[key]}")
            else:
                print(f"❌ {symbol}: {result['error']}")
        
        return results

    async def benchmark_latency(self, method: str = "get_version", iterations: int = 10):
        """Benchmark method latency"""
        print(f"\n⏱️  Benchmarking {method} ({iterations} calls)...")
        
        latencies = []
        success_count = 0
        
        for i in range(iterations):
            result = await self.call_method(method)
            if result["success"]:
                latencies.append(result["latency_ms"])
                success_count += 1
            print(f"  {i+1}/{iterations}: {'✅' if result['success'] else '❌'} {result['latency_ms']:.1f}ms")
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            print(f"\n📈 Latency Results for {method}:")
            print(f"  Success Rate: {success_count}/{iterations} ({success_count/iterations*100:.1f}%)")
            print(f"  Average: {avg_latency:.1f}ms")
            print(f"  P95: {p95_latency:.1f}ms") 
            print(f"  P99: {p99_latency:.1f}ms")
            
            return {
                "success_rate": success_count/iterations,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "p99_latency_ms": p99_latency,
                "all_latencies": latencies
            }
        else:
            print(f"❌ All calls failed for {method}")
            return {"success_rate": 0}

async def main():
    print("🚀 MCP MT5 Protocol Audit")
    print("=" * 50)
    
    server_url = "192.168.0.125:8000"
    tester = MCPProtocolTester(server_url)
    
    # Audit capabilities
    audit_results = await tester.audit_capabilities()
    
    # Benchmark some calls
    benchmark_results = await tester.benchmark_latency("get_version", 5)
    
    # Save results
    results = {
        "timestamp": time.time(),
        "server_url": server_url,
        "audit": audit_results,
        "benchmark": benchmark_results
    }
    
    with open("mcp_audit_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to mcp_audit_results.json")
    
    # Summary
    print("\n📋 SUMMARY")
    print("-" * 30)
    tools_count = 0
    if audit_results.get("tools_list", {}).get("success"):
        tools_data = audit_results["tools_list"]["data"].get("result", {})
        tools_count = len(tools_data.get("tools", []))
    
    print(f"🔧 Tools Available: {tools_count}")
    print(f"🔗 Server URL: http://{server_url}")
    
    # Check critical tools for trading
    critical_tools = ["get_account_info", "get_symbol_info", "order_send", "positions_get"]
    print(f"\n🎯 Critical Tools Status:")
    for tool in critical_tools:
        key = f"direct_{tool}"
        if key in audit_results:
            status = "✅" if audit_results[key]["success"] else "❌"
            print(f"  {tool}: {status}")
    
    if benchmark_results.get("success_rate", 0) > 0:
        print(f"\n⚡ Performance:")
        print(f"  Success Rate: {benchmark_results['success_rate']*100:.1f}%")
        print(f"  Average Latency: {benchmark_results['avg_latency_ms']:.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())