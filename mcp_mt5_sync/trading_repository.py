#!/usr/bin/env python3
"""
E2.7 - Trading Repository
DAOs e Repositories para persistência de decisões, ordens, fills e P&L
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import sys
import os

# Adicionar paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import asyncpg
    import pandas as pd
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    
from src.etapa2.swap_decision_client import SwapDecisionType, PositionState
from src.execution.service import ExecutionResult, ExecutionStatus, OrderResult

logger = logging.getLogger(__name__)

class DecisionStatus(Enum):
    """Status de decisão"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OrderStatus(Enum):
    """Status de ordem"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"

@dataclass
class DecisionRecord:
    """Record de decisão de swap"""
    decision_id: str
    execution_id: str
    strategy_id: str = "itsa_arbitrage"
    timestamp: datetime = None
    
    # Símbolos e contexto
    from_symbol: str = ""
    to_symbol: str = ""
    trigger_reason: str = ""
    decision_type: str = ""
    
    # Estado e posição
    current_state: str = ""
    target_state: str = ""
    position_quantity: Optional[int] = None
    position_entry_price: Optional[float] = None
    
    # Métricas de oportunidade
    premium_pn: Optional[float] = None
    spread_cost: Optional[float] = None
    net_opportunity: Optional[float] = None
    confidence_score: Optional[float] = None
    
    # Expectativas
    expected_profit: Optional[float] = None
    expected_return_pct: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    max_slippage: Optional[float] = None
    
    # Status e timing
    status: str = DecisionStatus.PENDING.value
    created_at: datetime = None
    updated_at: datetime = None
    completed_at: Optional[datetime] = None
    
    # Auditoria
    audit_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class OrderRecord:
    """Record de ordem individual"""
    order_id: str
    decision_id: str
    
    # Identificação externa
    client_id: Optional[str] = None
    mt5_order_id: Optional[int] = None
    magic_number: int = 20250829
    
    # Detalhes da ordem
    symbol: str = ""
    side: str = ""  # BUY, SELL
    order_type: str = "MARKET"
    quantity: int = 0
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Execução
    filled_quantity: int = 0
    remaining_quantity: Optional[int] = None
    avg_fill_price: Optional[float] = None
    
    # Status e timing
    status: str = OrderStatus.PENDING.value
    created_at: datetime = None
    updated_at: datetime = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Métricas de execução
    slippage_pct: Optional[float] = None
    execution_time_ms: Optional[int] = None
    retry_count: int = 0
    
    # Detalhes de erro
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    
    # Auditoria
    audit_trail: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

@dataclass
class FillRecord:
    """Record de execução (fill)"""
    fill_id: str
    order_id: str
    
    # Identificação externa
    mt5_deal_id: Optional[int] = None
    
    # Detalhes da execução
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: float = 0.0
    
    # Timing
    timestamp: datetime = None
    server_time: Optional[datetime] = None
    
    # Custos
    commission: float = 0.0
    swap: float = 0.0
    fees: float = 0.0
    
    # Contexto
    is_partial_fill: bool = False
    fill_sequence: int = 1
    
    # Auditoria
    source_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PnLRecord:
    """Record de P&L consolidado"""
    pnl_id: str
    decision_id: str
    
    # P&L realizado
    gross_proceeds: float = 0.0
    gross_cost: float = 0.0
    realized_pnl: float = 0.0
    
    # Custos detalhados
    commission_total: float = 0.0
    swap_total: float = 0.0
    fees_total: float = 0.0
    slippage_cost: float = 0.0
    
    # P&L líquido
    net_pnl: float = 0.0
    net_pnl_pct: float = 0.0
    
    # Métricas de performance
    capital_allocated: Optional[float] = None
    return_on_capital: Optional[float] = None
    holding_period_minutes: Optional[int] = None
    
    # Status
    is_final: bool = False
    calculation_method: str = "fifo"
    
    # Timing
    calculated_at: datetime = None
    position_opened_at: Optional[datetime] = None
    position_closed_at: Optional[datetime] = None
    
    # Contexto adicional
    market_conditions: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.now()

class DatabaseConnection:
    """Gerenciador de conexão com banco de dados"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or self._get_default_connection()
        self.pool = None
        self._connected = False
    
    def _get_default_connection(self) -> str:
        """Obtém string de conexão padrão"""
        # Para demo, usar configuração local
        return "postgresql://postgres:postgres@localhost:5432/trading_dev"
    
    async def connect(self):
        """Conecta ao banco de dados"""
        if not ASYNCPG_AVAILABLE:
            logger.warning("asyncpg not available, using mock connection")
            self._connected = True
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            self._connected = True
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            # Force mock mode on connection failure
            logger.warning("Falling back to mock mode")
            self._connected = True
            self.pool = None
    
    async def disconnect(self):
        """Desconecta do banco de dados"""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """Executa query sem retorno"""
        if not ASYNCPG_AVAILABLE or not self._connected or self.pool is None:
            logger.info(f"Mock execute: {query[:100]}...")
            return "OK"
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Executa query com retorno"""
        if not ASYNCPG_AVAILABLE or not self._connected or self.pool is None:
            logger.info(f"Mock fetch: {query[:100]}...")
            return []
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Executa query retornando uma linha"""
        if not ASYNCPG_AVAILABLE or not self._connected or self.pool is None:
            logger.info(f"Mock fetchrow: {query[:100]}...")
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def transaction(self):
        """Context manager para transações"""
        if not ASYNCPG_AVAILABLE or not self._connected or self.pool is None:
            return MockTransaction()
        
        return self.pool.acquire()

