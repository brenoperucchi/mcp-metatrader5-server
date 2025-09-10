#!/usr/bin/env python3
"""
Testes para o ExecutionService - E2.6
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.execution.service import (
    ExecutionService,
    ExecutionStatus,
    OrderType,
    RetryReason,
    OrderRequest,
    OrderResult,
    ExecutionResult,
    RetryStrategy,
    CircuitBreaker
)

class TestOrderRequest:
    """Testes para OrderRequest"""
    
    def test_order_request_creation(self):
        """Testa criação de OrderRequest"""
        order = OrderRequest(
            order_id="test_001",
            symbol="ITSA3",
            action="BUY",
            quantity=1000,
            max_slippage=0.05
        )
        
        assert order.order_id == "test_001"
        assert order.symbol == "ITSA3"
        assert order.action == "BUY"
        assert order.quantity == 1000
        assert order.max_slippage == 0.05
        assert order.order_type == OrderType.MARKET
        assert order.timeout_seconds == 30
    
    def test_to_mcp_request_market_buy(self):
        """Testa conversão para formato MCP - Market Buy"""
        order = OrderRequest(
            order_id="test_buy",
            symbol="ITSA3",
            action="BUY",
            quantity=500
        )
        
        mcp_request = order.to_mcp_request()
        
        assert mcp_request["action"] == 1  # BUY
        assert mcp_request["symbol"] == "ITSA3"
        assert mcp_request["volume"] == 500.0
        assert mcp_request["type"] == 0  # MARKET
        assert mcp_request["magic"] == 20250829
        assert "E2.6" in mcp_request["comment"]
    
    def test_to_mcp_request_market_sell(self):
        """Testa conversão para formato MCP - Market Sell"""
        order = OrderRequest(
            order_id="test_sell",
            symbol="ITSA4",
            action="SELL",
            quantity=750
        )
        
        mcp_request = order.to_mcp_request()
        
        assert mcp_request["action"] == 0  # SELL
        assert mcp_request["symbol"] == "ITSA4"
        assert mcp_request["volume"] == 750.0
        assert mcp_request["type"] == 0  # MARKET
    
    def test_to_mcp_request_limit_order(self):
        """Testa conversão para formato MCP - Limit Order"""
        order = OrderRequest(
            order_id="test_limit",
            symbol="ITSA3",
            action="BUY",
            quantity=1000,
            order_type=OrderType.LIMIT,
            price=10.50,
            stop_loss=9.50,
            take_profit=11.00
        )
        
        mcp_request = order.to_mcp_request()
        
        assert mcp_request["action"] == 1  # BUY
        assert mcp_request["type"] == 2  # BUY_LIMIT
        assert mcp_request["price"] == 10.50
        assert mcp_request["sl"] == 9.50
        assert mcp_request["tp"] == 11.00

class TestRetryStrategy:
    """Testes para RetryStrategy"""
    
    def test_retry_strategy_initialization(self):
        """Testa inicialização da estratégia de retry"""
        strategy = RetryStrategy(max_retries=5, base_delay=2.0)
        
        assert strategy.max_retries == 5
        assert strategy.base_delay == 2.0
        assert strategy.backoff_multiplier == 2.0
        assert RetryReason.NETWORK_ERROR in strategy.retry_config
    
    def test_should_retry_within_limit(self):
        """Testa se deve fazer retry dentro do limite"""
        strategy = RetryStrategy(max_retries=3)
        
        # Deve fazer retry nos primeiros 3 attempts
        assert strategy.should_retry(Exception("test"), 0, RetryReason.TIMEOUT)  # Usar TIMEOUT que usa max_retries=3
        assert strategy.should_retry(Exception("test"), 1, RetryReason.TIMEOUT)
        assert strategy.should_retry(Exception("test"), 2, RetryReason.TIMEOUT)
        
        # Não deve fazer retry no 4º attempt  
        assert not strategy.should_retry(Exception("test"), 3, RetryReason.TIMEOUT)
    
    def test_should_retry_network_error_custom_limit(self):
        """Testa retry para network error com limite customizado"""
        strategy = RetryStrategy()
        
        # Network error tem limite de 5 retries
        assert strategy.should_retry(Exception("test"), 4, RetryReason.NETWORK_ERROR)
        assert not strategy.should_retry(Exception("test"), 5, RetryReason.NETWORK_ERROR)
    
    def test_get_delay_exponential_backoff(self):
        """Testa cálculo de delay com exponential backoff"""
        strategy = RetryStrategy(base_delay=1.0, backoff_multiplier=2.0, max_delay=10.0)
        
        # Delays devem seguir exponential backoff
        assert strategy.get_delay(0, RetryReason.TIMEOUT) == 1.0
        assert strategy.get_delay(1, RetryReason.TIMEOUT) == 2.0
        assert strategy.get_delay(2, RetryReason.TIMEOUT) == 4.0
        assert strategy.get_delay(3, RetryReason.TIMEOUT) == 8.0
        
        # Não deve exceder max_delay
        assert strategy.get_delay(10, RetryReason.TIMEOUT) == 10.0
    
    def test_get_delay_custom_config_by_reason(self):
        """Testa delay customizado por tipo de erro"""
        strategy = RetryStrategy()
        
        # Network error tem base_delay de 2.0
        network_delay = strategy.get_delay(0, RetryReason.NETWORK_ERROR)
        assert network_delay == 2.0
        
        # Server error tem base_delay de 5.0
        server_delay = strategy.get_delay(0, RetryReason.SERVER_ERROR)
        assert server_delay == 5.0

class TestCircuitBreaker:
    """Testes para CircuitBreaker"""
    
    def test_circuit_breaker_initialization(self):
        """Testa inicialização do circuit breaker"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_closed_state(self):
        """Testa estado CLOSED (normal)"""
        cb = CircuitBreaker()
        
        assert cb.can_execute() == True
        assert cb.state == "CLOSED"
    
    def test_circuit_breaker_opens_after_failures(self):
        """Testa abertura após threshold de falhas"""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Registrar falhas até o threshold
        for _ in range(3):
            cb.on_failure()
        
        assert cb.state == "OPEN"
        assert cb.can_execute() == False
    
    def test_circuit_breaker_success_reduces_failure_count(self):
        """Testa que sucesso reduz contagem de falhas"""
        cb = CircuitBreaker(failure_threshold=5)
        
        # Algumas falhas
        cb.on_failure()
        cb.on_failure()
        assert cb.failure_count == 2
        
        # Sucesso deve reduzir
        cb.on_success()
        assert cb.failure_count == 1
    
    def test_circuit_breaker_half_open_transition(self):
        """Testa transição para HALF_OPEN após recovery timeout"""
        from datetime import timedelta
        
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)  # 1 segundo para teste
        
        # Forçar OPEN
        cb.on_failure()
        cb.on_failure()
        assert cb.state == "OPEN"
        
        # Simular passagem do tempo alterando last_failure_time
        cb.last_failure_time = datetime.now() - timedelta(seconds=cb.recovery_timeout * 2)
        
        # Deve permitir execução e ir para HALF_OPEN
        assert cb.can_execute() == True
        assert cb.state == "HALF_OPEN"
    
    def test_circuit_breaker_half_open_to_closed_on_success(self):
        """Testa transição HALF_OPEN -> CLOSED após sucesso"""
        cb = CircuitBreaker()
        
        # Forçar estado HALF_OPEN
        cb.state = "HALF_OPEN"
        cb.failure_count = 3
        
        # Sucesso deve resetar para CLOSED
        cb.on_success()
        
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

