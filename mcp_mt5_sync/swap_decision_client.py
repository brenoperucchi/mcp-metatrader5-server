#!/usr/bin/env python3
"""
E2.4 - Swap Decision Client
Cliente que integra MCP, normalização de símbolos e lógica de decisão de swap
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import time
import sys
import os

# Adicionar path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.b3_symbol_normalizer import (
    B3SymbolNormalizer,
    NormalizedSymbol,
    SymbolType
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SwapDecisionType(Enum):
    """Tipos de decisão de swap"""
    NO_ACTION = "NO_ACTION"
    ENTER_LONG_ON = "ENTER_LONG_ON"      # Comprar ITSA3 (ON)
    SWAP_TO_PN = "SWAP_TO_PN"            # Vender ITSA3, Comprar ITSA4
    CLOSE_PN_POSITION = "CLOSE_PN_POSITION"  # Vender ITSA4, lucro realizado
    EMERGENCY_EXIT = "EMERGENCY_EXIT"     # Saída de emergência

class PositionState(Enum):
    """Estados da posição"""
    IDLE = "IDLE"           # Sem posição
    LONG_ON = "LONG_ON"     # Posição longa em ON (ITSA3)
    LONG_PN = "LONG_PN"     # Posição longa em PN (ITSA4)

@dataclass
class MarketData:
    """Dados de mercado para um símbolo"""
    symbol: str
    normalized_symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime
    
    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        return (self.spread / self.bid * 100) if self.bid > 0 else 0

@dataclass
class ArbitrageOpportunity:
    """Oportunidade de arbitragem detectada"""
    on_data: MarketData  # ITSA3
    pn_data: MarketData  # ITSA4
    premium_pn: float    # Premium PN sobre ON (%)
    total_spread_cost: float  # Custo total de spread (%)
    net_opportunity: float    # Oportunidade líquida (%)
    is_profitable: bool
    expected_profit_pct: float
    confidence_score: float   # Score de confiança (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SwapDecision:
    """Decisão de swap tomada"""
    decision_type: SwapDecisionType
    timestamp: datetime
    current_state: PositionState
    target_state: PositionState
    opportunity: Optional[ArbitrageOpportunity]
    reasoning: str
    confidence: float
    risk_assessment: str
    expected_return: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp.isoformat(),
            "current_state": self.current_state.value,
            "target_state": self.target_state.value,
            "opportunity": self.opportunity.to_dict() if self.opportunity else None,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "risk_assessment": self.risk_assessment,
            "expected_return": self.expected_return,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit
        }

@dataclass
class Position:
    """Posição atual"""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    current_price: float
    unrealized_pnl: float
    state: PositionState

class SwapDecisionClient:
    """Cliente principal para decisões de swap ITSA3⇄ITSA4"""
    
    def __init__(self, 
                 mcp_server_url: str = "192.168.0.125:8000",
                 on_symbol: str = "ITSA3",
                 pn_symbol: str = "ITSA4",
                 config: Dict[str, Any] = None):
        
        self.mcp_server_url = mcp_server_url
        self.rpc_url = f"http://{mcp_server_url}/mcp"
        self.request_id = 1
        
        # Configurações padrão
        default_config = {
            "min_premium_threshold": 0.30,     # 0.30% mínimo para entrada
            "swap_threshold": 0.10,            # 0.10% para swap ON→PN
            "take_profit_threshold": 0.80,     # 0.80% para saída
            "max_spread_cost": 0.20,           # 0.20% máximo de custo
            "stop_loss_threshold": -2.0,       # -2.0% stop loss
            "min_volume": 10000,               # Volume mínimo
            "max_position_size": 100000.0,     # R$ 100k máximo
            "confidence_threshold": 0.70,      # 70% confiança mínima
            "max_holding_hours": 24,           # 24h máximo em posição
        }
        
        # Aplicar configurações customizadas
        self.config = default_config.copy()
        if config:
            self.config.update(config)
        
        # Inicializar componentes
        self.normalizer = B3SymbolNormalizer()
        self.on_symbol = on_symbol
        self.pn_symbol = pn_symbol
        
        # Normalizar símbolos
        self.on_norm = self.normalizer.normalize(on_symbol)
        self.pn_norm = self.normalizer.normalize(pn_symbol)
        
        if not self.on_norm or not self.pn_norm:
            raise ValueError(f"Invalid symbols: {on_symbol}, {pn_symbol}")
        
        if not self.normalizer.validate_pair(on_symbol, pn_symbol):
            raise ValueError(f"Invalid ON/PN pair: {on_symbol}, {pn_symbol}")
        
        # Estado
        self.current_position: Optional[Position] = None
        self.position_state = PositionState.IDLE
        self.decision_history: List[SwapDecision] = []
        self.market_data_cache: Dict[str, MarketData] = {}
        
        logger.info(f"SwapDecisionClient initialized for {on_symbol}⇄{pn_symbol}")
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chama ferramenta MCP"""
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
                            return {
                                "success": False,
                                "error": result["error"]["message"]
                            }
                        return {
                            "success": True,
                            "data": result.get("result", {}).get("content", {})
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Obtém dados de mercado para um símbolo"""
        # Normalizar símbolo
        norm = self.normalizer.normalize(symbol)
        if not norm:
            logger.error(f"Cannot normalize symbol: {symbol}")
            return None
        
        # Chamar MCP
        result = await self._call_mcp_tool("get_symbol_info", {"symbol": norm.normalized})
        
        if not result["success"]:
            logger.error(f"Failed to get market data for {symbol}: {result['error']}")
            return None
        
        data = result["data"]
        
        # Validar dados essenciais
        required_fields = ["bid", "ask", "last"]
        if not all(field in data for field in required_fields):
            logger.error(f"Missing required fields in market data for {symbol}")
            return None
        
        try:
            market_data = MarketData(
                symbol=symbol,
                normalized_symbol=norm.normalized,
                bid=float(data["bid"]),
                ask=float(data["ask"]),
                last=float(data["last"]),
                volume=int(data.get("volume", 0)),
                timestamp=datetime.now()
            )
            
            # Cache
            self.market_data_cache[symbol] = market_data
            
            return market_data
            
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing market data for {symbol}: {e}")
            return None
    
    async def get_both_quotes(self) -> Optional[Tuple[MarketData, MarketData]]:
        """Obtém cotações de ON e PN simultaneamente"""
        tasks = [
            self.get_market_data(self.on_symbol),
            self.get_market_data(self.pn_symbol)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        on_data, pn_data = results[0], results[1]
        
        if isinstance(on_data, Exception) or isinstance(pn_data, Exception):
            logger.error("Exception getting market data")
            return None
        
        if not on_data or not pn_data:
            logger.error("Failed to get market data for both symbols")
            return None
        
        return on_data, pn_data
    
    def analyze_arbitrage_opportunity(self, on_data: MarketData, pn_data: MarketData) -> ArbitrageOpportunity:
        """Analisa oportunidade de arbitragem"""
        # Calcular premium da PN sobre ON
        premium_pn = ((pn_data.mid_price - on_data.mid_price) / on_data.mid_price) * 100
        
        # Custo total de spread
        total_spread_cost = on_data.spread_pct + pn_data.spread_pct
        
        # Oportunidade líquida
        net_opportunity = premium_pn - total_spread_cost
        
        # Verificar se é lucrativa
        is_profitable = net_opportunity > self.config["min_premium_threshold"]
        
        # Lucro esperado
        expected_profit_pct = max(0, net_opportunity)
        
        # Score de confiança baseado em volume, spread e consistência
        volume_score = min(1.0, (on_data.volume + pn_data.volume) / (self.config["min_volume"] * 2))
        spread_score = max(0, 1.0 - (total_spread_cost / self.config["max_spread_cost"]))
        premium_score = min(1.0, abs(premium_pn) / 2.0)  # Normalizar premium
        
        confidence_score = (volume_score * 0.4 + spread_score * 0.4 + premium_score * 0.2)
        
        return ArbitrageOpportunity(
            on_data=on_data,
            pn_data=pn_data,
            premium_pn=premium_pn,
            total_spread_cost=total_spread_cost,
            net_opportunity=net_opportunity,
            is_profitable=is_profitable,
            expected_profit_pct=expected_profit_pct,
            confidence_score=confidence_score
        )
    
    def make_swap_decision(self, opportunity: ArbitrageOpportunity) -> SwapDecision:
        """Toma decisão de swap baseada na oportunidade"""
        current_time = datetime.now()
        
        # Estado IDLE - sem posição
        if self.position_state == PositionState.IDLE:
            
            # Verificar entrada
            if (opportunity.is_profitable and 
                opportunity.confidence_score >= self.config["confidence_threshold"] and
                opportunity.net_opportunity >= self.config["min_premium_threshold"]):
                
                return SwapDecision(
                    decision_type=SwapDecisionType.ENTER_LONG_ON,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=PositionState.LONG_ON,
                    opportunity=opportunity,
                    reasoning=f"Premium PN {opportunity.premium_pn:.2f}% > threshold {self.config['min_premium_threshold']:.2f}%",
                    confidence=opportunity.confidence_score,
                    risk_assessment="Low risk entry",
                    expected_return=opportunity.expected_profit_pct,
                    take_profit=opportunity.on_data.mid_price * (1 + self.config["take_profit_threshold"] / 100),
                    stop_loss=opportunity.on_data.mid_price * (1 + self.config["stop_loss_threshold"] / 100)
                )
            else:
                return SwapDecision(
                    decision_type=SwapDecisionType.NO_ACTION,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=self.position_state,
                    opportunity=opportunity,
                    reasoning=f"No entry: Premium {opportunity.premium_pn:.2f}%, Confidence {opportunity.confidence_score:.2f}",
                    confidence=opportunity.confidence_score,
                    risk_assessment="Waiting for better opportunity"
                )
        
        # Estado LONG_ON - posição longa em ITSA3
        elif self.position_state == PositionState.LONG_ON:
            
            # Verificar swap para PN
            if (opportunity.premium_pn >= self.config["swap_threshold"] and
                opportunity.confidence_score >= self.config["confidence_threshold"]):
                
                return SwapDecision(
                    decision_type=SwapDecisionType.SWAP_TO_PN,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=PositionState.LONG_PN,
                    opportunity=opportunity,
                    reasoning=f"Swap opportunity: Premium {opportunity.premium_pn:.2f}% >= {self.config['swap_threshold']:.2f}%",
                    confidence=opportunity.confidence_score,
                    risk_assessment="Medium risk swap",
                    expected_return=opportunity.expected_profit_pct
                )
            
            # Verificar stop loss
            elif self.current_position and self.current_position.unrealized_pnl < self.config["stop_loss_threshold"]:
                return SwapDecision(
                    decision_type=SwapDecisionType.EMERGENCY_EXIT,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=PositionState.IDLE,
                    opportunity=opportunity,
                    reasoning=f"Stop loss triggered: {self.current_position.unrealized_pnl:.2f}%",
                    confidence=1.0,
                    risk_assessment="Emergency exit"
                )
            
            else:
                return SwapDecision(
                    decision_type=SwapDecisionType.NO_ACTION,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=self.position_state,
                    opportunity=opportunity,
                    reasoning=f"Hold ON position: Premium {opportunity.premium_pn:.2f}% < swap threshold",
                    confidence=opportunity.confidence_score,
                    risk_assessment="Holding position"
                )
        
        # Estado LONG_PN - posição longa em ITSA4
        elif self.position_state == PositionState.LONG_PN:
            
            # Verificar take profit
            if (self.current_position and 
                self.current_position.unrealized_pnl >= self.config["take_profit_threshold"]):
                
                return SwapDecision(
                    decision_type=SwapDecisionType.CLOSE_PN_POSITION,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=PositionState.IDLE,
                    opportunity=opportunity,
                    reasoning=f"Take profit: {self.current_position.unrealized_pnl:.2f}% >= {self.config['take_profit_threshold']:.2f}%",
                    confidence=1.0,
                    risk_assessment="Profit realization",
                    expected_return=self.current_position.unrealized_pnl
                )
            
            # Verificar degradação do premium
            elif opportunity.premium_pn < -0.5:  # Premium negativo forte
                return SwapDecision(
                    decision_type=SwapDecisionType.CLOSE_PN_POSITION,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=PositionState.IDLE,
                    opportunity=opportunity,
                    reasoning=f"Premium degradation: {opportunity.premium_pn:.2f}% < -0.5%",
                    confidence=0.8,
                    risk_assessment="Risk mitigation"
                )
            
            else:
                return SwapDecision(
                    decision_type=SwapDecisionType.NO_ACTION,
                    timestamp=current_time,
                    current_state=self.position_state,
                    target_state=self.position_state,
                    opportunity=opportunity,
                    reasoning=f"Hold PN position: Premium {opportunity.premium_pn:.2f}%",
                    confidence=opportunity.confidence_score,
                    risk_assessment="Monitoring position"
                )
        
        # Estado desconhecido
        else:
            return SwapDecision(
                decision_type=SwapDecisionType.NO_ACTION,
                timestamp=current_time,
                current_state=self.position_state,
                target_state=self.position_state,
                opportunity=opportunity,
                reasoning="Unknown state",
                confidence=0.0,
                risk_assessment="System error"
            )
    
    async def run_decision_cycle(self) -> SwapDecision:
        """Executa um ciclo completo de decisão"""
        logger.info("Starting decision cycle...")
        
        # 1. Obter dados de mercado
        quotes = await self.get_both_quotes()
        if not quotes:
            logger.error("Failed to get market quotes")
            return SwapDecision(
                decision_type=SwapDecisionType.NO_ACTION,
                timestamp=datetime.now(),
                current_state=self.position_state,
                target_state=self.position_state,
                opportunity=None,
                reasoning="Market data unavailable",
                confidence=0.0,
                risk_assessment="System error"
            )
        
        on_data, pn_data = quotes
        
        # 2. Analisar oportunidade
        opportunity = self.analyze_arbitrage_opportunity(on_data, pn_data)
        
        # 3. Atualizar posição atual se existir
        if self.current_position:
            self.current_position.current_price = (
                on_data.mid_price if self.position_state == PositionState.LONG_ON 
                else pn_data.mid_price
            )
            price_change = (
                (self.current_position.current_price - self.current_position.entry_price) 
                / self.current_position.entry_price * 100
            )
            self.current_position.unrealized_pnl = price_change
        
        # 4. Tomar decisão
        decision = self.make_swap_decision(opportunity)
        
        # 5. Adicionar ao histórico
        self.decision_history.append(decision)
        
        # 6. Log da decisão
        logger.info(f"Decision: {decision.decision_type.value}")
        logger.info(f"Reasoning: {decision.reasoning}")
        logger.info(f"Premium PN: {opportunity.premium_pn:.2f}%")
        logger.info(f"Confidence: {decision.confidence:.2f}")
        
        return decision
    
    async def simulate_position_update(self, decision: SwapDecision):
        """Simula atualização de posição (para demonstração)"""
        if decision.decision_type == SwapDecisionType.ENTER_LONG_ON:
            self.position_state = PositionState.LONG_ON
            self.current_position = Position(
                symbol=self.on_symbol,
                quantity=1000,  # Simulado
                entry_price=decision.opportunity.on_data.mid_price,
                entry_time=decision.timestamp,
                current_price=decision.opportunity.on_data.mid_price,
                unrealized_pnl=0.0,
                state=PositionState.LONG_ON
            )
            logger.info(f"Opened LONG ON position: {self.current_position.quantity} @ {self.current_position.entry_price:.2f}")
        
        elif decision.decision_type == SwapDecisionType.SWAP_TO_PN:
            self.position_state = PositionState.LONG_PN
            if self.current_position:
                self.current_position.symbol = self.pn_symbol
                self.current_position.entry_price = decision.opportunity.pn_data.mid_price
                self.current_position.entry_time = decision.timestamp
                self.current_position.state = PositionState.LONG_PN
                logger.info(f"Swapped to LONG PN position: {self.current_position.quantity} @ {self.current_position.entry_price:.2f}")
        
        elif decision.decision_type == SwapDecisionType.CLOSE_PN_POSITION:
            logger.info(f"Closed position with PnL: {self.current_position.unrealized_pnl:.2f}%")
            self.current_position = None
            self.position_state = PositionState.IDLE
        
        elif decision.decision_type == SwapDecisionType.EMERGENCY_EXIT:
            logger.warning(f"Emergency exit with PnL: {self.current_position.unrealized_pnl:.2f}%")
            self.current_position = None
            self.position_state = PositionState.IDLE
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Retorna resumo do status atual"""
        return {
            "timestamp": datetime.now().isoformat(),
            "position_state": self.position_state.value,
            "current_position": asdict(self.current_position) if self.current_position else None,
            "total_decisions": len(self.decision_history),
            "last_decision": self.decision_history[-1].to_dict() if self.decision_history else None,
            "config": self.config,
            "symbols": {
                "on": self.on_symbol,
                "pn": self.pn_symbol
            }
        }
    
    def export_decision_history(self, filename: str = None) -> str:
        """Exporta histórico de decisões"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"swap_decisions_{timestamp}.json"
        
        history_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "symbols": f"{self.on_symbol}⇄{self.pn_symbol}",
                "total_decisions": len(self.decision_history),
                "config": self.config
            },
            "decisions": [decision.to_dict() for decision in self.decision_history],
            "summary": self.get_status_summary()
        }
        
        with open(filename, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)
        
        logger.info(f"Decision history exported to: {filename}")
        return filename