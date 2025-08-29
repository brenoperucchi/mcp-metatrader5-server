#!/usr/bin/env python3
"""
[ROCKET] Test Runner for MCP MetaTrader 5 Server
==========================================

Runs all tests in the proper order and provides comprehensive reporting.
"""

import sys
import asyncio
import subprocess
from pathlib import Path


class TestRunner:
    """Orchestrates all test execution"""
    
    def __init__(self):
        self.test_results = []
        self.base_path = Path(__file__).parent.parent
    
    def run_sync_test(self, test_file: str, description: str):
        """Run a synchronous test file"""
        print(f"\n[RUN] {description}")
        print("-" * 50)
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.base_path / test_file)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            success = result.returncode == 0
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            self.test_results.append((description, success))
            return success
            
        except subprocess.TimeoutExpired:
            print("[X] Test timed out")
            self.test_results.append((description, False))
            return False
        except Exception as e:
            print(f"[X] Error running test: {e}")
            self.test_results.append((description, False))
            return False
    
    async def run_async_test(self, test_file: str, description: str):
        """Run an async test file"""
        print(f"\n[RUN] {description}")
        print("-" * 50)
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(self.base_path / test_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            
            success = process.returncode == 0
            print(stdout.decode())
            if stderr:
                print("STDERR:", stderr.decode())
            
            self.test_results.append((description, success))
            return success
            
        except asyncio.TimeoutError:
            print("[X] Test timed out")
            self.test_results.append((description, False))
            return False
        except Exception as e:
            print(f"[X] Error running test: {e}")
            self.test_results.append((description, False))
            return False
    
    async def run_all_tests(self):
        """Run all tests in the proper order"""
        print("[TEST_TUBE] MCP METATRADER 5 - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        # 1. Environment validation
        print("\n[PHASE] PHASE 1: ENVIRONMENT VALIDATION")
        print("=" * 40)
        self.run_sync_test("tests/utils/test_setup.py", "Environment Setup Validation")
        
        # 2. Unit tests
        print("\n[PHASE] PHASE 2: UNIT TESTS")
        print("=" * 25)
        self.run_sync_test("tests/unit/test_mt5_basic.py", "MT5 Basic Functionality")
        self.run_sync_test("tests/unit/test_mcp_server.py", "MCP Server Functionality")
        
        # 3. Integration tests
        print("\n[PHASE] PHASE 3: INTEGRATION TESTS")
        print("=" * 32)
        await self.run_async_test("tests/integration/test_connectivity.py", "Network Connectivity")
        await self.run_async_test("tests/integration/test_complete_flow.py", "Complete Trading Flow")
        await self.run_async_test("tests/integration/test_comprehensive_coverage.py", "Comprehensive Method Coverage")
        
        # 4. Results summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("[DATA] TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, success in self.test_results:
            status = "[OK] PASSED" if success else "[X] FAILED"
            print(f"{status}: {test_name}")
            if success:
                passed += 1
        
        print("\n" + "=" * 60)
        print(f"[TP] OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            print("[SUCCESS] ALL TESTS PASSED! System is ready for production.")
            return True
        else:
            print("[FAIL] SOME TESTS FAILED! Please review the failures above.")
            return False


async def main():
    """Main entry point"""
    runner = TestRunner()
    success = await runner.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)
