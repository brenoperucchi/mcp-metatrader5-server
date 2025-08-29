#!/usr/bin/env python3
"""
Exemplo avançado de trading com cliente MT5 MCP

⚠️  ATENÇÃO: Este exemplo faz operações de trading reais!
    Certifique-se de estar usando uma conta DEMO.
    
Este exemplo demonstra:
- Verificações de segurança para contas demo
- Análise de mercado básica
- Envio de ordens
- Gerenciamento de posições
- Cálculo de risk/reward
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

try:
    from mt5_client import (
        MT5Client, TimeframeType, TradeAction, 
        PositionInfo, SymbolInfo, TickData, CandleData,
        ValidationError, TradingError
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from mt5_client import (
        MT5Client, TimeframeType, TradeAction,
        PositionInfo, SymbolInfo, TickData, CandleData,
        ValidationError, TradingError
    )


class TradingBot:
    """Bot simples de trading para demonstração"""
    
    def __init__(self, client: MT5Client):
        self.client = client
        self.risk_percent = 2.0  # 2% de risco por trade
        self.min_rr_ratio = 2.0  # Risk/Reward mínimo de 2:1
        
    async def analyze_symbol(self, symbol: str) -> dict:
        """Fazer análise básica de um símbolo"""
        
        # Obter informações do símbolo
        symbol_info = await self.client.get_symbol_info(symbol)
        
        # Últimas 50 velas H1 para análise de tendência
        candles = await self.client.copy_rates_from(
            symbol, TimeframeType.H1, 
            datetime.now() - timedelta(hours=50), 
            count=50
        )
        
        if len(candles) < 20:
            return {"error": "Dados insuficientes para análise"}
        
        # Análise simples: média móvel de 20 períodos
        closes = [c.close for c in candles[-20:]]
        sma20 = sum(closes) / len(closes)
        
        current_price = candles[-1].close
        trend = "bullish" if current_price > sma20 else "bearish"
        
        # Calcular volatilidade (range médio)
        ranges = [(c.high - c.low) for c in candles[-10:]]
        avg_range = sum(ranges) / len(ranges)
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "sma20": sma20,
            "trend": trend,
            "avg_range": avg_range,
            "spread": symbol_info.spread * symbol_info.point,
            "point": symbol_info.point,
            "digits": symbol_info.digits
        }
    
    async def calculate_position_size(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """Calcular tamanho da posição baseado no risco"""
        
        account = await self.client.get_account_info()
        symbol_info = await self.client.get_symbol_info(symbol)
        
        # Risco em moeda da conta
        risk_amount = account.balance * (self.risk_percent / 100)
        
        # Distância do stop em pontos
        stop_distance = abs(entry_price - stop_loss)
        
        # Valor por lote (simplificado - assumindo conta em USD)
        pip_value = symbol_info.trade_tick_value
        
        # Calcular volume
        if pip_value > 0 and stop_distance > 0:
            volume = risk_amount / (stop_distance * pip_value / symbol_info.point)
            
            # Arredondar para o step de volume
            volume = round(volume / symbol_info.volume_step) * symbol_info.volume_step
            
            # Aplicar limites
            volume = max(symbol_info.volume_min, volume)
            volume = min(symbol_info.volume_max, volume)
            
            return volume
        
        return symbol_info.volume_min
    
    async def create_trade_signal(self, analysis: dict) -> Optional[dict]:
        """Criar sinal de trading baseado na análise"""
        
        if "error" in analysis:
            return None
        
        symbol = analysis["symbol"]
        current_price = analysis["current_price"]
        sma20 = analysis["sma20"]
        avg_range = analysis["avg_range"]
        point = analysis["point"]
        
        # Estratégia simples: entrada na direção da tendência
        if analysis["trend"] == "bullish" and current_price > sma20:
            # Sinal de compra
            entry_price = current_price
            stop_loss = entry_price - (avg_range * 1.5)
            take_profit = entry_price + (avg_range * 3.0)  # RR 2:1
            
            return {
                "action": TradeAction.BUY,
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": "medium"
            }
            
        elif analysis["trend"] == "bearish" and current_price < sma20:
            # Sinal de venda
            entry_price = current_price
            stop_loss = entry_price + (avg_range * 1.5)
            take_profit = entry_price - (avg_range * 3.0)  # RR 2:1
            
            return {
                "action": TradeAction.SELL,
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": "medium"
            }
        
        return None


async def trading_safety_demo():
    """Demonstrar verificações de segurança para trading"""
    
    print("=== VERIFICAÇÕES DE SEGURANÇA ===")
    
    # Cliente configurado para demo apenas
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        account = await client.get_account_info()
        print(f"Conta: {account.login}")
        print(f"Tipo: {'DEMO' if account.is_demo else 'REAL'}")
        print(f"Servidor: {account.server}")
        print(f"Saldo: {account.balance:.2f} {account.currency}")
        
        if not account.is_demo:
            print("❌ ATENÇÃO: Esta não é uma conta demo!")
            print("   O trading será bloqueado por segurança.")
            return False
        
        print("✅ Conta demo confirmada - trading permitido")
        return True


async def market_analysis_demo():
    """Demonstrar análise de mercado"""
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== ANÁLISE DE MERCADO ===")
        
        bot = TradingBot(client)
        
        # Símbolos para análise
        test_symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        
        analyses = []
        
        for symbol in test_symbols:
            try:
                print(f"\n--- Analisando {symbol} ---")
                
                analysis = await bot.analyze_symbol(symbol)
                
                if "error" not in analysis:
                    print(f"Preço atual: {analysis['current_price']:.5f}")
                    print(f"SMA20: {analysis['sma20']:.5f}")
                    print(f"Tendência: {analysis['trend']}")
                    print(f"Range médio: {analysis['avg_range']:.5f}")
                    print(f"Spread: {analysis['spread']:.5f}")
                    
                    analyses.append(analysis)
                else:
                    print(f"❌ {analysis['error']}")
                    
            except Exception as e:
                print(f"❌ Erro ao analisar {symbol}: {e}")
        
        return analyses


async def signal_generation_demo(analyses: List[dict]):
    """Demonstrar geração de sinais de trading"""
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== GERAÇÃO DE SINAIS ===")
        
        bot = TradingBot(client)
        signals = []
        
        for analysis in analyses:
            symbol = analysis["symbol"]
            print(f"\n--- Sinais para {symbol} ---")
            
            signal = await bot.create_trade_signal(analysis)
            
            if signal:
                print(f"📈 Sinal encontrado!")
                print(f"Ação: {signal['action'].name}")
                print(f"Entrada: {signal['entry_price']:.5f}")
                print(f"Stop Loss: {signal['stop_loss']:.5f}")
                print(f"Take Profit: {signal['take_profit']:.5f}")
                print(f"Confiança: {signal['confidence']}")
                
                # Calcular Risk/Reward
                risk = abs(signal['entry_price'] - signal['stop_loss'])
                reward = abs(signal['take_profit'] - signal['entry_price'])
                rr_ratio = reward / risk if risk > 0 else 0
                
                print(f"Risk/Reward: {rr_ratio:.2f}:1")
                
                signals.append(signal)
            else:
                print("🔍 Nenhum sinal claro encontrado")
        
        return signals


async def position_sizing_demo(signals: List[dict]):
    """Demonstrar cálculo de tamanho de posição"""
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== CÁLCULO DE POSIÇÃO ===")
        
        bot = TradingBot(client)
        
        for signal in signals:
            symbol = signal["symbol"]
            print(f"\n--- Tamanho para {symbol} ---")
            
            try:
                volume = await bot.calculate_position_size(
                    symbol,
                    signal["entry_price"],
                    signal["stop_loss"]
                )
                
                print(f"Volume calculado: {volume:.2f} lotes")
                
                # Calcular margem necessária
                margin = await client.order_calc_margin(
                    signal["action"],
                    symbol,
                    volume,
                    signal["entry_price"]
                )
                
                print(f"Margem necessária: {margin:.2f}")
                
                signal["volume"] = volume
                signal["margin"] = margin
                
            except Exception as e:
                print(f"❌ Erro no cálculo: {e}")


async def order_simulation_demo(signals: List[dict]):
    """Demonstrar simulação de ordens (verificação apenas)"""
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== SIMULAÇÃO DE ORDENS ===")
        
        for signal in signals:
            if "volume" not in signal:
                continue
                
            symbol = signal["symbol"]
            print(f"\n--- Simulando ordem para {symbol} ---")
            
            try:
                # Verificar ordem antes de enviar
                check_result = await client.order_check(
                    symbol=symbol,
                    action=signal["action"],
                    volume=signal["volume"],
                    price=signal["entry_price"]
                )
                
                print(f"✅ Verificação de ordem:")
                print(f"   Resultado: {check_result.get('retcode', 'N/A')}")
                print(f"   Comentário: {check_result.get('comment', 'N/A')}")
                print(f"   Margem: {check_result.get('margin', 0):.2f}")
                print(f"   Profit: {check_result.get('profit', 0):.2f}")
                
            except Exception as e:
                print(f"❌ Erro na verificação: {e}")


async def real_trading_demo():
    """CUIDADO: Demonstrar trading real (apenas em conta demo)"""
    
    print("⚠️  TRADING REAL EM CONTA DEMO")
    print("Esta função faria trades reais, mas está desabilitada por segurança.")
    print("Para habilitar, remova o return abaixo e tenha certeza absoluta de estar em conta demo.")
    return
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== TRADING REAL (DEMO) ===")
        
        # Exemplo de trade simples
        try:
            # Trade mínimo no EURUSD
            result = await client.buy(
                symbol="EURUSD",
                volume=0.01,  # Volume mínimo
                comment="Demo trade from Python client"
            )
            
            print(f"✅ Ordem enviada:")
            print(f"   Ticket: {result.get('order', 'N/A')}")
            print(f"   Comentário: {result.get('comment', 'N/A')}")
            
            # Aguardar 10 segundos
            print("⏳ Aguardando 10 segundos...")
            await asyncio.sleep(10)
            
            # Fechar posição se ainda estiver aberta
            positions = await client.positions_get(symbol="EURUSD")
            
            if positions:
                position = positions[0]
                close_result = await client.close_position(
                    position.ticket,
                    "Closing demo position"
                )
                
                print(f"✅ Posição fechada:")
                print(f"   Ticket: {close_result.get('order', 'N/A')}")
                print(f"   Profit: {close_result.get('profit', 0):.2f}")
            
        except Exception as e:
            print(f"❌ Erro no trading: {e}")


async def risk_management_demo():
    """Demonstrar funcionalidades de gerenciamento de risco"""
    
    async with MT5Client(demo_only=True) as client:
        await client.connect()
        
        print("=== GERENCIAMENTO DE RISCO ===")
        
        account = await client.get_account_info()
        
        print(f"\n--- Status da Conta ---")
        print(f"Saldo: {account.balance:.2f}")
        print(f"Equity: {account.equity:.2f}")
        print(f"Margem usada: {account.margin:.2f}")
        print(f"Margem livre: {account.margin_free:.2f}")
        print(f"Nível de margem: {account.margin_level:.2f}%")
        
        # Verificar posições abertas
        positions = await client.positions_get()
        
        if positions:
            print(f"\n--- Posições Abertas ({len(positions)}) ---")
            total_profit = 0
            
            for pos in positions:
                print(f"Ticket: {pos.ticket}")
                print(f"  Símbolo: {pos.symbol}")
                print(f"  Tipo: {pos.type}")
                print(f"  Volume: {pos.volume}")
                print(f"  Profit: {pos.profit:.2f}")
                total_profit += pos.profit
                
            print(f"\nProfit total: {total_profit:.2f}")
            
            # Calcular risco atual
            risk_percent = (abs(total_profit) / account.balance) * 100
            print(f"Risco atual: {risk_percent:.2f}%")
        
        else:
            print("\n--- Nenhuma Posição Aberta ---")


async def main():
    """Executar demonstração completa de trading"""
    
    print("🔥 CLIENTE MT5 MCP - DEMONSTRAÇÃO DE TRADING")
    print("=" * 55)
    
    # Verificar segurança primeiro
    is_safe = await trading_safety_demo()
    if not is_safe:
        print("❌ Trading abortado por questões de segurança")
        return
    
    # Demonstrações
    demos = [
        ("Análise de Mercado", market_analysis_demo),
        ("Gerenciamento de Risco", risk_management_demo),
    ]
    
    analyses = []
    signals = []
    
    for name, demo_func in demos:
        try:
            print(f"\n{'='*20} {name} {'='*20}")
            
            if name == "Análise de Mercado":
                analyses = await demo_func()
            else:
                await demo_func()
                
        except Exception as e:
            print(f"❌ Erro em {name}: {e}")
            logging.exception(f"Erro detalhado em {name}")
        
        await asyncio.sleep(1)
    
    # Demonstrações que dependem das análises
    if analyses:
        try:
            print(f"\n{'='*20} Geração de Sinais {'='*20}")
            signals = await signal_generation_demo(analyses)
        except Exception as e:
            print(f"❌ Erro em Geração de Sinais: {e}")
        
        if signals:
            try:
                print(f"\n{'='*20} Cálculo de Posição {'='*20}")
                await position_sizing_demo(signals)
                
                print(f"\n{'='*20} Simulação de Ordens {'='*20}")
                await order_simulation_demo(signals)
                
            except Exception as e:
                print(f"❌ Erro em cálculos: {e}")
    
    # Demonstração de trading real (desabilitada por segurança)
    print(f"\n{'='*20} Trading Real {'='*20}")
    await real_trading_demo()
    
    print("\n✅ Demonstração de trading concluída!")
    print("\n⚠️  LEMBRETE: Este foi apenas um exemplo educativo.")
    print("   Trading real envolve riscos significativos!")


if __name__ == "__main__":
    asyncio.run(main())
