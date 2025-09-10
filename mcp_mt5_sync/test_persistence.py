#!/usr/bin/env python3
"""
E2.7 - Testes de Persistência
Testes para TradingRepository e persistência de dados
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.trading_repository import (
    TradingRepository,
    DatabaseConnection,
    DecisionRecord,
    OrderRecord,
    FillRecord,
    PnLRecord,
    DecisionStatus,
    OrderStatus
)
from src.execution.service import ExecutionResult, ExecutionStatus, OrderResult

class TestDatabaseConnection:
    """Testes para DatabaseConnection"""
    
    def test_database_connection_init(self):
        """Testa inicialização da conexão"""
        db = DatabaseConnection("postgresql://test:test@localhost:5432/test_db")
        
        assert db.connection_string == "postgresql://test:test@localhost:5432/test_db"
        assert db.pool is None
        assert not db._connected
    
    def test_default_connection_string(self):
        """Testa string de conexão padrão"""
        db = DatabaseConnection()
        
        assert "postgresql://" in db.connection_string
        assert "trading_dev" in db.connection_string
    
    @pytest.mark.asyncio
    async def test_mock_connection_operations(self):
        """Testa operações mock quando asyncpg não está disponível"""
        db = DatabaseConnection()
        
        # Mock operations should work without asyncpg
        result = await db.execute("SELECT 1")
        assert result == "OK"
        
        rows = await db.fetch("SELECT * FROM test")
        assert rows == []
        
        row = await db.fetchrow("SELECT * FROM test LIMIT 1")
        assert row is None

class TestDecisionRecord:
    """Testes para DecisionRecord"""
    
    def test_decision_record_creation(self):
        """Testa criação de DecisionRecord"""
        decision = DecisionRecord(
            decision_id="decision_test_001",
            execution_id="exec_test_001",
            from_symbol="ITSA3",
            to_symbol="ITSA4",
            decision_type="ENTER_LONG_ON",
            current_state="IDLE",
            target_state="LONG_ON"
        )
        
        assert decision.decision_id == "decision_test_001"
        assert decision.execution_id == "exec_test_001"
        assert decision.from_symbol == "ITSA3"
        assert decision.to_symbol == "ITSA4"
        assert decision.decision_type == "ENTER_LONG_ON"
        assert decision.status == DecisionStatus.PENDING.value
        assert isinstance(decision.timestamp, datetime)
        assert isinstance(decision.created_at, datetime)
    
    def test_decision_record_with_metrics(self):
        """Testa DecisionRecord com métricas completas"""
        decision = DecisionRecord(
            decision_id="decision_metrics_001",
            execution_id="exec_metrics_001",
            from_symbol="ITSA3",
            to_symbol="ITSA4",
            decision_type="SWAP_TO_PN",
            current_state="LONG_ON",
            target_state="LONG_PN",
            premium_pn=0.0055,
            confidence_score=0.75,
            expected_profit=250.00,
            expected_return_pct=2.5,
            take_profit=300.00,
            stop_loss=-100.00,
            max_slippage=0.05
        )
        
        assert decision.premium_pn == 0.0055
        assert decision.confidence_score == 0.75
        assert decision.expected_profit == 250.00
        assert decision.expected_return_pct == 2.5
        assert decision.take_profit == 300.00
        assert decision.stop_loss == -100.00
        assert decision.max_slippage == 0.05

class TestOrderRecord:
    """Testes para OrderRecord"""
    
    def test_order_record_creation(self):
        """Testa criação de OrderRecord"""
        order = OrderRecord(
            order_id="order_test_001",
            decision_id="decision_test_001",
            client_id="client_test_001",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.50
        )
        
        assert order.order_id == "order_test_001"
        assert order.decision_id == "decision_test_001"
        assert order.client_id == "client_test_001"
        assert order.symbol == "ITSA3"
        assert order.side == "BUY"
        assert order.quantity == 1000
        assert order.price == 10.50
        assert order.status == OrderStatus.PENDING.value
        assert order.remaining_quantity == 1000  # Inicializa com quantity
        assert order.magic_number == 20250829
    
    def test_order_record_execution_details(self):
        """Testa OrderRecord com detalhes de execução"""
        order = OrderRecord(
            order_id="order_exec_001",
            decision_id="decision_exec_001",
            symbol="ITSA4",
            side="SELL",
            quantity=500,
            filled_quantity=450,
            avg_fill_price=10.75,
            status=OrderStatus.PARTIAL_FILL.value,
            slippage_pct=0.025,
            execution_time_ms=150,
            retry_count=2
        )
        
        assert order.filled_quantity == 450
        assert order.avg_fill_price == 10.75
        assert order.status == OrderStatus.PARTIAL_FILL.value
        assert order.slippage_pct == 0.025
        assert order.execution_time_ms == 150
        assert order.retry_count == 2

class TestFillRecord:
    """Testes para FillRecord"""
    
    def test_fill_record_creation(self):
        """Testa criação de FillRecord"""
        fill = FillRecord(
            fill_id="fill_test_001",
            order_id="order_test_001",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.52,
            commission=3.16,
            fees=0.32
        )
        
        assert fill.fill_id == "fill_test_001"
        assert fill.order_id == "order_test_001"
        assert fill.symbol == "ITSA3"
        assert fill.side == "BUY"
        assert fill.quantity == 1000
        assert fill.price == 10.52
        assert fill.commission == 3.16
        assert fill.fees == 0.32
        assert isinstance(fill.timestamp, datetime)
        assert fill.fill_sequence == 1
        assert not fill.is_partial_fill
    
    def test_fill_record_partial(self):
        """Testa FillRecord parcial"""
        fill = FillRecord(
            fill_id="fill_partial_001",
            order_id="order_partial_001",
            mt5_deal_id=123456,
            symbol="ITSA4",
            side="SELL",
            quantity=250,
            price=10.80,
            commission=1.58,
            swap=-0.05,
            is_partial_fill=True,
            fill_sequence=2
        )
        
        assert fill.mt5_deal_id == 123456
        assert fill.quantity == 250
        assert fill.swap == -0.05
        assert fill.is_partial_fill
        assert fill.fill_sequence == 2

class TestPnLRecord:
    """Testes para PnLRecord"""
    
    def test_pnl_record_creation(self):
        """Testa criação de PnLRecord"""
        pnl = PnLRecord(
            pnl_id="pnl_test_001",
            decision_id="decision_test_001",
            gross_proceeds=10520.00,
            gross_cost=10000.00,
            realized_pnl=520.00,
            commission_total=6.30,
            net_pnl=513.70,
            net_pnl_pct=5.137,
            capital_allocated=10000.00
        )
        
        assert pnl.pnl_id == "pnl_test_001"
        assert pnl.decision_id == "decision_test_001"
        assert pnl.gross_proceeds == 10520.00
        assert pnl.gross_cost == 10000.00
        assert pnl.realized_pnl == 520.00
        assert pnl.commission_total == 6.30
        assert pnl.net_pnl == 513.70
        assert pnl.net_pnl_pct == 5.137
        assert pnl.capital_allocated == 10000.00
        assert not pnl.is_final
        assert pnl.calculation_method == "fifo"
    
    def test_pnl_record_with_performance_metrics(self):
        """Testa PnLRecord com métricas de performance"""
        pnl = PnLRecord(
            pnl_id="pnl_perf_001",
            decision_id="decision_perf_001",
            net_pnl=750.00,
            capital_allocated=15000.00,
            return_on_capital=5.0,
            holding_period_minutes=45,
            is_final=True,
            position_opened_at=datetime.now() - timedelta(minutes=45),
            position_closed_at=datetime.now()
        )
        
        assert pnl.return_on_capital == 5.0
        assert pnl.holding_period_minutes == 45
        assert pnl.is_final
        assert isinstance(pnl.position_opened_at, datetime)
        assert isinstance(pnl.position_closed_at, datetime)

class TestTradingRepository:
    """Testes para TradingRepository"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database connection"""
        db = MagicMock(spec=DatabaseConnection)
        db._connected = True
        db.execute = AsyncMock(return_value="OK")
        db.fetch = AsyncMock(return_value=[])
        db.fetchrow = AsyncMock(return_value=None)
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Repository com mock database"""
        return TradingRepository(mock_db)
    
    @pytest.mark.asyncio
    async def test_ensure_connection(self, repository, mock_db):
        """Testa garantia de conexão"""
        mock_db._connected = False
        mock_db.connect = AsyncMock()
        
        await repository.ensure_connection()
        
        mock_db.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_decision(self, repository, mock_db):
        """Testa salvamento de decisão"""
        decision = DecisionRecord(
            decision_id="test_decision_001",
            execution_id="test_exec_001",
            from_symbol="ITSA3",
            to_symbol="ITSA4",
            decision_type="ENTER_LONG_ON",
            current_state="IDLE",
            target_state="LONG_ON"
        )
        
        result = await repository.save_decision(decision)
        
        assert result == "test_decision_001"
        mock_db.execute.assert_called_once()
        
        # Verificar que os argumentos da query estão corretos
        call_args = mock_db.execute.call_args
        assert "test_decision_001" in call_args[0]
        assert "test_exec_001" in call_args[0]
        assert "ITSA3" in call_args[0]
        assert "ITSA4" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_decision_not_found(self, repository, mock_db):
        """Testa busca de decisão não encontrada"""
        mock_db.fetchrow.return_value = None
        
        result = await repository.get_decision("nonexistent_decision")
        
        assert result is None
        mock_db.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_decision_found(self, repository, mock_db):
        """Testa busca de decisão encontrada"""
        mock_row = {
            'decision_id': 'found_decision_001',
            'execution_id': 'found_exec_001',
            'strategy_id': 'itsa_arbitrage',
            'timestamp': datetime.now(),
            'from_symbol': 'ITSA3',
            'to_symbol': 'ITSA4',
            'trigger_reason': 'Premium exceeded',
            'decision_type': 'ENTER_LONG_ON',
            'current_state': 'IDLE',
            'target_state': 'LONG_ON',
            'position_quantity': 1000,
            'position_entry_price': None,
            'premium_pn': 0.0055,
            'spread_cost': 0.002,
            'net_opportunity': 0.0035,
            'confidence_score': 0.75,
            'expected_profit': 150.0,
            'expected_return_pct': 1.5,
            'take_profit': None,
            'stop_loss': None,
            'max_slippage': 0.05,
            'status': 'pending',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'completed_at': None,
            'audit_data': None,
            'error_details': None
        }
        mock_db.fetchrow.return_value = mock_row
        
        result = await repository.get_decision("found_decision_001")
        
        assert result is not None
        assert result.decision_id == "found_decision_001"
        assert result.execution_id == "found_exec_001"
        assert result.from_symbol == "ITSA3"
        assert result.to_symbol == "ITSA4"
        assert result.premium_pn == 0.0055
        assert result.confidence_score == 0.75
    
    @pytest.mark.asyncio
    async def test_update_decision_status(self, repository, mock_db):
        """Testa atualização de status da decisão"""
        result = await repository.update_decision_status(
            "test_decision_001", 
            DecisionStatus.COMPLETED,
            {"reason": "Trade completed successfully"}
        )
        
        assert result is True
        mock_db.execute.assert_called_once()
        
        # Verificar argumentos
        call_args = mock_db.execute.call_args
        assert "test_decision_001" in call_args[0]
        assert "completed" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_save_order(self, repository, mock_db):
        """Testa salvamento de ordem"""
        order = OrderRecord(
            order_id="test_order_001",
            decision_id="test_decision_001",
            client_id="client_001",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.50
        )
        
        result = await repository.save_order(order)
        
        assert result == "test_order_001"
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_orders_by_decision(self, repository, mock_db):
        """Testa busca de ordens por decisão"""
        mock_orders = [
            {
                'order_id': 'order_001',
                'decision_id': 'decision_001',
                'client_id': 'client_001',
                'mt5_order_id': None,
                'magic_number': 20250829,
                'symbol': 'ITSA3',
                'side': 'BUY',
                'order_type': 'MARKET',
                'quantity': 1000,
                'price': 10.50,
                'stop_loss': None,
                'take_profit': None,
                'filled_quantity': 1000,
                'remaining_quantity': 0,
                'avg_fill_price': 10.52,
                'status': 'filled',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'submitted_at': None,
                'filled_at': datetime.now(),
                'cancelled_at': None,
                'slippage_pct': 0.019,
                'execution_time_ms': 150,
                'retry_count': 0,
                'error_code': None,
                'error_message': None,
                'audit_trail': None
            }
        ]
        mock_db.fetch.return_value = mock_orders
        
        result = await repository.get_orders_by_decision("decision_001")
        
        assert len(result) == 1
        assert result[0].order_id == "order_001"
        assert result[0].symbol == "ITSA3"
        assert result[0].side == "BUY"
        assert result[0].filled_quantity == 1000
    
    @pytest.mark.asyncio
    async def test_save_fill(self, repository, mock_db):
        """Testa salvamento de fill"""
        fill = FillRecord(
            fill_id="test_fill_001",
            order_id="test_order_001",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            price=10.52,
            commission=3.16
        )
        
        result = await repository.save_fill(fill)
        
        assert result == "test_fill_001"
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fills_by_order(self, repository, mock_db):
        """Testa busca de fills por ordem"""
        mock_fills = [
            {
                'fill_id': 'fill_001',
                'order_id': 'order_001',
                'mt5_deal_id': 123456,
                'symbol': 'ITSA3',
                'side': 'BUY',
                'quantity': 1000,
                'price': 10.52,
                'timestamp': datetime.now(),
                'server_time': None,
                'commission': 3.16,
                'swap': -0.02,
                'fees': 0.32,
                'is_partial_fill': False,
                'fill_sequence': 1,
                'source_data': None
            }
        ]
        mock_db.fetch.return_value = mock_fills
        
        result = await repository.get_fills_by_order("order_001")
        
        assert len(result) == 1
        assert result[0].fill_id == "fill_001"
        assert result[0].quantity == 1000
        assert result[0].price == 10.52
        assert result[0].commission == 3.16
    
    @pytest.mark.asyncio
    async def test_save_pnl(self, repository, mock_db):
        """Testa salvamento de P&L"""
        pnl = PnLRecord(
            pnl_id="test_pnl_001",
            decision_id="test_decision_001",
            gross_proceeds=10520.00,
            gross_cost=10000.00,
            realized_pnl=520.00,
            commission_total=6.30,
            net_pnl=513.70
        )
        
        result = await repository.save_pnl(pnl)
        
        assert result == "test_pnl_001"
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_pnl_by_decision(self, repository, mock_db):
        """Testa busca de P&L por decisão"""
        mock_pnl = {
            'pnl_id': 'pnl_001',
            'decision_id': 'decision_001',
            'gross_proceeds': 10520.00,
            'gross_cost': 10000.00,
            'realized_pnl': 520.00,
            'commission_total': 6.30,
            'swap_total': -0.10,
            'fees_total': 0.64,
            'slippage_cost': 2.00,
            'net_pnl': 511.16,
            'net_pnl_pct': 5.11,
            'capital_allocated': 10000.00,
            'return_on_capital': 5.11,
            'holding_period_minutes': 30,
            'is_final': True,
            'calculation_method': 'fifo',
            'calculated_at': datetime.now(),
            'position_opened_at': datetime.now() - timedelta(minutes=30),
            'position_closed_at': datetime.now(),
            'market_conditions': None,
            'notes': None
        }
        mock_db.fetchrow.return_value = mock_pnl
        
        result = await repository.get_pnl_by_decision("decision_001")
        
        assert result is not None
        assert result.pnl_id == "pnl_001"
        assert result.net_pnl == 511.16
        assert result.net_pnl_pct == 5.11
        assert result.is_final
    
    @pytest.mark.asyncio
    async def test_get_reports(self, repository, mock_db):
        """Testa obtenção de relatórios"""
        # Mock data for reports
        mock_performance = [
            {
                'decision_id': 'dec_001',
                'execution_id': 'exec_001',
                'timestamp': datetime.now(),
                'from_symbol': 'ITSA3',
                'to_symbol': 'ITSA4',
                'net_pnl': 150.00,
                'win_rate_pct': 75.0
            }
        ]
        
        mock_daily_pnl = [
            {
                'trade_date': datetime.now().date(),
                'total_swaps': 5,
                'profitable_swaps': 4,
                'total_net_pnl': 750.00,
                'win_rate_pct': 80.0
            }
        ]
        
        mock_metrics = [
            {
                'symbol': 'ITSA3',
                'side': 'BUY',
                'success_rate_pct': 95.0,
                'avg_execution_time_ms': 125
            }
        ]
        
        # Test swap performance
        mock_db.fetch.return_value = mock_performance
        performance = await repository.get_swap_performance(30)
        assert len(performance) == 1
        
        # Test daily P&L
        mock_db.fetch.return_value = mock_daily_pnl
        daily_pnl = await repository.get_daily_pnl(30)
        assert len(daily_pnl) == 1
        
        # Test execution metrics
        mock_db.fetch.return_value = mock_metrics
        metrics = await repository.get_execution_metrics()
        assert len(metrics) == 1

class TestExecutionIntegration:
    """Testes de integração com ExecutionService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database connection"""
        db = MagicMock(spec=DatabaseConnection)
        db._connected = True
        db.execute = AsyncMock(return_value="OK")
        db.fetch = AsyncMock(return_value=[])
        db.fetchrow = AsyncMock(return_value=None)
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Repository com mock database"""
        return TradingRepository(mock_db)
    
    @pytest.fixture
    def sample_execution_result(self):
        """ExecutionResult de exemplo"""
        sell_order = OrderResult(
            order_id="sell_order_001",
            status=ExecutionStatus.FILLED,
            filled_quantity=1000,
            avg_fill_price=10.52,
            total_cost=10520.00,
            commission=3.16,
            swap=-0.01,
            mt5_order_id=123456,
            mt5_deal_id=654321,
            execution_time=0.150
        )
        
        buy_order = OrderResult(
            order_id="buy_order_001",
            status=ExecutionStatus.FILLED,
            filled_quantity=950,
            avg_fill_price=10.58,
            total_cost=10051.00,
            commission=3.02,
            swap=-0.02,
            mt5_order_id=123457,
            mt5_deal_id=654322,
            execution_time=0.125
        )
        
        return ExecutionResult(
            decision_id="integration_decision_001",
            execution_id="integration_exec_001",
            status=ExecutionStatus.FILLED,
            sell_order=sell_order,
            buy_order=buy_order,
            total_filled_value=20571.00,
            total_commission=6.18,
            net_proceeds=462.82,
            slippage_pct=0.025,
            execution_duration=1.5,
            retry_count=1
        )
    
    @pytest.mark.asyncio
    async def test_persist_execution_result(self, repository, mock_db, sample_execution_result):
        """Testa persistência completa de resultado de execução"""
        result = await repository.persist_execution_result(sample_execution_result)
        
        assert result is True
        
        # Verificar que múltiplas chamadas foram feitas
        assert mock_db.execute.call_count >= 3  # decision update, orders, fills, pnl
    
    @pytest.mark.asyncio
    async def test_convert_to_order_record(self, repository):
        """Testa conversão de OrderResult para OrderRecord"""
        order_result = OrderResult(
            order_id="SELL_test_order_001",
            status=ExecutionStatus.FILLED,
            filled_quantity=1000,
            avg_fill_price=10.52,
            commission=3.16,
            mt5_order_id=123456,
            execution_time=0.150
        )
        
        order_record = repository._convert_to_order_record(order_result, "test_decision_001")
        
        assert order_record.decision_id == "test_decision_001"
        assert order_record.client_id == "SELL_test_order_001"
        assert order_record.side == "SELL"
        assert order_record.filled_quantity == 1000
        assert order_record.avg_fill_price == 10.52
        assert order_record.mt5_order_id == 123456
        assert order_record.status == ExecutionStatus.FILLED.value
    
    @pytest.mark.asyncio
    async def test_create_fill_from_order(self, repository):
        """Testa criação de FillRecord a partir de OrderResult"""
        order_result = OrderResult(
            order_id="BUY_test_order_001",
            status=ExecutionStatus.FILLED,
            filled_quantity=1000,
            avg_fill_price=10.52,
            commission=3.16,
            swap=-0.02,
            mt5_deal_id=654321
        )
        
        fill_record = repository._create_fill_from_order(order_result)
        
        assert fill_record.order_id == "BUY_test_order_001"
        assert fill_record.side == "BUY"
        assert fill_record.quantity == 1000
        assert fill_record.price == 10.52
        assert fill_record.commission == 3.16
        assert fill_record.swap == -0.02
        assert fill_record.mt5_deal_id == 654321
    
    @pytest.mark.asyncio
    async def test_calculate_pnl_from_execution(self, repository, sample_execution_result):
        """Testa cálculo de P&L a partir de ExecutionResult"""
        pnl_record = repository._calculate_pnl_from_execution(sample_execution_result)
        
        assert pnl_record.decision_id == "integration_decision_001"
        
        # Verificar cálculos
        expected_proceeds = 1000 * 10.52  # 10520.00
        expected_cost = 950 * 10.58      # 10051.00
        expected_gross_pnl = expected_proceeds - expected_cost  # 469.00
        expected_commission = 3.16 + 3.02  # 6.18
        expected_swap = -0.01 + (-0.02)    # -0.03
        expected_net_pnl = expected_gross_pnl - expected_commission - expected_swap  # ~462.85
        
        assert abs(pnl_record.gross_proceeds - expected_proceeds) < 0.01
        assert abs(pnl_record.gross_cost - expected_cost) < 0.01
        assert abs(pnl_record.realized_pnl - expected_gross_pnl) < 0.01
        assert abs(pnl_record.commission_total - expected_commission) < 0.01
        assert abs(pnl_record.swap_total - expected_swap) < 0.01
        assert pnl_record.is_final
        assert pnl_record.capital_allocated == expected_cost


