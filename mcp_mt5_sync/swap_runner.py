#!/usr/bin/env python3
"""
E2.8 - Swap Backtest Runner
Simulador especializado para validação da estratégia de swap ITSA3⇄ITSA4
"""

import asyncio
import logging
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Adicionar path para o diretório principal do projeto
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.etapa2.swap_decision_client import (
    SwapDecisionClient,
    SwapDecisionType,
    PositionState,
    MarketData,
    Position
)
from src.execution.service import ExecutionService, ExecutionResult, ExecutionStatus
from src.db.trading_repository import (
    TradingRepository, 
    DatabaseConnection,
    DecisionRecord,
    PnLRecord
)

logger = logging.getLogger(__name__)

class MarketScenario(Enum):
    """Cenários de mercado para teste"""
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    DIVIDEND_SEASON = "dividend_season"
    LOW_LIQUIDITY = "low_liquidity"
    GAP_EVENTS = "gap_events"
    EXTREME_ZSCORES = "extreme_zscores"

@dataclass
class BacktestConfig:
    """Configuração do backtest"""
    # Período
    start_date: date
    end_date: date
    
    # Símbolos
    on_symbol: str = "ITSA3"
    pn_symbol: str = "ITSA4"
    
    # Capital
    initial_capital: float = 100000.0
    position_size_pct: float = 0.95
    
    # Thresholds de decisão
    min_premium_threshold: float = 0.20
    swap_threshold: float = 0.05
    take_profit_threshold: float = 0.50
    confidence_threshold: float = 0.60
    
    # Custos e slippage
    commission_rate: float = 0.0003  # 0.03%
    tax_rate: float = 0.00003  # 0.003%
    base_slippage_pct: float = 0.01  # 0.01%
    
    # Simulação
    tick_interval_seconds: int = 1
    decision_interval_minutes: int = 15
    max_trades_per_day: int = 5
    
    # Cenário
    scenario: MarketScenario = MarketScenario.NORMAL
    
    # Ruído de mercado
    noise_level: float = 0.0  # 0-1, onde 0 = sem ruído, 1 = máximo ruído
    gap_probability: float = 0.01  # 1% chance de gap
    gap_magnitude: float = 0.02  # 2% gap quando ocorre
    
    # Dividendos
    dividend_dates: List[date] = field(default_factory=list)
    dividend_impact_pct: float = 0.03  # 3% impacto no preço
    
    # Output
    save_results: bool = True
    output_dir: str = "reports/backtest"
    generate_html: bool = True
    generate_pdf: bool = False
    generate_csv: bool = True
    generate_json: bool = True

@dataclass
class TradeMetrics:
    """Métricas de um trade individual"""
    trade_id: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    
    # P&L
    gross_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0
    
    # Excursões
    mfe: float = 0.0  # Maximum Favorable Excursion
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe_pct: float = 0.0
    mae_pct: float = 0.0
    
    # Timing
    holding_time_minutes: int = 0
    time_to_mfe_minutes: int = 0
    time_to_mae_minutes: int = 0
    
    # Estado
    is_closed: bool = False
    is_profitable: bool = False
    exit_reason: Optional[str] = None

@dataclass
class BacktestResult:
    """Resultado completo do backtest"""
    # Identificação
    backtest_id: str
    config: BacktestConfig
    
    # Período
    start_date: date
    end_date: date
    trading_days: int
    
    # Performance
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    
    # Trades
    total_trades: int
    winning_trades: int
    losing_trades: int
    hit_rate: float  # Win rate percentual
    
    # P&L
    gross_pnl: float
    total_commission: float
    total_slippage: float
    total_taxes: float
    net_pnl: float
    
    # Estatísticas de trades
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float  # Sum(wins) / Sum(losses)
    
    # Risk metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    
    # MFE/MAE médios
    avg_mfe: float
    avg_mae: float
    avg_mfe_pct: float
    avg_mae_pct: float
    
    # Timing
    avg_holding_time_minutes: float
    max_holding_time_minutes: int
    min_holding_time_minutes: int
    
    # Swaps específicos
    total_swaps: int
    successful_swaps: int
    swap_success_rate: float
    avg_premium_at_entry: float
    avg_premium_at_swap: float
    avg_premium_at_exit: float
    
    # Trades detalhados
    trades: List[TradeMetrics] = field(default_factory=list)
    
    # Equity curve
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    # Decisões
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    execution_time_seconds: float = 0.0

