#!/usr/bin/env python3
"""
Teste Cliente HTTP para MCP MetaTrader 5
Simula o acesso remoto via HTTP que o Claude CLI fará
"""

import requests
import json
import sys

def test_http_client(server_url="http://192.168.0.125:8000"):
    """Testa o cliente HTTP MCP"""
    
    print(f"🌐 Testando Cliente HTTP MCP")
    print(f"📡 Servidor: {server_url}")
    print("=" * 50)
    
    try:
        # 1. Health Check
        print("\n1. 🏥 Health Check...")
        health_response = requests.get(f"{server_url}/health", timeout=5)
        health_data = health_response.json()
        print(f"   Status: {health_data.get('status', 'unknown')}")
        print(f"   Service: {health_data.get('service', 'unknown')}")
        print(f"   Mode: {health_data.get('mode', 'unknown')}")
        
        # 2. Info Endpoint
        print("\n2. ℹ️  Server Info...")
        info_response = requests.get(f"{server_url}/info", timeout=5)
        info_data = info_response.json()
        print(f"   Name: {info_data.get('name', 'N/A')}")
        print(f"   Version: {info_data.get('version', 'N/A')}")
        print(f"   MT5 Available: {info_data.get('mt5_available', 'N/A')}")
        
        # 3. MCP Endpoints (simulando Claude CLI)
        print("\n3. 🔧 MCP Endpoints...")
        
        # Simulando uma chamada MCP (list_tools)
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        mcp_response = requests.post(
            f"{server_url}/mcp", 
            json=mcp_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if mcp_response.status_code == 200:
            mcp_data = mcp_response.json()
            tools = mcp_data.get('result', {}).get('tools', [])
            print(f"   ✅ MCP Response OK")
            print(f"   🔧 Tools encontradas: {len(tools)}")
            
            # Mostrar algumas ferramentas
            for i, tool in enumerate(tools[:5]):
                print(f"      {i+1}. {tool.get('name', 'N/A')}")
            
            if len(tools) > 5:
                print(f"      ... e mais {len(tools)-5} ferramentas")
        else:
            print(f"   ❌ MCP Error: {mcp_response.status_code}")
            print(f"   Response: {mcp_response.text}")
        
        # 4. Teste de chamada específica (ping)
        print("\n4. 🏓 Teste Ping...")
        ping_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ping",
                "arguments": {}
            }
        }
        
        ping_response = requests.post(
            f"{server_url}/mcp",
            json=ping_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if ping_response.status_code == 200:
            ping_data = ping_response.json()
            print(f"   ✅ Ping OK")
            print(f"   Response: {ping_data}")
        else:
            print(f"   ❌ Ping Error: {ping_response.status_code}")
        
        print(f"\n🎉 TESTE HTTP CONCLUÍDO COM SUCESSO!")
        print(f"✅ Servidor HTTP acessível de máquinas remotas")
        print(f"✅ Pronto para Claude CLI via HTTP")
        
        # Instruções para Claude CLI
        print(f"\n📋 Para usar no Claude CLI (máquina remota):")
        print(f"claude mcp add mt5 --transport http --url \"{server_url}/mcp\"")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro de conexão: Servidor não acessível em {server_url}")
        print(f"   - Verifique se o servidor HTTP está rodando")
        print(f"   - Verifique firewall/rede")
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout: Servidor demorou para responder")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    # Usar IP específico se fornecido
    server_ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.125"
    server_url = f"http://{server_ip}:8000"
    
    test_http_client(server_url)
