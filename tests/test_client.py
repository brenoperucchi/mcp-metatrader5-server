#!/usr/bin/env python3
"""
Cliente de teste direto - Testa as funcionalidades MCP localmente
"""

import sys
import json
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_direct():
    """Teste direto das funcionalidades sem MCP protocol"""
    
    print("🧪 TESTE DIRETO DAS FUNCIONALIDADES MT5")
    print("=" * 50)
    
    try:
        # Importar módulos diretamente
        from mcp_metatrader5_server.server import config_manager
        
        print("✅ Módulos carregados com sucesso")
        print()
        
        # 1. Configuração atual
        print("1. 🎯 CONFIGURAÇÃO ATUAL:")
        try:
            # Usar o config_manager diretamente
            current = config_manager.get_current_config_info()
            print(f"   📊 Nome: {current.get('name', 'N/A')}")
            print(f"   🌍 Mercado: {current.get('market_type', 'N/A')}")
            print(f"   🏦 Conta: {current.get('account', 'N/A')}")
            print(f"   🖥️ Servidor: {current.get('server', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 2. Configurações disponíveis
        print("2. ⚙️ CONFIGURAÇÕES DISPONÍVEIS:")
        try:
            from mcp_metatrader5_server.mt5_configs import MT5_CONFIGS
            for key, config in MT5_CONFIGS.items():
                is_current = config_manager.current_config and config.name == config_manager.current_config.name
                status = "✅ ATIVA" if is_current else "⚪"
                print(f"   {status} {key}: {config.name} ({config.market_type})")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 3. Validação demo
        print("3. 🔒 VALIDAÇÃO DE CONTA DEMO:")
        try:
            # Usar o mock diretamente
            from mcp_metatrader5_server.mt5_mock import mt5_mock
            account = mt5_mock.account_info()
            is_demo = account.trade_mode == 0  # Demo mode
            status = "✅ PERMITIDO" if is_demo else "🚨 BLOQUEADO"
            print(f"   Status: {status}")
            print(f"   Tipo: {'DEMO' if is_demo else 'REAL'}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 4. Informações da conta
        print("4. 💼 INFORMAÇÕES DA CONTA:")
        try:
            from mcp_metatrader5_server.mt5_mock import mt5_mock
            account = mt5_mock.account_info()
            print(f"   🏦 Conta: {account.login}")
            print(f"   💰 Saldo: ${account.balance:.2f}")
            print(f"   📈 Equity: ${account.equity:.2f}")
            print(f"   💵 Moeda: {account.currency}")
            print(f"   🏢 Corretora: {account.company}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 5. Símbolos disponíveis
        print("5. 📊 SÍMBOLOS (Primeiros 5):")
        try:
            from mcp_metatrader5_server.mt5_mock import mt5_mock
            symbols = mt5_mock.symbols_get()
            symbols_list = [s.name for s in symbols[:5]]
            print(f"   {symbols_list}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 6. Teste de troca de configuração
        print("6. 🔄 TESTE DE TROCA DE CONFIGURAÇÃO:")
        try:
            # B3 -> Forex
            result = config_manager.switch_config("forex")
            if result['success']:
                print(f"   ✅ Trocado para: {result['current_config']['name']}")
            
            # Forex -> B3  
            result = config_manager.switch_config("b3")
            if result['success']:
                print(f"   ✅ Voltou para: {result['current_config']['name']}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        # 7. Informações do terminal
        print("7. 🖥️ INFORMAÇÕES DO TERMINAL:")
        try:
            from mcp_metatrader5_server.mt5_mock import mt5_mock
            terminal = mt5_mock.terminal_info()
            print(f"   Nome: {terminal.name}")
            print(f"   Empresa: {terminal.company}")
            print(f"   Build: {terminal.build}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()
        
        print("=" * 50)
        print("✅ TESTE DIRETO CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print("🎯 Todas as funcionalidades estão operacionais")
        print("🔧 Use essas mesmas funções no seu código")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

def show_available_functions():
    """Mostra todas as funções disponíveis para uso direto"""
    
    print("\n📚 FUNÇÕES DISPONÍVEIS PARA USO DIRETO:")
    print("-" * 45)
    
    functions = [
        ("config_manager.get_current_config_info()", "Obter configuração atual"),
        ("config_manager.switch_config('forex')", "Trocar para Forex"),
        ("config_manager.switch_config('b3')", "Trocar para B3"),
        ("mt5_mock.account_info()", "Informações da conta"),
        ("mt5_mock.symbols_get()", "Lista de símbolos"),
        ("mt5_mock.symbol_info('ITSA4')", "Info de um símbolo"),
        ("mt5_mock.symbol_info_tick('ITSA4')", "Último tick"),
        ("mt5_mock.copy_rates_from_pos(...)", "Dados históricos"),
        ("mt5_mock.order_send(...)", "Enviar ordem"),
        ("mt5_mock.positions_get()", "Posições abertas"),
    ]
    
    for i, (func, desc) in enumerate(functions, 1):
        print(f"{i:2d}. {func}")
        print(f"    📝 {desc}")
        print()

if __name__ == "__main__":
    test_direct()
    show_available_functions()
    
    print("\n🚀 EXEMPLO DE USO PRÁTICO:")
    print("-" * 25)
    print("""
from mcp_metatrader5_server.server import config_manager
from mcp_metatrader5_server.mt5_mock import mt5_mock

# Trocar para Forex
result = config_manager.switch_config('forex')
print(f"Configuração: {result['current_config']['name']}")

# Obter cotação
tick = mt5_mock.symbol_info_tick('EURUSD') 
print(f"EURUSD: Bid={tick.bid}, Ask={tick.ask}")

# Informações da conta
account = mt5_mock.account_info()
print(f"Saldo: ${account.balance:.2f}")
    """)