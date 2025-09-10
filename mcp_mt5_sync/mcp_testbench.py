#!/usr/bin/env python3
"""
E2.2 - MCP Testbench for ETAPA 2
Testbench com mocks e replay para testar decisão de swap ITSA3⇄ITSA4
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SwapDecision(Enum):
    """Decisões possíveis de swap"""
    NO_ACTION = "NO_ACTION"
    BUY_ON = "BUY_ON"  # Comprar ITSA3
    SWAP_TO_PN = "SWAP_TO_PN"  # Trocar ITSA3 -> ITSA4
    CLOSE_PN = "CLOSE_PN"  # Fechar posição ITSA4
    
@dataclass
class MarketQuote:
    """Dados de cotação"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        return (self.spread / self.bid * 100) if self.bid > 0 else 0
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

@dataclass
class ArbitrageMetrics:
    """Métricas de arbitragem ON/PN"""
    on_quote: MarketQuote  # ITSA3
    pn_quote: MarketQuote  # ITSA4
    premium_pn: float  # Premium % da PN sobre ON
    spread_total: float  # Spread combinado
    arbitrage_opportunity: bool
    expected_profit: float
    
class MockMarketData:
    """Gerador de dados de mercado mockados"""
    
    def __init__(self, base_price: float = 11.50):
        self.base_price = base_price
        self.tick_count = 0
        
    def generate_quote(self, symbol: str, scenario: str = "normal") -> MarketQuote:
        """Gera cotação baseada em cenário"""
        self.tick_count += 1
        
        # Base price com pequena variação
        if symbol == "ITSA3":
            base = self.base_price + random.uniform(-0.05, 0.05)
        else:  # ITSA4
            if scenario == "premium_high":
                # PN com premium alto (oportunidade)
                base = self.base_price * 1.01 + random.uniform(-0.02, 0.02)
            elif scenario == "premium_negative":
                # PN com desconto (sem oportunidade)
                base = self.base_price * 0.99 + random.uniform(-0.02, 0.02)
            else:  # normal
                base = self.base_price + random.uniform(-0.03, 0.03)
        
        # Spread baseado em cenário
        if scenario == "high_spread":
            spread = random.uniform(0.03, 0.05)
        elif scenario == "low_spread":
            spread = random.uniform(0.005, 0.01)
        else:
            spread = random.uniform(0.01, 0.02)
            
        bid = round(base - spread/2, 2)
        ask = round(base + spread/2, 2)
        last = round(base + random.uniform(-spread/2, spread/2), 2)
        volume = random.randint(1000, 50000) * 100
        
        return MarketQuote(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=last,
            volume=volume,
            timestamp=datetime.now()
        )

