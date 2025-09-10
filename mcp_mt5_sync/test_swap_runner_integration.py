"""
Testes de integração para SwapBacktestRunner

Foca nos testes essenciais de funcionalidade do sistema,
validando o comportamento end-to-end do backtest.
"""

import pytest
import tempfile
import json
from datetime import date
from pathlib import Path
import asyncio

from src.backtest.swap_runner import (
    SwapBacktestRunner,
    BacktestConfig,
    BacktestResult,
    MarketScenario
)


class TestSwapBacktestRunnerIntegration:
    """Testes de integração para o SwapBacktestRunner"""
    
    @pytest.fixture
    def conservative_config(self):
        """Configuração conservadora para testes"""
        return BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),  # Período curto
            initial_capital=10000.0,
            min_premium_threshold=0.1,
            scenario=MarketScenario.NORMAL,
            noise_level=0.1,
            save_results=False
        )
    
    @pytest.fixture
    def aggressive_config(self):
        """Configuração agressiva para forçar trades"""
        return BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
            initial_capital=10000.0,
            min_premium_threshold=0.01,  # Muito baixo
            swap_threshold=0.005,        # Muito baixo
            take_profit_threshold=0.02,  # Muito baixo
            confidence_threshold=0.1,    # Muito baixo
            scenario=MarketScenario.HIGH_VOLATILITY,
            noise_level=0.4,             # Alto ruído
            gap_probability=0.2,         # Muitos gaps
            save_results=False
        )
    
    @pytest.mark.asyncio
    async def test_basic_backtest_execution(self, conservative_config):
        """Testa execução básica do backtest"""
        runner = SwapBacktestRunner(conservative_config)
        
        # Executar backtest
        result = await runner.run_backtest()
        
        # Verificar estrutura do resultado
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == conservative_config.initial_capital
        assert result.start_date == conservative_config.start_date
        assert result.end_date == conservative_config.end_date
        
        # Verificar que métricas básicas foram calculadas
        assert result.total_return is not None
        assert result.total_return_pct is not None
        assert result.sharpe_ratio is not None
        assert result.max_drawdown_pct is not None
        
        # Capital final deve ser > 0
        assert result.final_capital >= 0
        
        # Número de trades deve ser >= 0
        assert result.total_trades >= 0
        
        # Se houver trades, verificar estrutura
        if result.total_trades > 0:
            assert len(result.trades) == result.total_trades
            
            # Verificar que custos foram aplicados
            assert result.total_commission >= 0
            assert result.total_slippage >= 0
            assert result.total_taxes >= 0
    
    @pytest.mark.asyncio
    async def test_aggressive_trading(self, aggressive_config):
        """Testa cenário agressivo que deve gerar trades"""
        runner = SwapBacktestRunner(aggressive_config)
        
        result = await runner.run_backtest()
        
        # Com configuração agressiva, espera-se alguma atividade
        # (mas não garantimos trades devido à natureza estocástica)
        assert result.total_trades >= 0
        
        # Se houver trades, verificar métricas MFE/MAE
        if result.total_trades > 0:
            assert result.avg_mfe >= 0
            assert result.avg_mae <= 0
            
            # Verificar trades individuais
            for trade in result.trades:
                assert trade.entry_time is not None
                assert trade.entry_price > 0
                assert trade.quantity > 0
                
                if trade.is_closed:
                    assert trade.exit_time is not None
                    assert trade.exit_price > 0
                    assert trade.net_pnl is not None
                    assert trade.mfe >= 0
                    assert trade.mae <= 0
    
    @pytest.mark.asyncio
    async def test_different_market_scenarios(self):
        """Testa diferentes cenários de mercado"""
        scenarios = [
            MarketScenario.NORMAL,
            MarketScenario.HIGH_VOLATILITY,
            MarketScenario.DIVIDEND_SEASON
        ]
        
        results = []
        
        for scenario in scenarios:
            config = BacktestConfig(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 3),
                initial_capital=10000.0,
                scenario=scenario,
                save_results=False
            )
            
            runner = SwapBacktestRunner(config)
            result = await runner.run_backtest()
            results.append(result)
            
            # Cada resultado deve ser válido
            assert isinstance(result, BacktestResult)
            assert result.final_capital >= 0
        
        # Todos os cenários devem ter executado
        assert len(results) == len(scenarios)
    
    @pytest.mark.asyncio
    async def test_equity_curve_generation(self, conservative_config):
        """Testa geração da curva de patrimônio"""
        runner = SwapBacktestRunner(conservative_config)
        
        result = await runner.run_backtest()
        
        # Deve haver pelo menos um ponto na curva
        assert len(result.equity_curve) >= 1
        
        # Verificar estrutura dos pontos
        for point in result.equity_curve:
            assert 'timestamp' in point
            assert 'capital' in point
            assert 'total_equity' in point
            assert point['capital'] >= 0
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self, aggressive_config):
        """Testa cálculo de custos"""
        runner = SwapBacktestRunner(aggressive_config)
        
        result = await runner.run_backtest()
        
        # Custos devem estar presentes
        assert result.total_commission >= 0
        assert result.total_slippage >= 0
        assert result.total_taxes >= 0
        
        # Se houver trades, custos devem ser > 0
        if result.total_trades > 0:
            total_costs = result.total_commission + abs(result.total_slippage) + result.total_taxes
            assert total_costs > 0
    
    @pytest.mark.asyncio
    async def test_swap_specific_metrics(self, aggressive_config):
        """Testa métricas específicas de swap"""
        runner = SwapBacktestRunner(aggressive_config)
        
        result = await runner.run_backtest()
        
        # Verificar que métricas de swap estão presentes
        assert result.total_swaps >= 0
        assert result.successful_swaps >= 0
        assert result.swap_success_rate >= 0
        
        # Métricas de prêmio
        assert result.avg_premium_at_entry >= 0
        assert result.avg_premium_at_swap >= 0
        assert result.avg_premium_at_exit >= 0
        
        # Se houver swaps, verificar consistência
        if result.total_swaps > 0:
            assert result.successful_swaps <= result.total_swaps
            assert result.swap_success_rate <= 100.0
    
    @pytest.mark.asyncio
    async def test_file_output_integration(self):
        """Testa integração completa com geração de arquivos"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = BacktestConfig(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 2),
                initial_capital=10000.0,
                scenario=MarketScenario.HIGH_VOLATILITY,
                noise_level=0.3,
                save_results=True,
                output_dir=temp_dir,
                generate_json=True,
                generate_csv=True,
                generate_html=True
            )
            
            runner = SwapBacktestRunner(config)
            result = await runner.run_backtest()
            
            # Verificar que arquivos foram criados
            output_path = Path(temp_dir)
            files = list(output_path.glob("*"))
            
            assert len(files) > 0  # Pelo menos algum arquivo foi criado
            
            # Verificar arquivo JSON se existir
            json_files = [f for f in files if f.suffix == '.json']
            if json_files:
                with open(json_files[0], 'r') as f:
                    data = json.load(f)
                
                # Verificar estrutura básica do JSON
                assert 'backtest_id' in data
                assert 'config' in data
                assert 'initial_capital' in data
                assert 'final_capital' in data
                assert 'total_return' in data
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, aggressive_config):
        """Testa cálculo de métricas de performance"""
        runner = SwapBacktestRunner(aggressive_config)
        
        result = await runner.run_backtest()
        
        # Verificar que todas as métricas estão presentes
        assert result.sharpe_ratio is not None
        assert result.sortino_ratio is not None
        assert result.max_drawdown >= 0
        assert result.max_drawdown_pct >= 0
        assert result.var_95 is not None
        assert result.cvar_95 is not None
        
        # Métricas de tempo
        assert result.avg_holding_time_minutes >= 0
        assert result.max_holding_time_minutes >= 0
        assert result.min_holding_time_minutes >= 0
        
        # Se houver trades, verificar consistência
        if result.total_trades > 0:
            if result.winning_trades > 0:
                assert result.avg_win > 0
                assert result.largest_win > 0
            
            if result.losing_trades > 0:
                assert result.avg_loss < 0
                assert result.largest_loss < 0
            
            # Hit rate deve ser consistente
            expected_hit_rate = (result.winning_trades / result.total_trades) * 100
            assert abs(result.hit_rate - expected_hit_rate) < 0.1
    
    @pytest.mark.asyncio
    async def test_edge_cases(self):
        """Testa casos extremos"""
        
        # Teste com capital muito baixo
        low_capital_config = BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 2),
            initial_capital=100.0,  # Muito baixo
            save_results=False
        )
        
        runner = SwapBacktestRunner(low_capital_config)
        result = await runner.run_backtest()
        
        # Deve executar sem erros
        assert result.final_capital >= 0
        
        # Teste com período de um dia
        one_day_config = BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),  # Mesmo dia
            initial_capital=10000.0,
            save_results=False
        )
        
        runner = SwapBacktestRunner(one_day_config)
        result = await runner.run_backtest()
        
        # Deve executar sem erros
        assert result.trading_days >= 0
        assert result.final_capital >= 0


class TestSwapBacktestRunnerQuickValidation:
    """Testes rápidos para validação básica"""
    
    @pytest.mark.asyncio
    async def test_demo_execution(self):
        """Testa que o demo funciona sem erros"""
        config = BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 2),
            initial_capital=5000.0,
            scenario=MarketScenario.HIGH_VOLATILITY,
            noise_level=0.2,
            save_results=False
        )
        
        runner = SwapBacktestRunner(config)
        result = await runner.run_backtest()
        
        # Validação mínima - o sistema deve funcionar
        assert isinstance(result, BacktestResult)
        assert result.execution_time_seconds >= 0
    
    @pytest.mark.asyncio 
    async def test_config_validation(self):
        """Testa validação básica de configuração"""
        
        # Configuração válida
        valid_config = BacktestConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 5),
            initial_capital=10000.0
        )
        
        runner = SwapBacktestRunner(valid_config)
        
        # Deve inicializar sem erros
        assert runner.config == valid_config
        assert runner.current_capital == valid_config.initial_capital
        assert runner.current_position is None


if __name__ == "__main__":
    # Executar testes de integração
    pytest.main([__file__, "-v"])