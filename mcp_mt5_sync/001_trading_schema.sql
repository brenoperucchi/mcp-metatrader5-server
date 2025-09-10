-- E2.7 - Trading Schema Migration
-- Esquema completo para persistência de decisões, ordens, fills e P&L

-- Criar schema trading se não existe
CREATE SCHEMA IF NOT EXISTS trading;

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================
-- TABELA: trading.decisions
-- ===================================
-- Decisões de swap com contexto completo
CREATE TABLE IF NOT EXISTS trading.decisions (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(100) UNIQUE,
    strategy_id VARCHAR(50) NOT NULL DEFAULT 'itsa_arbitrage',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Símbolos e contexto
    from_symbol VARCHAR(10) NOT NULL,
    to_symbol VARCHAR(10) NOT NULL,
    trigger_reason VARCHAR(200),
    decision_type VARCHAR(50) NOT NULL, -- ENTER_LONG_ON, SWAP_TO_PN, etc.
    
    -- Estado e posição
    current_state VARCHAR(20) NOT NULL,
    target_state VARCHAR(20) NOT NULL,
    position_quantity INTEGER,
    position_entry_price DECIMAL(10,4),
    
    -- Métricas de oportunidade
    premium_pn DECIMAL(8,4),
    spread_cost DECIMAL(8,4),
    net_opportunity DECIMAL(8,4),
    confidence_score DECIMAL(4,3),
    
    -- Expectativas
    expected_profit DECIMAL(10,4),
    expected_return_pct DECIMAL(6,3),
    take_profit DECIMAL(10,4),
    stop_loss DECIMAL(10,4),
    max_slippage DECIMAL(6,3),
    
    -- Status e timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, executing, completed, failed, cancelled
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Auditoria
    audit_data JSONB,
    error_details JSONB,
    
    -- Constraints
    CONSTRAINT chk_symbols CHECK (from_symbol != to_symbol),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'executing', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON trading.decisions (timestamp);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON trading.decisions (status);
CREATE INDEX IF NOT EXISTS idx_decisions_symbols ON trading.decisions (from_symbol, to_symbol);
CREATE INDEX IF NOT EXISTS idx_decisions_strategy ON trading.decisions (strategy_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_decisions_execution_id ON trading.decisions (execution_id);

-- ===================================
-- TABELA: trading.orders
-- ===================================
-- Ordens individuais dentro de cada decisão
CREATE TABLE IF NOT EXISTS trading.orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES trading.decisions(decision_id) ON DELETE CASCADE,
    
    -- Identificação externa
    client_id VARCHAR(50) UNIQUE, -- ID interno para correlação
    mt5_order_id BIGINT UNIQUE, -- ID do MT5
    magic_number INTEGER DEFAULT 20250829,
    
    -- Detalhes da ordem
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL, -- BUY, SELL
    order_type VARCHAR(10) NOT NULL DEFAULT 'MARKET', -- MARKET, LIMIT, STOP
    quantity INTEGER NOT NULL,
    price DECIMAL(10,4),
    stop_loss DECIMAL(10,4),
    take_profit DECIMAL(10,4),
    
    -- Execução
    filled_quantity INTEGER DEFAULT 0,
    remaining_quantity INTEGER,
    avg_fill_price DECIMAL(10,4),
    
    -- Status e timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    
    -- Métricas de execução
    slippage_pct DECIMAL(6,3),
    execution_time_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    
    -- Detalhes de erro
    error_code INTEGER,
    error_message TEXT,
    
    -- Auditoria
    audit_trail JSONB,
    
    -- Constraints
    CONSTRAINT chk_side CHECK (side IN ('BUY', 'SELL')),
    CONSTRAINT chk_order_type CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP')),
    CONSTRAINT chk_order_status CHECK (status IN ('pending', 'submitted', 'partial_fill', 'filled', 'cancelled', 'rejected', 'failed')),
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_filled_quantity CHECK (filled_quantity >= 0 AND filled_quantity <= quantity)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_orders_decision_id ON trading.orders (decision_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON trading.orders (symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON trading.orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON trading.orders (created_at);
CREATE INDEX IF NOT EXISTS idx_orders_mt5_id ON trading.orders (mt5_order_id) WHERE mt5_order_id IS NOT NULL;

-- ===================================
-- TABELA: trading.fills
-- ===================================  
-- Execuções parciais ou completas de ordens
CREATE TABLE IF NOT EXISTS trading.fills (
    fill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES trading.orders(order_id) ON DELETE CASCADE,
    
    -- Identificação externa
    mt5_deal_id BIGINT UNIQUE,
    
    -- Detalhes da execução
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    
    -- Timing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    server_time TIMESTAMPTZ,
    
    -- Custos
    commission DECIMAL(10,4) DEFAULT 0,
    swap DECIMAL(10,4) DEFAULT 0,
    fees DECIMAL(10,4) DEFAULT 0,
    
    -- Contexto
    is_partial_fill BOOLEAN DEFAULT FALSE,
    fill_sequence INTEGER DEFAULT 1,
    
    -- Auditoria
    source_data JSONB,
    
    -- Constraints
    CONSTRAINT chk_fill_side CHECK (side IN ('BUY', 'SELL')),
    CONSTRAINT chk_fill_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_fill_price_positive CHECK (price > 0)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_fills_order_id ON trading.fills (order_id);
CREATE INDEX IF NOT EXISTS idx_fills_timestamp ON trading.fills (timestamp);
CREATE INDEX IF NOT EXISTS idx_fills_symbol ON trading.fills (symbol);
CREATE INDEX IF NOT EXISTS idx_fills_mt5_deal ON trading.fills (mt5_deal_id) WHERE mt5_deal_id IS NOT NULL;

-- ===================================
-- TABELA: trading.pnl
-- ===================================
-- P&L consolidado por decisão de swap
CREATE TABLE IF NOT EXISTS trading.pnl (
    pnl_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES trading.decisions(decision_id) ON DELETE CASCADE,
    
    -- P&L realizado
    gross_proceeds DECIMAL(12,4) DEFAULT 0, -- Valor bruto das vendas
    gross_cost DECIMAL(12,4) DEFAULT 0, -- Custo bruto das compras
    realized_pnl DECIMAL(12,4) DEFAULT 0, -- P&L bruto (proceeds - cost)
    
    -- Custos detalhados
    commission_total DECIMAL(10,4) DEFAULT 0,
    swap_total DECIMAL(10,4) DEFAULT 0,
    fees_total DECIMAL(10,4) DEFAULT 0,
    slippage_cost DECIMAL(10,4) DEFAULT 0,
    
    -- P&L líquido
    net_pnl DECIMAL(12,4) DEFAULT 0, -- P&L após todos os custos
    net_pnl_pct DECIMAL(8,4) DEFAULT 0, -- Percentual sobre capital
    
    -- Métricas de performance
    capital_allocated DECIMAL(12,4),
    return_on_capital DECIMAL(8,4),
    holding_period_minutes INTEGER,
    
    -- Status
    is_final BOOLEAN DEFAULT FALSE,
    calculation_method VARCHAR(50) DEFAULT 'fifo',
    
    -- Timing
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    position_opened_at TIMESTAMPTZ,
    position_closed_at TIMESTAMPTZ,
    
    -- Contexto adicional
    market_conditions JSONB,
    notes TEXT,
    
    -- Constraints
    CONSTRAINT chk_pnl_capital_positive CHECK (capital_allocated > 0),
    CONSTRAINT chk_pnl_holding_period CHECK (holding_period_minutes >= 0)
);

-- Indices para performance  
CREATE INDEX IF NOT EXISTS idx_pnl_decision_id ON trading.pnl (decision_id);
CREATE INDEX IF NOT EXISTS idx_pnl_calculated_at ON trading.pnl (calculated_at);
CREATE INDEX IF NOT EXISTS idx_pnl_net_pnl ON trading.pnl (net_pnl);
CREATE INDEX IF NOT EXISTS idx_pnl_is_final ON trading.pnl (is_final);

-- ===================================
-- VIEWS PARA RELATÓRIOS
-- ===================================

-- View: Swap Performance Summary
CREATE OR REPLACE VIEW trading.v_swap_performance AS
SELECT 
    d.decision_id,
    d.execution_id,
    d.timestamp,
    d.from_symbol,
    d.to_symbol,
    d.decision_type,
    d.status as decision_status,
    d.premium_pn,
    d.confidence_score,
    
    -- Contagem de ordens
    COUNT(o.order_id) as total_orders,
    COUNT(CASE WHEN o.status = 'filled' THEN 1 END) as filled_orders,
    COUNT(CASE WHEN o.status = 'failed' THEN 1 END) as failed_orders,
    
    -- Métricas de execução
    AVG(o.slippage_pct) as avg_slippage_pct,
    AVG(o.execution_time_ms) as avg_execution_time_ms,
    SUM(o.retry_count) as total_retries,
    
    -- P&L
    p.realized_pnl,
    p.net_pnl,
    p.net_pnl_pct,
    p.commission_total,
    p.fees_total,
    p.holding_period_minutes,
    
    -- Status final
    CASE 
        WHEN d.status = 'completed' AND p.net_pnl > 0 THEN 'profitable'
        WHEN d.status = 'completed' AND p.net_pnl <= 0 THEN 'loss'
        WHEN d.status = 'failed' THEN 'failed'
        ELSE 'pending'
    END as outcome
    
FROM trading.decisions d
LEFT JOIN trading.orders o ON d.decision_id = o.decision_id
LEFT JOIN trading.pnl p ON d.decision_id = p.decision_id AND p.is_final = true
GROUP BY d.decision_id, d.execution_id, d.timestamp, d.from_symbol, d.to_symbol, 
         d.decision_type, d.status, d.premium_pn, d.confidence_score,
         p.realized_pnl, p.net_pnl, p.net_pnl_pct, p.commission_total, 
         p.fees_total, p.holding_period_minutes;

-- View: Daily P&L Summary
CREATE OR REPLACE VIEW trading.v_daily_pnl AS
SELECT 
    DATE(p.calculated_at) as trade_date,
    COUNT(DISTINCT p.decision_id) as total_swaps,
    COUNT(CASE WHEN p.net_pnl > 0 THEN 1 END) as profitable_swaps,
    COUNT(CASE WHEN p.net_pnl <= 0 THEN 1 END) as loss_swaps,
    
    -- P&L agregado
    SUM(p.gross_proceeds) as total_gross_proceeds,
    SUM(p.gross_cost) as total_gross_cost,
    SUM(p.realized_pnl) as total_realized_pnl,
    SUM(p.net_pnl) as total_net_pnl,
    
    -- Custos
    SUM(p.commission_total) as total_commission,
    SUM(p.fees_total) as total_fees,
    SUM(p.slippage_cost) as total_slippage,
    
    -- Métricas
    AVG(p.net_pnl_pct) as avg_return_pct,
    MAX(p.net_pnl) as best_trade,
    MIN(p.net_pnl) as worst_trade,
    AVG(p.holding_period_minutes) as avg_holding_minutes,
    
    -- Win rate
    ROUND(
        COUNT(CASE WHEN p.net_pnl > 0 THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(DISTINCT p.decision_id), 0) * 100, 
        2
    ) as win_rate_pct

FROM trading.pnl p
WHERE p.is_final = true
GROUP BY DATE(p.calculated_at)
ORDER BY trade_date DESC;

-- View: Execution Metrics
CREATE OR REPLACE VIEW trading.v_execution_metrics AS
SELECT 
    o.symbol,
    o.side,
    o.order_type,
    
    -- Contadores
    COUNT(*) as total_orders,
    COUNT(CASE WHEN o.status = 'filled' THEN 1 END) as filled_orders,
    COUNT(CASE WHEN o.status = 'partial_fill' THEN 1 END) as partial_fills,
    COUNT(CASE WHEN o.status = 'rejected' THEN 1 END) as rejected_orders,
    COUNT(CASE WHEN o.status = 'failed' THEN 1 END) as failed_orders,
    
    -- Success rate
    ROUND(
        COUNT(CASE WHEN o.status IN ('filled', 'partial_fill') THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(*), 0) * 100, 
        2
    ) as success_rate_pct,
    
    -- Métricas de timing
    AVG(o.execution_time_ms) as avg_execution_time_ms,
    MAX(o.execution_time_ms) as max_execution_time_ms,
    AVG(o.retry_count) as avg_retry_count,
    MAX(o.retry_count) as max_retry_count,
    
    -- Slippage
    AVG(o.slippage_pct) as avg_slippage_pct,
    MAX(o.slippage_pct) as max_slippage_pct,
    
    -- Fill ratio
    AVG(o.filled_quantity::DECIMAL / NULLIF(o.quantity, 0)) as avg_fill_ratio,
    
    -- Período
    MIN(o.created_at) as first_order_at,
    MAX(o.created_at) as last_order_at
    
FROM trading.orders o
GROUP BY o.symbol, o.side, o.order_type
ORDER BY o.symbol, o.side, o.order_type;

-- View: Fees Analysis
CREATE OR REPLACE VIEW trading.v_fees_analysis AS
SELECT 
    DATE(f.timestamp) as trade_date,
    f.symbol,
    f.side,
    
    -- Volume
    COUNT(*) as total_fills,
    SUM(f.quantity) as total_quantity,
    SUM(f.quantity * f.price) as total_volume,
    
    -- Custos médios
    AVG(f.commission) as avg_commission,
    AVG(f.swap) as avg_swap,
    AVG(f.fees) as avg_fees,
    
    -- Custos totais
    SUM(f.commission) as total_commission,
    SUM(f.swap) as total_swap,
    SUM(f.fees) as total_fees,
    SUM(f.commission + f.swap + f.fees) as total_costs,
    
    -- Cost basis points (bps)
    ROUND(
        SUM(f.commission + f.swap + f.fees) / 
        NULLIF(SUM(f.quantity * f.price), 0) * 10000, 
        2
    ) as cost_bps,
    
    -- Average price
    AVG(f.price) as avg_price,
    MIN(f.price) as min_price,
    MAX(f.price) as max_price

FROM trading.fills f
GROUP BY DATE(f.timestamp), f.symbol, f.side
ORDER BY trade_date DESC, f.symbol, f.side;

-- ===================================
-- TRIGGERS PARA AUDITORIA
-- ===================================

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION trading.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger nas tabelas principais
CREATE TRIGGER update_decisions_updated_at
    BEFORE UPDATE ON trading.decisions
    FOR EACH ROW EXECUTE FUNCTION trading.update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON trading.orders
    FOR EACH ROW EXECUTE FUNCTION trading.update_updated_at_column();

-- ===================================
-- PERMISSÕES
-- ===================================

-- Criar usuário para aplicação se não existe (opcional)
-- CREATE ROLE trading_app WITH LOGIN PASSWORD 'secure_password';

-- Grant permissions on schema and tables
GRANT USAGE ON SCHEMA trading TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA trading TO PUBLIC;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA trading TO PUBLIC;

-- Grant on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA trading 
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC;

-- ===================================
-- COMENTÁRIOS
-- ===================================

COMMENT ON SCHEMA trading IS 'E2.7 - Trading schema for decisions, orders, fills and P&L tracking';

COMMENT ON TABLE trading.decisions IS 'Swap decisions with full context and lifecycle';
COMMENT ON TABLE trading.orders IS 'Individual orders within each swap decision';  
COMMENT ON TABLE trading.fills IS 'Order executions (partial or complete)';
COMMENT ON TABLE trading.pnl IS 'Consolidated P&L per swap decision';

COMMENT ON VIEW trading.v_swap_performance IS 'Swap performance metrics per decision';
COMMENT ON VIEW trading.v_daily_pnl IS 'Daily P&L aggregation';
COMMENT ON VIEW trading.v_execution_metrics IS 'Order execution performance metrics';
COMMENT ON VIEW trading.v_fees_analysis IS 'Trading costs and fees analysis';

-- ===================================
-- SAMPLE DATA (para testes)
-- ===================================

-- Inserir uma decisão de exemplo
INSERT INTO trading.decisions (
    execution_id, from_symbol, to_symbol, decision_type,
    current_state, target_state, premium_pn, confidence_score,
    trigger_reason, expected_profit, status
) VALUES (
    'exec_sample_001', 'ITSA3', 'ITSA4', 'ENTER_LONG_ON',
    'IDLE', 'LONG_ON', 0.0055, 0.75,
    'Premium threshold exceeded', 150.00, 'completed'
) ON CONFLICT (execution_id) DO NOTHING;

-- Migration concluída
SELECT 'E2.7 Trading Schema Migration completed successfully!' as status;