
#!/usr/bin/env python3
"""
E2.2 - MCP Live Testbench
Testbench com conexão real ao servidor MCP para testar decisão de swap
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_testbench import MCPTestbench, logger
import argparse

async def test_real_connection():
    """Testa conexão real com servidor MCP"""
    logger.info("🔌 TESTANDO CONEXÃO REAL COM MCP")
    logger.info("="*60)
    
    # Criar testbench com conexão real
    testbench = MCPTestbench(use_mock=False)
    
    # Testar ferramentas principais
    tools_to_test = [
        ("validate_demo_for_trading", {}),
        ("get_account_info", {}),
        ("get_symbol_info", {"symbol": "ITSA3"}),
        ("get_symbol_info", {"symbol": "ITSA4"}),
    ]
    
    for tool_name, args in tools_to_test:
        logger.info(f"\n📡 Testando: {tool_name}")
        result = await testbench.call_mcp_tool(tool_name, args)
        
        if result["success"]:
            logger.info(f"   ✅ Sucesso!")
            if "data" in result and isinstance(result["data"], dict):
                for key, value in list(result["data"].items())[:5]:  # Primeiros 5 campos
                    logger.info(f"      {key}: {value}")
        else:
            logger.info(f"   ❌ Erro: {result.get('error')}")
    
    return testbench

async def live_arbitrage_monitor(duration: int = 30):
    """Monitora arbitragem em tempo real"""
    logger.info("\n📈 MONITOR DE ARBITRAGEM AO VIVO")
    logger.info("="*60)
    
    testbench = MCPTestbench(use_mock=False)
    
    logger.info(f"Monitorando por {duration} segundos...")
    logger.info("Premium PN = (ITSA4_mid - ITSA3_mid) / ITSA3_mid * 100")
    logger.info("-"*60)
    
    import time
    start_time = time.time()
    tick = 0
    
    premiums = []
    decisions = []
    
    while time.time() - start_time < duration:
        tick += 1
        
        try:
            # Obter cotações reais
            on_quote, pn_quote = await testbench.get_market_quotes()
            
            # Calcular métricas
            metrics = testbench.calculate_arbitrage_metrics(on_quote, pn_quote)
            
            # Decisão
            decision = testbench.make_swap_decision(metrics, has_position=(tick > 3))
            
            # Display
            logger.info(
                f"Tick {tick:3d} | "
                f"ITSA3: {on_quote.bid:.2f}/{on_quote.ask:.2f} | "
                f"ITSA4: {pn_quote.bid:.2f}/{pn_quote.ask:.2f} | "
                f"Premium: {metrics.premium_pn:+.2f}% | "
                f"Decision: {decision.value}"
            )
            
            premiums.append(metrics.premium_pn)
            decisions.append(decision)
            
            # Aguardar próximo tick
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Erro no tick {tick}: {e}")
            await asyncio.sleep(2)
    
    # Estatísticas
    if premiums:
        avg_premium = sum(premiums) / len(premiums)
        max_premium = max(premiums)
        min_premium = min(premiums)
        
        logger.info("\n📊 ESTATÍSTICAS DA SESSÃO")
        logger.info("-"*60)
        logger.info(f"Total ticks: {tick}")
        logger.info(f"Premium médio: {avg_premium:+.2f}%")
        logger.info(f"Premium máximo: {max_premium:+.2f}%")
        logger.info(f"Premium mínimo: {min_premium:+.2f}%")
        
        # Contar decisões
        from collections import Counter
        decision_counts = Counter([d.value for d in decisions])
        logger.info("\nDecisões tomadas:")
        for decision, count in decision_counts.items():
            pct = (count / len(decisions)) * 100
            logger.info(f"   {decision}: {count} ({pct:.1f}%)")

async def main():
    parser = argparse.ArgumentParser(description="MCP Live Testbench")
    parser.add_argument("--test", action="store_true", help="Testar conexão apenas")
    parser.add_argument("--monitor", type=int, default=30, help="Monitorar por N segundos")
    parser.add_argument("--mock", action="store_true", help="Usar dados mockados")
    
    args = parser.parse_args()
    
    logger.info("🚀 MCP LIVE TESTBENCH - ETAPA 2.2")
    logger.info("="*60)
    
    if args.test:
        await test_real_connection()
    else:
        if args.mock:
            # Usar testbench com mock
            testbench = MCPTestbench(use_mock=True)
            await testbench.run_test_scenario("Live Mock Test", args.monitor)
        else:
            # Monitor real
            await live_arbitrage_monitor(args.monitor)
    
    logger.info("\n✅ Testbench concluído!")

if __name__ == "__main__":
    asyncio.run(main())