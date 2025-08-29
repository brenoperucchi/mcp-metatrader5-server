#!/usr/bin/env python3
"""
Exemplo básico de uso do cliente MT5 MCP

Este exemplo demonstra como:
- Conectar ao servidor MCP
- Obter informações básicas da conta e terminal
- Buscar dados de mercado
- Listar símbolos disponíveis
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Assumindo que o cliente está instalado ou o caminho está no PYTHONPATH
try:
    from mt5_client import MT5Client, TimeframeType, CopyTicks
except ImportError:
    # Se executando do diretório do projeto
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from mt5_client import MT5Client, TimeframeType, CopyTicks


async def basic_info_demo():
    """Demonstrar funcionalidades básicas de informações"""
    
    async with MT5Client() as client:
        print("=== CONECTANDO AO MT5 ===")
        
        # Conectar ao MT5
        success = await client.connect()
        if not success:
            print("❌ Falha ao conectar ao MT5")
            return
        
        print("✅ Conectado ao MT5 com sucesso!")
        
        # Informações da conta
        print("\n=== INFORMAÇÕES DA CONTA ===")
        account = await client.get_account_info()
        print(f"Login: {account.login}")
        print(f"Servidor: {account.server}")
        print(f"Nome: {account.name}")
        print(f"Empresa: {account.company}")
        print(f"Moeda: {account.currency}")
        print(f"Saldo: {account.balance:.2f}")
        print(f"Equity: {account.equity:.2f}")
        print(f"Margem: {account.margin:.2f}")
        print(f"Margem Livre: {account.margin_free:.2f}")
        print(f"Tipo de conta: {'DEMO' if account.is_demo else 'REAL'}")
        
        # Informações do terminal
        print("\n=== INFORMAÇÕES DO TERMINAL ===")
        terminal = await client.get_terminal_info()
        print(f"Nome: {terminal.get('name', 'N/A')}")
        print(f"Empresa: {terminal.get('company', 'N/A')}")
        print(f"Path: {terminal.get('path', 'N/A')}")
        print(f"Build: {terminal.get('build', 'N/A')}")
        
        # Versão do MT5
        print("\n=== VERSÃO DO MT5 ===")
        version = await client.get_version()
        print(f"Versão: {version}")


async def market_data_demo():
    """Demonstrar funcionalidades de dados de mercado"""
    
    async with MT5Client() as client:
        await client.connect()
        
        print("=== DADOS DE MERCADO ===")
        
        # Símbolos disponíveis (primeiros 10)
        print("\n--- Símbolos Disponíveis (primeiros 10) ---")
        symbols = await client.get_symbols()
        
        for i, symbol in enumerate(symbols[:10]):
            print(f"{i+1:2d}. {symbol.name:12} - {symbol.description}")
        
        print(f"\nTotal de símbolos: {len(symbols)}")
        
        # Dados específicos do EURUSD (se disponível)
        target_symbol = "EURUSD"
        eurusd_symbols = [s for s in symbols if s.name == target_symbol]
        
        if eurusd_symbols:
            print(f"\n--- Dados do {target_symbol} ---")
            symbol_info = eurusd_symbols[0]
            
            print(f"Descrição: {symbol_info.description}")
            print(f"Dígitos: {symbol_info.digits}")
            print(f"Spread: {symbol_info.spread}")
            print(f"Volume mínimo: {symbol_info.volume_min}")
            print(f"Volume máximo: {symbol_info.volume_max}")
            print(f"Passo de volume: {symbol_info.volume_step}")
            
            # Último tick
            try:
                tick = await client.get_tick(target_symbol)
                print(f"Último tick:")
                print(f"  Bid: {tick.bid:.5f}")
                print(f"  Ask: {tick.ask:.5f}")
                print(f"  Spread: {(tick.ask - tick.bid):.5f}")
                print(f"  Volume: {tick.volume}")
                print(f"  Horário: {tick.time}")
            except Exception as e:
                print(f"❌ Erro ao obter tick: {e}")
                
        else:
            print(f"⚠️  Símbolo {target_symbol} não encontrado")


async def historical_data_demo():
    """Demonstrar obtenção de dados históricos"""
    
    async with MT5Client() as client:
        await client.connect()
        
        print("=== DADOS HISTÓRICOS ===")
        
        # Verificar se EURUSD está disponível
        symbols = await client.get_symbols()
        target_symbol = "EURUSD"
        
        if not any(s.name == target_symbol for s in symbols):
            # Usar o primeiro símbolo disponível
            if symbols:
                target_symbol = symbols[0].name
                print(f"EURUSD não encontrado, usando {target_symbol}")
            else:
                print("❌ Nenhum símbolo disponível")
                return
        
        try:
            # Velas H1 das últimas 24 horas
            print(f"\n--- Velas H1 de {target_symbol} (últimas 24h) ---")
            date_from = datetime.now() - timedelta(hours=24)
            
            candles = await client.copy_rates_from(
                target_symbol,
                TimeframeType.H1,
                date_from,
                count=24
            )
            
            print(f"Obtidas {len(candles)} velas:")
            print("Data/Hora            | Open     | High     | Low      | Close    | Volume")
            print("-" * 75)
            
            for candle in candles[-5:]:  # Últimas 5 velas
                print(f"{candle.time} | {candle.open:8.5f} | {candle.high:8.5f} | "
                      f"{candle.low:8.5f} | {candle.close:8.5f} | {candle.tick_volume:6d}")
        
        except Exception as e:
            print(f"❌ Erro ao obter dados históricos: {e}")
        
        try:
            # Ticks das últimas 2 horas
            print(f"\n--- Ticks de {target_symbol} (últimas 100) ---")
            
            ticks = await client.copy_ticks_from(
                target_symbol,
                datetime.now() - timedelta(hours=2),
                count=100,
                flags=CopyTicks.ALL
            )
            
            print(f"Obtidos {len(ticks)} ticks:")
            print("Data/Hora            | Bid      | Ask      | Volume")
            print("-" * 50)
            
            for tick in ticks[-3:]:  # Últimos 3 ticks
                print(f"{tick.time} | {tick.bid:8.5f} | {tick.ask:8.5f} | {tick.volume:6d}")
        
        except Exception as e:
            print(f"❌ Erro ao obter ticks: {e}")


async def positions_and_orders_demo():
    """Demonstrar consulta de posições e ordens"""
    
    async with MT5Client() as client:
        await client.connect()
        
        print("=== POSIÇÕES E ORDENS ===")
        
        # Posições abertas
        print("\n--- Posições Abertas ---")
        positions = await client.positions_get()
        
        if positions:
            print(f"Total de posições: {len(positions)}")
            for pos in positions:
                print(f"Ticket: {pos.ticket}, Símbolo: {pos.symbol}, "
                      f"Tipo: {pos.type}, Volume: {pos.volume}, "
                      f"Preço: {pos.price_open}, Profit: {pos.profit:.2f}")
        else:
            print("Nenhuma posição aberta")
        
        # Ordens ativas
        print("\n--- Ordens Ativas ---")
        orders = await client.orders_get()
        
        if orders:
            print(f"Total de ordens: {len(orders)}")
            for order in orders:
                print(f"Ticket: {order.ticket}, Símbolo: {order.symbol}, "
                      f"Tipo: {order.type}, Volume: {order.volume_initial}, "
                      f"Preço: {order.price_open}")
        else:
            print("Nenhuma ordem ativa")


async def statistics_demo():
    """Demonstrar estatísticas do cliente"""
    
    async with MT5Client() as client:
        await client.connect()
        
        print("=== ESTATÍSTICAS DO CLIENTE ===")
        
        # Fazer algumas operações para gerar estatísticas
        await client.get_account_info()
        await client.get_symbols()
        await client.get_terminal_info()
        
        # Obter estatísticas
        stats = client.get_stats()
        
        print(f"Conectado: {stats['connected']}")
        print(f"Servidor: {stats['server_url']}")
        print(f"Requisições enviadas: {stats['requests_sent']}")
        print(f"Requisições bem-sucedidas: {stats['requests_successful']}")
        print(f"Requisições falharam: {stats['requests_failed']}")
        print(f"Latência média: {stats['avg_latency_ms']:.1f}ms")
        print(f"Símbolos em cache: {stats['symbols_cached']}")
        print(f"Modo demo apenas: {stats['demo_only']}")
        
        # Teste de ping
        latency = await client.ping_server()
        print(f"Ping atual: {latency:.1f}ms")


async def main():
    """Executar todas as demonstrações"""
    
    print("🚀 CLIENTE MT5 MCP - DEMONSTRAÇÃO BÁSICA")
    print("=" * 50)
    
    demos = [
        ("Informações Básicas", basic_info_demo),
        ("Dados de Mercado", market_data_demo),
        ("Dados Históricos", historical_data_demo),
        ("Posições e Ordens", positions_and_orders_demo),
        ("Estatísticas", statistics_demo),
    ]
    
    for name, demo_func in demos:
        try:
            print(f"\n{'='*20} {name} {'='*20}")
            await demo_func()
            
        except Exception as e:
            print(f"❌ Erro em {name}: {e}")
            logging.exception(f"Erro detalhado em {name}")
        
        print(f"{'='*(42+len(name))}")
        
        # Pequena pausa entre demonstrações
        await asyncio.sleep(1)
    
    print("\n✅ Demonstração concluída!")


if __name__ == "__main__":
    # Executar demonstração
    asyncio.run(main())