class MCPTestbench:
    """Testbench para testar MCP com decisão de swap"""
    
    def __init__(self, server_url: str = "192.168.0.125:8000", use_mock: bool = True):
        self.server_url = server_url
        self.base_url = f"http://{server_url}"
        self.rpc_url = f"{self.base_url}/mcp"
        self.request_id = 1
        self.use_mock = use_mock
        self.mock_data = MockMarketData()
        self.replay_data: List[Dict] = []
        self.test_results: List[Dict] = []
        
    async def call_mcp_tool(self, tool_name: str, arguments: dict = None) -> Dict:
        """Chama ferramenta MCP ou retorna mock"""
        if self.use_mock:
            return self._mock_tool_response(tool_name, arguments)
            
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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "error" in result:
                            return {"success": False, "error": result["error"]["message"]}
                        return {"success": True, "data": result.get("result", {}).get("content", {})}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _mock_tool_response(self, tool_name: str, arguments: dict = None) -> Dict:
        """Gera resposta mockada para ferramenta"""
        if tool_name == "get_account_info":
            return {
                "success": True,
                "data": {
                    "login": 5000001,
                    "trade_mode": 0,  # DEMO
                    "balance": 100000.00,
                    "equity": 100500.00,
                    "margin_free": 95000.00,
                    "profit": 500.00
                }
            }
        elif tool_name == "get_symbol_info":
            symbol = arguments.get("symbol", "ITSA3")
            quote = self.mock_data.generate_quote(symbol, "normal")
            return {
                "success": True,
                "data": {
                    "bid": quote.bid,
                    "ask": quote.ask,
                    "last": quote.last,
                    "volume": quote.volume,
                    "time": int(quote.timestamp.timestamp())
                }
            }
        elif tool_name == "validate_demo_for_trading":
            return {"success": True, "data": True}
        elif tool_name == "order_check":
            return {
                "success": True,
                "data": {
                    "balance": 100000.00,
                    "margin_free": 95000.00,
                    "margin_required": arguments.get("request", {}).get("volume", 100) * 11.50
                }
            }
        else:
            return {"success": False, "error": f"Mock not implemented for {tool_name}"}
    
    async def get_market_quotes(self) -> Tuple[MarketQuote, MarketQuote]:
        """Obtém cotações de ITSA3 e ITSA4"""
        # Obter cotações em paralelo
        tasks = [
            self.call_mcp_tool("get_symbol_info", {"symbol": "ITSA3"}),
            self.call_mcp_tool("get_symbol_info", {"symbol": "ITSA4"})
        ]
        results = await asyncio.gather(*tasks)
        
        quotes = []
        for i, (symbol, result) in enumerate(zip(["ITSA3", "ITSA4"], results)):
            if result["success"]:
                data = result["data"]
                quote = MarketQuote(
                    symbol=symbol,
                    bid=data["bid"],
                    ask=data["ask"],
                    last=data["last"],
                    volume=data.get("volume", 0),
                    timestamp=datetime.now()
                )
                quotes.append(quote)
            else:
                raise Exception(f"Failed to get quote for {symbol}: {result.get('error')}")
        
        return quotes[0], quotes[1]
    
    def calculate_arbitrage_metrics(self, on_quote: MarketQuote, pn_quote: MarketQuote) -> ArbitrageMetrics:
        """Calcula métricas de arbitragem"""
        # Premium da PN sobre ON (usando mid price)
        premium_pn = ((pn_quote.mid - on_quote.mid) / on_quote.mid) * 100
        
        # Spread combinado (custo de entrada + saída)
        spread_total = on_quote.spread_pct + pn_quote.spread_pct
        
        # Oportunidade existe se premium > custos
        min_premium_threshold = 0.5  # 0.5% mínimo após custos
        arbitrage_opportunity = premium_pn > (spread_total + min_premium_threshold)
        
        # Lucro esperado (simplificado)
        expected_profit = max(0, premium_pn - spread_total)
        
        return ArbitrageMetrics(
            on_quote=on_quote,
            pn_quote=pn_quote,
            premium_pn=premium_pn,
            spread_total=spread_total,
            arbitrage_opportunity=arbitrage_opportunity,
            expected_profit=expected_profit
        )
    
    def make_swap_decision(self, metrics: ArbitrageMetrics, has_position: bool = False) -> SwapDecision:
        """Toma decisão de swap baseada nas métricas"""
        if not has_position:
            # Sem posição: avaliar entrada
            if metrics.arbitrage_opportunity and metrics.expected_profit > 0.3:
                return SwapDecision.BUY_ON
            return SwapDecision.NO_ACTION
        else:
            # Com posição ON: avaliar swap
            if metrics.premium_pn < -0.2:  # PN com desconto
                return SwapDecision.NO_ACTION
            elif metrics.premium_pn > 0.1:  # Premium razoável
                return SwapDecision.SWAP_TO_PN
            return SwapDecision.NO_ACTION
    
    async def run_test_scenario(self, scenario_name: str, duration_seconds: int = 10):
        """Executa cenário de teste"""
        logger.info(f"🎬 Iniciando cenário: {scenario_name}")
        logger.info(f"   Duração: {duration_seconds}s")
        logger.info(f"   Mock: {'Sim' if self.use_mock else 'Não'}")
        
        start_time = time.time()
        tick_count = 0
        decisions = []
        
        while time.time() - start_time < duration_seconds:
            tick_count += 1
            
            # Obter cotações
            try:
                on_quote, pn_quote = await self.get_market_quotes()
                
                # Calcular métricas
                metrics = self.calculate_arbitrage_metrics(on_quote, pn_quote)
                
                # Tomar decisão
                decision = self.make_swap_decision(metrics, has_position=(tick_count > 5))
                
                # Log do tick
                logger.info(f"   Tick {tick_count}: ON={on_quote.mid:.2f} PN={pn_quote.mid:.2f} "
                          f"Premium={metrics.premium_pn:.2f}% Decision={decision.value}")
                
                # Salvar para replay
                self.replay_data.append({
                    "tick": tick_count,
                    "timestamp": datetime.now().isoformat(),
                    "on_quote": asdict(on_quote),
                    "pn_quote": asdict(pn_quote),
                    "metrics": {
                        "premium_pn": metrics.premium_pn,
                        "spread_total": metrics.spread_total,
                        "arbitrage_opportunity": metrics.arbitrage_opportunity,
                        "expected_profit": metrics.expected_profit
                    },
                    "decision": decision.value
                })
                
                decisions.append(decision)
                
                # Aguardar próximo tick
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"   ❌ Erro no tick {tick_count}: {e}")
        
        # Resumo do cenário
        logger.info(f"\n📊 Resumo do Cenário '{scenario_name}':")
        logger.info(f"   Total ticks: {tick_count}")
        logger.info(f"   Decisões tomadas:")
        for decision_type in SwapDecision:
            count = decisions.count(decision_type)
            if count > 0:
                logger.info(f"      {decision_type.value}: {count}")
        
        self.test_results.append({
            "scenario": scenario_name,
            "duration": duration_seconds,
            "tick_count": tick_count,
            "decisions": [d.value for d in decisions]
        })
    
    async def replay_scenario(self, replay_file: str):
        """Reproduz cenário salvo"""
        logger.info(f"🔄 Reproduzindo cenário de: {replay_file}")
        
        with open(replay_file, 'r') as f:
            replay_data = json.load(f)
        
        for tick_data in replay_data:
            tick = tick_data["tick"]
            on_mid = (tick_data["on_quote"]["bid"] + tick_data["on_quote"]["ask"]) / 2
            pn_mid = (tick_data["pn_quote"]["bid"] + tick_data["pn_quote"]["ask"]) / 2
            premium = tick_data["metrics"]["premium_pn"]
            decision = tick_data["decision"]
            
            logger.info(f"   Replay Tick {tick}: ON={on_mid:.2f} PN={pn_mid:.2f} "
                      f"Premium={premium:.2f}% Decision={decision}")
            
            await asyncio.sleep(0.5)  # Replay mais rápido
    
    def save_replay_data(self, filename: str = None):
        """Salva dados para replay"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"replay_data_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.replay_data, f, indent=2, default=str)
        
        logger.info(f"💾 Dados salvos para replay: {filename}")
        return filename
    
    def generate_test_report(self):
        """Gera relatório de testes"""
        logger.info("\n" + "="*60)
        logger.info("📋 RELATÓRIO DE TESTES MCP - ETAPA 2.2")
        logger.info("="*60)
        
        for result in self.test_results:
            logger.info(f"\nCenário: {result['scenario']}")
            logger.info(f"Duração: {result['duration']}s")
            logger.info(f"Total ticks: {result['tick_count']}")
            
            # Análise de decisões
            decision_counts = {}
            for d in result['decisions']:
                decision_counts[d] = decision_counts.get(d, 0) + 1
            
            logger.info("Decisões:")
            for decision, count in decision_counts.items():
                pct = (count / result['tick_count']) * 100
                logger.info(f"   {decision}: {count} ({pct:.1f}%)")

async def main():
    """Função principal do testbench"""
    logger.info("🚀 MCP TESTBENCH - ETAPA 2.2")
    logger.info("="*60)
    
    # Criar testbench
    testbench = MCPTestbench(use_mock=True)  # Usar mock para testes
    
    # Executar cenários de teste
    scenarios = [
        ("Normal Market", 10),
        ("High Premium", 10),
        ("Negative Premium", 10)
    ]
    
    for scenario_name, duration in scenarios:
        await testbench.run_test_scenario(scenario_name, duration)
        await asyncio.sleep(2)  # Pausa entre cenários
    
    # Salvar dados para replay
    replay_file = testbench.save_replay_data()
    
    # Gerar relatório
    testbench.generate_test_report()
    
    # Demonstrar replay
    logger.info("\n" + "="*60)
    logger.info("🔄 DEMONSTRAÇÃO DE REPLAY")
    logger.info("="*60)
    await testbench.replay_scenario(replay_file)
    
    logger.info("\n✅ Testbench concluído com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())