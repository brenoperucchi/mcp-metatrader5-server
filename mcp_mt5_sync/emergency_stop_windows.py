"""
Emergency Stop Script for Windows Environment
CRITICAL: Use only in emergencies

Uso:
    python emergency_stop_windows.py

Este script deve ser executado no ambiente Windows onde o MT5 está rodando.
"""

import asyncio
import subprocess
import time
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

class WindowsEmergencyStop:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
    def kill_mcp_processes(self):
        """Kill all MCP-related processes"""
        try:
            # Kill Python processes that might be MCP servers
            subprocess.run([
                "taskkill", "/F", "/IM", "python.exe", 
                "/FI", "WINDOWTITLE eq MCP*"
            ], capture_output=True)
            
            # Kill by process name pattern
            subprocess.run([
                "wmic", "process", "where", 
                "name='python.exe' and CommandLine like '%mcp%'", 
                "delete"
            ], capture_output=True)
            
            print("✅ MCP processes terminated")
            return True
        except Exception as e:
            print(f"⚠️  Could not kill MCP processes: {e}")
            return False
    
    def cancel_mt5_orders(self):
        """Attempt to cancel all MT5 orders via direct MCP call"""
        try:
            # Try to use local MCP testbench if available
            if os.path.exists("../tools/mcp_testbench_live.py"):
                result = subprocess.run([
                    sys.executable, "../tools/mcp_testbench_live.py",
                    "--cancel-all-orders", "--emergency"
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    print("✅ MT5 orders cancelled via MCP")
                    return True
                else:
                    print(f"⚠️  MCP order cancellation failed: {result.stderr}")
            
            # Alternative: Try direct HTTP call to MCP server
            try:
                import requests
                response = requests.post(
                    "http://localhost:8000/cancel_all_orders",
                    timeout=10,
                    json={"emergency": True}
                )
                if response.status_code == 200:
                    print("✅ Orders cancelled via HTTP API")
                    return True
            except:
                pass
                
            print("⚠️  Could not cancel orders - may need manual MT5 intervention")
            return False
            
        except Exception as e:
            print(f"⚠️  Order cancellation error: {e}")
            return False
    
    def close_mt5_positions(self):
        """Attempt to close all MT5 positions"""
        try:
            # Try to close positions via MCP
            if os.path.exists("../tools/mcp_testbench_live.py"):
                result = subprocess.run([
                    sys.executable, "../tools/mcp_testbench_live.py",
                    "--close-all-positions", "--market", "--emergency"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✅ MT5 positions closed")
                    return True
                else:
                    print(f"⚠️  Position closing failed: {result.stderr}")
            
            print("⚠️  Could not close positions - MANUAL MT5 ACTION REQUIRED")
            return False
            
        except Exception as e:
            print(f"⚠️  Position closing error: {e}")
            return False
    
    def generate_emergency_report(self, actions_taken):
        """Generate detailed emergency report"""
        try:
            report = {
                "emergency_timestamp": datetime.now().isoformat(),
                "system_state": "EMERGENCY_STOPPED",
                "platform": "Windows",
                "actions_taken": actions_taken,
                "mt5_status": self.check_mt5_status(),
                "next_steps": [
                    "1. Verify all positions are closed in MT5 terminal",
                    "2. Check P&L impact",
                    "3. Investigate root cause",
                    "4. Run recovery validation before restarting",
                    "5. Generate post-mortem report"
                ],
                "manual_verification_required": [
                    "MT5 terminal - verify no open positions",
                    "MT5 terminal - verify no pending orders",
                    "Check account balance and P&L",
                    "Verify system logs for root cause"
                ]
            }
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"emergency_report_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(report, f, indent=2)
                
            print(f"📄 Emergency report generated: {filename}")
            
            # Also create human-readable version
            text_filename = f"emergency_report_{timestamp}.txt"
            with open(text_filename, "w") as f:
                f.write("🚨 EMERGENCY STOP REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Timestamp: {report['emergency_timestamp']}\n")
                f.write(f"Platform: {report['platform']}\n")
                f.write(f"Status: {report['system_state']}\n\n")
                f.write("Actions Taken:\n")
                for action in report['actions_taken']:
                    f.write(f"- {action}\n")
                f.write("\nNext Steps:\n")
                for step in report['next_steps']:
                    f.write(f"- {step}\n")
                f.write("\nManual Verification Required:\n")
                for item in report['manual_verification_required']:
                    f.write(f"- {item}\n")
            
            print(f"📄 Human-readable report: {text_filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Could not generate emergency report: {e}")
            return None
    
    def check_mt5_status(self):
        """Check MT5 terminal status"""
        try:
            # Check if MT5 terminal is running
            result = subprocess.run([
                "tasklist", "/FI", "IMAGENAME eq terminal64.exe"
            ], capture_output=True, text=True)
            
            mt5_running = "terminal64.exe" in result.stdout
            
            return {
                "process_running": mt5_running,
                "status": "RUNNING" if mt5_running else "NOT_RUNNING"
            }
        except Exception as e:
            return {
                "process_running": False,
                "status": "ERROR",
                "error": str(e)
            }
    
    async def execute_emergency_stop(self):
        """Execute full emergency stop procedure"""
        print("🚨" * 20)
        print("🚨 EXECUTING EMERGENCY STOP - WINDOWS")
        print("🚨" * 20)
        print()
        
        actions_taken = []
        
        try:
            # 1. Kill MCP processes
            print("1️⃣ Stopping MCP services...")
            if self.kill_mcp_processes():
                actions_taken.append("MCP processes terminated")
            else:
                actions_taken.append("MCP process termination failed")
            
            # Wait a moment for processes to stop
            time.sleep(2)
            
            # 2. Cancel orders
            print("\n2️⃣ Cancelling MT5 orders...")
            if self.cancel_mt5_orders():
                actions_taken.append("MT5 orders cancelled")
            else:
                actions_taken.append("Order cancellation failed - manual intervention required")
            
            # 3. Close positions
            print("\n3️⃣ Closing MT5 positions...")
            if self.close_mt5_positions():
                actions_taken.append("MT5 positions closed")
            else:
                actions_taken.append("Position closing failed - manual intervention required")
            
            # 4. Generate report
            print("\n4️⃣ Generating emergency report...")
            report_file = self.generate_emergency_report(actions_taken)
            if report_file:
                actions_taken.append(f"Emergency report generated: {report_file}")
            
            print("\n" + "=" * 50)
            print("🚨 EMERGENCY STOP COMPLETED")
            print("=" * 50)
            print()
            print("✅ Actions taken:")
            for action in actions_taken:
                print(f"   - {action}")
            
            print("\n🔴 SYSTEM IS NOW STOPPED")
            print("🔍 MANUAL VERIFICATION REQUIRED:")
            print("   1. Check MT5 terminal for open positions")
            print("   2. Check MT5 terminal for pending orders") 
            print("   3. Verify account P&L impact")
            print("   4. Review emergency report for next steps")
            print()
            print("⚠️  DO NOT RESTART until manual verification is complete!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Emergency stop failed with error: {e}")
            actions_taken.append(f"Emergency stop failed: {str(e)}")
            
            # Still try to generate report
            self.generate_emergency_report(actions_taken)
            return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("🚨 Emergency Stop Script for Windows")
        print("=" * 40)
        print("CRITICAL: Use only in emergencies!")
        print()
        print("Usage:")
        print("  python emergency_stop_windows.py")
        print()
        print("What this script does:")
        print("  1. Stops all MCP services")
        print("  2. Cancels all MT5 orders")
        print("  3. Closes all MT5 positions")
        print("  4. Generates emergency report")
        print()
        print("⚠️  This action is IRREVERSIBLE!")
        print("⚠️  Only use when system is out of control!")
        return
    
    print("🚨 EMERGENCY STOP INITIATED")
    print("⚠️  This will stop all trading operations!")
    
    # Confirmation prompt
    try:
        confirm = input("\nType 'EMERGENCY' to confirm: ").strip()
        if confirm != "EMERGENCY":
            print("❌ Emergency stop cancelled - confirmation not received")
            return
    except KeyboardInterrupt:
        print("\n❌ Emergency stop cancelled by user")
        return
    
    print("\n🚨 Proceeding with emergency stop...")
    
    stop = WindowsEmergencyStop()
    success = asyncio.run(stop.execute_emergency_stop())
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()