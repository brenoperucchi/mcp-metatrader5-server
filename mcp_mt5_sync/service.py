#!/usr/bin/env python3
"""
E2.6 - ExecutionService
Serviço de execução de ordens com idempotência, retry e auditoria completa
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import sys
import os

# Adicionar paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.etapa2.swap_decision_client import SwapDecisionType

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Status de execução de ordem"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"
    TIMEOUT = "timeout"

class OrderType(Enum):
    """Tipo de ordem"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class RetryReason(Enum):
    """Razões para retry"""
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    TEMPORARY_REJECT = "temporary_reject"

@dataclass
class OrderRequest:
    """Requisição de ordem"""
    order_id: str
    symbol: str
    action: str  # "BUY" ou "SELL"
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_slippage: float = 0.05  # 0.05%
    timeout_seconds: int = 30
    
    def to_mcp_request(self) -> Dict[str, Any]:
        """Converte para formato MCP"""
        request = {
            "action": 1 if self.action == "BUY" else 0,  # MT5 format
            "symbol": self.symbol,
            "volume": float(self.quantity),
            "type": 0,  # MARKET order
            "magic": 20250829,  # Magic number para identificação
            "comment": f"E2.6-{self.order_id[:8]}",
            "type_time": 0,  # Good Till Cancel
            "type_filling": 0,  # Fill or Kill
        }
        
        if self.order_type == OrderType.LIMIT and self.price:
            request["type"] = 2 if self.action == "BUY" else 3  # BUY_LIMIT/SELL_LIMIT
            request["price"] = self.price
        
        if self.stop_loss:
            request["sl"] = self.stop_loss
            
        if self.take_profit:
            request["tp"] = self.take_profit
            
        return request

@dataclass
class OrderResult:
    """Resultado de ordem executada"""
    order_id: str
    status: ExecutionStatus
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    total_cost: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    mt5_order_id: Optional[int] = None
    mt5_deal_id: Optional[int] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamps: Dict[str, datetime] = field(default_factory=dict)

@dataclass 
class ExecutionResult:
    """Resultado completo da execução do swap"""
    decision_id: str
    execution_id: str
    status: ExecutionStatus
    sell_order: Optional[OrderResult] = None
    buy_order: Optional[OrderResult] = None
    total_filled_value: float = 0.0
    total_commission: float = 0.0
    net_proceeds: float = 0.0
    slippage_pct: float = 0.0
    execution_duration: float = 0.0
    retry_count: int = 0
    error_details: Optional[Dict[str, Any]] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class RetryStrategy:
    """Estratégia de retry com exponential backoff"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_multiplier: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        
        # Configurações por tipo de erro
        self.retry_config = {
            RetryReason.NETWORK_ERROR: {"max_retries": 5, "base_delay": 2.0},
            RetryReason.TIMEOUT: {"max_retries": 3, "base_delay": 1.0},
            RetryReason.SERVER_ERROR: {"max_retries": 3, "base_delay": 5.0},
            RetryReason.TEMPORARY_REJECT: {"max_retries": 2, "base_delay": 3.0}
        }
    
    def should_retry(self, error: Exception, attempt: int, reason: RetryReason) -> bool:
        """Determina se deve fazer retry"""
        config = self.retry_config.get(reason, {"max_retries": self.max_retries})
        return attempt < config["max_retries"]
    
    def get_delay(self, attempt: int, reason: RetryReason) -> float:
        """Calcula delay para próximo retry"""
        config = self.retry_config.get(reason, {"base_delay": self.base_delay})
        delay = config["base_delay"] * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)

class CircuitBreaker:
    """Circuit breaker para falhas sistêmicas"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 300,  # 5 minutes
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Verifica se pode executar chamada"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def on_success(self):
        """Registra sucesso"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker reset to CLOSED")
        self.failure_count = max(0, self.failure_count - 1)
    
    def on_failure(self):
        """Registra falha"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == "HALF_OPEN":
            self.half_open_calls += 1
        
        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")

