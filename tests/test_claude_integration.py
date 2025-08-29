#!/usr/bin/env python3
"""
Teste de Integração Claude CLI - MCP MetaTrader 5 STDIO
Valida se a configuração STDIO está funcionando corretamente
"""

import subprocess
import sys
import json
from pathlib import Path

def test_claude_integration():
    """Testa a integração com Claude CLI via STDIO"""
    
    print("🧪 Testando Integração Claude CLI + MCP MT5 STDIO")
    print("=" * 60)
    
    # Caminho absoluto para o servidor
    server_path = Path(__file__).parent / "run_fork_mcp.py"
    
    print(f"📍 Servidor: {server_path}")
    print(f"📂 Diretório: {Path(__file__).parent}")
    
    # Configuração esperada pelo Claude
    config = {
        "mcpServers": {
            "mt5": {
                "command": "python",
                "args": ["-u", str(server_path)],
                "cwd": str(Path(__file__).parent),
                "env": {
                    "PYTHONUNBUFFERED": "1",
                    "MCP_LOG_LEVEL": "INFO", 
                    "MCPTransport": "stdio"
                }
            }
        }
    }
    
    print("\n📋 Configuração Claude CLI:")
    print(json.dumps(config, indent=2))
    
    # Instruções para o usuário
    print(f"\n🔧 Para adicionar no Claude CLI:")
    print(f"claude mcp add mt5 --transport stdio \\")
    print(f"  --command python \\")
    print(f"  --args \"-u\" \"{server_path}\" \\")
    print(f"  --cwd \"{Path(__file__).parent}\"")
    
    print(f"\n✅ Comandos de teste:")
    print(f"claude mcp list")
    print(f"claude mcp test mt5")
    print(f"claude mcp list-tools mt5") 
    print(f"claude mcp run mt5 ping")
    print(f"claude mcp run mt5 health")
    
    # Testar o servidor diretamente
    print(f"\n🚀 Testando servidor diretamente...")
    
    try:
        # Executar nosso cliente de teste
        result = subprocess.run([
            sys.executable, "mcp_client_simple.py", 
            "--startup-timeout", "5",
            "--retries", "1"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Servidor STDIO funcionando!")
            print("✅ Pronto para Claude CLI!")
        else:
            print("❌ Erro no servidor:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout - servidor pode estar funcionando")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print(f"\n📊 Logs disponíveis em:")
    print(f"   - Server: logs/run_fork_mcp/")
    print(f"   - Client: logs/mcp_client_simple/")

if __name__ == "__main__":
    test_claude_integration()
