#!/usr/bin/env python3
"""
MCP MT5 Server Configuration Manager
Gerencia configurações persistentes do servidor
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class ServerConfig:
    """Gerencia configuração persistente do servidor MT5"""
    
    def __init__(self, config_file: str = "config/server_config.json"):
        self.config_file = Path(config_file)
        # Criar diretório config se não existir
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_data = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                self.config_data = {
                    "servers": {},
                    "global": {
                        "created": datetime.now().isoformat(),
                        "version": "2.0.0"
                    }
                }
                self.save_config()
        except Exception as e:
            print(f"⚠️ Erro ao carregar config: {e}")
            self.config_data = {"servers": {}, "global": {}}
        
        return self.config_data
    
    def save_config(self) -> bool:
        """Salva configuração no arquivo JSON"""
        try:
            self.config_data["global"]["last_updated"] = datetime.now().isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar config: {e}")
            return False
    
    def get_server_config(self, port: int) -> Dict[str, Any]:
        """Obtém configuração específica de um servidor"""
        port_key = str(port)
        return self.config_data.get("servers", {}).get(port_key, {
            "port": port,
            "verbose": False,
            "host": "0.0.0.0",
            "mt5_config": "b3",
            "created": datetime.now().isoformat()
        })
    
    def set_server_config(self, port: int, **kwargs) -> bool:
        """Define configuração de um servidor"""
        port_key = str(port)
        
        if "servers" not in self.config_data:
            self.config_data["servers"] = {}
        
        if port_key not in self.config_data["servers"]:
            self.config_data["servers"][port_key] = {
                "port": port,
                "created": datetime.now().isoformat()
            }
        
        # Atualizar configurações
        config = self.config_data["servers"][port_key]
        config.update(kwargs)
        config["last_updated"] = datetime.now().isoformat()
        
        return self.save_config()
    
    def is_verbose(self, port: int) -> bool:
        """Verifica se modo verbose está ativo para porta"""
        config = self.get_server_config(port)
        return config.get("verbose", False)
    
    def set_verbose(self, port: int, verbose: bool) -> bool:
        """Define modo verbose para porta"""
        return self.set_server_config(port, verbose=verbose)
    
    def get_launch_args(self, port: int) -> list:
        """Gera argumentos de linha de comando para o servidor"""
        config = self.get_server_config(port)
        
        args = [
            "python", "mcp_mt5_server.py",
            "--host", config.get("host", "0.0.0.0"),
            "--port", str(port)
        ]
        
        # Adicionar flags baseadas na configuração
        if config.get("verbose", False):
            args.append("--info")
        
        mt5_config = config.get("mt5_config")
        if mt5_config and mt5_config != "b3":  # b3 é default
            args.extend(["--mt5-config", mt5_config])
        
        return args
    
    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """Lista todos os servidores configurados"""
        return self.config_data.get("servers", {})
    
    def remove_server(self, port: int) -> bool:
        """Remove configuração de um servidor"""
        port_key = str(port)
        if "servers" in self.config_data and port_key in self.config_data["servers"]:
            del self.config_data["servers"][port_key]
            return self.save_config()
        return True
    
    def get_config_file_path(self) -> Path:
        """Retorna caminho do arquivo de configuração"""
        return self.config_file.absolute()
    
    def show_config(self, port: Optional[int] = None) -> None:
        """Mostra configuração atual (para debug)"""
        print(f"📁 Config file: {self.get_config_file_path()}")
        
        if port:
            config = self.get_server_config(port)
            print(f"🔧 Server {port} config:")
            for key, value in config.items():
                print(f"   {key}: {value}")
        else:
            print("🔧 All servers config:")
            servers = self.list_servers()
            if not servers:
                print("   (No servers configured)")
            else:
                for port_key, config in servers.items():
                    print(f"   Port {port_key}:")
                    for key, value in config.items():
                        if key != "port":
                            print(f"     {key}: {value}")

# Instância global para facilitar uso
server_config = ServerConfig()

def main():
    """CLI para testar/gerenciar configurações"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MT5 Server Config Manager")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--show", action="store_true", help="Show current config")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    parser.add_argument("--no-verbose", action="store_true", help="Disable verbose mode")
    parser.add_argument("--reset", action="store_true", help="Reset server config")
    
    args = parser.parse_args()
    
    if args.show:
        server_config.show_config(args.port)
    elif args.verbose:
        server_config.set_verbose(args.port, True)
        print(f"✅ Verbose mode enabled for server {args.port}")
    elif args.no_verbose:
        server_config.set_verbose(args.port, False)
        print(f"✅ Verbose mode disabled for server {args.port}")
    elif args.reset:
        server_config.remove_server(args.port)
        print(f"✅ Config reset for server {args.port}")
    else:
        # Mostrar argumentos que seriam usados para lançar o servidor
        args_list = server_config.get_launch_args(args.port)
        print(f"🚀 Launch args for server {args.port}:")
        print(f"   {' '.join(args_list)}")

if __name__ == "__main__":
    main()