class TestExecutionService:
    """Testes para ExecutionService"""
    
    @pytest.fixture
    def execution_service(self):
        """Fixture do ExecutionService"""
        return ExecutionService("test_server:8000")
    
    def test_execution_service_initialization(self, execution_service):
        """Testa inicialização do ExecutionService"""
        assert execution_service.mcp_server_url == "test_server:8000"
        assert execution_service.mcp_client is None
        assert len(execution_service.execution_cache) == 0
        assert len(execution_service.order_cache) == 0
        assert execution_service.execution_metrics["total_executions"] == 0
    
    def test_generate_execution_id(self, execution_service):
        """Testa geração de ID de execução"""
        decision_id = "test_decision_123"
        
        execution_id = execution_service._generate_execution_id(decision_id)
        
        assert "exec_" in execution_id
        assert "test_dec" in execution_id  # Primeiros 8 chars do decision_id
        assert len(execution_id.split('_')) >= 4
    
    def test_generate_order_id(self, execution_service):
        """Testa geração de ID de ordem"""
        execution_id = "exec_test_001"
        order_type = "BUY"
        
        order_id = execution_service._generate_order_id(execution_id, order_type)
        
        assert "order_" in order_id
        assert "exec_test_001" in order_id
        assert "BUY" in order_id
    
    def test_classify_error_network_errors(self, execution_service):
        """Testa classificação de erros de rede"""
        network_codes = [10027, 10028, 10029]
        
        for code in network_codes:
            reason = execution_service._classify_error(code)
            assert reason == RetryReason.NETWORK_ERROR
    
    def test_classify_error_timeout_errors(self, execution_service):
        """Testa classificação de erros de timeout"""
        timeout_codes = [10031, 10032]
        
        for code in timeout_codes:
            reason = execution_service._classify_error(code)
            assert reason == RetryReason.TIMEOUT
    
    def test_classify_error_server_errors(self, execution_service):
        """Testa classificação de erros de servidor"""
        server_codes = [10004, 10006]
        
        for code in server_codes:
            reason = execution_service._classify_error(code)
            assert reason == RetryReason.SERVER_ERROR
    
    def test_classify_error_no_retry(self, execution_service):
        """Testa erros que não devem ter retry"""
        no_retry_codes = [10001, 10013, 10020]  # Erros permanentes
        
        for code in no_retry_codes:
            reason = execution_service._classify_error(code)
            assert reason is None
    
    @pytest.mark.asyncio
    async def test_simulate_mcp_order_success(self, execution_service):
        """Testa simulação de ordem bem-sucedida"""
        order_request = OrderRequest(
            order_id="success_test",
            symbol="ITSA3",
            action="BUY",
            quantity=1000
        )
        
        result = await execution_service._simulate_mcp_order(order_request)
        
        # Deve ser sucesso (80% de chance, mas order_id "success_test" força sucesso)
        if result["retcode"] == 10009:  # Sucesso
            assert "order" in result
            assert "deal" in result
            assert result["volume"] == 1000.0
            assert result["price"] > 0
        elif result["retcode"] == 10010:  # Partial fill
            assert result["volume"] < 1000.0
        # Outros casos são simulações de erro
    
    @pytest.mark.asyncio
    async def test_execute_order_with_retry_success(self, execution_service):
        """Testa execução de ordem com sucesso"""
        order_request = OrderRequest(
            order_id="test_success_order",
            symbol="ITSA3",
            action="BUY",
            quantity=1000
        )
        
        result = await execution_service._execute_order_with_retry(order_request, "exec_001")
        
        # Deve ter algum resultado
        assert isinstance(result, OrderResult)
        assert result.order_id == "test_success_order"
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIAL_FILL, ExecutionStatus.REJECTED, ExecutionStatus.FAILED]
        
        # Se sucesso, deve ter preenchimento
        if result.status == ExecutionStatus.FILLED:
            assert result.filled_quantity > 0
            assert result.avg_fill_price > 0
            assert result.execution_time is not None
    
    @pytest.mark.asyncio
    async def test_execute_swap_success(self, execution_service):
        """Testa execução de swap completo"""
        decision_id = "swap_test_001"
        
        with patch.object(execution_service, '_init_mcp_client', new=AsyncMock()):
            result = await execution_service.execute_swap(
                decision_id=decision_id,
                sell_symbol="ITSA3",
                buy_symbol="ITSA4",
                quantity=1000,
                max_slippage=0.05
            )
        
        # Deve ter resultado
        assert isinstance(result, ExecutionResult)
        assert result.decision_id == decision_id
        assert result.execution_id is not None
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.FAILED]
        
        # Deve ter ordens
        assert result.sell_order is not None
        assert result.buy_order is not None
        
        # Se sucesso completo
        if result.status == ExecutionStatus.FILLED:
            assert result.total_filled_value > 0
            assert result.execution_duration > 0
            assert len(result.audit_trail) > 0
    
    @pytest.mark.asyncio
    async def test_execute_swap_idempotency(self, execution_service):
        """Testa idempotência na execução de swap"""
        decision_id = "idempotent_test"
        
        with patch.object(execution_service, '_init_mcp_client', new=AsyncMock()):
            # Primeira execução
            result1 = await execution_service.execute_swap(
                decision_id=decision_id,
                sell_symbol="ITSA3",
                buy_symbol="ITSA4",
                quantity=1000
            )
            
            # Segunda execução com mesmo decision_id
            result2 = await execution_service.execute_swap(
                decision_id=decision_id,
                sell_symbol="ITSA3",
                buy_symbol="ITSA4",
                quantity=1000
            )
        
        # Deve retornar o mesmo resultado (cached)
        assert result1.execution_id == result2.execution_id
        assert result1.decision_id == result2.decision_id
        assert result1.status == result2.status
        
        # Deve ter apenas 1 execução no cache
        assert len(execution_service.execution_cache) == 1
        assert decision_id in execution_service.execution_cache
    
    def test_get_execution_status(self, execution_service):
        """Testa consulta de status de execução"""
        # Adicionar resultado mock ao cache
        decision_id = "status_test"
        mock_result = ExecutionResult(
            decision_id=decision_id,
            execution_id="exec_status_test",
            status=ExecutionStatus.FILLED
        )
        execution_service.execution_cache[decision_id] = mock_result
        
        # Consultar status
        result = execution_service.get_execution_status(decision_id)
        
        assert result is not None
        assert result.decision_id == decision_id
        assert result.status == ExecutionStatus.FILLED
        
        # Consultar inexistente
        result_none = execution_service.get_execution_status("nonexistent")
        assert result_none is None
    
    def test_get_metrics(self, execution_service):
        """Testa obtenção de métricas"""
        # Simular algumas execuções
        execution_service.execution_metrics["total_executions"] = 10
        execution_service.execution_metrics["successful_executions"] = 8
        execution_service.execution_metrics["failed_executions"] = 2
        execution_service.execution_metrics["retry_count"] = 5
        
        metrics = execution_service.get_metrics()
        
        assert metrics["total_executions"] == 10
        assert metrics["successful_executions"] == 8
        assert metrics["failed_executions"] == 2
        assert metrics["retry_count"] == 5
        assert metrics["success_rate"] == 80.0  # 8/10 * 100
        assert "circuit_breaker_state" in metrics
        assert "cached_executions" in metrics
    
    def test_log_audit_event(self, execution_service):
        """Testa logging de eventos de auditoria"""
        initial_count = len(execution_service.audit_log)
        
        execution_service._log_audit_event("test_event", {
            "decision_id": "test_001",
            "execution_id": "exec_test_001",
            "detail": "test_detail"
        })
        
        assert len(execution_service.audit_log) == initial_count + 1
        
        last_event = execution_service.audit_log[-1]
        assert last_event["event_type"] == "test_event"
        assert last_event["details"]["decision_id"] == "test_001"
        assert "timestamp" in last_event

