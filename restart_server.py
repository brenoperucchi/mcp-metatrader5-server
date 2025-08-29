#!/usr/bin/env python3
"""
MCP MetaTrader 5 Server Restart Utility
Utilitário para disparar restart do servidor zerando o arquivo .pid
Funciona do WSL para Windows
"""

import argparse
import sys
from pathlib import Path
import time

def restart_server(port=8000, wait_confirmation=True):
    """
    Dispara restart do servidor zerando o arquivo PID
    
    Args:
        port: Porta do servidor (default: 8000)
        wait_confirmation: Se deve aguardar confirmação visual do restart
    
    Returns:
        bool: True se conseguiu disparar o restart, False caso contrário
    """
    pid_file = Path(f"server_{port}.pid")
    
    try:
        print(f"🔄 Disparando restart do servidor na porta {port}...")
        print(f"📁 Arquivo PID: {pid_file.absolute()}")
        
        if not pid_file.exists():
            print(f"⚠️  Arquivo PID não encontrado. Servidor pode não estar rodando.")
            print(f"   Certifique-se que o watcher está ativo: python watch_server.py --port {port}")
            return False
        
        # Lê conteúdo atual do PID file
        try:
            with open(pid_file, 'r') as f:
                current_content = f.read().strip()
            
            if current_content:
                print(f"📋 PID atual do servidor: {current_content}")
            else:
                print("📋 Arquivo PID já está vazio")
        except Exception as e:
            print(f"⚠️  Erro ao ler PID file: {e}")
        
        # Zera o arquivo PID para disparar o restart
        with open(pid_file, 'w') as f:
            f.write("")  # Arquivo vazio dispara o restart no watcher
        
        print("✅ Restart disparado! O watcher detectará e reiniciará o servidor.")
        
        if wait_confirmation:
            print("⏳ Aguardando confirmação do restart (10 segundos)...")
            
            # Aguarda até 10 segundos para o novo PID aparecer
            for i in range(10):
                time.sleep(1)
                try:
                    with open(pid_file, 'r') as f:
                        new_content = f.read().strip()
                    
                    if new_content and new_content != current_content:
                        print(f"✅ Servidor reiniciado! Novo PID: {new_content}")
                        return True
                except FileNotFoundError:
                    pass
                
                print(f"   Aguardando... ({i+1}/10)")
            
            print("⚠️  Timeout aguardando confirmação. Verifique o watcher e logs.")
            return False
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Arquivo PID não encontrado: {pid_file.absolute()}")
        print("   Certifique-se que:")
        print("   1. O servidor está rodando")
        print("   2. O watcher está ativo")
        print(f"   3. Você está no diretório correto: {Path.cwd()}")
        return False
    except PermissionError:
        print(f"❌ Sem permissão para modificar arquivo PID: {pid_file.absolute()}")
        print("   Verifique as permissões do arquivo e diretório")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Restart MCP MetaTrader 5 Server via PID file"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for restart confirmation"
    )
    parser.add_argument(
        "--status",
        action="store_true", 
        help="Show current server status"
    )
    
    args = parser.parse_args()
    
    pid_file = Path(f"server_{args.port}.pid")
    
    # Modo status
    if args.status:
        print(f"🔍 Status do servidor na porta {args.port}:")
        print(f"📁 Arquivo PID: {pid_file.absolute()}")
        
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    content = f.read().strip()
                
                if content:
                    print(f"📋 PID atual: {content}")
                    print("✅ Servidor parece estar rodando")
                else:
                    print("📋 Arquivo PID está vazio")
                    print("⚠️  Restart pode estar em andamento")
            except Exception as e:
                print(f"❌ Erro ao ler arquivo PID: {e}")
        else:
            print("❌ Arquivo PID não encontrado")
            print("   Servidor não está rodando ou watcher não está ativo")
        return
    
    # Modo restart
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           🔄 MCP Server Restart Utility                          ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🎯 Porta:          {args.port:<49} ║
║ 📁 Arquivo PID:    server_{args.port}.pid{' ' * (39 - len(str(args.port)))} ║
║ ⏳ Aguardar:       {'Não' if args.no_wait else 'Sim':<49} ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    success = restart_server(
        port=args.port, 
        wait_confirmation=not args.no_wait
    )
    
    if success:
        print(f"\n🎉 Restart disparado com sucesso!")
        print(f"   O servidor na porta {args.port} será reiniciado automaticamente.")
    else:
        print(f"\n❌ Falha ao disparar restart do servidor na porta {args.port}")
        sys.exit(1)

if __name__ == "__main__":
    main()