class TestDataIntegrity:
    """Testes de integridade de dados"""
    
    def test_decision_record_constraints(self):
        """Testa constraints dos records"""
        # Test valid decision
        decision = DecisionRecord(
            decision_id="valid_decision",
            execution_id="valid_exec",
            from_symbol="ITSA3",
            to_symbol="ITSA4",
            decision_type="ENTER_LONG_ON",
            current_state="IDLE",
            target_state="LONG_ON",
            confidence_score=0.75
        )
        
        assert decision.confidence_score == 0.75
        
        # Test confidence score boundaries
        decision.confidence_score = 0.0
        assert decision.confidence_score == 0.0
        
        decision.confidence_score = 1.0
        assert decision.confidence_score == 1.0
    
    def test_order_record_constraints(self):
        """Testa constraints de ordem"""
        order = OrderRecord(
            order_id="test_order",
            decision_id="test_decision",
            symbol="ITSA3",
            side="BUY",
            quantity=1000,
            filled_quantity=800
        )
        
        # Filled quantity deve ser <= quantity
        assert order.filled_quantity <= order.quantity
        
        # Remaining quantity deve ser quantity - filled_quantity
        order.remaining_quantity = order.quantity - order.filled_quantity
        assert order.remaining_quantity == 200
    
    def test_pnl_calculations(self):
        """Testa cálculos de P&L"""
        pnl = PnLRecord(
            pnl_id="test_pnl",
            decision_id="test_decision",
            gross_proceeds=10520.00,
            gross_cost=10000.00,
            commission_total=6.30,
            fees_total=0.64
        )
        
        # Calculate realized P&L
        pnl.realized_pnl = pnl.gross_proceeds - pnl.gross_cost
        assert pnl.realized_pnl == 520.00
        
        # Calculate net P&L
        pnl.net_pnl = pnl.realized_pnl - pnl.commission_total - pnl.fees_total
        assert abs(pnl.net_pnl - 513.06) < 0.01
        
        # Calculate percentage
        if pnl.gross_cost > 0:
            pnl.net_pnl_pct = (pnl.net_pnl / pnl.gross_cost) * 100
            assert abs(pnl.net_pnl_pct - 5.1306) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])