class CostCalculator:
    """Calculadora de custos de transação"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".CostCalculator")
    
    def calculate_commission(self, quantity: int, price: float) -> float:
        """Calcula comissão"""
        trade_value = quantity * price
        return trade_value * self.config.commission_rate
    
    def calculate_slippage(self, quantity: int, price: float, 
                         is_buy: bool, liquidity_factor: float = 1.0) -> float:
        """Calcula slippage baseado em liquidez"""
        trade_value = quantity * price
        
        # Ajustar slippage baseado no cenário
        slippage_multiplier = 1.0
        
        if self.config.scenario == MarketScenario.HIGH_VOLATILITY:
            slippage_multiplier = 2.0
        elif self.config.scenario == MarketScenario.LOW_LIQUIDITY:
            slippage_multiplier = 3.0
        elif self.config.scenario == MarketScenario.GAP_EVENTS:
            slippage_multiplier = 5.0
        
        # Aplicar fator de liquidez
        slippage_multiplier *= liquidity_factor
        
        # Calcular slippage
        base_slippage = trade_value * self.config.base_slippage_pct / 100
        actual_slippage = base_slippage * slippage_multiplier
        
        # Slippage é custo para compra e ganho para venda
        return actual_slippage if is_buy else -actual_slippage
    
    def calculate_taxes(self, quantity: int, price: float) -> float:
        """Calcula taxas e emolumentos"""
        trade_value = quantity * price
        return trade_value * self.config.tax_rate
    
    def calculate_total_cost(self, quantity: int, price: float, 
                           is_buy: bool, liquidity_factor: float = 1.0) -> Dict[str, float]:
        """Calcula todos os custos"""
        commission = self.calculate_commission(quantity, price)
        slippage = self.calculate_slippage(quantity, price, is_buy, liquidity_factor)
        taxes = self.calculate_taxes(quantity, price)
        
        total = commission + slippage + taxes
        
        return {
            "commission": commission,
            "slippage": slippage,
            "taxes": taxes,
            "total": total
        }

class MarketDataGenerator:
    """Gerador de dados de mercado com ruído e cenários"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".MarketDataGenerator")
        self.base_data = None
        self.current_index = 0
    
    def load_historical_data(self, on_path: str, pn_path: str) -> bool:
        """Carrega dados históricos"""
        try:
            # Carregar dados ON
            on_data = pd.read_csv(on_path)
            on_data['timestamp'] = pd.to_datetime(on_data['timestamp'] if 'timestamp' in on_data.columns else on_data['time'])
            on_data.set_index('timestamp', inplace=True)
            
            # Carregar dados PN
            pn_data = pd.read_csv(pn_path)
            pn_data['timestamp'] = pd.to_datetime(pn_data['timestamp'] if 'timestamp' in pn_data.columns else pn_data['time'])
            pn_data.set_index('timestamp', inplace=True)
            
            # Filtrar período
            start_dt = pd.to_datetime(self.config.start_date)
            end_dt = pd.to_datetime(self.config.end_date)
            
            on_data = on_data[(on_data.index >= start_dt) & (on_data.index <= end_dt)]
            pn_data = pn_data[(pn_data.index >= start_dt) & (pn_data.index <= end_dt)]
            
            self.base_data = {
                'ON': on_data,
                'PN': pn_data
            }
            
            self.logger.info(f"Loaded {len(on_data)} ON and {len(pn_data)} PN records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load historical data: {e}")
            return False
    
    def apply_noise(self, price: float) -> float:
        """Aplica ruído ao preço"""
        if self.config.noise_level == 0:
            return price
        
        # Ruído gaussiano proporcional ao nível configurado
        noise = np.random.normal(0, self.config.noise_level * 0.01) * price
        return price + noise
    
    def apply_gap(self, price: float) -> float:
        """Aplica gap se necessário"""
        if self.config.scenario == MarketScenario.GAP_EVENTS:
            if np.random.random() < self.config.gap_probability:
                gap = price * self.config.gap_magnitude * (1 if np.random.random() > 0.5 else -1)
                self.logger.info(f"Gap event: {gap:+.2f} ({self.config.gap_magnitude*100:.1f}%)")
                return price + gap
        return price
    
    def apply_dividend_impact(self, price: float, symbol: str, current_date: date) -> float:
        """Aplica impacto de dividendos"""
        if current_date in self.config.dividend_dates:
            if symbol == self.config.pn_symbol:
                # PN geralmente tem direito a dividendos maiores
                impact = price * self.config.dividend_impact_pct
                self.logger.info(f"Dividend impact on {symbol}: {impact:+.2f}")
                return price - impact  # Preço cai após ex-dividendo
        return price
    
    def apply_volatility_adjustment(self, price: float) -> float:
        """Ajusta volatilidade baseado no cenário"""
        if self.config.scenario == MarketScenario.HIGH_VOLATILITY:
            # Aumenta volatilidade
            vol_multiplier = 2.0
            change = np.random.normal(0, 0.005 * vol_multiplier) * price
            return price + change
        elif self.config.scenario == MarketScenario.EXTREME_ZSCORES:
            # Força valores extremos ocasionalmente
            if np.random.random() < 0.1:  # 10% chance
                extreme_move = price * np.random.uniform(0.02, 0.05) * (1 if np.random.random() > 0.5 else -1)
                return price + extreme_move
        return price
    
    def generate_tick(self, timestamp: datetime) -> Tuple[MarketData, MarketData]:
        """Gera tick de mercado"""
        if self.base_data is None:
            # Gerar dados sintéticos se não houver histórico
            return self._generate_synthetic_tick(timestamp)
        
        # Usar dados históricos com modificações
        try:
            # Encontrar dados mais próximos
            on_data = self.base_data['ON'].iloc[self.base_data['ON'].index.get_indexer([timestamp], method='nearest')[0]]
            pn_data = self.base_data['PN'].iloc[self.base_data['PN'].index.get_indexer([timestamp], method='nearest')[0]]
            
            # Aplicar modificações
            on_price = on_data['close']
            pn_price = pn_data['close']
            
            # Aplicar ruído
            on_price = self.apply_noise(on_price)
            pn_price = self.apply_noise(pn_price)
            
            # Aplicar gaps
            on_price = self.apply_gap(on_price)
            pn_price = self.apply_gap(pn_price)
            
            # Aplicar dividendos
            current_date = timestamp.date()
            on_price = self.apply_dividend_impact(on_price, self.config.on_symbol, current_date)
            pn_price = self.apply_dividend_impact(pn_price, self.config.pn_symbol, current_date)
            
            # Aplicar ajuste de volatilidade
            on_price = self.apply_volatility_adjustment(on_price)
            pn_price = self.apply_volatility_adjustment(pn_price)
            
            # Criar MarketData
            spread_pct = 0.001  # 0.1% spread
            
            on_market = MarketData(
                symbol=self.config.on_symbol,
                normalized_symbol=self.config.on_symbol,
                bid=on_price * (1 - spread_pct),
                ask=on_price * (1 + spread_pct),
                last=on_price,
                volume=int(on_data.get('volume', 10000)),
                timestamp=timestamp
            )
            
            pn_market = MarketData(
                symbol=self.config.pn_symbol,
                normalized_symbol=self.config.pn_symbol,
                bid=pn_price * (1 - spread_pct),
                ask=pn_price * (1 + spread_pct),
                last=pn_price,
                volume=int(pn_data.get('volume', 8000)),
                timestamp=timestamp
            )
            
            return on_market, pn_market
            
        except Exception as e:
            self.logger.error(f"Error generating tick: {e}")
            return self._generate_synthetic_tick(timestamp)
    
    def _generate_synthetic_tick(self, timestamp: datetime) -> Tuple[MarketData, MarketData]:
        """Gera tick sintético quando não há dados históricos"""
        # Preços base
        on_base = 10.00
        pn_base = 10.20  # PN com premium de 2%
        
        # Adicionar variação temporal
        time_factor = (timestamp.hour * 60 + timestamp.minute) / (24 * 60)
        on_price = on_base + np.sin(time_factor * 2 * np.pi) * 0.10
        pn_price = pn_base + np.sin(time_factor * 2 * np.pi + 0.5) * 0.12
        
        # Aplicar modificações
        on_price = self.apply_noise(on_price)
        pn_price = self.apply_noise(pn_price)
        
        # Spread
        spread_pct = 0.001
        
        on_market = MarketData(
            symbol=self.config.on_symbol,
            normalized_symbol=self.config.on_symbol,
            bid=on_price * (1 - spread_pct),
            ask=on_price * (1 + spread_pct),
            last=on_price,
            volume=10000,
            timestamp=timestamp
        )
        
        pn_market = MarketData(
            symbol=self.config.pn_symbol,
            normalized_symbol=self.config.pn_symbol,
            bid=pn_price * (1 - spread_pct),
            ask=pn_price * (1 + spread_pct),
            last=pn_price,
            volume=8000,
            timestamp=timestamp
        )
        
        return on_market, pn_market

