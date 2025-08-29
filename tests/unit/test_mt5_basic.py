#!/usr/bin/env python3
"""
[TEST_TUBE] MT5 Basic Functionality Tests
================================

Consolidated tests for basic MT5 operations including:
- Connection and initialization
- Symbol information
- Market data retrieval
- Brazilian symbols specific tests
"""

import MetaTrader5 as mt5


class TestMT5Basic:
    """Basic MT5 functionality tests"""
    
    def __init__(self):
        self.found_symbol = None
        self.symbol_info = None
    
    def test_initialization(self):
        """Test MT5 initialization"""
        print("[TOOL] Testing MT5 initialization...")
        
        if not mt5.initialize():
            print(f"[X] Failed to initialize: {mt5.last_error()}")
            return False
        
        print("[OK] MT5 initialized successfully")
        
        # Get version info
        version = mt5.version()
        if version:
            print(f"[OK] MT5 Version: {version}")
        
        return True
    
    def test_brazilian_symbols(self):
        """Test Brazilian symbols availability"""
        print("🇧🇷 Testing Brazilian symbols...")
        
        # Common Brazilian stocks
        test_symbols = ["PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "B3SA3", "WEGE3"]
        
        for symbol in test_symbols:
            info = mt5.symbol_info(symbol)
            if info:
                self.found_symbol = symbol
                self.symbol_info = info
                print(f"[OK] Found {symbol}: bid={info.bid}, ask={info.ask}, spread={info.spread}")
                return True
        
        print("[WARN] No Brazilian symbols found, using first available symbol")
        return self._get_first_available_symbol()
    
    def _get_first_available_symbol(self):
        """Get first available symbol as fallback"""
        symbols = mt5.symbols_get()
        if symbols and len(symbols) > 0:
            self.found_symbol = symbols[0].name
            self.symbol_info = mt5.symbol_info(self.found_symbol)
            print(f"[OK] Using first symbol: {self.found_symbol}")
            if self.symbol_info:
                print(f"   bid={self.symbol_info.bid}, ask={self.symbol_info.ask}")
            return True
        
        print("[X] No symbols available")
        return False
    
    def test_market_data(self):
        """Test market data retrieval"""
        if not self.found_symbol or not self.symbol_info:
            print("[X] No symbol available for market data test")
            return False
        
        print(f"[DATA] Testing market data for {self.found_symbol}...")
        
        # Test historical data
        rates = mt5.copy_rates_from_pos(self.found_symbol, 1, 0, 5)  # 5 M1 bars
        if rates is not None:
            print(f"[OK] {len(rates)} bars retrieved")
            last_bar = rates[-1]
            print(f"   Last bar: O={last_bar[1]:.5f} H={last_bar[2]:.5f} L={last_bar[3]:.5f} C={last_bar[4]:.5f}")
        else:
            print("[WARN] No historical data available")
        
        return True
    
    def test_market_book(self):
        """Test Level 2 market book"""
        if not self.found_symbol:
            print("[X] No symbol available for book test")
            return False
        
        print(f"📚 Testing Level 2 book for {self.found_symbol}...")
        
        if mt5.market_book_add(self.found_symbol):
            print("[OK] Subscribed to market book")
            book = mt5.market_book_get(self.found_symbol)
            if book and len(book) > 0:
                print(f"[OK] Book L2: {len(book)} levels")
                for i, level in enumerate(book[:3]):
                    order_type = "BUY" if level.type == 0 else "SELL"
                    print(f"   {order_type}: {level.price:.5f} vol={level.volume}")
            else:
                print("[WARN] Empty market book")
            mt5.market_book_release(self.found_symbol)
            return True
        else:
            print("[WARN] Could not subscribe to market book")
            return False
    
    def test_account_info(self):
        """Test account information"""
        print("[MONEY] Testing account information...")
        
        account = mt5.account_info()
        if account:
            print(f"[OK] Account: {account.login}")
            print(f"   Balance: {account.balance:.2f} {account.currency}")
            print(f"   Equity: {account.equity:.2f}")
            print(f"   Leverage: {account.leverage}")
            print(f"   Server: {account.server}")
            print(f"   Company: {account.company}")
            return True
        else:
            print("[WARN] Account information not available")
            return False
    
    def run_all_tests(self):
        """Run all basic tests"""
        print("[TEST_TUBE] RUNNING MT5 BASIC TESTS")
        print("=" * 40)
        
        tests = [
            ("Initialization", self.test_initialization),
            ("Brazilian Symbols", self.test_brazilian_symbols),
            ("Market Data", self.test_market_data),
            ("Market Book", self.test_market_book),
            ("Account Info", self.test_account_info),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n[RUN] {test_name}")
            print("-" * 30)
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"[X] Error in {test_name}: {e}")
                results.append((test_name, False))
        
        # Cleanup
        mt5.shutdown()
        print("\n[OK] MT5 connection closed")
        
        # Summary
        print("\n[PHASE] TEST SUMMARY")
        print("=" * 20)
        passed = 0
        for test_name, result in results:
            status = "[OK] PASSED" if result else "[X] FAILED"
            print(f"{status}: {test_name}")
            if result:
                passed += 1
        
        print(f"\n[TP] Result: {passed}/{len(results)} tests passed")
        return passed == len(results)


def main():
    """Main function"""
    tester = TestMT5Basic()
    success = tester.run_all_tests()
    
    if success:
        print("\n[SUCCESS] All basic tests passed!")
        return 0
    else:
        print("\n[FAIL] Some tests failed!")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
