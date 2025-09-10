"""
Comprehensive Health Check for Windows Environment
Sistema de monitoramento de saúde do sistema ETAPA 2

Uso:
    python health_check_windows.py                 # Check básico
    python health_check_windows.py --comprehensive # Check completo
    python health_check_windows.py --continuous    # Monitoramento contínuo
"""

import subprocess
import json
import time
import sys
import os
import psutil
import requests
from datetime import datetime
from pathlib import Path

class WindowsHealthCheck:
    def __init__(self, comprehensive=False):
        self.comprehensive = comprehensive
        self.checks = {}
        self.timestamp = datetime.now()
        
    def check_mt5_connection(self):
        """Check if MT5 is running and accessible"""
        try:
            print("🔌 Checking MT5 connection...")
            
            # Check if MT5 terminal process is running
            mt5_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                if 'terminal64.exe' in proc.info['name'].lower():
                    mt5_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'uptime_seconds': time.time() - proc.info['create_time']
                    })
            
            mt5_running = len(mt5_processes) > 0
            
            status = {
                "process_count": len(mt5_processes),
                "processes": mt5_processes,
                "status": "RUNNING" if mt5_running else "DOWN"
            }
            
            # If comprehensive, try to check MT5 connection quality
            if self.comprehensive and mt5_running:
                try:
                    # Try to get symbol info via MCP if available
                    if os.path.exists("../tools/mcp_testbench_live.py"):
                        result = subprocess.run([
                            sys.executable, "../tools/mcp_testbench_live.py",
                            "--test-symbols", "ITSA3"
                        ], capture_output=True, text=True, timeout=10)
                        
                        status["connection_test"] = {
                            "success": result.returncode == 0,
                            "response": result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
                        }
                except Exception as e:
                    status["connection_test"] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return status
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    def check_mcp_server(self):
        """Check MCP server health and responsiveness"""
        try:
            print("🔌 Checking MCP server...")
            
            # Check if MCP server is responding
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                server_responsive = response.status_code == 200
                response_time = response.elapsed.total_seconds() * 1000  # ms
                
                status = {
                    "server_responsive": server_responsive,
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "status": "OK" if server_responsive else "ERROR"
                }
                
                if self.comprehensive and server_responsive:
                    # Test actual MCP functionality
                    try:
                        test_response = requests.post(
                            "http://localhost:8000/mcp/call",
                            json={
                                "tool": "get_account_info",
                                "parameters": {}
                            },
                            timeout=10
                        )
                        status["functionality_test"] = {
                            "success": test_response.status_code == 200,
                            "response_time_ms": round(test_response.elapsed.total_seconds() * 1000, 2)
                        }
                    except Exception as e:
                        status["functionality_test"] = {
                            "success": False,
                            "error": str(e)
                        }
                
            except requests.exceptions.RequestException as e:
                status = {
                    "server_responsive": False,
                    "status": "DOWN",
                    "error": str(e)
                }
            
            return status
            
        except Exception as e:
            return {
                "status": "ERROR", 
                "error": str(e)
            }
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            print("💻 Checking system resources...")
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage for current drive
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            
            status = {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "memory_available_gb": round(memory_available_gb, 2),
                "disk_percent": round(disk_percent, 2),
                "disk_free_gb": round(disk_free_gb, 2),
                "status": "OK"
            }
            
            # Check if resources are under stress
            if cpu_percent > 80 or memory_percent > 90 or disk_percent > 95:
                status["status"] = "WARNING"
                status["warnings"] = []
                if cpu_percent > 80:
                    status["warnings"].append(f"High CPU usage: {cpu_percent}%")
                if memory_percent > 90:
                    status["warnings"].append(f"High memory usage: {memory_percent}%")
                if disk_percent > 95:
                    status["warnings"].append(f"Low disk space: {disk_free_gb:.1f}GB free")
            
            return status
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    def check_network_connectivity(self):
        """Check network connectivity to essential services"""
        try:
            print("🌐 Checking network connectivity...")
            
            # Test connections to various endpoints
            endpoints = [
                ("localhost:8000", "MCP Server"),
                ("www.google.com:80", "Internet"),
                ("www.b3.com.br:80", "B3 Exchange")
            ]
            
            connectivity = {}
            
            for endpoint, description in endpoints:
                try:
                    host, port = endpoint.split(':')
                    port = int(port)
                    
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    connectivity[description] = {
                        "endpoint": endpoint,
                        "status": "OK" if result == 0 else "DOWN",
                        "reachable": result == 0
                    }
                    
                except Exception as e:
                    connectivity[description] = {
                        "endpoint": endpoint,
                        "status": "ERROR",
                        "reachable": False,
                        "error": str(e)
                    }
            
            # Overall network status
            all_reachable = all(conn["reachable"] for conn in connectivity.values())
            mcp_reachable = connectivity.get("MCP Server", {}).get("reachable", False)
            
            return {
                "endpoints": connectivity,
                "mcp_reachable": mcp_reachable,
                "internet_available": connectivity.get("Internet", {}).get("reachable", False),
                "status": "OK" if mcp_reachable else "WARNING"
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    def check_trading_prerequisites(self):
        """Check if system is ready for trading"""
        try:
            print("📊 Checking trading prerequisites...")
            
            prerequisites = {
                "market_hours": self.is_market_hours(),
                "symbols_available": False,
                "account_accessible": False,
                "configuration_valid": False
            }
            
            # Test symbols if MCP is available
            if self.checks.get("mcp", {}).get("server_responsive", False):
                try:
                    result = subprocess.run([
                        sys.executable, "../tools/mcp_testbench_live.py",
                        "--test-symbols", "ITSA3", "ITSA4"
                    ], capture_output=True, text=True, timeout=15)
                    
                    prerequisites["symbols_available"] = result.returncode == 0
                    prerequisites["symbol_test_output"] = result.stdout.strip()
                except:
                    pass
            
            # Test account access
            if self.checks.get("mcp", {}).get("server_responsive", False):
                try:
                    result = subprocess.run([
                        sys.executable, "../tools/mcp_testbench_live.py", 
                        "--get-balance"
                    ], capture_output=True, text=True, timeout=10)
                    
                    prerequisites["account_accessible"] = result.returncode == 0
                    prerequisites["account_test_output"] = result.stdout.strip()
                except:
                    pass
            
            # Check configuration files
            config_files = [
                "../config/core_parameters.yaml",
                "../config/trading_configuration.yaml"
            ]
            
            config_status = []
            for config_file in config_files:
                if os.path.exists(config_file):
                    config_status.append({
                        "file": config_file,
                        "exists": True,
                        "size": os.path.getsize(config_file)
                    })
                else:
                    config_status.append({
                        "file": config_file,
                        "exists": False
                    })
            
            prerequisites["configuration_valid"] = all(c["exists"] for c in config_status)
            prerequisites["config_files"] = config_status
            
            # Overall trading readiness
            ready_count = sum(1 for v in prerequisites.values() if isinstance(v, bool) and v)
            total_checks = 4
            
            return {
                "prerequisites": prerequisites,
                "ready_count": ready_count,
                "total_checks": total_checks,
                "readiness_percent": round((ready_count / total_checks) * 100, 1),
                "status": "OK" if ready_count >= 3 else "WARNING"
            }
            
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    def is_market_hours(self):
        """Check if it's currently market hours (B3)"""
        try:
            now = datetime.now()
            
            # Check if it's a weekday (Monday=0, Sunday=6)
            if now.weekday() >= 5:  # Saturday or Sunday
                return False
            
            # Check if it's within trading hours (9:00 - 18:00 BRT)
            # Note: This is simplified - doesn't account for holidays
            hour = now.hour
            return 9 <= hour <= 17  # Conservative range
            
        except:
            return False
    
    def run_comprehensive_check(self):
        """Run all health checks"""
        print("🔍 Windows Health Check - ETAPA 2")
        print("=" * 50)
        
        self.checks = {
            "timestamp": self.timestamp.isoformat(),
            "platform": "Windows",
            "comprehensive": self.comprehensive
        }
        
        # Core checks
        self.checks["mt5"] = self.check_mt5_connection()
        self.checks["mcp"] = self.check_mcp_server()
        self.checks["system"] = self.check_system_resources()
        
        if self.comprehensive:
            self.checks["network"] = self.check_network_connectivity()
            self.checks["trading"] = self.check_trading_prerequisites()
        
        # Print results
        self.print_results()
        
        # Determine overall health
        self.determine_overall_health()
        
        return self.checks
    
    def print_results(self):
        """Print formatted health check results"""
        print("\n📋 HEALTH CHECK RESULTS")
        print("-" * 30)
        
        # MT5 Status
        mt5_status = self.checks["mt5"]["status"]
        status_icon = "✅" if mt5_status == "RUNNING" else "❌" if mt5_status == "DOWN" else "⚠️"
        print(f"{status_icon} MT5 Terminal: {mt5_status}")
        if mt5_status == "RUNNING":
            process_count = self.checks["mt5"]["process_count"]
            print(f"   📊 Processes: {process_count}")
        
        # MCP Status  
        mcp_status = self.checks["mcp"]["status"]
        status_icon = "✅" if mcp_status == "OK" else "❌" if mcp_status == "DOWN" else "⚠️"
        print(f"{status_icon} MCP Server: {mcp_status}")
        if mcp_status == "OK":
            response_time = self.checks["mcp"]["response_time_ms"]
            print(f"   ⏱️ Response Time: {response_time}ms")
        
        # System Resources
        system_status = self.checks["system"]["status"] 
        status_icon = "✅" if system_status == "OK" else "⚠️"
        print(f"{status_icon} System Resources: {system_status}")
        print(f"   🖥️ CPU: {self.checks['system']['cpu_percent']}%")
        print(f"   💾 Memory: {self.checks['system']['memory_percent']}%")
        print(f"   💿 Disk: {self.checks['system']['disk_percent']}%")
        
        if self.comprehensive:
            # Network
            network_status = self.checks["network"]["status"]
            status_icon = "✅" if network_status == "OK" else "⚠️"
            print(f"{status_icon} Network: {network_status}")
            print(f"   🌐 MCP Reachable: {'Yes' if self.checks['network']['mcp_reachable'] else 'No'}")
            
            # Trading Readiness
            trading_status = self.checks["trading"]["status"]
            status_icon = "✅" if trading_status == "OK" else "⚠️"
            readiness = self.checks["trading"]["readiness_percent"]
            print(f"{status_icon} Trading Ready: {trading_status} ({readiness}%)")
    
    def determine_overall_health(self):
        """Determine overall system health"""
        critical_checks = ["mt5", "mcp"]
        critical_ok = all(
            self.checks[check]["status"] in ["OK", "RUNNING"] 
            for check in critical_checks
        )
        
        if critical_ok:
            if self.comprehensive:
                # Check additional factors
                system_ok = self.checks["system"]["status"] == "OK"
                network_ok = self.checks["network"]["status"] == "OK"
                trading_ready = self.checks["trading"]["readiness_percent"] >= 75
                
                if system_ok and network_ok and trading_ready:
                    overall = "HEALTHY"
                elif trading_ready:
                    overall = "DEGRADED"
                else:
                    overall = "WARNING"
            else:
                overall = "HEALTHY"
        else:
            overall = "CRITICAL"
        
        self.checks["overall_health"] = overall
        
        print(f"\n🏥 OVERALL HEALTH: {overall}")
        
        # Provide recommendations based on status
        if overall == "CRITICAL":
            print("🚨 CRITICAL ISSUES DETECTED:")
            print("   - System cannot operate safely")
            print("   - Manual intervention required")
        elif overall == "WARNING":
            print("⚠️  WARNINGS DETECTED:")
            print("   - System may have reduced functionality")  
            print("   - Monitor closely")
        elif overall == "DEGRADED":
            print("🔶 SYSTEM DEGRADED:")
            print("   - Core functions working")
            print("   - Some features may be limited")
        else:
            print("✅ System is healthy and ready for operation")
    
    def save_report(self):
        """Save health check report to file"""
        timestamp = self.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"health_report_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(self.checks, f, indent=2, default=str)
        
        print(f"\n📄 Health report saved: {filename}")
        return filename

def continuous_monitoring(interval_minutes=5):
    """Run continuous health monitoring"""
    print(f"🔄 Starting continuous monitoring (every {interval_minutes} minutes)")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            print(f"\n{'='*20} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {'='*20}")
            
            checker = WindowsHealthCheck(comprehensive=False)
            health = checker.run_comprehensive_check()
            
            # Alert on critical issues
            if health["overall_health"] == "CRITICAL":
                print("🚨 CRITICAL ALERT - Manual intervention required!")
            
            # Wait for next check
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\n⏹️ Continuous monitoring stopped")

def main():
    """Main entry point"""
    if "--help" in sys.argv:
        print("🔍 Health Check Script for Windows")
        print("=" * 40)
        print("Usage:")
        print("  python health_check_windows.py                 # Basic check")
        print("  python health_check_windows.py --comprehensive # Comprehensive check")
        print("  python health_check_windows.py --continuous    # Continuous monitoring")
        print("  python health_check_windows.py --save          # Save report to file")
        print()
        print("What this script checks:")
        print("  ✅ MT5 terminal status and connectivity")
        print("  ✅ MCP server health and response time")
        print("  ✅ System resources (CPU, memory, disk)")
        print("  ✅ Network connectivity (comprehensive)")
        print("  ✅ Trading prerequisites (comprehensive)")
        return
    
    comprehensive = "--comprehensive" in sys.argv
    continuous = "--continuous" in sys.argv
    save_report = "--save" in sys.argv
    
    if continuous:
        continuous_monitoring()
        return
    
    checker = WindowsHealthCheck(comprehensive=comprehensive)
    health = checker.run_comprehensive_check()
    
    if save_report:
        checker.save_report()
    
    # Exit with appropriate code
    exit_code = 0
    if health["overall_health"] == "CRITICAL":
        exit_code = 2
    elif health["overall_health"] in ["WARNING", "DEGRADED"]:
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()