class ExecutionService:
    """Serviço de execução de ordens com idempotência e retry"""
    
    def __init__(self, mcp_server_url: str = "192.168.0.125:8000"):
        self.mcp_server_url = mcp_server_url
        self.mcp_client = None  # Será inicializado quando necessário
        
        # Controle de idempotência
        self.execution_cache: Dict[str, ExecutionResult] = {}
        self.order_cache: Dict[str, OrderResult] = {}
        
        # Estratégia de retry e circuit breaker
        self.retry_strategy = RetryStrategy()
        self.circuit_breaker = CircuitBreaker()
        
        # Métricas e auditoria
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "retry_count": 0,
            "circuit_breaker_trips": 0
        }
        
        self.audit_log: List[Dict[str, Any]] = []
        
        logger.info(f"ExecutionService initialized with MCP server: {mcp_server_url}")
    
    async def _init_mcp_client(self):
        """Inicializa cliente MCP se necessário"""
        if self.mcp_client is None:
            try:
                # Import aqui para evitar circular dependency
                from src.connectors.mcp_client import McpClient
                self.mcp_client = McpClient(self.mcp_server_url)
                await self.mcp_client.connect()
                logger.info("MCP client initialized successfully")
            except ImportError:
                # Para demo, usar cliente simulado
                logger.info("Using simulated MCP client for demo")
                self.mcp_client = "simulated"
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _generate_execution_id(self, decision_id: str) -> str:
        """Gera ID único para execução"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"exec_{decision_id[:8]}_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    def _generate_order_id(self, execution_id: str, order_type: str) -> str:
        """Gera ID único para ordem"""
        return f"order_{execution_id}_{order_type}_{uuid.uuid4().hex[:6]}"
    
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Registra evento de auditoria"""
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        self.audit_log.append(audit_event)
        logger.info(f"Audit event: {event_type}", extra=details)
    
    async def _execute_order_with_retry(self, 
                                      order_request: OrderRequest,
                                      execution_id: str) -> OrderResult:
        """Executa ordem com retry logic"""
        order_result = OrderResult(
            order_id=order_request.order_id,
            status=ExecutionStatus.PENDING
        )
        
        attempt = 0
        last_error = None
        
        while attempt <= self.retry_strategy.max_retries:
            if not self.circuit_breaker.can_execute():
                order_result.status = ExecutionStatus.FAILED
                order_result.error_message = "Circuit breaker is OPEN"
                self._log_audit_event("order_circuit_breaker", {
                    "order_id": order_request.order_id,
                    "execution_id": execution_id,
                    "circuit_breaker_state": self.circuit_breaker.state
                })
                break
            
            try:
                self._log_audit_event("order_attempt", {
                    "order_id": order_request.order_id,
                    "execution_id": execution_id,
                    "attempt": attempt + 1,
                    "symbol": order_request.symbol,
                    "action": order_request.action,
                    "quantity": order_request.quantity
                })
                
                # Executar ordem via MCP
                start_time = time.time()
                order_result.timestamps["submit"] = datetime.now()
                
                # Simulated execution para demo (substitua pela chamada MCP real)
                mcp_result = await self._simulate_mcp_order(order_request)
                
                execution_time = time.time() - start_time
                order_result.execution_time = execution_time
                order_result.timestamps["complete"] = datetime.now()
                
                # Processar resultado
                if mcp_result.get("retcode") == 10009:  # TRADE_RETCODE_DONE
                    order_result.status = ExecutionStatus.FILLED
                    order_result.filled_quantity = order_request.quantity
                    order_result.avg_fill_price = mcp_result.get("price", 0.0)
                    order_result.total_cost = order_result.filled_quantity * order_result.avg_fill_price
                    order_result.mt5_order_id = mcp_result.get("order", 0)
                    order_result.mt5_deal_id = mcp_result.get("deal", 0)
                    
                    self.circuit_breaker.on_success()
                    
                    self._log_audit_event("order_success", {
                        "order_id": order_request.order_id,
                        "execution_id": execution_id,
                        "filled_quantity": order_result.filled_quantity,
                        "avg_price": order_result.avg_fill_price,
                        "execution_time": execution_time,
                        "mt5_order_id": order_result.mt5_order_id
                    })
                    
                    break
                    
                elif mcp_result.get("retcode") == 10010:  # TRADE_RETCODE_DONE_PARTIAL
                    order_result.status = ExecutionStatus.PARTIAL_FILL
                    order_result.filled_quantity = int(mcp_result.get("volume", 0))
                    order_result.avg_fill_price = mcp_result.get("price", 0.0)
                    
                    self._log_audit_event("order_partial_fill", {
                        "order_id": order_request.order_id,
                        "execution_id": execution_id,
                        "requested": order_request.quantity,
                        "filled": order_result.filled_quantity,
                        "remaining": order_request.quantity - order_result.filled_quantity
                    })
                    
                    # Decidir se continua com partial fill ou cancela
                    if order_result.filled_quantity >= order_request.quantity * 0.8:  # 80% preenchido
                        break
                    else:
                        # Cancelar e retry
                        await self._cancel_order(order_result.mt5_order_id)
                        raise Exception("Partial fill below threshold")
                
                else:
                    # Erro na execução
                    error_code = mcp_result.get("retcode", 0)
                    error_msg = mcp_result.get("comment", "Unknown error")
                    
                    order_result.error_code = error_code
                    order_result.error_message = error_msg
                    
                    # Determinar se deve fazer retry
                    retry_reason = self._classify_error(error_code)
                    if retry_reason and self.retry_strategy.should_retry(Exception(error_msg), attempt, retry_reason):
                        delay = self.retry_strategy.get_delay(attempt, retry_reason)
                        
                        self._log_audit_event("order_retry", {
                            "order_id": order_request.order_id,
                            "execution_id": execution_id,
                            "attempt": attempt + 1,
                            "error_code": error_code,
                            "error_message": error_msg,
                            "retry_reason": retry_reason.value,
                            "delay": delay
                        })
                        
                        await asyncio.sleep(delay)
                        attempt += 1
                        self.execution_metrics["retry_count"] += 1
                        continue
                    else:
                        order_result.status = ExecutionStatus.REJECTED
                        break
                    
            except asyncio.TimeoutError:
                self._log_audit_event("order_timeout", {
                    "order_id": order_request.order_id,
                    "execution_id": execution_id,
                    "timeout_seconds": order_request.timeout_seconds,
                    "attempt": attempt + 1
                })
                
                if self.retry_strategy.should_retry(last_error, attempt, RetryReason.TIMEOUT):
                    delay = self.retry_strategy.get_delay(attempt, RetryReason.TIMEOUT)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                else:
                    order_result.status = ExecutionStatus.TIMEOUT
                    break
                    
            except Exception as e:
                last_error = e
                self.circuit_breaker.on_failure()
                
                self._log_audit_event("order_error", {
                    "order_id": order_request.order_id,
                    "execution_id": execution_id,
                    "error": str(e),
                    "attempt": attempt + 1
                })
                
                # Classificar erro para retry
                retry_reason = RetryReason.NETWORK_ERROR
                if "timeout" in str(e).lower():
                    retry_reason = RetryReason.TIMEOUT
                elif "server" in str(e).lower() or "5" in str(e):
                    retry_reason = RetryReason.SERVER_ERROR
                
                if self.retry_strategy.should_retry(e, attempt, retry_reason):
                    delay = self.retry_strategy.get_delay(attempt, retry_reason)
                    await asyncio.sleep(delay)
                    attempt += 1
                    self.execution_metrics["retry_count"] += 1
                    continue
                else:
                    order_result.status = ExecutionStatus.FAILED
                    order_result.error_message = str(e)
                    break
        
        # Cache do resultado
        self.order_cache[order_request.order_id] = order_result
        return order_result
    
    async def _simulate_mcp_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Simula execução de ordem MCP para demo"""
        # Simular delay de rede
        await asyncio.sleep(0.1 + (0.05 * abs(hash(order_request.order_id)) % 10))
        
        # Simular diferentes cenários
        scenario_hash = abs(hash(order_request.order_id)) % 100
        
        if scenario_hash < 80:  # 80% sucesso
            return {
                "retcode": 10009,  # TRADE_RETCODE_DONE
                "order": abs(hash(order_request.order_id)) % 1000000,
                "deal": abs(hash(order_request.order_id)) % 2000000,
                "volume": float(order_request.quantity),
                "price": 10.0 + (scenario_hash % 20) * 0.01,  # Preço simulado
                "comment": "Executed successfully"
            }
        elif scenario_hash < 90:  # 10% partial fill
            return {
                "retcode": 10010,  # TRADE_RETCODE_DONE_PARTIAL
                "order": abs(hash(order_request.order_id)) % 1000000,
                "volume": float(order_request.quantity * 0.7),  # 70% preenchido
                "price": 10.0 + (scenario_hash % 20) * 0.01,
                "comment": "Partial fill"
            }
        else:  # 10% erro
            return {
                "retcode": 10013,  # TRADE_RETCODE_INVALID_REQUEST
                "comment": "Invalid price"
            }
    
    def _classify_error(self, error_code: int) -> Optional[RetryReason]:
        """Classifica erro para determinar estratégia de retry"""
        if error_code in [10027, 10028, 10029]:  # Network/connection errors
            return RetryReason.NETWORK_ERROR
        elif error_code in [10031, 10032]:  # Timeout errors
            return RetryReason.TIMEOUT
        elif error_code in [10004, 10006]:  # Server busy, no connection
            return RetryReason.SERVER_ERROR
        elif error_code in [10015, 10016]:  # Market closed, insufficient funds (temporary)
            return RetryReason.TEMPORARY_REJECT
        else:
            return None  # Não deve fazer retry
    
    async def _cancel_order(self, mt5_order_id: Optional[int]):
        """Cancela ordem no MT5"""
        if not mt5_order_id:
            return
            
        try:
            # Simular cancelamento
            self._log_audit_event("order_cancelled", {
                "mt5_order_id": mt5_order_id
            })
        except Exception as e:
            logger.error(f"Failed to cancel order {mt5_order_id}: {e}")
    
    async def execute_swap(self,
                          decision_id: str,
                          sell_symbol: str,
                          buy_symbol: str,
                          quantity: int,
                          max_slippage: float = 0.05) -> ExecutionResult:
        """Executa swap completo com idempotência"""
        
        # Verificar idempotência
        if decision_id in self.execution_cache:
            cached_result = self.execution_cache[decision_id]
            self._log_audit_event("execution_idempotent", {
                "decision_id": decision_id,
                "cached_execution_id": cached_result.execution_id
            })
            return cached_result
        
        # Gerar IDs únicos
        execution_id = self._generate_execution_id(decision_id)
        
        # Inicializar resultado
        result = ExecutionResult(
            decision_id=decision_id,
            execution_id=execution_id,
            status=ExecutionStatus.PENDING
        )
        
        start_time = time.time()
        
        try:
            # Inicializar cliente MCP
            await self._init_mcp_client()
            
            self._log_audit_event("execution_start", {
                "decision_id": decision_id,
                "execution_id": execution_id,
                "sell_symbol": sell_symbol,
                "buy_symbol": buy_symbol,
                "quantity": quantity,
                "max_slippage": max_slippage
            })
            
            # Executar ordem de venda primeiro
            sell_order_id = self._generate_order_id(execution_id, "SELL")
            sell_request = OrderRequest(
                order_id=sell_order_id,
                symbol=sell_symbol,
                action="SELL",
                quantity=quantity,
                max_slippage=max_slippage
            )
            
            result.sell_order = await self._execute_order_with_retry(sell_request, execution_id)
            
            if result.sell_order.status not in [ExecutionStatus.FILLED, ExecutionStatus.PARTIAL_FILL]:
                result.status = ExecutionStatus.FAILED
                result.error_details = {
                    "reason": "Sell order failed",
                    "sell_status": result.sell_order.status.value,
                    "sell_error": result.sell_order.error_message
                }
                
                self._log_audit_event("execution_failed", {
                    "decision_id": decision_id,
                    "execution_id": execution_id,
                    "reason": "sell_order_failed",
                    "sell_order_status": result.sell_order.status.value
                })
                
                self.execution_metrics["failed_executions"] += 1
                return result
            
            # Calcular quantidade a comprar baseada na venda executada
            sell_proceeds = result.sell_order.filled_quantity * result.sell_order.avg_fill_price
            buy_quantity = int(sell_proceeds * 0.99 / 10.0)  # Estimativa com margem de segurança
            
            # Executar ordem de compra
            buy_order_id = self._generate_order_id(execution_id, "BUY")
            buy_request = OrderRequest(
                order_id=buy_order_id,
                symbol=buy_symbol,
                action="BUY",
                quantity=buy_quantity,
                max_slippage=max_slippage
            )
            
            result.buy_order = await self._execute_order_with_retry(buy_request, execution_id)
            
            # Determinar status final
            if result.buy_order.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIAL_FILL]:
                result.status = ExecutionStatus.FILLED
                
                # Calcular métricas finais
                result.total_filled_value = result.buy_order.filled_quantity * result.buy_order.avg_fill_price
                result.total_commission = result.sell_order.commission + result.buy_order.commission
                result.net_proceeds = sell_proceeds - result.total_filled_value - result.total_commission
                
                # Calcular slippage
                expected_sell_price = 10.0  # Preço esperado (simplificado)
                expected_buy_price = 10.0
                actual_slippage_sell = abs(result.sell_order.avg_fill_price - expected_sell_price) / expected_sell_price
                actual_slippage_buy = abs(result.buy_order.avg_fill_price - expected_buy_price) / expected_buy_price
                result.slippage_pct = (actual_slippage_sell + actual_slippage_buy) * 100
                
                self.execution_metrics["successful_executions"] += 1
                
                self._log_audit_event("execution_success", {
                    "decision_id": decision_id,
                    "execution_id": execution_id,
                    "sell_filled": result.sell_order.filled_quantity,
                    "buy_filled": result.buy_order.filled_quantity,
                    "net_proceeds": result.net_proceeds,
                    "slippage_pct": result.slippage_pct
                })
                
            else:
                result.status = ExecutionStatus.FAILED
                result.error_details = {
                    "reason": "Buy order failed after successful sell",
                    "buy_status": result.buy_order.status.value,
                    "buy_error": result.buy_order.error_message
                }
                
                self._log_audit_event("execution_partial_failure", {
                    "decision_id": decision_id,
                    "execution_id": execution_id,
                    "sell_success": True,
                    "buy_failed": True,
                    "buy_error": result.buy_order.error_message
                })
                
                self.execution_metrics["failed_executions"] += 1
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_details = {
                "reason": "Execution exception",
                "error": str(e)
            }
            
            self._log_audit_event("execution_exception", {
                "decision_id": decision_id,
                "execution_id": execution_id,
                "error": str(e)
            })
            
            self.execution_metrics["failed_executions"] += 1
            
        finally:
            result.execution_duration = time.time() - start_time
            result.audit_trail = [event for event in self.audit_log if 
                                event["details"].get("execution_id") == execution_id]
            
            # Cache do resultado para idempotência
            self.execution_cache[decision_id] = result
            self.execution_metrics["total_executions"] += 1
            
            self._log_audit_event("execution_complete", {
                "decision_id": decision_id,
                "execution_id": execution_id,
                "final_status": result.status.value,
                "duration": result.execution_duration,
                "retry_count": result.retry_count
            })
        
        return result
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancela execução em andamento"""
        try:
            self._log_audit_event("execution_cancel_request", {
                "execution_id": execution_id
            })
            
            # Cancelar ordens pendentes
            # (implementação dependeria do estado atual da execução)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
    
    def get_execution_status(self, decision_id: str) -> Optional[ExecutionResult]:
        """Obtém status de execução por decision_id"""
        return self.execution_cache.get(decision_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de execução"""
        metrics = self.execution_metrics.copy()
        metrics.update({
            "success_rate": (metrics["successful_executions"] / max(metrics["total_executions"], 1)) * 100,
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "cached_executions": len(self.execution_cache),
            "audit_events": len(self.audit_log)
        })
        return metrics
    
    def export_audit_log(self, filename: Optional[str] = None) -> str:
        """Exporta log de auditoria"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_audit_{timestamp}.json"
        
        audit_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "service": "ExecutionService"
            },
            "metrics": self.get_metrics(),
            "audit_log": self.audit_log[-1000:] if len(self.audit_log) > 1000 else self.audit_log  # Últimos 1000 eventos
        }
        
        with open(filename, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        
        logger.info(f"Audit log exported to {filename}")
        return filename


# Funções de demonstração e teste
async def demo_execution_service():
    """Demonstração do ExecutionService"""
    print("🚀 EXECUTION SERVICE DEMO")
    print("="*60)
    
    # Criar serviço
    service = ExecutionService()
    
    # Configurações de teste
    test_cases = [
        {
            "name": "Swap Sucesso",
            "decision_id": "decision_001",
            "sell_symbol": "ITSA3",
            "buy_symbol": "ITSA4",
            "quantity": 1000
        },
        {
            "name": "Swap com Retry",
            "decision_id": "decision_002",
            "sell_symbol": "ITSA3", 
            "buy_symbol": "ITSA4",
            "quantity": 500
        },
        {
            "name": "Idempotência",
            "decision_id": "decision_001",  # Mesmo ID para testar cache
            "sell_symbol": "ITSA3",
            "buy_symbol": "ITSA4", 
            "quantity": 1000
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Teste {i}: {test_case['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            result = await service.execute_swap(
                decision_id=test_case["decision_id"],
                sell_symbol=test_case["sell_symbol"],
                buy_symbol=test_case["buy_symbol"],
                quantity=test_case["quantity"],
                max_slippage=0.05
            )
            
            execution_time = time.time() - start_time
            
            print(f"Status: {result.status.value}")
            print(f"Execution ID: {result.execution_id}")
            print(f"Duration: {execution_time:.2f}s")
            
            if result.sell_order:
                print(f"Sell Order: {result.sell_order.status.value} - {result.sell_order.filled_quantity} @ {result.sell_order.avg_fill_price:.2f}")
            
            if result.buy_order:
                print(f"Buy Order: {result.buy_order.status.value} - {result.buy_order.filled_quantity} @ {result.buy_order.avg_fill_price:.2f}")
            
            if result.status == ExecutionStatus.FILLED:
                print(f"Net Proceeds: R$ {result.net_proceeds:+.2f}")
                print(f"Slippage: {result.slippage_pct:.3f}%")
                print(f"Commission: R$ {result.total_commission:.2f}")
            
            if result.error_details:
                print(f"Error: {result.error_details.get('reason', 'Unknown')}")
            
            results.append(result)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    # Mostrar métricas finais
    print("\n" + "="*60)
    print("📊 MÉTRICAS DO SERVIÇO")
    print("="*60)
    
    metrics = service.get_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Exportar auditoria
    audit_file = service.export_audit_log()
    print(f"\n💾 Audit log: {audit_file}")
    
    return results


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executar demo
    asyncio.run(demo_execution_service())