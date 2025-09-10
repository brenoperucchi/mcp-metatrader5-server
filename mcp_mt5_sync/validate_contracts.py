#!/usr/bin/env python3
"""
E2.1 Contract Validation Tool
Valida se os contratos MCP estão sendo respeitados pelo servidor
"""

import asyncio
import aiohttp
import yaml
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

class ContractValidator:
    def __init__(self, server_url="192.168.0.125:8000", contracts_file="contracts_etapa2_simple.yaml"):
        self.server_url = server_url
        self.base_url = f"http://{server_url}"
        self.rpc_url = f"{self.base_url}/mcp"
        self.request_id = 1
        self.contracts = {}
        self.results = {}
        
        # Carregar contratos
        self.load_contracts(contracts_file)
        
    def load_contracts(self, contracts_file: str):
        """Carrega especificações dos contratos"""
        try:
            with open(contracts_file, 'r') as f:
                self.contracts = yaml.safe_load(f)
            print(f"✅ Contratos carregados: {contracts_file}")
        except Exception as e:
            print(f"❌ Erro ao carregar contratos: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Chama ferramenta via MCP"""
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
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if "error" in result:
                            return {
                                "success": False,
                                "error": result["error"]["message"],
                                "latency_ms": latency_ms,
                                "raw_response": result
                            }
                        
                        content = result.get("result", {}).get("content", {})
                        return {
                            "success": True,
                            "data": content,
                            "latency_ms": latency_ms,
                            "raw_response": result
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

    async def validate_connection_tools(self):
        """Valida ferramentas de conexão"""
        print("\n🔗 VALIDAÇÃO: CONNECTION TOOLS")
        print("-" * 50)
        
        connection_tools = self.contracts.get("connection_tools", {})
        results = {}
        
        for tool_name, spec in connection_tools.items():
            print(f"\n🔍 Validando: {tool_name}")
            
            # Testar ferramenta
            result = await self.call_tool(tool_name)
            
            # Validar SLA
            sla_ms = spec.get("sla_ms", 1000)
            sla_met = result["latency_ms"] <= sla_ms
            
            # Validar schema básico
            schema_valid = self.validate_response_schema(result, spec, tool_name)
            
            # Validar regras específicas
            business_rules_ok = await self.validate_business_rules(tool_name, result)
            
            if result["success"]:
                print(f"   ✅ Execução: OK ({result['latency_ms']:.1f}ms)")
                print(f"   {'✅' if sla_met else '❌'} SLA: {sla_ms}ms ({'PASS' if sla_met else 'FAIL'})")
                print(f"   {'✅' if schema_valid else '❌'} Schema: {'VALID' if schema_valid else 'INVALID'}")
                print(f"   {'✅' if business_rules_ok else '❌'} Business Rules: {'OK' if business_rules_ok else 'FAIL'}")
            else:
                print(f"   ❌ Execução: {result['error']}")
                sla_met = False
                schema_valid = False
                business_rules_ok = False
            
            results[tool_name] = {
                "success": result["success"],
                "latency_ms": result["latency_ms"],
                "sla_met": sla_met,
                "schema_valid": schema_valid,
                "business_rules_ok": business_rules_ok,
                "critical": spec.get("critical_for_etapa2", False)
            }
        
        self.results["connection_tools"] = results
        return results

    async def validate_market_data_tools(self):
        """Valida ferramentas de market data"""
        print("\n📊 VALIDAÇÃO: MARKET DATA TOOLS")
        print("-" * 50)
        
        market_tools = self.contracts.get("market_data_tools", {})
        results = {}
        
        # Teste com símbolos ITSA3 e ITSA4
        test_symbols = ["ITSA3", "ITSA4"]
        
        for tool_name, spec in market_tools.items():
            print(f"\n📈 Validando: {tool_name}")
            
            # Para tools que precisam de símbolo, testar com ITSA3 e ITSA4
            if tool_name in ["get_symbol_info", "get_symbol_info_tick", "symbol_select"]:
                symbol_results = {}
                
                for symbol in test_symbols:
                    print(f"   🔍 Testando com {symbol}:")
                    
                    args = {"symbol": symbol}
                    if tool_name == "symbol_select":
                        args["visible"] = True
                    
                    result = await self.call_tool(tool_name, args)
                    
                    # Validações específicas para market data
                    data_quality_ok = self.validate_market_data_quality(result, symbol)
                    sla_ms = spec.get("sla_ms", 100)
                    sla_met = result["latency_ms"] <= sla_ms
                    
                    if result["success"]:
                        print(f"      ✅ OK ({result['latency_ms']:.1f}ms)")
                        
                        # Para get_symbol_info, mostrar dados críticos
                        if tool_name == "get_symbol_info" and isinstance(result["data"], dict):
                            data = result["data"]
                            bid = data.get("bid", 0)
                            ask = data.get("ask", 0)
                            spread = ask - bid if bid and ask else 0
                            spread_pct = (spread / bid * 100) if bid > 0 else 0
                            
                            print(f"         💰 Bid: {bid} | Ask: {ask} | Spread: {spread_pct:.2f}%")
                            
                    else:
                        print(f"      ❌ {result['error']}")
                        data_quality_ok = False
                        sla_met = False
                    
                    symbol_results[symbol] = {
                        "success": result["success"],
                        "latency_ms": result["latency_ms"],
                        "sla_met": sla_met,
                        "data_quality_ok": data_quality_ok
                    }
                
                # Calcular resultado consolidado
                all_success = all(r["success"] for r in symbol_results.values())
                avg_latency = sum(r["latency_ms"] for r in symbol_results.values()) / len(symbol_results)
                all_sla_met = all(r["sla_met"] for r in symbol_results.values())
                
                results[tool_name] = {
                    "success": all_success,
                    "avg_latency_ms": avg_latency,
                    "sla_met": all_sla_met,
                    "symbols_tested": symbol_results,
                    "critical": spec.get("critical_for_etapa2", False)
                }
                
            else:
                # Tools que não precisam de símbolo específico
                result = await self.call_tool(tool_name)
                sla_ms = spec.get("sla_ms", 100)
                sla_met = result["latency_ms"] <= sla_ms
                
                results[tool_name] = {
                    "success": result["success"],
                    "latency_ms": result["latency_ms"],
                    "sla_met": sla_met,
                    "critical": spec.get("critical_for_etapa2", False)
                }
        
        self.results["market_data_tools"] = results
        return results

    async def validate_trading_tools_safety(self):
        """Valida ferramentas de trading (apenas order_check por segurança)"""
        print("\n⚡ VALIDAÇÃO: TRADING TOOLS (SAFETY ONLY)")
        print("-" * 50)
        
        # APENAS testar order_check, nunca order_send em validação
        print("🛡️  Testando apenas order_check por segurança")
        
        result = await self.call_tool("order_check", {
            "request": {
                "action": 1,  # TRADE_ACTION_DEAL
                "symbol": "ITSA3",
                "volume": 100,
                "type": 0,  # ORDER_TYPE_BUY
                "price": 11.50,
                "comment": "ETAPA2-VALIDATION-TEST",
                "magic": 234000
            }
        })
        
        sla_met = result["latency_ms"] <= 200  # SLA 200ms
        
        if result["success"]:
            print(f"   ✅ order_check: OK ({result['latency_ms']:.1f}ms)")
            
            # Verificar se dados de margem estão presentes
            data = result["data"]
            if isinstance(data, dict):
                balance = data.get("balance", 0)
                margin_free = data.get("margin_free", 0)
                print(f"      💰 Balance: R$ {balance:,.2f}")
                print(f"      📊 Margin Free: R$ {margin_free:,.2f}")
        else:
            print(f"   ❌ order_check: {result['error']}")
            sla_met = False
        
        self.results["trading_tools"] = {
            "order_check": {
                "success": result["success"],
                "latency_ms": result["latency_ms"],
                "sla_met": sla_met,
                "critical": True
            },
            "order_send": {
                "success": None,
                "note": "NOT TESTED - Safety validation only"
            }
        }
        
        return self.results["trading_tools"]

    def validate_response_schema(self, result: dict, spec: dict, tool_name: str) -> bool:
        """Valida schema básico da resposta"""
        if not result["success"]:
            return False
        
        data = result.get("data", {})
        
        # Validações básicas dependendo da ferramenta
        if tool_name == "get_account_info":
            required_fields = ["login", "trade_mode", "balance", "equity"]
            return all(field in data for field in required_fields)
        
        elif tool_name in ["get_symbol_info", "get_symbol_info_tick"]:
            required_fields = ["bid", "ask", "last"]
            return all(field in data and isinstance(data[field], (int, float)) and data[field] > 0 
                      for field in required_fields)
        
        elif tool_name == "order_check":
            required_fields = ["balance", "margin_free"]
            return all(field in data for field in required_fields)
        
        # Default: se retornou dados, considera válido
        return isinstance(data, (dict, list, bool, str, int, float))

    def validate_market_data_quality(self, result: dict, symbol: str) -> bool:
        """Valida qualidade dos dados de market data"""
        if not result["success"]:
            return False
        
        data = result.get("data", {})
        
        # Se data não é um dict, não podemos validar dados de mercado
        if not isinstance(data, dict):
            return True  # Para tools como symbol_select que retornam boolean
        
        # Verificar se é get_symbol_info
        if "bid" in data and "ask" in data:
            bid = data.get("bid", 0)
            ask = data.get("ask", 0)
            
            # Validações de qualidade
            if bid <= 0 or ask <= 0:
                return False
            
            if ask < bid:  # Spread negativo
                return False
            
            # Spread muito alto (> 5%)
            spread_pct = ((ask - bid) / bid * 100) if bid > 0 else 0
            if spread_pct > 5:
                return False
            
            # Preços muito baixos ou altos (sanity check)
            if bid < 0.10 or bid > 1000:
                return False
        
        return True

    async def validate_business_rules(self, tool_name: str, result: dict) -> bool:
        """Valida regras específicas de negócio"""
        if not result["success"]:
            return False
        
        if tool_name == "get_account_info":
            data = result.get("data", {})
            trade_mode = data.get("trade_mode")
            
            # CRÍTICO: Deve ser conta DEMO (trade_mode = 0)
            if trade_mode != 0:
                print(f"      ⚠️  WARNING: Account is not DEMO (trade_mode={trade_mode})")
                return False
            
            # Balance mínimo para operação
            balance = data.get("balance", 0)
            if balance < 1000:
                print(f"      ⚠️  WARNING: Balance too low ({balance})")
                return False
        
        return True

    async def generate_validation_report(self):
        """Gera relatório de validação"""
        print("\n📋 RELATÓRIO DE VALIDAÇÃO DE CONTRATOS")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        critical_failures = 0
        
        for category, tools in self.results.items():
            if not tools:
                continue
                
            print(f"\n📊 {category.upper().replace('_', ' ')}")
            print("-" * 30)
            
            for tool_name, result in tools.items():
                if result.get("success") is None:
                    continue
                
                total_tests += 1
                is_critical = result.get("critical", False)
                success = result.get("success", False)
                
                if success:
                    passed_tests += 1
                    status = "✅"
                elif is_critical:
                    critical_failures += 1
                    status = "🔴"
                else:
                    status = "⚠️"
                
                latency = result.get("latency_ms", 0)
                sla_met = result.get("sla_met", False)
                
                print(f"   {status} {tool_name}: {latency:.1f}ms ({'SLA OK' if sla_met else 'SLA FAIL'})")
        
        # Status final
        print(f"\n🎯 RESULTADO FINAL")
        print("-" * 30)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"📊 Testes: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"🔴 Falhas críticas: {critical_failures}")
        
        if critical_failures == 0 and success_rate >= 80:
            final_status = "🟢 APROVADO"
            message = "Contratos validados com sucesso"
        elif critical_failures == 0:
            final_status = "🟡 APROVADO COM RESSALVAS" 
            message = "Alguns testes falharam, mas nenhum crítico"
        else:
            final_status = "🔴 REPROVADO"
            message = f"{critical_failures} falhas críticas encontradas"
        
        print(f"\n{final_status}")
        print(f"💬 {message}")
        
        # Salvar relatório JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"contract_validation_{timestamp}.json"
        
        report_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "server_url": self.server_url,
                "validation_type": "Contract Compliance E2.1"
            },
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "critical_failures": critical_failures,
                "success_rate": success_rate,
                "final_status": final_status,
                "message": message
            },
            "detailed_results": self.results
        }
        
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Relatório salvo: {report_file}")
        
        return final_status == "🟢 APROVADO"

    async def run_validation(self):
        """Executa validação completa dos contratos"""
        print("🔍 VALIDAÇÃO DE CONTRATOS MCP - ETAPA 2.1")
        print("=" * 60)
        print(f"🔗 Servidor: {self.server_url}")
        print(f"📄 Contratos: {len(self.contracts)} categorias")
        
        # Executar validações
        await self.validate_connection_tools()
        await self.validate_market_data_tools()
        await self.validate_trading_tools_safety()
        
        # Gerar relatório final
        success = await self.generate_validation_report()
        
        return success

async def main():
    validator = ContractValidator()
    
    try:
        success = await validator.run_validation()
        
        if success:
            print("\n🚀 PRÓXIMO PASSO: E2.2 - Implementar testbench Python")
        else:
            print("\n⚠️  Corrigir problemas antes de prosseguir para E2.2")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Erro durante validação: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)