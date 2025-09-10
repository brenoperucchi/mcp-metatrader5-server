#!/usr/bin/env python3
"""
E2.4 - Swap Decision Client Demo
Demonstração do cliente de decisão de swap ITSA3⇄ITSA4
"""

import asyncio
import sys
import os
import argparse
import json
from datetime import datetime

# Adicionar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etapa2.swap_decision_client import (
    SwapDecisionClient,
    SwapDecisionType,
    PositionState
)

async def demo_single_decision():
    """Demonstra uma única decisão de swap"""
    print("🎯 DEMO: Decisão Única de Swap")
    print("="*60)
    
    # Configuração personalizada
    config = {
        "min_premium_threshold": 0.20,    # 0.20% para entrada
        "swap_threshold": 0.05,           # 0.05% para swap
        "take_profit_threshold": 0.60,    # 0.60% para saída
        "confidence_threshold": 0.60,     # 60% confiança
    }
    
    # Criar cliente
    client = SwapDecisionClient(
        mcp_server_url="192.168.0.125:8000",
        on_symbol="ITSA3",
        pn_symbol="ITSA4",
        config=config
    )
    
    print(f"Cliente inicializado: {client.on_symbol}⇄{client.pn_symbol}")
    print(f"Estado inicial: {client.position_state.value}")
    print(f"Configuração: {json.dumps(config, indent=2)}")
    
    # Executar decisão
    print("\n📊 Obtendo dados de mercado e tomando decisão...")
    decision = await client.run_decision_cycle()
    
    # Simular execução
    await client.simulate_position_update(decision)
    
    # Mostrar resultado
    print("\n📋 RESULTADO DA DECISÃO")
    print("-"*40)
    print(f"Decisão: {decision.decision_type.value}")
    print(f"Estado: {decision.current_state.value} → {decision.target_state.value}")
    print(f"Raciocínio: {decision.reasoning}")
    print(f"Confiança: {decision.confidence:.2f}")
    print(f"Avaliação de risco: {decision.risk_assessment}")
    
    if decision.opportunity:
        opp = decision.opportunity
        print(f"\n💰 OPORTUNIDADE DETECTADA")
        print(f"Premium PN: {opp.premium_pn:+.2f}%")
        print(f"Custo spread: {opp.total_spread_cost:.2f}%")
        print(f"Oportunidade líquida: {opp.net_opportunity:+.2f}%")
        print(f"Lucrativa: {'✅ Sim' if opp.is_profitable else '❌ Não'}")
        print(f"Score confiança: {opp.confidence_score:.2f}")
        
        print(f"\n📈 DADOS DE MERCADO")
        print(f"ITSA3: Bid={opp.on_data.bid:.2f} Ask={opp.on_data.ask:.2f} Mid={opp.on_data.mid_price:.2f}")
        print(f"ITSA4: Bid={opp.pn_data.bid:.2f} Ask={opp.pn_data.ask:.2f} Mid={opp.pn_data.mid_price:.2f}")
        print(f"Volume: ITSA3={opp.on_data.volume:,} ITSA4={opp.pn_data.volume:,}")
    
    return client

async def demo_trading_session(duration_minutes: int = 5):
    """Demonstra sessão de trading por vários ciclos"""
    print(f"📈 DEMO: Sessão de Trading ({duration_minutes} minutos)")
    print("="*60)
    
    # Configuração mais agressiva para demonstração
    config = {
        "min_premium_threshold": 0.15,
        "swap_threshold": 0.05,
        "take_profit_threshold": 0.40,
        "confidence_threshold": 0.50,
    }
    
    client = SwapDecisionClient(config=config)
    
    print(f"📊 Monitorando {client.on_symbol}⇄{client.pn_symbol} por {duration_minutes} minutos...")
    print(f"Intervalo: 15 segundos entre decisões")
    print("-"*60)
    
    cycles = duration_minutes * 4  # 15s intervals = 4 per minute
    decisions_made = []
    
    for i in range(cycles):
        print(f"\n⏱️  Ciclo {i+1}/{cycles}")
        
        # Executar decisão
        decision = await client.run_decision_cycle()
        
        # Simular execução
        await client.simulate_position_update(decision)
        
        # Log resumido
        if decision.decision_type != SwapDecisionType.NO_ACTION:
            print(f"   🎯 AÇÃO: {decision.decision_type.value}")
            print(f"   📍 Estado: {client.position_state.value}")
            decisions_made.append(decision)
        else:
            premium = decision.opportunity.premium_pn if decision.opportunity else 0
            print(f"   💭 Aguardando: Premium {premium:+.2f}%")
        
        # Mostrar posição se existir
        if client.current_position:
            pos = client.current_position
            print(f"   📊 Posição: {pos.symbol} {pos.quantity} @ {pos.entry_price:.2f} (PnL: {pos.unrealized_pnl:+.2f}%)")
        
        # Aguardar próximo ciclo
        if i < cycles - 1:
            await asyncio.sleep(15)
    
    # Resumo da sessão
    print("\n" + "="*60)
    print("📊 RESUMO DA SESSÃO")
    print("="*60)
    
    print(f"Total de ciclos: {cycles}")
    print(f"Decisões de ação: {len(decisions_made)}")
    print(f"Estado final: {client.position_state.value}")
    
    # Estatísticas de decisões
    decision_counts = {}
    for decision in client.decision_history:
        dt = decision.decision_type.value
        decision_counts[dt] = decision_counts.get(dt, 0) + 1
    
    print("\nDistribuição de decisões:")
    for decision_type, count in decision_counts.items():
        pct = (count / len(client.decision_history)) * 100
        print(f"   {decision_type}: {count} ({pct:.1f}%)")
    
    # Análise de performance
    if decisions_made:
        print(f"\nPrimeira ação: {decisions_made[0].decision_type.value}")
        print(f"Última ação: {decisions_made[-1].decision_type.value}")
        
        # Oportunidades detectadas
        opportunities = [d for d in client.decision_history if d.opportunity and d.opportunity.is_profitable]
        print(f"Oportunidades lucrativas detectadas: {len(opportunities)}")
        
        if opportunities:
            avg_premium = sum(o.opportunity.premium_pn for o in opportunities) / len(opportunities)
            print(f"Premium médio das oportunidades: {avg_premium:+.2f}%")
    
    # Exportar histórico
    filename = client.export_decision_history()
    print(f"\n💾 Histórico exportado: {filename}")
    
    return client

