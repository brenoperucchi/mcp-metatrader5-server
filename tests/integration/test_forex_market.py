#!/usr/bin/env python3
"""
💱 MCP MetaTrader 5 - Forex Market Integration Test
==================================================

Specific test for Forex market server (port 50052)
- Darwinex Demo Account: 3000064180
- Forex symbols: EURUSD, GBPUSD, USDJPY, etc.
- Real-time data and trading capabilities

Server Configuration:
- Host: 192.168.0.125:50052
- Account: 3000064180
- Server: Darwinex-Demo
- Market: forex
"""

import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from client.mcp_mt5_client import MT5MCPClient


class ForexMarketTest:
    """Forex market specific integration test"""
    
    def __init__(self, server_url: str = "http://192.168.0.125:50052"):
        self.client = MT5MCPClient(server_url)
        self.test_results = []
        self.forex_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        self.test_symbol = None
    
    async def log_test(self, test_name: str, success: bool, data: dict = None, error: str = None):
        """Log test result"""
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
            print(f"   [ERROR] {error}")
        elif data:
            formatted_data = json.dumps(data, indent=2)[:200]
            print(f"   [DATA] {formatted_data}...")
    
    async def test_forex_connectivity(self):
        """Test connection to Forex server"""
        try:
            # Test basic connection
            connected = await self.client.test_connection()
            if not connected:
                await self.log_test("Forex Conectividade", False, error="Servidor Forex não responde")
                return False
            
            # Get symbols list
            symbols_result = await self.client.list_symbols()
            if symbols_result.get("error"):
                await self.log_test("Forex Conectividade", False, error=symbols_result["error"])
                return False
            
            symbol_list = symbols_result.get('result', {}).get('content', [])
            await self.log_test("Forex Conectividade", True, {"total_symbols": len(symbol_list)})
            
            # Find available Forex symbols
            available_forex = [symbol for symbol in self.forex_symbols if symbol in symbol_list]
            
            if available_forex:
                self.test_symbol = available_forex[0]
                print(f"[FOREX] Símbolo Forex selecionado: {self.test_symbol}")
                print(f"[FOREX] Símbolos disponíveis: {', '.join(available_forex[:5])}")
            else:
                # Use first available symbol if no standard Forex pairs found
                self.test_symbol = symbol_list[0] if symbol_list else None
                print(f"[WARN] Símbolos Forex padrão não encontrados, usando: {self.test_symbol}")
            
            return True
            
        except Exception as e:
            await self.log_test("Forex Conectividade", False, error=str(e))
            return False
    
    async def test_forex_account(self):
        """Test Forex account information"""
        try:
            account_info = await self.client.get_account_info()
            if account_info.get("error"):
                await self.log_test("Conta Forex", False, error=account_info["error"])
                return False
            
            account_data = account_info.get('result', {}).get('content', {})
            
            # Validate this is the expected Forex account
            expected_login = 3000064180
            actual_login = account_data.get("login")
            
            if actual_login != expected_login:
                await self.log_test("Conta Forex", False, 
                                  error=f"Conta incorreta. Esperado: {expected_login}, Atual: {actual_login}")
                return False
            
            await self.log_test("Conta Forex", True, {
                "login": account_data.get("login"),
                "server": account_data.get("server"),
                "company": account_data.get("company"),
                "balance": account_data.get("balance"),
                "currency": account_data.get("currency"),
                "leverage": account_data.get("leverage"),
                "is_demo": account_data.get("is_demo")
            })
            
            # Validate server
            expected_server = "Darwinex-Demo"
            actual_server = account_data.get("server")
            if expected_server not in str(actual_server):
                print(f"[WARN] Servidor pode estar incorreto. Esperado: {expected_server}, Atual: {actual_server}")
            
            return True
            
        except Exception as e:
            await self.log_test("Conta Forex", False, error=str(e))
            return False
    
    async def test_forex_quotes(self):
        """Test Forex real-time quotes"""
        if not self.test_symbol:
            await self.log_test("Cotações Forex", False, error="Nenhum símbolo Forex disponível")
            return False
        
        try:
            symbol_info = await self.client.get_symbol_info(self.test_symbol)
            if symbol_info.get("error"):
                await self.log_test("Cotações Forex", False, error=symbol_info["error"])
                return False
            
            data = symbol_info.get('result', {}).get('content', {})
            
            # Validate Forex-specific data
            bid = data.get("bid", 0.0)
            ask = data.get("ask", 0.0)
            spread = data.get("spread", 0)
            digits = data.get("digits", 0)
            
            # Forex pairs typically have 4-5 digits
            if digits not in [4, 5]:
                print(f"[WARN] Digits incomuns para Forex: {digits}")
            
            # Validate quotes are reasonable for Forex
            if bid <= 0 or ask <= 0:
                await self.log_test("Cotações Forex", False, 
                                  error=f"Cotações inválidas - Bid: {bid}, Ask: {ask}")
                return False
            
            await self.log_test("Cotações Forex", True, {
                "symbol": self.test_symbol,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "spread_points": spread,
                "digits": digits,
                "pip_value": data.get("trade_tick_value"),
                "contract_size": data.get("trade_contract_size")
            })
            
            return True
            
        except Exception as e:
            await self.log_test("Cotações Forex", False, error=str(e))
            return False
    
    async def test_forex_market_depth(self):
        """Test Forex market depth (Book L2)"""
        if not self.test_symbol:
            await self.log_test("Profundidade Forex", False, error="Nenhum símbolo Forex disponível")
            return False
        
        try:
            book_result = await self.client.get_book_l2(self.test_symbol)
            if book_result.get("error"):
                await self.log_test("Profundidade Forex", False, error=book_result["error"])
                return False
            
            book_data = book_result.get('result', {}).get('content', [])
            
            # Analyze market depth structure
            if book_data:
                first_level = book_data[0] if isinstance(book_data, list) else book_data
                
                await self.log_test("Profundidade Forex", True, {
                    "symbol": self.test_symbol,
                    "depth_levels": len(book_data) if isinstance(book_data, list) else 1,
                    "first_level": first_level,
                    "has_buy_orders": "price" in str(first_level).lower(),
                    "has_sell_orders": "volume" in str(first_level).lower()
                })
            else:
                await self.log_test("Profundidade Forex", True, {
                    "symbol": self.test_symbol,
                    "depth_levels": 0,
                    "note": "Sem dados de profundidade disponíveis"
                })
            
            return True
            
        except Exception as e:
            await self.log_test("Profundidade Forex", False, error=str(e))
            return False
    
    async def test_forex_positions(self):
        """Test Forex positions and orders"""
        try:
            # Test positions
            positions = await self.client.get_positions()
            if positions.get("error"):
                await self.log_test("Posições Forex", False, error=positions["error"])
                return False
            
            pos_data = positions.get('result', {}).get('content', [])
            
            # Test orders
            orders = await self.client.get_orders()
            if orders.get("error"):
                await self.log_test("Ordens Forex", False, error=orders["error"])
                return False
            
            order_data = orders.get('result', {}).get('content', [])
            
            await self.log_test("Posições e Ordens Forex", True, {
                "open_positions": len(pos_data),
                "pending_orders": len(order_data),
                "positions_sample": pos_data[:2] if pos_data else [],
                "orders_sample": order_data[:2] if order_data else []
            })
            
            return True
            
        except Exception as e:
            await self.log_test("Posições e Ordens Forex", False, error=str(e))
            return False
    
    async def test_forex_demo_validation(self):
        """Test demo validation for Forex account"""
        try:
            validation = await self.client.validate_demo_for_trading()
            if validation.get("error"):
                await self.log_test("Validação Demo Forex", False, error=validation["error"])
                return False
            
            validation_data = validation.get('result', {}).get('content', {})
            
            await self.log_test("Validação Demo Forex", True, {
                "is_demo": validation_data.get("is_demo"),
                "trading_allowed": validation_data.get("allowed"),
                "account_type": validation_data.get("account_type"),
                "risk_level": validation_data.get("risk_level", "demo")
            })
            
            # Verify it's properly configured for demo trading
            if not validation_data.get("allowed"):
                print("[WARN] Trading não permitido - verifique configuração da conta")
            
            return True
            
        except Exception as e:
            await self.log_test("Validação Demo Forex", False, error=str(e))
            return False
    
    async def run_forex_tests(self):
        """Run all Forex-specific tests"""
        print("[FOREX] MCP METATRADER 5 - FOREX MARKET TEST")
        print("=" * 50)
        print("[FOREX] Server: 192.168.0.125:50052")
        print("[FOREX] Account: 3000064180 (Darwinex-Demo)")
        print("[FOREX] Market: Forex")
        print("=" * 50)
        
        tests = [
            ("Forex Server Connectivity", self.test_forex_connectivity()),
            ("Forex Account Validation", self.test_forex_account()),
            ("Forex Real-time Quotes", self.test_forex_quotes()),
            ("Forex Market Depth", self.test_forex_market_depth()),
            ("Forex Positions & Orders", self.test_forex_positions()),
            ("Forex Demo Validation", self.test_forex_demo_validation()),
        ]
        
        for test_name, test_coro in tests:
            print(f"\n[TEST] {test_name}")
            print("-" * 40)
            
            try:
                await test_coro
            except Exception as e:
                await self.log_test(test_name, False, error=str(e))
        
        # Summary
        print("\n[REPORT] FOREX TEST SUMMARY")
        print("=" * 30)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "[OK] PASSED" if result["success"] else "[X] FAILED"
            print(f"{status}: {result['test']}")
            if result.get("error"):
                print(f"    Error: {result['error']}")
        
        print(f"\n[RESULT] {passed}/{total} tests passed")
        print(f"[SUCCESS] Success rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("[SUCCESS] All Forex tests passed! Server is ready for trading.")
            return True
        else:
            print("[FAIL] Some Forex tests failed! Check configuration above.")
            return False


async def main():
    """Main function"""
    print("[FOREX] MCP METATRADER 5 - FOREX MARKET INTEGRATION TEST")
    print("Testing Forex-specific functionality on port 50052")
    print("=" * 65)
    
    # Check server URL from args
    server_url = "http://192.168.0.125:50052"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"[NET] Connecting to Forex server: {server_url}")
    
    # Run Forex tests
    tester = ForexMarketTest(server_url)
    
    async with tester.client:
        success = await tester.run_forex_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Servidor Forex ativo: {data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"   ❌ Servidor retornou status {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro de conectividade: {e}")
            return False
    
    async def test_forex_configuration(self):
        """Testa se a configuração Forex está ativa"""
        print("🔧 [2/6] Verificando configuração Forex...")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_current_config",
                        "arguments": {}
                    },
                    "id": 1
                }
                
                response = await client.post(self.mcp_endpoint, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    config = data.get("result", {}).get("content", {})
                    
                    if config.get("market_type") == "forex":
                        print(f"   ✅ Configuração Forex ativa")
                        print(f"   📊 Conta: {config.get('account')}")
                        print(f"   🏢 Servidor: {config.get('server')}")
                        print(f"   💱 Mercado: {config.get('market_type')}")
                        return True
                    else:
                        print(f"   ❌ Configuração incorreta: {config.get('market_type')}")
                        return False
                else:
                    print(f"   ❌ Erro na requisição: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro ao verificar configuração: {e}")
            return False
    
    async def test_forex_symbols(self):
        """Testa disponibilidade de símbolos Forex"""
        print("💱 [3/6] Testando símbolos Forex...")
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_symbols",
                        "arguments": {}
                    },
                    "id": 1
                }
                
                response = await client.post(self.mcp_endpoint, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    symbols = data.get("result", {}).get("content", [])
                    
                    if symbols:
                        print(f"   ✅ Total de símbolos disponíveis: {len(symbols)}")
                        
                        # Verificar símbolos Forex específicos
                        found_forex = []
                        for forex_symbol in self.forex_symbols:
                            if forex_symbol in symbols:
                                found_forex.append(forex_symbol)
                        
                        print(f"   💱 Símbolos Forex encontrados: {len(found_forex)}")
                        for symbol in found_forex:
                            print(f"      • {symbol}")
                        
                        return len(found_forex) > 0
                    else:
                        print("   ❌ Nenhum símbolo encontrado")
                        return False
                else:
                    print(f"   ❌ Erro na requisição: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro ao obter símbolos: {e}")
            return False
    
    async def test_forex_symbol_info(self):
        """Testa informações detalhadas de símbolos Forex"""
        print("📊 [4/6] Testando informações de símbolos Forex...")
        
        # Testar EURUSD como exemplo principal
        test_symbol = "EURUSD"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "get_symbol_info",
                        "arguments": {"symbol": test_symbol}
                    },
                    "id": 1
                }
                
                response = await client.post(self.mcp_endpoint, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    symbol_info = data.get("result", {}).get("content", {})
                    
                    if "error" not in symbol_info:
                        print(f"   ✅ Informações do {test_symbol}:")
                        print(f"      📈 Bid: {symbol_info.get('bid', 'N/A')}")
                        print(f"      📉 Ask: {symbol_info.get('ask', 'N/A')}")
                        print(f"      🎯 Spread: {symbol_info.get('spread', 'N/A')} pontos")
                        print(f"      🔢 Dígitos: {symbol_info.get('digits', 'N/A')}")
                        print(f"      📊 Volume mín: {symbol_info.get('volume_min', 'N/A')}")
                        print(f"      💹 Último preço: {symbol_info.get('tick_last', 'N/A')}")
                        
                        # Verificar se é par de moedas válido
                        bid = symbol_info.get('bid', 0)
                        ask = symbol_info.get('ask', 0)
                        
                        if bid > 0 and ask > 0 and ask >= bid:
                            spread_pips = (ask - bid) * 10000  # Para pares USD
                            print(f"      💰 Spread: {spread_pips:.1f} pips")
                            return True
                        else:
                            print(f"   ⚠️  Preços inválidos: Bid={bid}, Ask={ask}")
                            return False
                    else:
                        print(f"   ❌ Erro no símbolo: {symbol_info.get('error')}")
                        return False
                else:
                    print(f"   ❌ Erro na requisição: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro ao obter info do símbolo: {e}")
            return False
    
    async def test_forex_market_hours(self):
        """Testa se o mercado Forex está ativo"""
        print("🕐 [5/6] Verificando horário do mercado Forex...")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Testar múltiplos símbolos para verificar atividade
                active_symbols = 0
                
                for symbol in self.forex_symbols[:3]:  # Testar apenas os 3 primeiros
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "get_symbol_info",
                            "arguments": {"symbol": symbol}
                        },
                        "id": 1
                    }
                    
                    response = await client.post(self.mcp_endpoint, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        symbol_info = data.get("result", {}).get("content", {})
                        
                        bid = symbol_info.get('bid', 0)
                        ask = symbol_info.get('ask', 0)
                        
                        if bid > 0 and ask > 0:
                            active_symbols += 1
                
                if active_symbols > 0:
                    print(f"   ✅ Mercado ativo: {active_symbols}/3 símbolos com preços")
                    if active_symbols == 3:
                        print("   🟢 Mercado Forex totalmente ativo")
                    else:
                        print("   🟡 Mercado parcialmente ativo (pode ser horário de baixa liquidez)")
                    return True
                else:
                    print("   🔴 Mercado fechado ou sem dados")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro ao verificar mercado: {e}")
            return False
    
    async def test_forex_account_demo(self):
        """Verifica se a conta Forex é demo (segurança)"""
        print("🛡️  [6/6] Verificando segurança da conta (demo)...")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "validate_demo_for_trading",
                        "arguments": {}
                    },
                    "id": 1
                }
                
                response = await client.post(self.mcp_endpoint, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    validation = data.get("result", {}).get("content", {})
                    
                    is_demo = validation.get("allowed", False)
                    account_type = validation.get("account_type", "unknown")
                    reason = validation.get("reason", "")
                    
                    if is_demo and account_type == "demo":
                        print(f"   ✅ Conta demo verificada")
                        print(f"   🔒 Trading seguro permitido")
                        print(f"   📋 Razão: {reason}")
                        return True
                    else:
                        print(f"   ⚠️  Tipo de conta: {account_type}")
                        print(f"   ⚠️  Trading permitido: {is_demo}")
                        print(f"   📋 Razão: {reason}")
                        return False
                else:
                    print(f"   ❌ Erro na validação: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro na validação: {e}")
            return False
    
    async def run_all_tests(self):
        """Executa todos os testes do mercado Forex"""
        print("🧪 INICIANDO TESTES DO MERCADO FOREX")
        print("=" * 50)
        
        tests = [
            ("Conectividade", self.test_server_health),
            ("Configuração Forex", self.test_forex_configuration),
            ("Símbolos Disponíveis", self.test_forex_symbols),
            ("Informações de Símbolos", self.test_forex_symbol_info),
            ("Horário do Mercado", self.test_forex_market_hours),
            ("Validação Demo", self.test_forex_account_demo)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
                print()  # Linha em branco entre testes
            except Exception as e:
                print(f"   ❌ Erro crítico em {test_name}: {e}")
                results.append((test_name, False))
                print()
        
        # Relatório final
        print("📋 RELATÓRIO FINAL - MERCADO FOREX")
        print("=" * 50)
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASSOU" if result else "❌ FALHOU"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        print()
        print(f"📊 Resumo: {passed}/{len(results)} testes passaram")
        
        if passed == len(results):
            print("🎉 TODOS OS TESTES PASSARAM - Mercado Forex totalmente funcional!")
            return 0
        elif passed > len(results) // 2:
            print("⚠️  MAIORIA DOS TESTES PASSOU - Funcionalidade parcial")
            return 1
        else:
            print("❌ MAIORIA DOS TESTES FALHOU - Problemas detectados")
            return 2

async def main():
    """Função principal"""
    print("🚀 Testador do Mercado Forex - MCP MetaTrader 5")
    print()
    print("📋 Este teste verifica:")
    print("   • Conectividade com servidor Forex (porta 50052)")
    print("   • Configuração específica do mercado Forex")
    print("   • Disponibilidade de pares de moedas")
    print("   • Dados de mercado em tempo real")
    print("   • Segurança da conta (demo only)")
    print()
    
    # Verificar se o usuário quer usar porta diferente
    if len(sys.argv) > 1:
        port = sys.argv[1]
        server_url = f"http://localhost:{port}"
        print(f"🔧 Usando servidor customizado: {server_url}")
    else:
        server_url = "http://localhost:50052"
        print(f"🔧 Usando servidor padrão: {server_url}")
    
    print()
    
    tester = ForexMarketTester(server_url)
    result = await tester.run_all_tests()
    
    print()
    if result == 0:
        print("🎯 SUCESSO: Mercado Forex totalmente operacional!")
    elif result == 1:
        print("⚠️  AVISO: Funcionalidade parcial do mercado Forex")
    else:
        print("🚨 ERRO: Problemas críticos no mercado Forex")
    
    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n🛑 Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        sys.exit(1)