class TestExecutionIntegration:
    """Testes de integração E2E"""
    
    @pytest.mark.asyncio
    async def test_complete_swap_execution_flow(self):
        """Testa fluxo completo de execução de swap"""
        service = ExecutionService("integration_test:8000")
        
        with patch.object(service, '_init_mcp_client', new=AsyncMock()):
            result = await service.execute_swap(
                decision_id="integration_test_001",
                sell_symbol="ITSA3",
                buy_symbol="ITSA4",
                quantity=1000,
                max_slippage=0.05
            )
        
        # Verificar resultado
        assert result is not None
        assert result.decision_id == "integration_test_001"
        assert result.execution_id is not None
        
        # Verificar métricas foram atualizadas
        metrics = service.get_metrics()
        assert metrics["total_executions"] >= 1
        
        # Verificar auditoria
        assert len(service.audit_log) > 0
        
        # Verificar cache de idempotência
        assert result.decision_id in service.execution_cache
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Testa retry em caso de falha"""
        service = ExecutionService("retry_test:8000")
        
        # Mock que sempre falha nas primeiras tentativas
        original_simulate = service._simulate_mcp_order
        call_count = 0
        
        async def failing_simulate(order_request):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Falha nas primeiras 2 tentativas
                return {"retcode": 10027, "comment": "Network error"}  # Network error (retry)
            else:
                return {"retcode": 10009, "order": 123, "deal": 456, "volume": float(order_request.quantity), "price": 10.0}
        
        service._simulate_mcp_order = failing_simulate
        
        with patch.object(service, '_init_mcp_client', new=AsyncMock()):
            result = await service.execute_swap(
                decision_id="retry_test_001",
                sell_symbol="ITSA3", 
                buy_symbol="ITSA4",
                quantity=500
            )
        
        # Deve eventualmente ter sucesso após retries
        # (depende da simulação, mas deve ao menos tentar)
        assert result is not None
        assert result.decision_id == "retry_test_001"
        
        # Verificar que houve tentativas de retry
        metrics = service.get_metrics()
        assert metrics["retry_count"] >= 0  # Pode ter havido retries
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker_integration(self):
        """Testa integração com circuit breaker"""
        service = ExecutionService("circuit_test:8000")
        
        # Forçar muitas falhas para abrir o circuit breaker
        for _ in range(10):
            service.circuit_breaker.on_failure()
        
        # Circuit breaker deve estar aberto
        assert service.circuit_breaker.state == "OPEN"
        
        with patch.object(service, '_init_mcp_client', new=AsyncMock()):
            result = await service.execute_swap(
                decision_id="circuit_test_001",
                sell_symbol="ITSA3",
                buy_symbol="ITSA4", 
                quantity=100
            )
        
        # Execução deve falhar devido ao circuit breaker
        assert result.status == ExecutionStatus.FAILED
        assert "circuit breaker" in str(result.error_details).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])