async def demo_risk_scenarios():
    """Demonstra diferentes cenários de risco"""
    print("⚠️  DEMO: Cenários de Risco")
    print("="*60)
    
    scenarios = [
        {
            "name": "Conservador",
            "config": {
                "min_premium_threshold": 0.50,
                "confidence_threshold": 0.80,
                "take_profit_threshold": 0.30
            }
        },
        {
            "name": "Moderado",
            "config": {
                "min_premium_threshold": 0.25,
                "confidence_threshold": 0.65,
                "take_profit_threshold": 0.50
            }
        },
        {
            "name": "Agressivo",
            "config": {
                "min_premium_threshold": 0.10,
                "confidence_threshold": 0.50,
                "take_profit_threshold": 0.80
            }
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n🎯 Testando perfil: {scenario['name']}")
        print("-"*40)
        
        client = SwapDecisionClient(config=scenario['config'])
        decision = await client.run_decision_cycle()
        
        print(f"Decisão: {decision.decision_type.value}")
        print(f"Confiança: {decision.confidence:.2f}")
        
        if decision.opportunity:
            opp = decision.opportunity
            print(f"Premium necessário: ≥{scenario['config']['min_premium_threshold']:.2f}%")
            print(f"Premium detectado: {opp.premium_pn:+.2f}%")
            print(f"Ação: {'✅ Tomada' if decision.decision_type != SwapDecisionType.NO_ACTION else '❌ Aguardando'}")
        
        results.append({
            "scenario": scenario['name'],
            "decision": decision.decision_type.value,
            "confidence": decision.confidence,
            "config": scenario['config']
        })
    
    # Comparação
    print("\n📊 COMPARAÇÃO DE PERFIS")
    print("-"*60)
    for result in results:
        action_taken = "Sim" if result['decision'] != 'NO_ACTION' else "Não"
        print(f"{result['scenario']:<12}: Ação={action_taken:<4} Confiança={result['confidence']:.2f}")
    
    return results

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Swap Decision Client Demo")
    parser.add_argument("--mode", choices=["single", "session", "risk", "all"], 
                       default="single", help="Modo de demonstração")
    parser.add_argument("--duration", type=int, default=5, 
                       help="Duração da sessão em minutos")
    
    args = parser.parse_args()
    
    print("🚀 E2.4 - SWAP DECISION CLIENT")
    print("="*60)
    print(f"Modo: {args.mode}")
    print(f"Servidor MCP: 192.168.0.125:8000")
    print(f"Par: ITSA3⇄ITSA4")
    
    async def run_demos():
        try:
            if args.mode == "single" or args.mode == "all":
                await demo_single_decision()
            
            if args.mode == "session" or args.mode == "all":
                if args.mode == "all":
                    print("\n" + "="*60)
                await demo_trading_session(args.duration)
            
            if args.mode == "risk" or args.mode == "all":
                if args.mode == "all":
                    print("\n" + "="*60)
                await demo_risk_scenarios()
            
            print("\n✅ Demonstração concluída com sucesso!")
            
        except Exception as e:
            print(f"\n❌ Erro durante demonstração: {e}")
            import traceback
            traceback.print_exc()
    
    # Executar
    asyncio.run(run_demos())

if __name__ == "__main__":
    main()