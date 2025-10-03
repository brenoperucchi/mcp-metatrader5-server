#!/usr/bin/env python3
"""
Diagnóstico de Dados Históricos MT5
==================================
Script para diagnosticar problemas de dados históricos no MT5 e MCP server.
Verifica limitações, disponibilidade de símbolos e ranges válidos de dados.

Autor: MCP MT5 Diagnostic System
Data: 2025-01-19
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Optional imports - will handle gracefully if not available
try:
    import requests
except ImportError:
    print("WARNING: requests library not installed. Install with: pip install requests")
    sys.exit(1)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("INFO: MetaTrader5 not available - will use HTTP-only tests")

# Constants
DEFAULT_SERVER = "http://localhost:8000"
DEFAULT_SYMBOL = "ITSA3"
REQUEST_TIMEOUT = 30

# Create logs directory structure following project convention
LOGS_DIR = Path("mcp_mt5_sync/logs/historical_diagnosis")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging following project convention
def setup_logging(verbose: bool = False):
    """Configure logging for both console and file output"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Console handler - use UTF-8 encoding for Windows
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                       datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)

    # File handler with timestamp - following project convention
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"diagnosis_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Configure root logger
    logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])

    return logging.getLogger(__name__)

class HistoricalDataDiagnostics:
    """Diagnostic tool for MT5 historical data availability"""

    def __init__(self, symbol: str, server_url: str, logger: logging.Logger):
        self.symbol = symbol
        self.server_url = server_url.rstrip('/')
        self.logger = logger
        self.session = requests.Session()
        self.mt5_initialized = False
        self.diagnosis_results = {
            "symbol": symbol,
            "server_url": server_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mt5_direct": {},
            "mcp_server": {},
            "data_availability": {},
            "recommendations": []
        }

    def init_mt5_if_available(self) -> bool:
        """Initialize MT5 directly if available"""
        if not MT5_AVAILABLE:
            self.logger.info("MetaTrader5 module not available")
            return False

        try:
            if not mt5.initialize():
                self.logger.warning("Failed to initialize MT5")
                return False

            info = mt5.account_info()
            if info:
                self.logger.info(f"✅ MT5 initialized - Account: {info.login}")
                self.mt5_initialized = True
                self.diagnosis_results["mt5_direct"]["initialized"] = True
                self.diagnosis_results["mt5_direct"]["account"] = {
                    "login": info.login,
                    "server": info.server,
                    "company": info.company
                }
                return True

        except Exception as e:
            self.logger.warning(f"MT5 initialization error: {e}")

        self.diagnosis_results["mt5_direct"]["initialized"] = False
        return False

    def check_symbol_direct(self) -> Dict[str, Any]:
        """Check symbol information directly with MT5"""
        result = {"available": False, "info": None, "error": None}

        if not self.mt5_initialized:
            result["error"] = "MT5 not initialized"
            return result

        try:
            # Select symbol first
            if not mt5.symbol_select(self.symbol, True):
                result["error"] = f"Failed to select symbol: {mt5.last_error()}"
                return result

            # Get symbol info
            info = mt5.symbol_info(self.symbol)
            if info is None:
                result["error"] = f"Symbol info not available: {mt5.last_error()}"
                return result

            result["available"] = True
            result["info"] = {
                "name": info.name,
                "description": info.description,
                "currency_base": info.currency_base,
                "currency_profit": info.currency_profit,
                "point": info.point,
                "digits": info.digits,
                "bid": info.bid,
                "ask": info.ask,
                "visible": info.visible,
                "select": info.select,
                "time": info.time
            }

            self.logger.info(f"✅ Symbol {self.symbol} is available - Bid: {info.bid}, Ask: {info.ask}")

        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Error checking symbol: {e}")

        return result

    def test_data_ranges_direct(self) -> Dict[str, Any]:
        """Test different data ranges directly with MT5 to find limits"""
        results = {
            "rates_ranges": [],
            "ticks_ranges": [],
            "max_available_range": None,
            "current_data_available": False
        }

        if not self.mt5_initialized:
            return results

        # Test current/recent data first
        now = datetime.now()

        # Test ranges going backwards from current time
        test_ranges = [
            ("1 hour", timedelta(hours=1)),
            ("6 hours", timedelta(hours=6)),
            ("1 day", timedelta(days=1)),
            ("3 days", timedelta(days=3)),
            ("1 week", timedelta(weeks=1)),
            ("1 month", timedelta(days=30)),
            ("3 months", timedelta(days=90)),
            ("6 months", timedelta(days=180)),
            ("1 year", timedelta(days=365)),
            ("2 years", timedelta(days=730)),
        ]

        self.logger.info(f"Testing data availability ranges for {self.symbol}...")

        for range_name, delta in test_ranges:
            date_from = now - delta

            # Test rates (OHLCV data)
            try:
                rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, date_from, now)
                rates_result = {
                    "range": range_name,
                    "from": date_from.isoformat(),
                    "to": now.isoformat(),
                    "success": rates is not None,
                    "count": len(rates) if rates is not None else 0,
                    "error": None if rates is not None else str(mt5.last_error())
                }

                if rates is not None and len(rates) > 0:
                    rates_result["first_time"] = pd.to_datetime(rates[0]['time'], unit='s').isoformat()
                    rates_result["last_time"] = pd.to_datetime(rates[-1]['time'], unit='s').isoformat()
                    self.logger.info(f"  ✅ Rates {range_name}: {len(rates)} bars")
                else:
                    self.logger.warning(f"  ❌ Rates {range_name}: {rates_result['error']}")

                results["rates_ranges"].append(rates_result)

            except Exception as e:
                results["rates_ranges"].append({
                    "range": range_name,
                    "from": date_from.isoformat(),
                    "to": now.isoformat(),
                    "success": False,
                    "count": 0,
                    "error": str(e)
                })
                self.logger.error(f"  ❌ Rates {range_name}: {e}")

            # Test ticks (for shorter ranges only - ticks generate huge amounts of data)
            if delta <= timedelta(days=7):
                try:
                    ticks = mt5.copy_ticks_range(self.symbol, date_from, now, mt5.COPY_TICKS_ALL)
                    ticks_result = {
                        "range": range_name,
                        "from": date_from.isoformat(),
                        "to": now.isoformat(),
                        "success": ticks is not None,
                        "count": len(ticks) if ticks is not None else 0,
                        "error": None if ticks is not None else str(mt5.last_error())
                    }

                    if ticks is not None and len(ticks) > 0:
                        ticks_result["first_time"] = pd.to_datetime(ticks[0]['time'], unit='s').isoformat()
                        ticks_result["last_time"] = pd.to_datetime(ticks[-1]['time'], unit='s').isoformat()
                        self.logger.info(f"  ✅ Ticks {range_name}: {len(ticks)} ticks")
                    else:
                        self.logger.warning(f"  ❌ Ticks {range_name}: {ticks_result['error']}")

                    results["ticks_ranges"].append(ticks_result)

                except Exception as e:
                    results["ticks_ranges"].append({
                        "range": range_name,
                        "from": date_from.isoformat(),
                        "to": now.isoformat(),
                        "success": False,
                        "count": 0,
                        "error": str(e)
                    })
                    self.logger.error(f"  ❌ Ticks {range_name}: {e}")

        # Find maximum available range
        successful_rates = [r for r in results["rates_ranges"] if r["success"] and r["count"] > 0]
        if successful_rates:
            # Sort by range (longer ranges first) and take the longest successful one
            range_order = {r["range"]: i for i, (name, _) in enumerate(test_ranges)}
            successful_rates.sort(key=lambda x: range_order.get(x["range"], 999), reverse=True)
            results["max_available_range"] = successful_rates[0]["range"]
            results["current_data_available"] = True

        return results

    def test_specific_january_range(self) -> Dict[str, Any]:
        """Test the specific January 2025 range that's causing issues"""
        results = {
            "january_2025_test": {
                "requested_from": "2025-01-01",
                "requested_to": "2025-01-30",
                "rates_success": False,
                "ticks_success": False,
                "rates_error": None,
                "ticks_error": None,
                "explanation": None
            }
        }

        if not self.mt5_initialized:
            results["january_2025_test"]["explanation"] = "MT5 not initialized for direct testing"
            return results

        # The problematic date range
        date_from = datetime(2025, 1, 1)
        date_to = datetime(2025, 1, 30)

        self.logger.info(f"Testing specific January 2025 range: {date_from} to {date_to}")

        # Test rates
        try:
            rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, date_from, date_to)
            if rates is not None:
                results["january_2025_test"]["rates_success"] = True
                results["january_2025_test"]["rates_count"] = len(rates)
                self.logger.info(f"  ✅ January 2025 rates: {len(rates)} bars")
            else:
                error = mt5.last_error()
                results["january_2025_test"]["rates_error"] = str(error)
                self.logger.warning(f"  ❌ January 2025 rates failed: {error}")
        except Exception as e:
            results["january_2025_test"]["rates_error"] = str(e)
            self.logger.error(f"  ❌ January 2025 rates exception: {e}")

        # Test ticks
        try:
            ticks = mt5.copy_ticks_range(self.symbol, date_from, date_to, mt5.COPY_TICKS_ALL)
            if ticks is not None:
                results["january_2025_test"]["ticks_success"] = True
                results["january_2025_test"]["ticks_count"] = len(ticks)
                self.logger.info(f"  ✅ January 2025 ticks: {len(ticks)} ticks")
            else:
                error = mt5.last_error()
                results["january_2025_test"]["ticks_error"] = str(error)
                self.logger.warning(f"  ❌ January 2025 ticks failed: {error}")
        except Exception as e:
            results["january_2025_test"]["ticks_error"] = str(e)
            self.logger.error(f"  ❌ January 2025 ticks exception: {e}")

        # Provide explanation
        if not results["january_2025_test"]["rates_success"] and not results["january_2025_test"]["ticks_success"]:
            # January 2025 is in the future - that's the problem!
            current_time = datetime.now()
            if date_from > current_time:
                results["january_2025_test"]["explanation"] = (
                    f"PROBLEMA IDENTIFICADO: Janeiro 2025 está no futuro! "
                    f"Data atual: {current_time.strftime('%Y-%m-%d')}. "
                    f"MT5 não pode fornecer dados históricos para datas futuras."
                )
            else:
                results["january_2025_test"]["explanation"] = (
                    "Dados não disponíveis para o período solicitado. "
                    "Possíveis causas: símbolo não estava sendo negociado, "
                    "dados não foram sincronizados ou limitações do provedor."
                )

        return results

    def test_mcp_server_connectivity(self) -> Dict[str, Any]:
        """Test MCP server connectivity and tool availability"""
        results = {
            "server_reachable": False,
            "tools_available": [],
            "copy_rates_range_available": False,
            "copy_ticks_range_available": False,
            "test_call_success": False,
            "test_call_error": None
        }

        # Check if server is reachable
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                results["server_reachable"] = True
                self.logger.info("✅ MCP server is reachable")
            else:
                self.logger.warning(f"MCP server returned status {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ MCP server not reachable: {e}")
            return results

        # Check available tools
        try:
            response = self.session.post(
                f"{self.server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if "result" in data and "tools" in data["result"]:
                    tools = data["result"]["tools"]
                    results["tools_available"] = [t["name"] for t in tools if isinstance(t, dict)]

                    if "copy_rates_range" in results["tools_available"]:
                        results["copy_rates_range_available"] = True

                    if "copy_ticks_range" in results["tools_available"]:
                        results["copy_ticks_range_available"] = True

                    self.logger.info(f"✅ Found {len(results['tools_available'])} MCP tools")

        except Exception as e:
            self.logger.error(f"Error checking MCP tools: {e}")

        # Test a simple call
        if results["copy_rates_range_available"]:
            try:
                # Use a safe recent date range
                now = datetime.now()
                from_date = now - timedelta(hours=6)

                response = self.session.post(
                    f"{self.server_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "copy_rates_range",
                            "arguments": {
                                "symbol": self.symbol,
                                "timeframe": 1,  # M1
                                "date_from": from_date.isoformat(),
                                "date_to": now.isoformat()
                            }
                        }
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        results["test_call_success"] = True
                        self.logger.info("✅ MCP server test call successful")
                    elif "error" in data:
                        results["test_call_error"] = data["error"]
                        self.logger.warning(f"MCP server test call error: {data['error']}")

            except Exception as e:
                results["test_call_error"] = str(e)
                self.logger.error(f"MCP server test call exception: {e}")

        return results

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on diagnosis results"""
        recommendations = []

        # Check the specific January 2025 issue
        january_test = self.diagnosis_results.get("data_availability", {}).get("january_2025_test", {})
        if january_test.get("explanation"):
            if "futuro" in january_test.get("explanation", ""):
                recommendations.append(
                    "🎯 PROBLEMA PRINCIPAL: Você está tentando acessar dados de Janeiro 2025, "
                    "que é no futuro! Use datas passadas para testar a funcionalidade."
                )

        # Recommend valid date ranges
        max_range = self.diagnosis_results.get("data_availability", {}).get("max_available_range")
        if max_range:
            recommendations.append(
                f"📅 RANGE VÁLIDO: Dados disponíveis até {max_range} atrás. "
                f"Use este período para testes."
            )
        else:
            recommendations.append(
                "📅 TESTAR PERÍODOS RECENTES: Comece com as últimas 6-24 horas "
                "para verificar se há dados disponíveis."
            )

        # Symbol-specific recommendations
        symbol_info = self.diagnosis_results.get("mt5_direct", {}).get("symbol_check", {})
        if not symbol_info.get("available", False):
            recommendations.append(
                f"🔍 VERIFICAR SÍMBOLO: {self.symbol} pode não estar disponível "
                f"ou selecionado no Market Watch. Verifique se o símbolo existe."
            )

        # Market hours recommendation
        recommendations.append(
            "🕐 HORÁRIOS DE MERCADO: B3 (Bovespa) opera de segunda a sexta, "
            "10:00-17:00 (horário de Brasília). Dados fora deste período podem ser limitados."
        )

        # Testing recommendation with concrete dates
        now = datetime.now()
        recent_from = now - timedelta(days=7)
        recommendations.append(
            f"🧪 TESTE SUGERIDO: Use o período de {recent_from.strftime('%Y-%m-%d')} "
            f"a {now.strftime('%Y-%m-%d')} para testar a funcionalidade."
        )

        # Configuration recommendations
        recommendations.append(
            "⚙️ CONFIGURAÇÃO: Verifique se o MT5 está conectado ao servidor correto "
            "e se os dados históricos estão sendo sincronizados."
        )

        return recommendations

    def run_full_diagnosis(self) -> Dict[str, Any]:
        """Run complete diagnosis"""
        self.logger.info("=" * 60)
        self.logger.info(f"Iniciando diagnóstico completo para {self.symbol}")
        self.logger.info("=" * 60)

        # Step 1: Initialize MT5 if available
        self.init_mt5_if_available()

        # Step 2: Check symbol availability
        if self.mt5_initialized:
            self.diagnosis_results["mt5_direct"]["symbol_check"] = self.check_symbol_direct()

        # Step 3: Test data ranges
        if self.mt5_initialized:
            self.logger.info("\n📊 Testando disponibilidade de dados...")
            data_availability = self.test_data_ranges_direct()

            # Test the specific problematic range
            january_test = self.test_specific_january_range()
            data_availability.update(january_test)

            self.diagnosis_results["data_availability"] = data_availability

        # Step 4: Test MCP server
        self.logger.info("\n🌐 Testando conectividade do servidor MCP...")
        self.diagnosis_results["mcp_server"] = self.test_mcp_server_connectivity()

        # Step 5: Generate recommendations
        self.diagnosis_results["recommendations"] = self.generate_recommendations()

        return self.diagnosis_results

    def save_results(self) -> str:
        """Save diagnosis results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = LOGS_DIR / f"diagnosis_results_{timestamp}.json"

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.diagnosis_results, f, indent=2, default=str, ensure_ascii=False)

        self.logger.info(f"📄 Resultados salvos em: {results_file}")
        return str(results_file)

    def print_summary(self):
        """Print diagnosis summary"""
        print("\n" + "=" * 60)
        print("📋 RESUMO DO DIAGNÓSTICO")
        print("=" * 60)

        # Symbol status
        symbol_check = self.diagnosis_results.get("mt5_direct", {}).get("symbol_check", {})
        if symbol_check.get("available"):
            print(f"✅ Símbolo {self.symbol}: Disponível")
        else:
            print(f"❌ Símbolo {self.symbol}: {symbol_check.get('error', 'Não disponível')}")

        # Data availability
        max_range = self.diagnosis_results.get("data_availability", {}).get("max_available_range")
        if max_range:
            print(f"📅 Dados disponíveis: Até {max_range} atrás")
        else:
            print("📅 Dados: Limitados ou não disponíveis")

        # January 2025 specific issue
        january_test = self.diagnosis_results.get("data_availability", {}).get("january_2025_test", {})
        if january_test.get("explanation"):
            print(f"🎯 Janeiro 2025: {january_test['explanation']}")

        # MCP server
        mcp_status = self.diagnosis_results.get("mcp_server", {})
        if mcp_status.get("server_reachable"):
            print("✅ Servidor MCP: Online")
            if mcp_status.get("copy_rates_range_available"):
                print("✅ copy_rates_range: Disponível")
            if mcp_status.get("copy_ticks_range_available"):
                print("✅ copy_ticks_range: Disponível")
        else:
            print("❌ Servidor MCP: Offline ou inacessível")

        # Recommendations
        print("\n🎯 RECOMENDAÇÕES:")
        for i, rec in enumerate(self.diagnosis_results.get("recommendations", []), 1):
            print(f"{i}. {rec}")

        print(f"\n📂 Logs salvos em: {LOGS_DIR.absolute()}")

    def cleanup(self):
        """Cleanup resources"""
        if self.mt5_initialized and MT5_AVAILABLE:
            mt5.shutdown()
            self.logger.info("🔌 Conexão MT5 fechada")
        self.session.close()

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Diagnóstico de problemas de dados históricos MT5"
    )

    parser.add_argument(
        "--symbol", "-s",
        default=DEFAULT_SYMBOL,
        help=f"Símbolo para diagnosticar (default: {DEFAULT_SYMBOL})"
    )

    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"URL do servidor MCP (default: {DEFAULT_SERVER})"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)

    # Create diagnostics and run
    diagnostics = HistoricalDataDiagnostics(args.symbol, args.server, logger)

    try:
        diagnostics.run_full_diagnosis()
        diagnostics.save_results()
        diagnostics.print_summary()
    except KeyboardInterrupt:
        logger.info("\n🛑 Diagnóstico interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro durante diagnóstico: {e}", exc_info=True)
    finally:
        diagnostics.cleanup()

if __name__ == "__main__":
    # Import pandas here to avoid import error at module level
    try:
        import pandas as pd
    except ImportError:
        print("WARNING: pandas not available, some features may be limited")
        # Create a minimal pandas replacement for basic functionality
        class MockPandas:
            @staticmethod
            def to_datetime(data, unit=None):
                if unit == 's':
                    return datetime.fromtimestamp(data)
                return data
        pd = MockPandas()

    main()