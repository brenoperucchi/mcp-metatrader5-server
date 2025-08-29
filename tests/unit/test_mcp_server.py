"""
Teste do servidor MCP localmente
"""

import requests
import json

def test_mcp_server():
    """Testa o servidor MCP localmente"""
    
    base_url = "http://localhost:50051"
    
    print("[TEST_TUBE] Testando servidor MCP...")
    
    # Teste 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Health check: OK")
        else:
            print(f"[X] Health check falhou: {response.status_code}")
            return False
    except Exception as e:
        print(f"[X] Erro no health check: {e}")
        return False
    
    # Teste 2: Listar ferramentas
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(
            f"{base_url}/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                tools = data["result"].get("tools", [])
                print(f"[OK] {len(tools)} ferramentas disponíveis:")
                for tool in tools:
                    print(f"   • {tool.get('name')}: {tool.get('description')}")
            else:
                print(f"[X] Resposta inesperada: {data}")
                return False
        else:
            print(f"[X] Erro ao listar ferramentas: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[X] Erro ao testar ferramentas: {e}")
        return False
    
    # Teste 3: Obter símbolos
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_symbols",
                "arguments": {}
            }
        }
        
        response = requests.post(
            f"{base_url}/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                symbols = data["result"]["content"]
                print(f"[OK] {len(symbols)} símbolos obtidos")
                print(f"Primeiros 5: {symbols[:5]}")
            else:
                print(f"[X] Erro nos símbolos: {data}")
        else:
            print(f"[X] Erro ao obter símbolos: {response.status_code}")
            
    except Exception as e:
        print(f"[X] Erro ao testar símbolos: {e}")
    
    # Teste 4: Informações de símbolo
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_symbol_info",
                "arguments": {"symbol": "PETR4"}
            }
        }
        
        response = requests.post(
            f"{base_url}/mcp",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                info = data["result"]["content"]
                print(f"[OK] Info PETR4: bid={info.get('bid')}, ask={info.get('ask')}")
            else:
                print(f"[X] Erro na info do símbolo: {data}")
        else:
            print(f"[X] Erro ao obter info: {response.status_code}")
            
    except Exception as e:
        print(f"[X] Erro ao testar info do símbolo: {e}")
    
    print("[OK] Teste do servidor MCP concluído")
    return True

if __name__ == "__main__":
    test_mcp_server()