class SwapBacktestRunner:
    """Runner principal do backtest de swap"""
    
    def __init__(self, config: BacktestConfig, data_source: Optional[str] = None):
        self.config = config
        self.data_source = data_source
        
        # Componentes
        self.decision_client = SwapDecisionClient(
            on_symbol=config.on_symbol,
            pn_symbol=config.pn_symbol,
            config={
                "min_premium_threshold": config.min_premium_threshold,
                "swap_threshold": config.swap_threshold,
                "take_profit_threshold": config.take_profit_threshold,
                "confidence_threshold": config.confidence_threshold
            }
        )
        
        self.cost_calculator = CostCalculator(config)
        self.data_generator = MarketDataGenerator(config)
        
        # Estado
        self.current_capital = config.initial_capital
        self.current_position = None
        self.trades: List[TradeMetrics] = []
        self.current_trade: Optional[TradeMetrics] = None
        self.equity_curve = []
        self.decisions = []
        
        # Métricas
        self.max_equity = config.initial_capital
        self.max_drawdown = 0.0
        self.daily_returns = []
        
        self.logger = logging.getLogger(__name__ + ".SwapBacktestRunner")
    
    async def run_backtest(self) -> BacktestResult:
        """Executa backtest completo"""
        start_time = time.time()
        
        self.logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")
        
        # Carregar dados históricos se disponível
        if self.data_source:
            on_path = f"{self.data_source}/{self.config.on_symbol}.csv"
            pn_path = f"{self.data_source}/{self.config.pn_symbol}.csv"
            self.data_generator.load_historical_data(on_path, pn_path)
        
        # Simular período
        current_date = self.config.start_date
        trades_today = 0
        last_decision_time = None
        
        while current_date <= self.config.end_date:
            # Reset contador diário
            if current_date != self.config.start_date:
                trades_today = 0
            
            # Simular dia de trading (9h às 18h)
            for hour in range(9, 18):
                for minute in range(0, 60, self.config.decision_interval_minutes):
                    timestamp = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                    
                    # Verificar limite diário
                    if trades_today >= self.config.max_trades_per_day:
                        continue
                    
                    # Gerar dados de mercado
                    on_market, pn_market = self.data_generator.generate_tick(timestamp)
                    
                    # Atualizar MFE/MAE do trade atual
                    if self.current_trade and not self.current_trade.is_closed:
                        self._update_trade_excursions(self.current_trade, on_market, pn_market)
                    
                    # Analisar oportunidade
                    opportunity = self.decision_client.analyze_arbitrage_opportunity(on_market, pn_market)
                    
                    # Atualizar posição atual no cliente
                    self.decision_client.position_state = self._get_position_state()
                    self.decision_client.current_position = self._create_position_object(on_market, pn_market)
                    
                    # Tomar decisão
                    decision = self.decision_client.make_swap_decision(opportunity)
                    
                    # Registrar decisão
                    self.decisions.append({
                        "timestamp": timestamp,
                        "decision_type": decision.decision_type.value,
                        "confidence": decision.confidence,
                        "premium_pn": opportunity.premium_pn if opportunity else 0,
                        "reasoning": decision.reasoning
                    })
                    
                    # Executar decisão
                    if decision.decision_type != SwapDecisionType.NO_ACTION:
                        trade_executed = await self._execute_decision(decision, on_market, pn_market, timestamp)
                        if trade_executed:
                            trades_today += 1
                    
                    # Atualizar equity curve
                    self._update_equity_curve(timestamp, on_market, pn_market)
            
            # Próximo dia
            current_date += timedelta(days=1)
        
        # Fechar posições abertas
        if self.current_trade and not self.current_trade.is_closed:
            await self._close_position("End of backtest", on_market.mid_price, datetime.combine(self.config.end_date, datetime.max.time()))
        
        # Calcular resultado final
        execution_time = time.time() - start_time
        result = self._calculate_final_result(execution_time)
        
        # Salvar resultados
        if self.config.save_results:
            await self._save_results(result)
        
        self.logger.info(f"Backtest completed in {execution_time:.2f} seconds")
        self.logger.info(f"Final return: {result.total_return_pct:+.2f}%")
        self.logger.info(f"Hit rate: {result.hit_rate:.1f}%")
        self.logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
        
        return result
    
    def _get_position_state(self) -> PositionState:
        """Obtém estado atual da posição"""
        if self.current_position is None:
            return PositionState.IDLE
        elif self.current_position['symbol'] == self.config.on_symbol:
            return PositionState.LONG_ON
        elif self.current_position['symbol'] == self.config.pn_symbol:
            return PositionState.LONG_PN
        else:
            return PositionState.IDLE
    
    def _create_position_object(self, on_market: MarketData, pn_market: MarketData) -> Optional[Position]:
        """Cria objeto Position para o cliente de decisão"""
        if self.current_position is None:
            return None
        
        current_price = on_market.mid_price if self.current_position['symbol'] == self.config.on_symbol else pn_market.mid_price
        pnl_pct = ((current_price - self.current_position['entry_price']) / self.current_position['entry_price']) * 100
        
        return Position(
            symbol=self.current_position['symbol'],
            quantity=self.current_position['quantity'],
            entry_price=self.current_position['entry_price'],
            entry_time=self.current_position['entry_time'],
            current_price=current_price,
            unrealized_pnl=pnl_pct,
            state=self._get_position_state()
        )
    
    async def _execute_decision(self, decision, on_market: MarketData, pn_market: MarketData, timestamp: datetime) -> bool:
        """Executa decisão de trading"""
        try:
            if decision.decision_type == SwapDecisionType.ENTER_LONG_ON:
                # Calcular quantidade
                position_value = self.current_capital * self.config.position_size_pct
                quantity = int(position_value / on_market.ask)
                
                if quantity > 0:
                    # Calcular custos
                    costs = self.cost_calculator.calculate_total_cost(quantity, on_market.ask, is_buy=True)
                    effective_price = on_market.ask + (costs['slippage'] / quantity)
                    
                    # Criar trade
                    self.current_trade = TradeMetrics(
                        trade_id=f"trade_{len(self.trades)+1:04d}",
                        entry_time=timestamp,
                        entry_price=effective_price,
                        quantity=quantity,
                        exit_time=None,
                        exit_price=None,
                        commission=costs['commission'],
                        slippage=costs['slippage']
                    )
                    
                    # Atualizar posição
                    self.current_position = {
                        "symbol": self.config.on_symbol,
                        "quantity": quantity,
                        "entry_price": effective_price,
                        "entry_time": timestamp
                    }
                    
                    # Atualizar capital
                    total_cost = (quantity * effective_price) + costs['total']
                    self.current_capital -= total_cost
                    
                    self.logger.info(f"ENTER LONG ON: {quantity} @ {effective_price:.2f} (cost: {costs['total']:.2f})")
                    return True
            
            elif decision.decision_type == SwapDecisionType.SWAP_TO_PN:
                if self.current_position and self.current_position['symbol'] == self.config.on_symbol:
                    # Vender ON
                    sell_costs = self.cost_calculator.calculate_total_cost(
                        self.current_position['quantity'], 
                        on_market.bid, 
                        is_buy=False
                    )
                    sell_effective_price = on_market.bid - (sell_costs['slippage'] / self.current_position['quantity'])
                    sell_proceeds = self.current_position['quantity'] * sell_effective_price - sell_costs['total']
                    
                    # Comprar PN
                    pn_quantity = int(sell_proceeds * 0.99 / pn_market.ask)  # 99% para margem
                    buy_costs = self.cost_calculator.calculate_total_cost(pn_quantity, pn_market.ask, is_buy=True)
                    buy_effective_price = pn_market.ask + (buy_costs['slippage'] / pn_quantity)
                    
                    # Atualizar posição
                    self.current_position = {
                        "symbol": self.config.pn_symbol,
                        "quantity": pn_quantity,
                        "entry_price": buy_effective_price,
                        "entry_time": timestamp,
                        "swap_from_price": sell_effective_price
                    }
                    
                    # Atualizar capital
                    self.current_capital = sell_proceeds - (pn_quantity * buy_effective_price + buy_costs['total'])
                    
                    # Atualizar custos do trade
                    if self.current_trade:
                        self.current_trade.commission += sell_costs['commission'] + buy_costs['commission']
                        self.current_trade.slippage += sell_costs['slippage'] + buy_costs['slippage']
                    
                    self.logger.info(f"SWAP TO PN: {self.current_position['quantity']} @ {buy_effective_price:.2f}")
                    return True
            
            elif decision.decision_type in [SwapDecisionType.CLOSE_PN_POSITION, SwapDecisionType.EMERGENCY_EXIT]:
                if self.current_position:
                    symbol = self.current_position['symbol']
                    price = pn_market.bid if symbol == self.config.pn_symbol else on_market.bid
                    
                    await self._close_position(decision.reasoning, price, timestamp)
                    return True
            
        except Exception as e:
            self.logger.error(f"Error executing decision: {e}")
        
        return False
    
    async def _close_position(self, reason: str, price: float, timestamp: datetime):
        """Fecha posição atual"""
        if not self.current_position or not self.current_trade:
            return
        
        # Calcular custos de saída
        costs = self.cost_calculator.calculate_total_cost(
            self.current_position['quantity'],
            price,
            is_buy=False
        )
        
        effective_price = price - (costs['slippage'] / self.current_position['quantity'])
        proceeds = self.current_position['quantity'] * effective_price - costs['total']
        
        # Atualizar capital
        self.current_capital += proceeds
        
        # Finalizar trade
        self.current_trade.exit_time = timestamp
        self.current_trade.exit_price = effective_price
        self.current_trade.commission += costs['commission']
        self.current_trade.slippage += costs['slippage']
        
        # Calcular P&L
        entry_cost = self.current_position['quantity'] * self.current_position['entry_price']
        self.current_trade.gross_pnl = proceeds - entry_cost
        self.current_trade.net_pnl = self.current_trade.gross_pnl - self.current_trade.commission - abs(self.current_trade.slippage)
        
        self.current_trade.is_closed = True
        self.current_trade.is_profitable = self.current_trade.net_pnl > 0
        self.current_trade.exit_reason = reason
        
        # Calcular holding time
        self.current_trade.holding_time_minutes = int((timestamp - self.current_trade.entry_time).total_seconds() / 60)
        
        # Adicionar à lista de trades
        self.trades.append(self.current_trade)
        
        self.logger.info(f"CLOSE POSITION: {self.current_position['quantity']} @ {effective_price:.2f} (P&L: {self.current_trade.net_pnl:+.2f})")
        
        # Limpar posição
        self.current_position = None
        self.current_trade = None
    
    def _update_trade_excursions(self, trade: TradeMetrics, on_market: MarketData, pn_market: MarketData):
        """Atualiza MFE/MAE do trade"""
        if not self.current_position:
            return
        
        current_price = on_market.mid_price if self.current_position['symbol'] == self.config.on_symbol else pn_market.mid_price
        
        # Calcular P&L não realizado
        unrealized_pnl = (current_price - trade.entry_price) * self.current_position['quantity']
        unrealized_pnl_pct = (unrealized_pnl / (trade.entry_price * self.current_position['quantity'])) * 100
        
        # Atualizar MFE (Maximum Favorable Excursion)
        if unrealized_pnl > trade.mfe:
            trade.mfe = unrealized_pnl
            trade.mfe_pct = unrealized_pnl_pct
            trade.time_to_mfe_minutes = int((datetime.now() - trade.entry_time).total_seconds() / 60)
        
        # Atualizar MAE (Maximum Adverse Excursion)
        if unrealized_pnl < trade.mae:
            trade.mae = unrealized_pnl
            trade.mae_pct = unrealized_pnl_pct
            trade.time_to_mae_minutes = int((datetime.now() - trade.entry_time).total_seconds() / 60)
    
    def _update_equity_curve(self, timestamp: datetime, on_market: MarketData, pn_market: MarketData):
        """Atualiza equity curve"""
        # Calcular valor da posição atual
        position_value = 0
        if self.current_position:
            current_price = on_market.mid_price if self.current_position['symbol'] == self.config.on_symbol else pn_market.mid_price
            position_value = self.current_position['quantity'] * current_price
        
        # Equity total
        total_equity = self.current_capital + position_value
        
        # Atualizar max drawdown
        if total_equity > self.max_equity:
            self.max_equity = total_equity
        
        drawdown = self.max_equity - total_equity
        drawdown_pct = (drawdown / self.max_equity) * 100 if self.max_equity > 0 else 0
        
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Adicionar ponto à equity curve
        self.equity_curve.append({
            "timestamp": timestamp,
            "capital": self.current_capital,
            "position_value": position_value,
            "total_equity": total_equity,
            "drawdown": drawdown,
            "drawdown_pct": drawdown_pct,
            "on_price": on_market.mid_price,
            "pn_price": pn_market.mid_price,
            "premium": ((pn_market.mid_price - on_market.mid_price) / on_market.mid_price) * 100
        })
    
    def _calculate_final_result(self, execution_time: float) -> BacktestResult:
        """Calcula resultado final do backtest"""
        # Performance básica
        initial_capital = self.config.initial_capital
        final_capital = self.current_capital
        
        # Adicionar valor de posição aberta se houver
        if self.current_position:
            # Usar último preço da equity curve
            if self.equity_curve:
                final_capital = self.equity_curve[-1]['total_equity']
        
        total_return = final_capital - initial_capital
        total_return_pct = (total_return / initial_capital) * 100 if initial_capital > 0 else 0
        
        # Estatísticas de trades
        closed_trades = [t for t in self.trades if t.is_closed]
        winning_trades = [t for t in closed_trades if t.is_profitable]
        losing_trades = [t for t in closed_trades if not t.is_profitable]
        
        hit_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        # P&L
        gross_pnl = sum(t.gross_pnl for t in closed_trades)
        total_commission = sum(t.commission for t in closed_trades)
        total_slippage = sum(abs(t.slippage) for t in closed_trades)
        net_pnl = sum(t.net_pnl for t in closed_trades)
        
        # Estatísticas de win/loss
        avg_win = np.mean([t.net_pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.net_pnl for t in losing_trades]) if losing_trades else 0
        largest_win = max([t.net_pnl for t in winning_trades]) if winning_trades else 0
        largest_loss = min([t.net_pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        total_wins = sum(t.net_pnl for t in winning_trades) if winning_trades else 0
        total_losses = abs(sum(t.net_pnl for t in losing_trades)) if losing_trades else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Risk metrics
        equity_returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1]['total_equity']
            curr_equity = self.equity_curve[i]['total_equity']
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                equity_returns.append(ret)
        
        if equity_returns:
            # Sharpe ratio (assumindo taxa livre de risco = 0)
            sharpe_ratio = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if np.std(equity_returns) > 0 else 0
            
            # Sortino ratio (considerando apenas retornos negativos)
            negative_returns = [r for r in equity_returns if r < 0]
            downside_std = np.std(negative_returns) if negative_returns else 1
            sortino_ratio = np.mean(equity_returns) / downside_std * np.sqrt(252) if downside_std > 0 else 0
            
            # VaR e CVaR
            var_95 = np.percentile(equity_returns, 5) * initial_capital if equity_returns else 0
            cvar_95 = np.mean([r * initial_capital for r in equity_returns if r <= np.percentile(equity_returns, 5)]) if equity_returns else 0
        else:
            sharpe_ratio = sortino_ratio = var_95 = cvar_95 = 0
        
        # MFE/MAE médios
        if closed_trades:
            avg_mfe = np.mean([t.mfe for t in closed_trades])
            avg_mae = np.mean([t.mae for t in closed_trades])
            avg_mfe_pct = np.mean([t.mfe_pct for t in closed_trades])
            avg_mae_pct = np.mean([t.mae_pct for t in closed_trades])
        else:
            avg_mfe = avg_mae = avg_mfe_pct = avg_mae_pct = 0
        
        # Timing
        if closed_trades:
            avg_holding = np.mean([t.holding_time_minutes for t in closed_trades])
            max_holding = max(t.holding_time_minutes for t in closed_trades)
            min_holding = min(t.holding_time_minutes for t in closed_trades)
        else:
            avg_holding = max_holding = min_holding = 0
        
        # Swaps específicos
        swap_decisions = [d for d in self.decisions if 'SWAP' in d['decision_type']]
        total_swaps = len(swap_decisions)
        
        # Calcular taxa de sucesso de swaps (simplificado)
        successful_swaps = 0
        for i, decision in enumerate(self.decisions):
            if decision['decision_type'] == 'SWAP_TO_PN':
                # Verificar se próxima decisão foi de fechar com lucro
                for j in range(i+1, len(self.decisions)):
                    if self.decisions[j]['decision_type'] in ['CLOSE_PN_POSITION']:
                        # Verificar se trade correspondente foi lucrativo
                        if closed_trades:
                            # Simplificado: assumir que swap foi bem-sucedido se trade foi lucrativo
                            successful_swaps += 1 if closed_trades[-1].is_profitable else 0
                        break
        
        swap_success_rate = (successful_swaps / total_swaps * 100) if total_swaps > 0 else 0
        
        # Premiums médios
        entry_premiums = [d['premium_pn'] for d in self.decisions if d['decision_type'] == 'ENTER_LONG_ON']
        swap_premiums = [d['premium_pn'] for d in self.decisions if d['decision_type'] == 'SWAP_TO_PN']
        exit_premiums = [d['premium_pn'] for d in self.decisions if 'CLOSE' in d['decision_type']]
        
        avg_premium_entry = np.mean(entry_premiums) if entry_premiums else 0
        avg_premium_swap = np.mean(swap_premiums) if swap_premiums else 0
        avg_premium_exit = np.mean(exit_premiums) if exit_premiums else 0
        
        # Trading days
        if self.equity_curve:
            first_date = self.equity_curve[0]['timestamp'].date()
            last_date = self.equity_curve[-1]['timestamp'].date()
            trading_days = (last_date - first_date).days + 1
        else:
            trading_days = (self.config.end_date - self.config.start_date).days + 1
        
        # Max drawdown percentual
        max_drawdown_pct = (self.max_drawdown / self.max_equity * 100) if self.max_equity > 0 else 0
        
        return BacktestResult(
            backtest_id=f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config=self.config,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            trading_days=trading_days,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            total_trades=len(closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            hit_rate=hit_rate,
            gross_pnl=gross_pnl,
            total_commission=total_commission,
            total_slippage=total_slippage,
            total_taxes=0,  # Simplificado
            net_pnl=net_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            var_95=var_95,
            cvar_95=cvar_95,
            avg_mfe=avg_mfe,
            avg_mae=avg_mae,
            avg_mfe_pct=avg_mfe_pct,
            avg_mae_pct=avg_mae_pct,
            avg_holding_time_minutes=avg_holding,
            max_holding_time_minutes=int(max_holding),
            min_holding_time_minutes=int(min_holding),
            total_swaps=total_swaps,
            successful_swaps=successful_swaps,
            swap_success_rate=swap_success_rate,
            avg_premium_at_entry=avg_premium_entry,
            avg_premium_at_swap=avg_premium_swap,
            avg_premium_at_exit=avg_premium_exit,
            trades=self.trades,
            equity_curve=self.equity_curve,
            decisions=self.decisions,
            execution_time_seconds=execution_time
        )
    
    async def _save_results(self, result: BacktestResult):
        """Salva resultados em diferentes formatos"""
        # Criar diretório se não existir
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{self.config.output_dir}/swap_backtest_{timestamp}"
        
        # JSON
        if self.config.generate_json:
            json_file = f"{base_filename}.json"
            with open(json_file, 'w') as f:
                # Converter para dict serializável
                result_dict = asdict(result)
                # Converter dates para string
                result_dict['start_date'] = str(result.start_date)
                result_dict['end_date'] = str(result.end_date)
                result_dict['created_at'] = result.created_at.isoformat()
                result_dict['config']['start_date'] = str(result.config.start_date)
                result_dict['config']['end_date'] = str(result.config.end_date)
                result_dict['config']['scenario'] = result.config.scenario.value
                result_dict['config']['dividend_dates'] = [str(d) for d in result.config.dividend_dates]
                
                json.dump(result_dict, f, indent=2, default=str)
            self.logger.info(f"Results saved to {json_file}")
        
        # CSV
        if self.config.generate_csv:
            csv_file = f"{base_filename}_trades.csv"
            trades_df = pd.DataFrame([asdict(t) for t in result.trades])
            trades_df.to_csv(csv_file, index=False)
            self.logger.info(f"Trades saved to {csv_file}")
            
            # Equity curve CSV
            equity_csv = f"{base_filename}_equity.csv"
            equity_df = pd.DataFrame(result.equity_curve)
            equity_df.to_csv(equity_csv, index=False)
            self.logger.info(f"Equity curve saved to {equity_csv}")
        
        # HTML
        if self.config.generate_html:
            html_file = f"{base_filename}.html"
            html_content = self._generate_html_report(result)
            with open(html_file, 'w') as f:
                f.write(html_content)
            self.logger.info(f"HTML report saved to {html_file}")
    
    def _generate_html_report(self, result: BacktestResult) -> str:
        """Gera relatório HTML interativo"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Swap Backtest Report - {result.backtest_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-label {{ font-weight: bold; color: #666; }}
                .metric-value {{ font-size: 1.2em; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary-box {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Swap Backtest Report</h1>
            <div class="summary-box">
                <h2>Summary</h2>
                <div class="metric">
                    <span class="metric-label">Period:</span>
                    <span class="metric-value">{result.start_date} to {result.end_date}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Initial Capital:</span>
                    <span class="metric-value">R$ {result.initial_capital:,.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Final Capital:</span>
                    <span class="metric-value">R$ {result.final_capital:,.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Return:</span>
                    <span class="metric-value {'positive' if result.total_return_pct > 0 else 'negative'}">
                        {result.total_return_pct:+.2f}%
                    </span>
                </div>
            </div>
            
            <h2>Performance Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Trades</td><td>{result.total_trades}</td></tr>
                <tr><td>Winning Trades</td><td>{result.winning_trades}</td></tr>
                <tr><td>Losing Trades</td><td>{result.losing_trades}</td></tr>
                <tr><td>Hit Rate</td><td>{result.hit_rate:.1f}%</td></tr>
                <tr><td>Average Win</td><td>R$ {result.avg_win:,.2f}</td></tr>
                <tr><td>Average Loss</td><td>R$ {result.avg_loss:,.2f}</td></tr>
                <tr><td>Profit Factor</td><td>{result.profit_factor:.2f}</td></tr>
                <tr><td>Sharpe Ratio</td><td>{result.sharpe_ratio:.2f}</td></tr>
                <tr><td>Max Drawdown</td><td>{result.max_drawdown_pct:.2f}%</td></tr>
            </table>
            
            <h2>Swap Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Swaps</td><td>{result.total_swaps}</td></tr>
                <tr><td>Successful Swaps</td><td>{result.successful_swaps}</td></tr>
                <tr><td>Swap Success Rate</td><td>{result.swap_success_rate:.1f}%</td></tr>
                <tr><td>Avg Premium at Entry</td><td>{result.avg_premium_at_entry:+.2f}%</td></tr>
                <tr><td>Avg Premium at Swap</td><td>{result.avg_premium_at_swap:+.2f}%</td></tr>
                <tr><td>Avg Premium at Exit</td><td>{result.avg_premium_at_exit:+.2f}%</td></tr>
            </table>
            
            <h2>MFE/MAE Analysis</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Average MFE</td><td>R$ {result.avg_mfe:,.2f}</td></tr>
                <tr><td>Average MFE %</td><td>{result.avg_mfe_pct:.2f}%</td></tr>
                <tr><td>Average MAE</td><td>R$ {result.avg_mae:,.2f}</td></tr>
                <tr><td>Average MAE %</td><td>{result.avg_mae_pct:.2f}%</td></tr>
            </table>
            
            <h2>Cost Analysis</h2>
            <table>
                <tr><th>Cost Type</th><th>Amount</th></tr>
                <tr><td>Commission</td><td>R$ {result.total_commission:,.2f}</td></tr>
                <tr><td>Slippage</td><td>R$ {result.total_slippage:,.2f}</td></tr>
                <tr><td>Taxes</td><td>R$ {result.total_taxes:,.2f}</td></tr>
                <tr><td>Total Costs</td><td>R$ {result.total_commission + result.total_slippage + result.total_taxes:,.2f}</td></tr>
            </table>
            
            <p style="text-align: center; color: #999; margin-top: 50px;">
                Generated at {result.created_at.strftime('%Y-%m-%d %H:%M:%S')} | 
                Execution time: {result.execution_time_seconds:.2f} seconds
            </p>
        </body>
        </html>
        """
        return html


# Funções de demonstração
async def run_backtest_demo():
    """Demonstração do backtest de swap"""
    print("🚀 SWAP BACKTEST RUNNER DEMO")
    print("="*60)
    
    # Configuração para demo com parâmetros mais agressivos
    config = BacktestConfig(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 5),   # 5 dias para demo mais rápido
        initial_capital=100000.0,
        min_premium_threshold=0.02,  # Threshold muito baixo para permitir trades
        swap_threshold=0.01,         # Threshold baixo para swaps
        take_profit_threshold=0.05,  # Take profit baixo para sair rapidamente
        confidence_threshold=0.1,    # Confiança muito baixa
        scenario=MarketScenario.HIGH_VOLATILITY,  # Alta volatilidade
        noise_level=0.3,             # 30% de ruído para criar oportunidades
        gap_probability=0.1,         # 10% chance de gaps
        gap_magnitude=0.08,          # Gaps de 8%
        save_results=True,
        generate_html=True,
        generate_csv=True,
        generate_json=True
    )
    
    print(f"Configuration:")
    print(f"  Period: {config.start_date} to {config.end_date}")
    print(f"  Capital: R$ {config.initial_capital:,.2f}")
    print(f"  Scenario: {config.scenario.value}")
    print(f"  Noise Level: {config.noise_level*100:.0f}%")
    
    # Criar runner
    runner = SwapBacktestRunner(config)
    
    # Executar backtest
    print("\nRunning backtest...")
    result = await runner.run_backtest()
    
    # Mostrar resultados
    print("\n" + "="*60)
    print("📊 BACKTEST RESULTS")
    print("="*60)
    
    print(f"\n💰 PERFORMANCE")
    print(f"  Total Return: {result.total_return_pct:+.2f}%")
    print(f"  Net P&L: R$ {result.net_pnl:+,.2f}")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
    
    print(f"\n📈 TRADES")
    print(f"  Total: {result.total_trades}")
    print(f"  Winners: {result.winning_trades}")
    print(f"  Losers: {result.losing_trades}")
    print(f"  Hit Rate: {result.hit_rate:.1f}%")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    
    print(f"\n🔄 SWAPS")
    print(f"  Total: {result.total_swaps}")
    print(f"  Successful: {result.successful_swaps}")
    print(f"  Success Rate: {result.swap_success_rate:.1f}%")
    
    print(f"\n📊 MFE/MAE")
    print(f"  Avg MFE: {result.avg_mfe_pct:.2f}%")
    print(f"  Avg MAE: {result.avg_mae_pct:.2f}%")
    
    print(f"\n💸 COSTS")
    print(f"  Commission: R$ {result.total_commission:,.2f}")
    print(f"  Slippage: R$ {result.total_slippage:,.2f}")
    print(f"  Total: R$ {result.total_commission + result.total_slippage:,.2f}")
    
    print(f"\n⏱️  TIMING")
    print(f"  Avg Holding: {result.avg_holding_time_minutes:.0f} minutes")
    print(f"  Execution Time: {result.execution_time_seconds:.2f} seconds")
    
    if config.save_results:
        print(f"\n💾 Results saved to {config.output_dir}/")
    
    return result


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executar demo
    asyncio.run(run_backtest_demo())