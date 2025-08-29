#!/usr/bin/env python3
"""
MCP MetaTrader 5 Server Watcher
Monitora o arquivo .pid e reinicia o servidor automaticamente quando necessário
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
import threading
import argparse
import logging

class ServerWatcher:
    def __init__(self, server_script="mcp_mt5_server.py", host="0.0.0.0", port=8000, check_interval=2):
        self.server_script = Path(server_script)
        self.host = host
        self.port = port
        self.check_interval = check_interval
        self.pid_file = Path(f"server_{port}.pid")
        self.server_process = None
        self.running = True
        
        # Setup logging with date-based file pattern
        from datetime import datetime
        
        # Create logs directory structure
        logs_dir = Path(__file__).parent / "logs" / "watch_server"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Use date-time based naming pattern: server_watcher_YYYYMMDD_HHMMSS.log
        datetime_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"server_watcher_{datetime_suffix}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, mode='a', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def is_server_running(self):
        """Verifica se o servidor está rodando verificando processo e PID file"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid_content = f.read().strip()
            
            # Se arquivo está vazio (zerado), servidor deve ser reiniciado
            if not pid_content:
                self.logger.info("PID file is empty - restart requested")
                return False
            
            pid = int(pid_content)
            
            # Verifica se o processo existe
            try:
                os.kill(pid, 0)  # Signal 0 apenas testa se o processo existe
                return True
            except OSError:
                self.logger.warning(f"Process {pid} not found")
                return False
                
        except (ValueError, FileNotFoundError) as e:
            self.logger.warning(f"Error reading PID file: {e}")
            return False
    
    def start_server(self):
        """Inicia o servidor"""
        try:
            cmd = [
                sys.executable,
                str(self.server_script),
                "--host", self.host,
                "--port", str(self.port)
            ]
            
            self.logger.info(f"Starting server: {' '.join(cmd)}")
            
            # No Windows, abre em nova janela de console independente
            if os.name == 'nt':
                self.server_process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=None,
                    stderr=None,
                    stdin=None
                )
            else:
                # Linux/WSL
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            # Aguarda um pouco para o servidor inicializar
            time.sleep(5)
            
            # Verifica se o processo ainda está rodando
            if self.server_process.poll() is None:
                # Verifica se o PID file foi criado com sucesso
                if self.pid_file.exists():
                    try:
                        with open(self.pid_file, 'r') as f:
                            pid_content = f.read().strip()
                        if pid_content:
                            self.logger.info(f"Server started successfully with PID {pid_content} (process PID: {self.server_process.pid})")
                            return True
                    except:
                        pass
                
                self.logger.info(f"Server process started (PID: {self.server_process.pid}), waiting for PID file...")
                return True
            else:
                self.logger.error(f"Server process failed to start (exit code: {self.server_process.returncode})")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            return False
    
    def stop_server(self):
        """Para o servidor"""
        if self.server_process and self.server_process.poll() is None:
            try:
                self.logger.info("Stopping server...")
                
                # Tenta terminar graciosamente
                self.server_process.terminate()
                
                # Aguarda até 10 segundos para terminar graciosamente
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill se não parar graciosamente
                    self.logger.warning("Force killing server process")
                    self.server_process.kill()
                    self.server_process.wait()
                
                self.logger.info("Server stopped")
                
            except Exception as e:
                self.logger.error(f"Error stopping server: {e}")
        
        self.server_process = None
        
        # Remove PID file se existir
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                self.logger.info("PID file removed")
            except Exception as e:
                self.logger.error(f"Error removing PID file: {e}")
    
    def watch(self):
        """Loop principal do watcher"""
        self.logger.info(f"Starting server watcher (checking every {self.check_interval}s)")
        self.logger.info(f"Monitoring PID file: {self.pid_file.absolute()}")
        self.logger.info(f"Server script: {self.server_script.absolute()}")
        
        try:
            while self.running:
                if not self.is_server_running():
                    self.logger.info("Server not running, starting...")
                    
                    # Para processo anterior se existir
                    self.stop_server()
                    
                    # Inicia novo processo
                    if not self.start_server():
                        self.logger.error("Failed to start server, waiting before retry...")
                        time.sleep(10)
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Watcher interrupted by user")
        except Exception as e:
            self.logger.error(f"Watcher error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Para o watcher e o servidor"""
        self.running = False
        self.stop_server()
        self.logger.info("Watcher stopped")
    
    def signal_handler(self, signum, frame):
        """Handler para sinais do sistema"""
        self.logger.info(f"Received signal {signum}, stopping...")
        self.stop()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description="MCP MetaTrader 5 Server Watcher - Auto-restart server when PID file changes"
    )
    parser.add_argument(
        "--server-script", 
        default="mcp_mt5_server.py",
        help="Server script to run (default: mcp_mt5_server.py)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="Host to bind server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind server to (default: 8000)"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=2,
        help="Check interval in seconds (default: 2)"
    )
    
    args = parser.parse_args()
    
    # Verifica se o script do servidor existe
    server_script = Path(args.server_script)
    if not server_script.exists():
        print(f"❌ Server script not found: {server_script.absolute()}")
        sys.exit(1)
    
    # Cria watcher
    watcher = ServerWatcher(
        server_script=args.server_script,
        host=args.host,
        port=args.port,
        check_interval=args.interval
    )
    
    # Registra handlers para sinais
    signal.signal(signal.SIGINT, watcher.signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, watcher.signal_handler)
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           🔍 MCP MetaTrader 5 Server Watcher                     ║
╠═══════════════════════════════════════════════════════════════════╣
║ 📜 Server Script:  {args.server_script:<45} ║
║ 🌐 Host:Port:      {args.host}:{args.port:<38} ║  
║ 📁 PID File:       server_{args.port}.pid{' ' * (34 - len(str(args.port)))} ║
║ ⏱️  Check Interval: {args.interval}s{' ' * 44} ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🔧 Como usar:                                                     ║
║ - Zere o arquivo PID para reiniciar: echo "" > server_{args.port}.pid{' ' * (14 - len(str(args.port)))} ║
║ - Ou do WSL: python restart_server.py --port {args.port}{' ' * (21 - len(str(args.port)))} ║
║ - Para parar: Ctrl+C                                             ║
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ Watcher is running! Press Ctrl+C to stop                      ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    # Inicia o watcher
    try:
        watcher.watch()
    except Exception as e:
        print(f"❌ Watcher error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()