class MockTransaction:
    """Mock transaction para quando asyncpg não está disponível"""
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class TradingRepository:
    """Repository principal para operações de trading"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.logger = logging.getLogger(__name__ + ".TradingRepository")
    
    async def ensure_connection(self):
        """Garante que há conexão com o banco"""
        if not self.db._connected:
            try:
                await self.db.connect()
            except Exception as e:
                self.logger.warning(f"Database connection failed, using mock mode: {e}")
                self.db._connected = True  # Force mock mode
    
    # ===================================
    # DECISIONS
    # ===================================
    
    async def save_decision(self, decision: DecisionRecord) -> str:
        """Salva decisão de swap (upsert)"""
        await self.ensure_connection()
        
        query = """
        INSERT INTO trading.decisions (
            decision_id, execution_id, strategy_id, timestamp,
            from_symbol, to_symbol, trigger_reason, decision_type,
            current_state, target_state, position_quantity, position_entry_price,
            premium_pn, spread_cost, net_opportunity, confidence_score,
            expected_profit, expected_return_pct, take_profit, stop_loss, max_slippage,
            status, audit_data, error_details
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24
        )
        ON CONFLICT (decision_id) DO UPDATE SET
            status = $22,
            updated_at = NOW(),
            completed_at = CASE WHEN $22 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
            audit_data = $23,
            error_details = $24
        """
        
        try:
            await self.db.execute(
                query, 
                decision.decision_id, decision.execution_id, decision.strategy_id, decision.timestamp,
                decision.from_symbol, decision.to_symbol, decision.trigger_reason, decision.decision_type,
                decision.current_state, decision.target_state, decision.position_quantity, decision.position_entry_price,
                decision.premium_pn, decision.spread_cost, decision.net_opportunity, decision.confidence_score,
                decision.expected_profit, decision.expected_return_pct, decision.take_profit, decision.stop_loss, decision.max_slippage,
                decision.status, 
                json.dumps(decision.audit_data) if decision.audit_data else None,
                json.dumps(decision.error_details) if decision.error_details else None
            )
            
            self.logger.info(f"Decision saved: {decision.decision_id} ({decision.status})")
            return decision.decision_id
            
        except Exception as e:
            self.logger.error(f"Failed to save decision {decision.decision_id}: {e}")
            raise
    
    async def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Obtém decisão por ID"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.decisions WHERE decision_id = $1
        """
        
        try:
            row = await self.db.fetchrow(query, decision_id)
            if not row:
                return None
            
            # Converter para DecisionRecord
            decision = DecisionRecord(
                decision_id=row['decision_id'],
                execution_id=row['execution_id'],
                strategy_id=row['strategy_id'],
                timestamp=row['timestamp'],
                from_symbol=row['from_symbol'],
                to_symbol=row['to_symbol'],
                trigger_reason=row['trigger_reason'],
                decision_type=row['decision_type'],
                current_state=row['current_state'],
                target_state=row['target_state'],
                position_quantity=row['position_quantity'],
                position_entry_price=float(row['position_entry_price']) if row['position_entry_price'] else None,
                premium_pn=float(row['premium_pn']) if row['premium_pn'] else None,
                spread_cost=float(row['spread_cost']) if row['spread_cost'] else None,
                net_opportunity=float(row['net_opportunity']) if row['net_opportunity'] else None,
                confidence_score=float(row['confidence_score']) if row['confidence_score'] else None,
                expected_profit=float(row['expected_profit']) if row['expected_profit'] else None,
                expected_return_pct=float(row['expected_return_pct']) if row['expected_return_pct'] else None,
                take_profit=float(row['take_profit']) if row['take_profit'] else None,
                stop_loss=float(row['stop_loss']) if row['stop_loss'] else None,
                max_slippage=float(row['max_slippage']) if row['max_slippage'] else None,
                status=row['status'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                completed_at=row['completed_at'],
                audit_data=json.loads(row['audit_data']) if row['audit_data'] else None,
                error_details=json.loads(row['error_details']) if row['error_details'] else None
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Failed to get decision {decision_id}: {e}")
            raise
    
    async def update_decision_status(self, decision_id: str, status: DecisionStatus, 
                                   error_details: Optional[Dict[str, Any]] = None) -> bool:
        """Atualiza status da decisão"""
        await self.ensure_connection()
        
        query = """
        UPDATE trading.decisions 
        SET status = $2, 
            updated_at = NOW(),
            completed_at = CASE WHEN $2 IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END,
            error_details = $3
        WHERE decision_id = $1
        """
        
        try:
            result = await self.db.execute(
                query, 
                decision_id, 
                status.value,
                json.dumps(error_details) if error_details else None
            )
            
            self.logger.info(f"Decision status updated: {decision_id} -> {status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update decision status {decision_id}: {e}")
            return False
    
    # ===================================
    # ORDERS
    # ===================================
    
    async def save_order(self, order: OrderRecord) -> str:
        """Salva ordem (upsert)"""
        await self.ensure_connection()
        
        query = """
        INSERT INTO trading.orders (
            order_id, decision_id, client_id, mt5_order_id, magic_number,
            symbol, side, order_type, quantity, price, stop_loss, take_profit,
            filled_quantity, remaining_quantity, avg_fill_price,
            status, submitted_at, filled_at, cancelled_at,
            slippage_pct, execution_time_ms, retry_count,
            error_code, error_message, audit_trail
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
            $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25
        )
        ON CONFLICT (order_id) DO UPDATE SET
            filled_quantity = $13,
            remaining_quantity = $14,
            avg_fill_price = $15,
            status = $16,
            updated_at = NOW(),
            submitted_at = COALESCE($17, orders.submitted_at),
            filled_at = COALESCE($18, orders.filled_at),
            cancelled_at = COALESCE($19, orders.cancelled_at),
            slippage_pct = COALESCE($20, orders.slippage_pct),
            execution_time_ms = COALESCE($21, orders.execution_time_ms),
            retry_count = $22,
            error_code = COALESCE($23, orders.error_code),
            error_message = COALESCE($24, orders.error_message),
            audit_trail = COALESCE($25, orders.audit_trail)
        """
        
        try:
            await self.db.execute(
                query,
                order.order_id, order.decision_id, order.client_id, order.mt5_order_id, order.magic_number,
                order.symbol, order.side, order.order_type, order.quantity, order.price, order.stop_loss, order.take_profit,
                order.filled_quantity, order.remaining_quantity, order.avg_fill_price,
                order.status, order.submitted_at, order.filled_at, order.cancelled_at,
                order.slippage_pct, order.execution_time_ms, order.retry_count,
                order.error_code, order.error_message,
                json.dumps(order.audit_trail) if order.audit_trail else None
            )
            
            self.logger.info(f"Order saved: {order.order_id} ({order.status})")
            return order.order_id
            
        except Exception as e:
            self.logger.error(f"Failed to save order {order.order_id}: {e}")
            raise
    
    async def get_orders_by_decision(self, decision_id: str) -> List[OrderRecord]:
        """Obtém todas as ordens de uma decisão"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.orders WHERE decision_id = $1 ORDER BY created_at
        """
        
        try:
            rows = await self.db.fetch(query, decision_id)
            orders = []
            
            for row in rows:
                order = OrderRecord(
                    order_id=row['order_id'],
                    decision_id=row['decision_id'],
                    client_id=row['client_id'],
                    mt5_order_id=row['mt5_order_id'],
                    magic_number=row['magic_number'],
                    symbol=row['symbol'],
                    side=row['side'],
                    order_type=row['order_type'],
                    quantity=row['quantity'],
                    price=float(row['price']) if row['price'] else None,
                    stop_loss=float(row['stop_loss']) if row['stop_loss'] else None,
                    take_profit=float(row['take_profit']) if row['take_profit'] else None,
                    filled_quantity=row['filled_quantity'],
                    remaining_quantity=row['remaining_quantity'],
                    avg_fill_price=float(row['avg_fill_price']) if row['avg_fill_price'] else None,
                    status=row['status'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    submitted_at=row['submitted_at'],
                    filled_at=row['filled_at'],
                    cancelled_at=row['cancelled_at'],
                    slippage_pct=float(row['slippage_pct']) if row['slippage_pct'] else None,
                    execution_time_ms=row['execution_time_ms'],
                    retry_count=row['retry_count'],
                    error_code=row['error_code'],
                    error_message=row['error_message'],
                    audit_trail=json.loads(row['audit_trail']) if row['audit_trail'] else None
                )
                orders.append(order)
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Failed to get orders for decision {decision_id}: {e}")
            raise
    
    # ===================================
    # FILLS
    # ===================================
    
    async def save_fill(self, fill: FillRecord) -> str:
        """Salva fill (execução)"""
        await self.ensure_connection()
        
        query = """
        INSERT INTO trading.fills (
            fill_id, order_id, mt5_deal_id,
            symbol, side, quantity, price,
            timestamp, server_time,
            commission, swap, fees,
            is_partial_fill, fill_sequence,
            source_data
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
        ON CONFLICT (fill_id) DO UPDATE SET
            commission = $10,
            swap = $11, 
            fees = $12,
            source_data = $15
        """
        
        try:
            await self.db.execute(
                query,
                fill.fill_id, fill.order_id, fill.mt5_deal_id,
                fill.symbol, fill.side, fill.quantity, fill.price,
                fill.timestamp, fill.server_time,
                fill.commission, fill.swap, fill.fees,
                fill.is_partial_fill, fill.fill_sequence,
                json.dumps(fill.source_data) if fill.source_data else None
            )
            
            self.logger.info(f"Fill saved: {fill.fill_id} ({fill.quantity} {fill.symbol} @ {fill.price})")
            return fill.fill_id
            
        except Exception as e:
            self.logger.error(f"Failed to save fill {fill.fill_id}: {e}")
            raise
    
    async def get_fills_by_order(self, order_id: str) -> List[FillRecord]:
        """Obtém todos os fills de uma ordem"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.fills WHERE order_id = $1 ORDER BY timestamp
        """
        
        try:
            rows = await self.db.fetch(query, order_id)
            fills = []
            
            for row in rows:
                fill = FillRecord(
                    fill_id=row['fill_id'],
                    order_id=row['order_id'],
                    mt5_deal_id=row['mt5_deal_id'],
                    symbol=row['symbol'],
                    side=row['side'],
                    quantity=row['quantity'],
                    price=float(row['price']),
                    timestamp=row['timestamp'],
                    server_time=row['server_time'],
                    commission=float(row['commission']),
                    swap=float(row['swap']),
                    fees=float(row['fees']),
                    is_partial_fill=row['is_partial_fill'],
                    fill_sequence=row['fill_sequence'],
                    source_data=json.loads(row['source_data']) if row['source_data'] else None
                )
                fills.append(fill)
            
            return fills
            
        except Exception as e:
            self.logger.error(f"Failed to get fills for order {order_id}: {e}")
            raise
    
    # ===================================
    # PNL
    # ===================================
    
    async def save_pnl(self, pnl: PnLRecord) -> str:
        """Salva P&L consolidado"""
        await self.ensure_connection()
        
        query = """
        INSERT INTO trading.pnl (
            pnl_id, decision_id,
            gross_proceeds, gross_cost, realized_pnl,
            commission_total, swap_total, fees_total, slippage_cost,
            net_pnl, net_pnl_pct,
            capital_allocated, return_on_capital, holding_period_minutes,
            is_final, calculation_method,
            calculated_at, position_opened_at, position_closed_at,
            market_conditions, notes
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
        )
        ON CONFLICT (pnl_id) DO UPDATE SET
            gross_proceeds = $3,
            gross_cost = $4,
            realized_pnl = $5,
            commission_total = $6,
            swap_total = $7,
            fees_total = $8,
            slippage_cost = $9,
            net_pnl = $10,
            net_pnl_pct = $11,
            capital_allocated = $12,
            return_on_capital = $13,
            holding_period_minutes = $14,
            is_final = $15,
            calculated_at = $17,
            position_closed_at = $19,
            market_conditions = $20,
            notes = $21
        """
        
        try:
            await self.db.execute(
                query,
                pnl.pnl_id, pnl.decision_id,
                pnl.gross_proceeds, pnl.gross_cost, pnl.realized_pnl,
                pnl.commission_total, pnl.swap_total, pnl.fees_total, pnl.slippage_cost,
                pnl.net_pnl, pnl.net_pnl_pct,
                pnl.capital_allocated, pnl.return_on_capital, pnl.holding_period_minutes,
                pnl.is_final, pnl.calculation_method,
                pnl.calculated_at, pnl.position_opened_at, pnl.position_closed_at,
                json.dumps(pnl.market_conditions) if pnl.market_conditions else None,
                pnl.notes
            )
            
            self.logger.info(f"P&L saved: {pnl.pnl_id} (net: {pnl.net_pnl:.2f})")
            return pnl.pnl_id
            
        except Exception as e:
            self.logger.error(f"Failed to save P&L {pnl.pnl_id}: {e}")
            raise
    
    async def get_pnl_by_decision(self, decision_id: str) -> Optional[PnLRecord]:
        """Obtém P&L por decisão"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.pnl WHERE decision_id = $1 AND is_final = true ORDER BY calculated_at DESC LIMIT 1
        """
        
        try:
            row = await self.db.fetchrow(query, decision_id)
            if not row:
                return None
            
            pnl = PnLRecord(
                pnl_id=row['pnl_id'],
                decision_id=row['decision_id'],
                gross_proceeds=float(row['gross_proceeds']),
                gross_cost=float(row['gross_cost']),
                realized_pnl=float(row['realized_pnl']),
                commission_total=float(row['commission_total']),
                swap_total=float(row['swap_total']),
                fees_total=float(row['fees_total']),
                slippage_cost=float(row['slippage_cost']),
                net_pnl=float(row['net_pnl']),
                net_pnl_pct=float(row['net_pnl_pct']),
                capital_allocated=float(row['capital_allocated']) if row['capital_allocated'] else None,
                return_on_capital=float(row['return_on_capital']) if row['return_on_capital'] else None,
                holding_period_minutes=row['holding_period_minutes'],
                is_final=row['is_final'],
                calculation_method=row['calculation_method'],
                calculated_at=row['calculated_at'],
                position_opened_at=row['position_opened_at'],
                position_closed_at=row['position_closed_at'],
                market_conditions=json.loads(row['market_conditions']) if row['market_conditions'] else None,
                notes=row['notes']
            )
            
            return pnl
            
        except Exception as e:
            self.logger.error(f"Failed to get P&L for decision {decision_id}: {e}")
            raise
    
    # ===================================
    # RELATÓRIOS E VIEWS
    # ===================================
    
    async def get_swap_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """Obtém performance de swaps"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.v_swap_performance 
        WHERE timestamp >= NOW() - INTERVAL '%d days'
        ORDER BY timestamp DESC
        """ % days
        
        try:
            return await self.db.fetch(query)
        except Exception as e:
            self.logger.error(f"Failed to get swap performance: {e}")
            return []
    
    async def get_daily_pnl(self, days: int = 30) -> List[Dict[str, Any]]:
        """Obtém P&L diário"""
        await self.ensure_connection()
        
        query = """
        SELECT * FROM trading.v_daily_pnl 
        WHERE trade_date >= CURRENT_DATE - INTERVAL '%d days'
        ORDER BY trade_date DESC
        """ % days
        
        try:
            return await self.db.fetch(query)
        except Exception as e:
            self.logger.error(f"Failed to get daily P&L: {e}")
            return []
    
    async def get_execution_metrics(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Obtém métricas de execução"""
        await self.ensure_connection()
        
        if symbol:
            query = "SELECT * FROM trading.v_execution_metrics WHERE symbol = $1"
            args = [symbol]
        else:
            query = "SELECT * FROM trading.v_execution_metrics"
            args = []
        
        try:
            return await self.db.fetch(query, *args)
        except Exception as e:
            self.logger.error(f"Failed to get execution metrics: {e}")
            return []
    
    # ===================================
    # INTEGRAÇÃO COM EXECUTION SERVICE
    # ===================================
    
    async def persist_execution_result(self, result: ExecutionResult) -> bool:
        """Persiste resultado completo de execução"""
        try:
            # 1. Atualizar status da decisão
            decision_status = DecisionStatus.COMPLETED if result.status == ExecutionStatus.FILLED else DecisionStatus.FAILED
            await self.update_decision_status(result.decision_id, decision_status, result.error_details)
            
            # 2. Salvar ordens
            if result.sell_order:
                sell_order = self._convert_to_order_record(result.sell_order, result.decision_id)
                await self.save_order(sell_order)
                
                # Salvar fills da venda
                if result.sell_order.status == ExecutionStatus.FILLED:
                    sell_fill = self._create_fill_from_order(result.sell_order)
                    await self.save_fill(sell_fill)
            
            if result.buy_order:
                buy_order = self._convert_to_order_record(result.buy_order, result.decision_id)
                await self.save_order(buy_order)
                
                # Salvar fills da compra
                if result.buy_order.status == ExecutionStatus.FILLED:
                    buy_fill = self._create_fill_from_order(result.buy_order)
                    await self.save_fill(buy_fill)
            
            # 3. Calcular e salvar P&L se execução foi bem-sucedida
            if result.status == ExecutionStatus.FILLED and result.sell_order and result.buy_order:
                pnl = self._calculate_pnl_from_execution(result)
                await self.save_pnl(pnl)
            
            self.logger.info(f"Execution result persisted: {result.execution_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to persist execution result {result.execution_id}: {e}")
            return False
    
    def _convert_to_order_record(self, order_result: OrderResult, decision_id: str) -> OrderRecord:
        """Converte OrderResult para OrderRecord"""
        return OrderRecord(
            order_id=str(uuid.uuid4()),
            decision_id=decision_id,
            client_id=order_result.order_id,
            mt5_order_id=order_result.mt5_order_id,
            symbol=order_result.order_id.split('_')[0] if '_' in order_result.order_id else "UNKNOWN",  # Extrair do order_id
            side="SELL" if "SELL" in order_result.order_id else "BUY",
            quantity=order_result.filled_quantity,
            filled_quantity=order_result.filled_quantity,
            avg_fill_price=order_result.avg_fill_price,
            status=order_result.status.value,
            execution_time_ms=int(order_result.execution_time * 1000) if order_result.execution_time else None,
            error_code=order_result.error_code,
            error_message=order_result.error_message,
            filled_at=datetime.now() if order_result.status == ExecutionStatus.FILLED else None
        )
    
    def _create_fill_from_order(self, order_result: OrderResult) -> FillRecord:
        """Cria FillRecord a partir de OrderResult"""
        return FillRecord(
            fill_id=str(uuid.uuid4()),
            order_id=order_result.order_id,
            mt5_deal_id=order_result.mt5_deal_id,
            symbol=order_result.order_id.split('_')[0] if '_' in order_result.order_id else "UNKNOWN",
            side="SELL" if "SELL" in order_result.order_id else "BUY",
            quantity=order_result.filled_quantity,
            price=order_result.avg_fill_price,
            commission=order_result.commission,
            swap=order_result.swap,
            fees=0.0,  # Calcular se necessário
            timestamp=datetime.now()
        )
    
    def _calculate_pnl_from_execution(self, result: ExecutionResult) -> PnLRecord:
        """Calcula P&L a partir do resultado de execução"""
        sell_proceeds = result.sell_order.filled_quantity * result.sell_order.avg_fill_price
        buy_cost = result.buy_order.filled_quantity * result.buy_order.avg_fill_price
        
        total_commission = result.sell_order.commission + result.buy_order.commission
        total_swap = result.sell_order.swap + result.buy_order.swap
        
        gross_pnl = sell_proceeds - buy_cost
        net_pnl = gross_pnl - total_commission - total_swap
        
        return PnLRecord(
            pnl_id=str(uuid.uuid4()),
            decision_id=result.decision_id,
            gross_proceeds=sell_proceeds,
            gross_cost=buy_cost,
            realized_pnl=gross_pnl,
            commission_total=total_commission,
            swap_total=total_swap,
            fees_total=0.0,
            slippage_cost=result.slippage_pct * buy_cost / 100 if result.slippage_pct else 0.0,
            net_pnl=net_pnl,
            net_pnl_pct=(net_pnl / buy_cost * 100) if buy_cost > 0 else 0.0,
            capital_allocated=buy_cost,
            return_on_capital=(net_pnl / buy_cost * 100) if buy_cost > 0 else 0.0,
            holding_period_minutes=int(result.execution_duration / 60) if result.execution_duration else None,
            is_final=True,
            position_opened_at=datetime.now() - timedelta(minutes=int(result.execution_duration / 60)) if result.execution_duration else None,
            position_closed_at=datetime.now()
        )


# Funções utilitárias para demo
async def demo_trading_repository():
    """Demo do TradingRepository"""
    print("🚀 TRADING REPOSITORY DEMO")
    print("="*60)
    
    # Conectar ao banco
    db = DatabaseConnection()
    repo = TradingRepository(db)
    
    try:
        await repo.ensure_connection()
        print("✅ Database connection established (mock mode)")
        
        # Criar decisão de exemplo
        decision = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            execution_id="exec_demo_001",
            from_symbol="ITSA3",
            to_symbol="ITSA4",
            decision_type="ENTER_LONG_ON",
            current_state="IDLE",
            target_state="LONG_ON",
            premium_pn=0.0055,
            confidence_score=0.75,
            trigger_reason="Premium threshold exceeded",
            expected_profit=150.00,
            status=DecisionStatus.EXECUTING.value
        )
        
        # Salvar decisão
        decision_id = await repo.save_decision(decision)
        print(f"✅ Decision saved: {decision_id}")
        
        # Criar e salvar ordem
        order = OrderRecord(
            order_id=str(uuid.uuid4()),
            decision_id=decision_id,
            client_id="order_demo_001",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.50,
            filled_quantity=1000,
            avg_fill_price=10.52,
            status=OrderStatus.FILLED.value
        )
        
        order_id = await repo.save_order(order)
        print(f"✅ Order saved: {order_id}")
        
        # Criar e salvar fill
        fill = FillRecord(
            fill_id=str(uuid.uuid4()),
            order_id=order_id,
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.52,
            commission=3.15,
            fees=0.32
        )
        
        fill_id = await repo.save_fill(fill)
        print(f"✅ Fill saved: {fill_id}")
        
        # Criar e salvar P&L
        pnl = PnLRecord(
            pnl_id=str(uuid.uuid4()),
            decision_id=decision_id,
            gross_proceeds=10520.00,
            gross_cost=10000.00,
            realized_pnl=520.00,
            commission_total=6.30,
            net_pnl=513.70,
            net_pnl_pct=5.137,
            capital_allocated=10000.00,
            is_final=True
        )
        
        pnl_id = await repo.save_pnl(pnl)
        print(f"✅ P&L saved: {pnl_id}")
        
        # Atualizar status da decisão
        await repo.update_decision_status(decision_id, DecisionStatus.COMPLETED)
        print(f"✅ Decision status updated: COMPLETED")
        
        # Consultar dados
        saved_decision = await repo.get_decision(decision_id)
        if saved_decision:
            print(f"✅ Decision retrieved: {saved_decision.execution_id} ({saved_decision.status})")
        
        orders = await repo.get_orders_by_decision(decision_id)
        print(f"✅ Orders retrieved: {len(orders)}")
        
        fills = await repo.get_fills_by_order(order_id)
        print(f"✅ Fills retrieved: {len(fills)}")
        
        saved_pnl = await repo.get_pnl_by_decision(decision_id)
        if saved_pnl:
            print(f"✅ P&L retrieved: {saved_pnl.net_pnl:.2f} ({saved_pnl.net_pnl_pct:.3f}%)")
        
        # Relatórios
        performance = await repo.get_swap_performance(30)
        print(f"✅ Swap performance: {len(performance)} records")
        
        daily_pnl = await repo.get_daily_pnl(30)
        print(f"✅ Daily P&L: {len(daily_pnl)} records")
        
        metrics = await repo.get_execution_metrics()
        print(f"✅ Execution metrics: {len(metrics)} records")
        
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executar demo
    asyncio.run(demo_trading_repository())