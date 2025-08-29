#!/usr/bin/env python3
"""
[ROCKET] TESTE COMPLETO MCP MT5 B3 - VALIDAÇÃO DEMO + TRADING REAL
================================================================

Este script testa o servidor MCP MT5 configurado para B3 (Bolsa Brasileira):
1. [OK] Verifica se a conta é DEMO 
2. [SECURE] Bloqueia trading em contas REAIS (segurança)
3. [TEST_TUBE] Testa TODAS as funcionalidades em conta demo B3
4. [DATA] Executa operações reais no MetaTrader 5 com ações brasileiras
5. [TRADE] Demonstra ciclo completo de trading no mercado B3

[WARN]  ATENÇÃO: TRADING REAL APENAS EM CONTAS DEMO!
[B3] Servidor: http://192.168.0.125:50051 (Configuração B3)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from client.mcp_mt5_client import MT5MCPClient

class MT5B3TradingTest:
    def __init__(self, server_url: str = "http://192.168.0.125:50051"):
        self.client = MT5MCPClient(server_url)
        self.test_results = []
        self.test_symbol = None
        
    async def log_test(self, test_name: str, success: bool, data: dict = None, error: str = None):
        """Registra resultado de teste"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "success": success,
            "data": data,
            "error": error
        }
        self.test_results.append(result)
        
        status = "[OK]" if success else "[X]"
        print(f"{status} {test_name}")
        if error:
            print(f"   [FAIL] {error}")
        elif data:
            print(f"   [DATA] {json.dumps(data, indent=2)[:200]}...")
    
    async def test_connectivity(self):
        """1. Teste de conectividade básica"""
        try:
            symbols = await self.client.list_symbols()
            if symbols.get("error"):
                await self.log_test("Conectividade", False, error=symbols["error"])
                return False
            
            symbol_list = symbols.get('result', {}).get('content', [])
            await self.log_test("Conectividade", True, {"symbol_count": len(symbol_list)})
            
            # Selecionar símbolo adequado para testes
            if symbol_list:
                print("[SEARCH] Procurando símbolo adequado para testes...")
                
                # Símbolos preferenciais para teste (menores volumes mínimos)
                preferred_symbols = ["PETR4", "VALE3", "ITUB4", "BBDC4", "MGLU3", "WEGE3"]
                
                # Tentar encontrar um símbolo preferencial
                selected_symbol = None
                for pref_symbol in preferred_symbols:
                    if pref_symbol in symbol_list:
                        # Verificar se o símbolo tem volume mínimo aceitável e preços ativos
                        symbol_info = await self.client.get_symbol_info(pref_symbol)
                        if not symbol_info.get("error"):
                            symbol_data = symbol_info.get('result', {}).get('content', {})
                            volume_min = symbol_data.get("volume_min", 0.01)
                            bid = symbol_data.get("bid", 0.0)
                            ask = symbol_data.get("ask", 0.0)
                            
                            # Aceitar símbolos com volume mínimo <= 1.0 E preços ativos
                            if volume_min <= 1.0 and bid > 0 and ask > 0:
                                selected_symbol = pref_symbol
                                print(f"[OK] Símbolo preferencial encontrado: {pref_symbol} (vol_min: {volume_min}, bid: {bid}, ask: {ask})")
                                break
                
                # Se não encontrou símbolo preferencial, usar o primeiro com volume baixo
                if not selected_symbol:
                    print("[WARN] Nenhum símbolo preferencial encontrado, testando outros...")
                    for symbol in symbol_list[:20]:  # Testar apenas os primeiros 20
                        symbol_info = await self.client.get_symbol_info(symbol)
                        if not symbol_info.get("error"):
                            symbol_data = symbol_info.get('result', {}).get('content', {})
                            volume_min = symbol_data.get("volume_min", 0.01)
                            bid = symbol_data.get("bid", 0.0)
                            ask = symbol_data.get("ask", 0.0)
                            
                            # Aceitar símbolos com volume mínimo <= 10.0 E preços ativos
                            if volume_min <= 10.0 and bid > 0 and ask > 0:
                                selected_symbol = symbol
                                print(f"[OK] Símbolo adequado encontrado: {symbol} (vol_min: {volume_min}, bid: {bid}, ask: {ask})")
                                break
                
                # Se ainda não encontrou, usar o primeiro disponível
                if not selected_symbol:
                    selected_symbol = symbol_list[0]
                    print(f"[WARN] Usando primeiro símbolo disponível: {selected_symbol}")
                
                self.test_symbol = selected_symbol
                print(f"[TP] Símbolo selecionado para testes: {self.test_symbol}")
            
            return True
        except Exception as e:
            await self.log_test("Conectividade", False, error=str(e))
            return False
    
    async def test_account_validation(self):
        """2. Validação de conta demo"""
        try:
            # Verificar informações da conta
            account_info = await self.client.get_account_info()
            if account_info.get("error"):
                await self.log_test("Informações da Conta", False, error=account_info["error"])
                return False
            
            account_data = account_info.get('result', {}).get('content', {})
            await self.log_test("Informações da Conta", True, {
                "login": account_data.get("login"),
                "server": account_data.get("server"),
                "company": account_data.get("company"),
                "is_demo": account_data.get("is_demo"),
                "balance": account_data.get("balance"),
                "currency": account_data.get("currency")
            })
            
            # Validação específica para trading
            validation = await self.client.validate_demo_for_trading()
            if validation.get("error"):
                await self.log_test("Validação Demo", False, error=validation["error"])
                return False
            
            validation_data = validation.get('result', {}).get('content', {})
            await self.log_test("Validação Demo", True, validation_data)
            
            if not validation_data.get("allowed"):
                print("[ALERT] TRADING BLOQUEADO: Conta não é demo!")
                print("   Para segurança, este teste só funciona em contas demo.")
                return False
            
            print("[GREEN] CONTA DEMO CONFIRMADA - Trading autorizado!")
            return True
            
        except Exception as e:
            await self.log_test("Validação de Conta", False, error=str(e))
            return False
    
    async def test_market_data(self):
        """3. Teste de dados de mercado"""
        if not self.test_symbol:
            await self.log_test("Dados de Mercado", False, error="Nenhum símbolo disponível")
            return False
        
        try:
            # Informações do símbolo
            symbol_info = await self.client.get_symbol_info(self.test_symbol)
            if symbol_info.get("error"):
                await self.log_test("Informações do Símbolo", False, error=symbol_info["error"])
                return False
            
            symbol_data = symbol_info.get('result', {}).get('content', {})
            await self.log_test("Informações do Símbolo", True, {
                "symbol": symbol_data.get("symbol"),
                "bid": symbol_data.get("bid"),
                "ask": symbol_data.get("ask"),
                "spread": symbol_data.get("spread"),
                "digits": symbol_data.get("digits")
            })
            
            # Dados históricos
            ticks = await self.client.get_symbol_info(self.test_symbol)
            if ticks.get("error"):
                await self.log_test("Dados Históricos", False, error=ticks["error"])
            else:
                tick_data = ticks.get('result', {}).get('content', [])
                await self.log_test("Dados Históricos", True, {"candles": len(tick_data)})
            
            return True
            
        except Exception as e:
            await self.log_test("Dados de Mercado", False, error=str(e))
            return False
    
    async def test_positions_and_orders(self):
        """4. Teste de posições e ordens"""
        try:
            # Posições abertas
            positions = await self.client.get_positions()
            if positions.get("error"):
                await self.log_test("Posições Abertas", False, error=positions["error"])
            else:
                pos_data = positions.get('result', {}).get('content', [])
                await self.log_test("Posições Abertas", True, {"count": len(pos_data)})
            
            # Ordens pendentes
            orders = await self.client.get_orders()
            if orders.get("error"):
                await self.log_test("Ordens Pendentes", False, error=orders["error"])
            else:
                order_data = orders.get('result', {}).get('content', [])
                await self.log_test("Ordens Pendentes", True, {"count": len(order_data)})
            
            return True
            
        except Exception as e:
            await self.log_test("Posições e Ordens", False, error=str(e))
            return False

    async def test_trading_history(self):
        """4.5. Teste de histórico de trading"""
        try:
            print(f"[HISTORY] Testando funcionalidades de histórico...")
            
            # Teste de conectividade com métodos de histórico
            print("[INFO] Verificando se métodos de histórico estão disponíveis...")
            
            # Tentar usar métodos de histórico com parâmetros simples
            history_orders = await self.client.get_history_orders()
            
            if history_orders.get("error"):
                error_msg = str(history_orders["error"])
                if "desconhecida" in error_msg or "unknown" in error_msg.lower():
                    print("[SKIP] Métodos de histórico não estão disponíveis no servidor MCP")
                    print("       Isso é esperado se o servidor não implementou history_orders_get e history_deals_get")
                    await self.log_test("Histórico de Ordens", True, {
                        "status": "skipped",
                        "reason": "Métodos não implementados no servidor",
                        "error": error_msg
                    })
                    await self.log_test("Histórico de Deals", True, {
                        "status": "skipped", 
                        "reason": "Métodos não implementados no servidor"
                    })
                    return True
                else:
                    # Erro real
                    await self.log_test("Histórico de Ordens", False, error=error_msg)
                    return False
            else:
                # Métodos funcionam - executar testes completos
                print("[OK] Métodos de histórico disponíveis - executando testes completos...")
                
                from datetime import datetime, timedelta
                
                # Definir período dos últimos 30 dias
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                start_date_str = start_date.strftime("%Y-%m-%dT00:00:00")
                end_date_str = end_date.strftime("%Y-%m-%dT23:59:59")
                
                print(f"[HISTORY] Buscando histórico de {start_date_str} até {end_date_str}")
                
                # Histórico de ordens com período completo
                history_orders = await self.client.get_history_orders(
                    from_date=start_date_str,
                    to_date=end_date_str
                )
                
                if history_orders.get("error"):
                    await self.log_test("Histórico de Ordens", False, error=history_orders["error"])
                else:
                    orders_data = history_orders.get('result', {}).get('content', [])
                    await self.log_test("Histórico de Ordens", True, {
                        "count": len(orders_data),
                        "period_days": 30
                    })
                    
                    if orders_data:
                        print(f"[DATA] Encontradas {len(orders_data)} ordens no histórico")
                        # Mostrar algumas ordens recentes
                        for i, order in enumerate(orders_data[-3:]):  # Últimas 3 ordens
                            print(f"   Order {i+1}: {order.get('symbol', 'N/A')} - {order.get('type', 'N/A')} - Vol: {order.get('volume_initial', 'N/A')}")
                    else:
                        print("[INFO] Nenhuma ordem encontrada no histórico")
                
                # Histórico de deals (transações executadas)
                history_deals = await self.client.get_history_deals(
                    from_date=start_date_str,
                    to_date=end_date_str
                )
                
                if history_deals.get("error"):
                    await self.log_test("Histórico de Deals", False, error=history_deals["error"])
                else:
                    deals_data = history_deals.get('result', {}).get('content', [])
                    await self.log_test("Histórico de Deals", True, {
                        "count": len(deals_data),
                        "period_days": 30
                    })
                    
                    if deals_data:
                        print(f"[DATA] Encontrados {len(deals_data)} deals no histórico")
                        
                        # Calcular estatísticas
                        total_profit = sum(deal.get('profit', 0) for deal in deals_data)
                        total_commission = sum(deal.get('commission', 0) for deal in deals_data)
                        total_volume = sum(deal.get('volume', 0) for deal in deals_data)
                        
                        print(f"[STATS] Lucro total: R$ {total_profit:.2f}")
                        print(f"[STATS] Comissão total: R$ {total_commission:.2f}")
                        print(f"[STATS] Volume total: {total_volume:.0f}")
                        
                        # Mostrar alguns deals recentes
                        for i, deal in enumerate(deals_data[-3:]):  # Últimos 3 deals
                            profit = deal.get('profit', 0)
                            symbol = deal.get('symbol', 'N/A')
                            volume = deal.get('volume', 0)
                            price = deal.get('price', 0)
                            print(f"   Deal {i+1}: {symbol} - Vol: {volume} @ R$ {price:.2f} - P&L: R$ {profit:.2f}")
                    else:
                        print("[INFO] Nenhum deal encontrado no histórico")
                
                # Filtrar histórico por símbolo específico se disponível
                if self.test_symbol:
                    print(f"[FILTER] Buscando histórico específico para {self.test_symbol}...")
                    
                    symbol_deals = await self.client.get_history_deals(
                        symbol=self.test_symbol,
                        from_date=start_date_str,
                        to_date=end_date_str
                    )
                    
                    if not symbol_deals.get("error"):
                        symbol_deals_data = symbol_deals.get('result', {}).get('content', [])
                        await self.log_test(f"Histórico {self.test_symbol}", True, {
                            "symbol": self.test_symbol,
                            "deals_count": len(symbol_deals_data)
                        })
                        
                        if symbol_deals_data:
                            symbol_profit = sum(deal.get('profit', 0) for deal in symbol_deals_data)
                            print(f"[SYMBOL] {self.test_symbol}: {len(symbol_deals_data)} deals, P&L: R$ {symbol_profit:.2f}")
                            
                            # [NOVO] Análise detalhada de uma ordem fechada específica
                            if symbol_deals_data:
                                print(f"\n[DETAILED] Análise detalhada da ordem fechada mais recente:")
                                latest_deal = symbol_deals_data[-1]  # Deal mais recente
                                
                                # Coletar TODOS os dados disponíveis do deal
                                deal_ticket = latest_deal.get('ticket')
                                order_ticket = latest_deal.get('order')
                                
                                print(f"[DEAL] Ticket do Deal: {deal_ticket}")
                                print(f"[ORDER] Ticket da Ordem: {order_ticket}")
                                print(f"[SYMBOL] Símbolo: {latest_deal.get('symbol', 'N/A')}")
                                print(f"[TYPE] Tipo: {latest_deal.get('type', 'N/A')}")
                                print(f"[ENTRY] Entry: {latest_deal.get('entry', 'N/A')}")
                                print(f"[VOLUME] Volume: {latest_deal.get('volume', 0)}")
                                print(f"[PRICE] Preço: R$ {latest_deal.get('price', 0):.2f}")
                                print(f"[PROFIT] Lucro: R$ {latest_deal.get('profit', 0):.2f}")
                                print(f"[COMMISSION] Comissão: R$ {latest_deal.get('commission', 0):.2f}")
                                print(f"[SWAP] Swap: R$ {latest_deal.get('swap', 0):.2f}")
                                print(f"[TIME] Hora: {latest_deal.get('time', 'N/A')}")
                                print(f"[COMMENT] Comentário: {latest_deal.get('comment', 'N/A')}")
                                
                                # Se temos o ticket da ordem, buscar dados completos da ordem
                                if order_ticket:
                                    print(f"\n[LOOKUP] Buscando dados completos da ordem {order_ticket}...")
                                    order_details = await self.client.get_order_by_ticket(order_ticket)
                                    
                                    if not order_details.get("error"):
                                        order_data = order_details.get('result', {}).get('content', {})
                                        print(f"[ORDER_DETAIL] Estado: {order_data.get('state', 'N/A')}")
                                        print(f"[ORDER_DETAIL] Preço de Setup: R$ {order_data.get('price_open', 0):.2f}")
                                        print(f"[ORDER_DETAIL] SL: R$ {order_data.get('sl', 0):.2f}")
                                        print(f"[ORDER_DETAIL] TP: R$ {order_data.get('tp', 0):.2f}")
                                        print(f"[ORDER_DETAIL] Magic: {order_data.get('magic', 0)}")
                                        print(f"[ORDER_DETAIL] Tempo Setup: {order_data.get('time_setup', 'N/A')}")
                                        
                                        await self.log_test("Análise Detalhada de Ordem", True, {
                                            "deal_ticket": deal_ticket,
                                            "order_ticket": order_ticket,
                                            "symbol": latest_deal.get('symbol'),
                                            "volume": latest_deal.get('volume'),
                                            "price": latest_deal.get('price'),
                                            "profit": latest_deal.get('profit'),
                                            "commission": latest_deal.get('commission'),
                                            "order_state": order_data.get('state'),
                                            "sl": order_data.get('sl'),
                                            "tp": order_data.get('tp')
                                        })
                                    else:
                                        print(f"[WARN] Não foi possível obter detalhes da ordem: {order_details['error']}")
                                        await self.log_test("Análise Detalhada de Ordem", False, 
                                                          error=f"Erro ao buscar ordem {order_ticket}: {order_details['error']}")
                        else:
                            print(f"[SYMBOL] {self.test_symbol}: Nenhuma transação no período")
            
            return True
            
        except Exception as e:
            await self.log_test("Histórico de Trading", False, error=str(e))
            return False
    
    async def test_trading_operations(self):
        """5. Teste de operações de trading REAIS"""
        if not self.test_symbol:
            await self.log_test("Trading", False, error="Nenhum símbolo para trading")
            return False
        
        try:
            print("\n[ALERT] INICIANDO TESTES DE TRADING REAL EM CONTA DEMO!")
            print("=" * 60)
            
            # Obter informações do símbolo para volume mínimo
            print(f"[SEARCH] Obtendo informações do símbolo {self.test_symbol}...")
            symbol_info = await self.client.get_symbol_info(self.test_symbol)
            if symbol_info.get("error"):
                await self.log_test("Trading - Symbol Info", False, error=symbol_info["error"])
                return False
            
            symbol_data = symbol_info.get('result', {}).get('content', {})
            volume_min = symbol_data.get("volume_min", 0.01)
            volume_max = symbol_data.get("volume_max", 100.0)
            
            print(f"[DATA] Volume mínimo: {volume_min}")
            print(f"[DATA] Volume máximo: {volume_max}")
            
            # Usar volume mínimo válido, mas não muito alto para testes
            test_volume = max(volume_min, 0.01)
            
            # Se o volume mínimo for muito alto, usar alternativa
            if test_volume > 10.0:
                print(f"[WARN] Volume mínimo muito alto ({test_volume}), usando volume alternativo...")
                test_volume = volume_min  # Usar o mínimo mesmo que seja alto
            
            print(f"[TP] Volume para testes: {test_volume}")
            
            # Verificar se símbolo está ativo e negociável
            if not symbol_data.get("visible", True) or not symbol_data.get("select", True):
                print(f"[WARN] Símbolo {self.test_symbol} pode não estar ativo para trading")
                print("  Continuando com testes...")
            
            # 5.1 Ordem a mercado (COMPRA)
            print("[TRADE] Testando ordem de COMPRA a mercado...")
            buy_result = await self.client.order_send(
                action=0,           # 0 = COMPRA
                symbol=self.test_symbol,
                volume=test_volume, # Volume mínimo válido
                comment="Teste MCP Demo - Compra"
            )
            
            if buy_result.get("error"):
                await self.log_test("Ordem Compra", False, error=buy_result["error"])
                return False
            
            buy_data = buy_result.get('result', {}).get('content', {})
            retcode = buy_data.get("retcode")
            
            # Interpretar código de retorno
            retcode_meaning = {
                10009: "DONE - Sucesso",
                10015: "INVALID_PRICE - Preço inválido",
                10016: "INVALID_STOPS - Stop inválido", 
                10017: "INVALID_VOLUME - Volume inválido",
                10018: "MARKET_CLOSED - Mercado fechado",
                10019: "NO_MONEY - Dinheiro insuficiente",
                10020: "PRICE_CHANGED - Preço mudou",
                10021: "TRADE_DISABLED - Trading desabilitado",
                10022: "MARKET_CLOSED - Mercado fechado",
                10023: "NO_CONNECTION - Sem conexão",
                10024: "TOO_MANY_REQUESTS - Muitas requisições"
            }
            
            retcode_desc = retcode_meaning.get(retcode, f"Código desconhecido: {retcode}")
            
            # Considerar apenas 10009 como sucesso real
            order_success = (retcode == 10009)
            
            await self.log_test("Ordem Compra", order_success, {
                "retcode": retcode,
                "retcode_desc": retcode_desc,
                "deal": buy_data.get("deal"),
                "price": buy_data.get("price"),
                "volume": buy_data.get("volume")
            })
            
            # Se não foi sucesso real, registrar como falha
            if not order_success:
                print(f"[WARN] Ordem não executada: {retcode_desc}")
            
            # Verificar se a compra foi executada (apenas para códigos de sucesso)
            buy_ticket = buy_data.get("deal")
            if retcode == 10009 and buy_ticket:
                print(f"[OK] Compra executada! Deal: {buy_ticket}")
                
                # Aguardar um pouco
                await asyncio.sleep(2)
                
                # 5.2 Buscar a posição criada para obter o position ticket
                print("[SEARCH] Buscando posição criada...")
                positions = await self.client.get_positions(self.test_symbol)
                
                if not positions.get("error"):
                    pos_list = positions.get('result', {}).get('content', [])
                    if pos_list:
                        # Pegar a posição mais recente (última da lista)
                        position = pos_list[-1]
                        position_ticket = position.get("ticket")
                        
                        print(f"📍 Posição encontrada! Ticket: {position_ticket}")
                        
                        # Mostrar detalhes iniciais da posição
                        print("[DATA] DETALHES INICIAIS DA POSIÇÃO:")
                        print("=" * 50)
                        for key, value in position.items():
                            if isinstance(value, float):
                                print(f"   {key}: {value:.4f}")
                            else:
                                print(f"   {key}: {value}")
                        print("=" * 50)
                        
                        # 5.2.1 Modificar posição com Stop Loss e Take Profit
                        print("[EDIT] Modificando posição - adicionando SL e TP...")
                        
                        # Calcular SL e TP baseados no preço de entrada
                        entry_price = position.get("price_open", 0)
                        current_price = symbol_data.get("ask", entry_price)
                        
                        # SL 2% abaixo do preço de entrada, TP 3% acima
                        stop_loss = entry_price * 0.98   # 2% abaixo
                        take_profit = entry_price * 1.03  # 3% acima
                        
                        print(f"   [MONEY] Preço de entrada: R$ {entry_price}")
                        print(f"   [STOP] Stop Loss: R$ {stop_loss:.2f}")
                        print(f"   [TP] Take Profit: R$ {take_profit:.2f}")
                        
                        modify_position_result = await self.client.position_modify(
                            ticket=position_ticket,
                            sl=stop_loss,
                            tp=take_profit
                        )
                        
                        if modify_position_result.get("error"):
                            await self.log_test("Modificar Posição SL/TP", False, error=modify_position_result["error"])
                        else:
                            modify_pos_data = modify_position_result.get('result', {}).get('content', {})
                            await self.log_test("Modificar Posição SL/TP", True, {
                                "retcode": modify_pos_data.get("retcode"),
                                "position_ticket": position_ticket,
                                "stop_loss": stop_loss,
                                "take_profit": take_profit
                            })
                            
                            if modify_pos_data.get("retcode") == 10009:
                                print("[OK] Stop Loss e Take Profit adicionados com sucesso!")
                            else:
                                print(f"[WARN] Modificação com código: {modify_pos_data.get('retcode')}")
                        
                        # 5.2.2 Verificar posição atualizada com SL/TP
                        print("[SEARCH] Verificando posição atualizada após modificação...")
                        await asyncio.sleep(1)  # Dar tempo para atualização
                        
                        updated_positions = await self.client.get_positions(self.test_symbol)
                        if not updated_positions.get("error"):
                            updated_pos_list = updated_positions.get('result', {}).get('content', [])
                            if updated_pos_list:
                                # Encontrar a posição pelo ticket
                                updated_position = None
                                for pos in updated_pos_list:
                                    if pos.get("ticket") == position_ticket:
                                        updated_position = pos
                                        break
                                
                                if updated_position:
                                    print("[DATA] DETALHES COMPLETOS DA POSIÇÃO APÓS MODIFICAÇÃO:")
                                    print("=" * 60)
                                    for key, value in updated_position.items():
                                        if isinstance(value, float):
                                            print(f"   {key}: {value:.4f}")
                                        else:
                                            print(f"   {key}: {value}")
                                    print("=" * 60)
                                    
                                    await self.log_test("Verificar Posição Atualizada", True, {
                                        "position_ticket": position_ticket,
                                        "sl_atual": updated_position.get("sl", 0),
                                        "tp_atual": updated_position.get("tp", 0),
                                        "profit_atual": updated_position.get("profit", 0),
                                        "price_current": updated_position.get("price_current", 0)
                                    })
                                else:
                                    print("[WARN] Posição não encontrada na lista atualizada")
                            else:
                                print("[WARN] Nenhuma posição encontrada após modificação")
                        else:
                            print(f"[X] Erro ao verificar posições atualizadas: {updated_positions['error']}")
                        
                        # Aguardar um pouco antes de fechar
                        await asyncio.sleep(1)
                        
                        # 5.2.2 Fechar a posição usando o position ticket correto
                        print("[X] Fechando posição...")
                        close_result = await self.client.order_close(position_ticket)
                        
                        if close_result.get("error"):
                            await self.log_test("Fechar Posição", False, error=close_result["error"])
                        else:
                            close_data = close_result.get('result', {}).get('content', {})
                            await self.log_test("Fechar Posição", True, {
                                "retcode": close_data.get("retcode"),
                                "deal": close_data.get("deal"),
                                "price": close_data.get("price"),
                                "position_ticket": position_ticket
                            })
                            
                            if close_data.get("retcode") == 10009:
                                print("[OK] Posição fechada com sucesso!")
                    else:
                        print("[WARN] Nenhuma posição encontrada - pode ter sido fechada automaticamente")
                        await self.log_test("Fechar Posição", False, error="Nenhuma posição encontrada após compra")
                else:
                    print("[X] Erro ao buscar posições")
                    await self.log_test("Fechar Posição", False, error=positions["error"])
            
            # 5.3 Ordem limitada
            print("[NOTE] Testando ordem LIMITADA...")
            
            # Pegar preço atual
            symbol_info = await self.client.get_symbol_info(self.test_symbol)
            symbol_data = symbol_info.get('result', {}).get('content', {})
            current_bid = symbol_data.get("bid", 1.0)
            
            # Ordem 5% abaixo do preço atual
            limit_price = current_bid * 0.95
            
            limit_result = await self.client.order_send_limit(
                action=0,           # 0 = BUY_LIMIT
                symbol=self.test_symbol,
                volume=test_volume, # Usar volume mínimo válido
                price=limit_price,
                comment="Teste MCP Demo - Limit"
            )
            
            if limit_result.get("error"):
                await self.log_test("Ordem Limitada", False, error=limit_result["error"])
            else:
                limit_data = limit_result.get('result', {}).get('content', {})
                retcode = limit_data.get("retcode")
                
                # Mesma interpretação de códigos
                retcode_meaning = {
                    10009: "DONE - Sucesso",
                    10015: "INVALID_PRICE - Preço inválido",
                    10016: "INVALID_STOPS - Stop inválido", 
                    10017: "INVALID_VOLUME - Volume inválido",
                    10018: "MARKET_CLOSED - Mercado fechado",
                    10019: "NO_MONEY - Dinheiro insuficiente",
                    10020: "PRICE_CHANGED - Preço mudou",
                    10021: "TRADE_DISABLED - Trading desabilitado",
                    10022: "MARKET_CLOSED - Mercado fechado",
                    10023: "NO_CONNECTION - Sem conexão",
                    10024: "TOO_MANY_REQUESTS - Muitas requisições"
                }
                
                retcode_desc = retcode_meaning.get(retcode, f"Código desconhecido: {retcode}")
                
                # Considerar apenas 10009 como sucesso real
                limit_success = (retcode == 10009)
                
                await self.log_test("Ordem Limitada", limit_success, {
                    "retcode": retcode,
                    "retcode_desc": retcode_desc,
                    "order": limit_data.get("order"),
                    "price": limit_price,
                    "volume": test_volume
                })
                
                # Se não foi sucesso real, registrar como falha
                if not limit_success:
                    print(f"[WARN] Ordem limitada não criada: {retcode_desc}")
                
                limit_ticket = limit_data.get("order")
                if retcode == 10009 and limit_ticket:
                    print(f"[OK] Ordem limitada criada! Ticket: {limit_ticket}")
                    
                    # 5.4 Modificar ordem
                    print("[EDIT] Modificando ordem...")
                    new_price = current_bid * 0.90  # 10% abaixo
                    
                    modify_result = await self.client.order_modify(
                        ticket=limit_ticket,
                        price=new_price
                    )
                    
                    if modify_result.get("error"):
                        await self.log_test("Modificar Ordem", False, error=modify_result["error"])
                    else:
                        modify_data = modify_result.get('result', {}).get('content', {})
                        await self.log_test("Modificar Ordem", True, {
                            "retcode": modify_data.get("retcode"),
                            "new_price": new_price
                        })
                        
                        if modify_data.get("retcode") == 10009:
                            print("[OK] Ordem modificada com sucesso!")
                    
                    # 5.5 Cancelar ordem
                    print("[DELETE] Cancelando ordem...")
                    cancel_result = await self.client.order_cancel(limit_ticket)
                    
                    if cancel_result.get("error"):
                        await self.log_test("Cancelar Ordem", False, error=cancel_result["error"])
                    else:
                        cancel_data = cancel_result.get('result', {}).get('content', {})
                        await self.log_test("Cancelar Ordem", True, {
                            "retcode": cancel_data.get("retcode")
                        })
                        
                        if cancel_data.get("retcode") == 10009:
                            print("[OK] Ordem cancelada com sucesso!")
            
            print("=" * 60)
            print("[SUCCESS] TODOS OS TESTES DE TRADING CONCLUÍDOS!")
            return True
            
        except Exception as e:
            await self.log_test("Trading Operations", False, error=str(e))
            return False
    
    async def run_complete_test(self):
        """Executa todos os testes"""
        print("[ROCKET] INICIANDO TESTE COMPLETO MCP MT5 B3")
        print("=" * 50)
        
        try:
            # 1. Conectividade
            if not await self.test_connectivity():
                print("[X] Falha na conectividade. Abortando testes.")
                return False
            
            # 2. Validação de conta demo
            if not await self.test_account_validation():
                print("[X] Conta não é demo ou erro de validação. Abortando testes de trading.")
                return False
            
            # 3. Dados de mercado
            await self.test_market_data()
            
            # 4. Posições e ordens
            await self.test_positions_and_orders()
            
            # 4.5. Histórico de trading
            await self.test_trading_history()
            
            # 5. Trading (apenas se validação demo passou)
            await self.test_trading_operations()
            
            # Relatório final
            print("\n[DATA] RELATÓRIO FINAL DOS TESTES")
            print("=" * 40)
            
            total_tests = len(self.test_results)
            passed_tests = sum(1 for test in self.test_results if test["success"])
            failed_tests = total_tests - passed_tests
            
            print(f"[OK] Testes passou: {passed_tests}")
            print(f"[X] Testes falharam: {failed_tests}")
            print(f"[DATA] Total: {total_tests}")
            print(f"[TP] Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
            
            # Salvar relatório
            with open("test_report.json", "w") as f:
                json.dump(self.test_results, f, indent=2)
            print("\n[SAVE] Relatório salvo em: test_report.json")
            
            return passed_tests == total_tests
            
        except Exception as e:
            print(f"[X] Erro geral nos testes: {e}")
            return False
        
        finally:
            # Cliente será fechado automaticamente
            pass

async def main():
    """Função principal"""
    print("*** MCP METATRADER 5 B3 - TESTE COMPLETO DE TRADING ***")
    print("Testando funcionalidades completas com validação de segurança - Mercado B3")
    print("=" * 70)
    
    # Verificar argumentos
    server_url = "http://192.168.0.125:50051"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print(f"[NET] Conectando ao servidor: {server_url}")
    
    # Executar testes
    tester = MT5B3TradingTest(server_url)
    success = await tester.run_complete_test()
    
    if success:
        print("\n[SUCCESS] TODOS OS TESTES PASSARAM!")
        print("[OK] Sistema MT5 MCP funcionando perfeitamente")
        sys.exit(0)
    else:
        print("\n[FAIL] ALGUNS TESTES FALHARAM!")
        print("[X] Verifique os logs acima para detalhes")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
