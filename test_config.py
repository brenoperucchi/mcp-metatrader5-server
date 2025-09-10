#!/usr/bin/env python3
"""
Teste do sistema de configuração persistente
"""

import sys
from server_config import server_config

def test_config_system():
    """Testa o sistema de configuração"""
    
    print("🧪 Testando sistema de configuração persistente")
    print("="*60)
    
    port = 8000
    
    # Teste 1: Configuração inicial
    print("\n1️⃣ Configuração inicial:")
    config = server_config.get_server_config(port)
    print(f"   Verbose: {config.get('verbose', False)}")
    print(f"   Host: {config.get('host', '0.0.0.0')}")
    
    # Teste 2: Ativar verbose
    print("\n2️⃣ Ativando modo verbose:")
    server_config.set_verbose(port, True)
    server_config.set_server_config(port, host="0.0.0.0", mt5_config="b3")
    
    config = server_config.get_server_config(port)
    print(f"   Verbose: {config.get('verbose', False)} ✅")
    
    # Teste 3: Gerar argumentos de launch
    print("\n3️⃣ Argumentos de launch:")
    args = server_config.get_launch_args(port)
    print(f"   Comando: {' '.join(args)}")
    
    if "--info" in args:
        print("   ✅ Flag --info presente")
    else:
        print("   ❌ Flag --info ausente")
    
    # Teste 4: Verificar persistência
    print("\n4️⃣ Testando persistência:")
    config_path = server_config.get_config_file_path()
    print(f"   Arquivo: {config_path}")
    print(f"   Existe: {'✅' if config_path.exists() else '❌'}")
    
    if config_path.exists():
        import json
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        print(f"   Conteúdo:")
        print(f"     Servidores: {list(data.get('servers', {}).keys())}")
        if str(port) in data.get('servers', {}):
            server_data = data['servers'][str(port)]
            print(f"     Porta {port}:")
            for key, value in server_data.items():
                print(f"       {key}: {value}")
    
    # Teste 5: Desativar verbose
    print("\n5️⃣ Desativando modo verbose:")
    server_config.set_verbose(port, False)
    
    args = server_config.get_launch_args(port)
    print(f"   Comando: {' '.join(args)}")
    
    if "--info" not in args:
        print("   ✅ Flag --info removida")
    else:
        print("   ❌ Flag --info ainda presente")
    
    print("\n" + "="*60)
    print("🎯 Teste concluído!")
    
    # Mostrar configuração final
    print("\n📋 Configuração final:")
    server_config.show_config(port)

if __name__ == "__main__":
    test_config_system()