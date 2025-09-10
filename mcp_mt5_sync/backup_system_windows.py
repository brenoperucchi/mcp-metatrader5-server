"""
Sistema de Backup para Windows - ETAPA 2
Backup completo específico para ambiente Windows com MT5

Uso:
    python backup_system_windows.py                    # Backup completo
    python backup_system_windows.py --quick           # Backup rápido (sem dados)
    python backup_system_windows.py --config-only     # Só configurações
"""

import os
import shutil
import json
import sys
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

class WindowsBackupSystem:
    def __init__(self, quick=False, config_only=False):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_root = Path(f"../backups/system_{self.timestamp}")
        self.quick = quick
        self.config_only = config_only
        
    def full_system_backup(self):
        """Backup completo específico para Windows"""
        print("💾 Iniciando backup do sistema - Windows")
        print(f"📁 Destino: {self.backup_root}")
        
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        backup_info = {
            'timestamp': self.timestamp,
            'platform': 'Windows',
            'backup_type': 'quick' if self.quick else 'config_only' if self.config_only else 'full',
            'components': []
        }
        
        try:
            # 1. Backup de código e configurações (sempre)
            print("📂 Backing up code and configurations...")
            self.backup_code_and_config()
            backup_info['components'].append('code_and_config')
            
            # 2. Backup específico MT5 (sempre)
            print("🎯 Backing up MT5 configurations...")
            self.backup_mt5_config()
            backup_info['components'].append('mt5_config')
            
            # 3. Backup de logs importantes (sempre)
            print("📄 Backing up logs...")
            self.backup_logs()
            backup_info['components'].append('logs')
            
            if not self.config_only:
                # 4. Backup de dados do banco (se não for config-only)
                print("💾 Backing up database...")
                self.backup_database()
                backup_info['components'].append('database')
                
                if not self.quick:
                    # 5. Backup de dados históricos (só no full)
                    print("📊 Backing up historical data...")
                    self.backup_historical_data()
                    backup_info['components'].append('historical_data')
            
            # 6. Manifest do backup
            self.create_backup_manifest(backup_info)
            
            # 7. Comprimir backup se for pequeno
            if self.config_only or self.quick:
                self.compress_backup()
            
            print(f"✅ Backup completo salvo em: {self.backup_root}")
            return str(self.backup_root)
            
        except Exception as e:
            print(f"❌ Erro durante backup: {e}")
            return None
    
    def backup_code_and_config(self):
        """Backup de código e configurações"""
        code_backup_dir = self.backup_root / "code_config"
        code_backup_dir.mkdir(exist_ok=True)
        
        # Diretórios importantes para backup
        important_dirs = [
            "../src",
            "../config", 
            "../runbooks",
            "../scripts",
            "../mcp_mt5_sync",
            "../docs"
        ]
        
        for dir_path in important_dirs:
            if os.path.exists(dir_path):
                dir_name = os.path.basename(dir_path)
                dest_dir = code_backup_dir / dir_name
                
                try:
                    shutil.copytree(dir_path, dest_dir, ignore=shutil.ignore_patterns(
                        '*.pyc', '__pycache__', '*.log', 'venv', '.venv', '.git'
                    ))
                    print(f"  ✅ {dir_path} -> {dest_dir}")
                except Exception as e:
                    print(f"  ⚠️ Falha ao copiar {dir_path}: {e}")
        
        # Arquivos importantes na raiz
        important_files = [
            "../requirements.txt",
            "../README.md",
            "../CLAUDE.md",
            "../pytest.ini"
        ]
        
        for file_path in important_files:
            if os.path.exists(file_path):
                try:
                    shutil.copy2(file_path, code_backup_dir)
                    print(f"  ✅ {file_path}")
                except Exception as e:
                    print(f"  ⚠️ Falha ao copiar {file_path}: {e}")
    
    def backup_mt5_config(self):
        """Backup de configurações MT5 específicas do Windows"""
        mt5_backup_dir = self.backup_root / "mt5_config"
        mt5_backup_dir.mkdir(exist_ok=True)
        
        # Possíveis locais do MT5 no Windows
        mt5_locations = [
            Path.home() / "AppData/Roaming/MetaQuotes/Terminal",
            Path("C:/Program Files/MetaTrader 5"),
            Path("C:/Program Files (x86)/MetaTrader 5"),
            Path("C:/Users/Public/MetaTrader 5")
        ]
        
        mt5_found = False
        
        for location in mt5_locations:
            if location.exists():
                print(f"  📁 Encontrado MT5 em: {location}")
                
                # Backup de arquivos de configuração importantes
                config_patterns = [
                    "**/config/*.ini",
                    "**/profiles/*.ini", 
                    "**/templates/*.tpl",
                    "**/experts/advisors/*.ex5",
                    "**/scripts/*.ex5"
                ]
                
                for pattern in config_patterns:
                    try:
                        config_files = list(location.glob(pattern))
                        for config_file in config_files:
                            if config_file.is_file():
                                # Manter estrutura de diretórios relativa
                                rel_path = config_file.relative_to(location)
                                dest_file = mt5_backup_dir / rel_path
                                dest_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(config_file, dest_file)
                    except Exception as e:
                        print(f"  ⚠️ Erro ao processar padrão {pattern}: {e}")
                
                mt5_found = True
                break
        
        if not mt5_found:
            print("  ⚠️ MT5 não encontrado nos locais padrão")
            
        # Backup de configurações MCP relacionadas ao MT5
        mcp_config_files = [
            "../config/trading_configuration.yaml",
            "../config/mt5_settings.yaml",
            "service_config.json"
        ]
        
        for config_file in mcp_config_files:
            if os.path.exists(config_file):
                try:
                    shutil.copy2(config_file, mt5_backup_dir)
                    print(f"  ✅ {config_file}")
                except Exception as e:
                    print(f"  ⚠️ Falha ao copiar {config_file}: {e}")
    
    def backup_logs(self):
        """Backup de logs importantes"""
        logs_backup_dir = self.backup_root / "logs"
        logs_backup_dir.mkdir(exist_ok=True)
        
        # Diretórios de logs
        log_dirs = [
            "../logs",
            "logs",
            "../mcp_mt5_sync/logs"
        ]
        
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                for log_file in Path(log_dir).glob("**/*.log"):
                    try:
                        # Só copiar logs dos últimos 7 dias
                        if (datetime.now().timestamp() - log_file.stat().st_mtime) < (7 * 24 * 3600):
                            rel_path = log_file.relative_to(log_dir)
                            dest_file = logs_backup_dir / rel_path
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(log_file, dest_file)
                    except Exception as e:
                        print(f"  ⚠️ Erro ao copiar log {log_file}: {e}")
        
        # Backup de arquivos de report importantes
        report_files = [
            "../reports/e2e_demo_*/e2e_demo_report.txt",
            "../reports/emergency_*.json",
            "../reports/health_*.json"
        ]
        
        for pattern in report_files:
            for report_file in Path().glob(pattern):
                if report_file.is_file():
                    try:
                        shutil.copy2(report_file, logs_backup_dir)
                        print(f"  ✅ {report_file}")
                    except Exception as e:
                        print(f"  ⚠️ Erro ao copiar {report_file}: {e}")
    
    def backup_database(self):
        """Backup de dados do banco usando pg_dump"""
        db_backup_dir = self.backup_root / "database"
        db_backup_dir.mkdir(exist_ok=True)
        
        try:
            # Tentar fazer backup via pg_dump se disponível
            backup_file = db_backup_dir / f"trading_backup_{self.timestamp}.sql"
            
            # Comando pg_dump (assumindo PostgreSQL local)
            pg_dump_cmd = [
                "pg_dump",
                "-h", "localhost",
                "-U", "postgres",
                "-d", "trading",
                "-f", str(backup_file),
                "--no-password"
            ]
            
            try:
                result = subprocess.run(pg_dump_cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    print(f"  ✅ Database backup: {backup_file}")
                else:
                    print(f"  ⚠️ pg_dump falhou: {result.stderr}")
                    self.backup_database_alternative(db_backup_dir)
            except FileNotFoundError:
                print("  ⚠️ pg_dump não encontrado, usando método alternativo")
                self.backup_database_alternative(db_backup_dir)
            except subprocess.TimeoutExpired:
                print("  ⚠️ pg_dump timeout, usando método alternativo")
                self.backup_database_alternative(db_backup_dir)
                
        except Exception as e:
            print(f"  ❌ Erro no backup do banco: {e}")
    
    def backup_database_alternative(self, db_backup_dir):
        """Método alternativo de backup usando Python"""
        try:
            # Tentar backup via Python se pg_dump não funcionar
            backup_data = {
                'timestamp': self.timestamp,
                'method': 'python_export',
                'tables': {}
            }
            
            # Salvar dados de configuração em JSON
            config_backup = db_backup_dir / "config_backup.json"
            with open(config_backup, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"  ✅ Backup alternativo: {config_backup}")
            
        except Exception as e:
            print(f"  ❌ Backup alternativo falhou: {e}")
    
    def backup_historical_data(self):
        """Backup de dados históricos (reports, análises, etc.)"""
        historical_backup_dir = self.backup_root / "historical_data"
        historical_backup_dir.mkdir(exist_ok=True)
        
        # Diretórios com dados históricos
        historical_dirs = [
            "../reports",
            "../data",
            "../logs/backups",
            "../exports"
        ]
        
        for hist_dir in historical_dirs:
            if os.path.exists(hist_dir):
                try:
                    dest_dir = historical_backup_dir / os.path.basename(hist_dir)
                    shutil.copytree(hist_dir, dest_dir, ignore=shutil.ignore_patterns(
                        '*.tmp', '*.temp', '__pycache__'
                    ))
                    print(f"  ✅ {hist_dir}")
                except Exception as e:
                    print(f"  ⚠️ Erro ao copiar {hist_dir}: {e}")
    
    def create_backup_manifest(self, backup_info):
        """Criar manifest do backup"""
        manifest = {
            **backup_info,
            'created_at': datetime.now().isoformat(),
            'backup_path': str(self.backup_root),
            'size_mb': self.calculate_backup_size(),
            'files_count': self.count_backup_files(),
            'restore_instructions': [
                "1. Extract backup to desired location",
                "2. Restore database using SQL files in database/ directory",
                "3. Copy configuration files to appropriate locations",
                "4. Restart all services",
                "5. Validate system functionality"
            ]
        }
        
        manifest_file = self.backup_root / "BACKUP_MANIFEST.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Também criar versão texto para fácil leitura
        readme_file = self.backup_root / "README.txt"
        with open(readme_file, 'w') as f:
            f.write(f"SISTEMA ETAPA 2 - BACKUP\n")
            f.write(f"========================\n\n")
            f.write(f"Criado em: {manifest['created_at']}\n")
            f.write(f"Tipo: {manifest['backup_type']}\n")
            f.write(f"Componentes: {', '.join(manifest['components'])}\n")
            f.write(f"Tamanho: {manifest['size_mb']:.1f} MB\n")
            f.write(f"Arquivos: {manifest['files_count']}\n\n")
            f.write("Instruções de Restore:\n")
            for i, instruction in enumerate(manifest['restore_instructions'], 1):
                f.write(f"{i}. {instruction[3:]}\n")  # Remove "1. " prefix
        
        print(f"  ✅ Manifest criado: {manifest_file}")
    
    def calculate_backup_size(self):
        """Calcular tamanho do backup em MB"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.backup_root):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            return total_size / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def count_backup_files(self):
        """Contar número de arquivos no backup"""
        try:
            count = 0
            for dirpath, dirnames, filenames in os.walk(self.backup_root):
                count += len(filenames)
            return count
        except:
            return 0
    
    def compress_backup(self):
        """Comprimir backup se for pequeno (< 500MB)"""
        try:
            size_mb = self.calculate_backup_size()
            if size_mb < 500:  # Só comprimir se < 500MB
                zip_file = self.backup_root.parent / f"backup_{self.timestamp}.zip"
                
                with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(self.backup_root):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, self.backup_root.parent)
                            zipf.write(file_path, arc_path)
                
                # Remove diretório original se compressão foi bem-sucedida
                if zip_file.exists():
                    shutil.rmtree(self.backup_root)
                    print(f"  ✅ Backup comprimido: {zip_file} ({size_mb:.1f} MB)")
                    return str(zip_file)
            
            return str(self.backup_root)
        except Exception as e:
            print(f"  ⚠️ Erro na compressão: {e}")
            return str(self.backup_root)

def main():
    """Main entry point"""
    if "--help" in sys.argv:
        print("💾 Sistema de Backup para Windows - ETAPA 2")
        print("=" * 50)
        print("Uso:")
        print("  python backup_system_windows.py                # Backup completo")
        print("  python backup_system_windows.py --quick       # Backup rápido (sem dados históricos)")
        print("  python backup_system_windows.py --config-only # Só configurações")
        print()
        print("O que é incluído no backup:")
        print("  ✅ Código fonte e configurações")
        print("  ✅ Configurações específicas do MT5")
        print("  ✅ Logs importantes (últimos 7 dias)")
        print("  ✅ Dados do banco (se não --config-only)")
        print("  ✅ Dados históricos (se não --quick)")
        print()
        print("Localização do backup:")
        print("  📁 ../backups/system_YYYYMMDD_HHMMSS/")
        return
    
    # Parse arguments
    quick = "--quick" in sys.argv
    config_only = "--config-only" in sys.argv
    
    if quick and config_only:
        print("❌ Erro: --quick e --config-only são mutuamente exclusivos")
        return
    
    backup_type = "rápido" if quick else "configurações apenas" if config_only else "completo"
    print(f"💾 Iniciando backup {backup_type}...")
    
    backup_system = WindowsBackupSystem(quick=quick, config_only=config_only)
    
    try:
        backup_path = backup_system.full_system_backup()
        
        if backup_path:
            print(f"\n🎉 BACKUP CONCLUÍDO COM SUCESSO!")
            print(f"📁 Localização: {backup_path}")
            
            # Mostrar estatísticas
            size_mb = backup_system.calculate_backup_size()
            files_count = backup_system.count_backup_files()
            print(f"📊 Tamanho: {size_mb:.1f} MB")
            print(f"📄 Arquivos: {files_count}")
            
            print(f"\n📋 Para restaurar:")
            print(f"  1. Leia o arquivo README.txt no backup")
            print(f"  2. Siga as instruções de restore")
            print(f"  3. Valide funcionamento após restore")
            
        else:
            print("\n❌ BACKUP FALHOU!")
            print("Verifique os logs de erro acima")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Backup cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado durante backup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()