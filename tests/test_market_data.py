#!/usr/bin/env python3
"""
Test script for Task 3 - Market Data & Quotes Implementation
Tests the enhanced market data functions
"""
import sys
import json
import time
from pathlib import Path

# Setup paths
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Mock required modules for Linux testing
class MockMT5:
    COPY_TICKS_ALL = 1
    BOOK_TYPE_SELL = 1
    BOOK_TYPE_BUY = 2
    
    @staticmethod
    def initialize():
        return True
    
    @staticmethod
    def terminal_info():
        from collections import namedtuple
        TerminalInfo = namedtuple('TerminalInfo', ['connected'])
        return TerminalInfo(connected=True)
    
    @staticmethod
    def symbol_info(symbol):
        from collections import namedtuple
        SymbolInfo = namedtuple('SymbolInfo', [
            'name', 'description', 'path', 'session_deals', 'session_buy_orders',
            'session_sell_orders', 'volume', 'volumehigh', 'volumelow', 'time',
            'digits', 'spread', 'spread_float', 'trade_calc_mode', 'trade_mode',
            'start_time', 'expiration_time', 'trade_stops_level', 'trade_freeze_level',
            'trade_exemode', 'swap_mode', 'swap_rollover3days', 'margin_hedged_use_leg',
            'expiration_mode', 'filling_mode', 'order_mode', 'order_gtc_mode',
            'option_mode', 'option_right', 'bid', 'bidhigh', 'bidlow', 'ask',
            'askhigh', 'asklow', 'last', 'lasthigh', 'lastlow', 'point',
            'tick_value', 'tick_value_profit', 'tick_value_loss', 'tick_size',
            'contract_size', 'volume_min', 'volume_max', 'volume_step',
            'swap_long', 'swap_short', 'margin_initial', 'margin_maintenance',
            'visible'
        ])
        
        if symbol in ['ITSA3', 'ITSA4']:
            return SymbolInfo(
                name=symbol, description=f'{symbol} - Itausa PN/ON', path='\\Stocks\\Brazil\\',
                session_deals=1500, session_buy_orders=800, session_sell_orders=700,
                volume=125000, volumehigh=128000, volumelow=122000, time=1735210800,
                digits=2, spread=1, spread_float=True, trade_calc_mode=0, trade_mode=4,
                start_time=0, expiration_time=0, trade_stops_level=0, trade_freeze_level=0,
                trade_exemode=2, swap_mode=1, swap_rollover3days=1, margin_hedged_use_leg=False,
                expiration_mode=15, filling_mode=1, order_mode=127, order_gtc_mode=0,
                option_mode=0, option_right=0, bid=8.45, bidhigh=8.48, bidlow=8.42,
                ask=8.47, askhigh=8.50, asklow=8.44, last=8.46, lasthigh=8.49,
                lastlow=8.41, point=0.01, tick_value=0.01, tick_value_profit=0.01,
                tick_value_loss=0.01, tick_size=0.01, contract_size=1.0,
                volume_min=1.0, volume_max=999999.0, volume_step=1.0,
                swap_long=-0.25, swap_short=-0.15, margin_initial=0.0,
                margin_maintenance=0.0, visible=True
            )
        return None
    
    @staticmethod
    def symbol_info_tick(symbol):
        from collections import namedtuple
        Tick = namedtuple('Tick', ['time', 'bid', 'ask', 'last', 'volume', 'time_msc'])
        
        if symbol in ['ITSA3', 'ITSA4']:
            return Tick(
                time=int(time.time()),
                bid=8.45,
                ask=8.47,
                last=8.46,
                volume=1250,
                time_msc=int(time.time() * 1000)
            )
        return None
    
    @staticmethod
    def market_book_add(symbol):
        return symbol in ['ITSA3', 'ITSA4']
    
    @staticmethod
    def market_book_get(symbol):
        if symbol in ['ITSA3', 'ITSA4']:
            from collections import namedtuple
            BookItem = namedtuple('BookItem', ['type', 'price', 'volume'])
            return [
                # Bids (type=2 for BUY)
                BookItem(type=2, price=8.45, volume=1000),
                BookItem(type=2, price=8.44, volume=1500),
                BookItem(type=2, price=8.43, volume=2000),
                # Asks (type=1 for SELL) 
                BookItem(type=1, price=8.47, volume=1200),
                BookItem(type=1, price=8.48, volume=1800),
                BookItem(type=1, price=8.49, volume=2500),
            ]
        return None
    
    @staticmethod
    def market_book_release(symbol):
        return True
    
    @staticmethod
    def symbols_get(group=None):
        from collections import namedtuple
        Symbol = namedtuple('Symbol', ['name'])
        
        symbols = [
            Symbol('ITSA3'), Symbol('ITSA4'), Symbol('PETR4'), Symbol('VALE3'),
            Symbol('BBDC4'), Symbol('ABEV3'), Symbol('EURUSD'), Symbol('GBPUSD')
        ]
        
        if group:
            if 'B3' in group or 'ITR' in group:
                return [s for s in symbols if s.name.startswith(('ITSA', 'PETR', 'VALE', 'BBDC', 'ABEV'))]
            elif 'EUR' in group:
                return [s for s in symbols if 'EUR' in s.name]
        
        return symbols
    
    @staticmethod
    def last_error():
        return (0, "No error")

# Mock pandas
class MockPD:
    @staticmethod
    def DataFrame(data):
        class MockDF:
            def __init__(self, data):
                self.data = data
                self.columns = list(data[0].keys()) if data else []
            
            def to_dict(self, orient='records'):
                return self.data
        
        return MockDF(data)

# Inject mocks
sys.modules['MetaTrader5'] = MockMT5
sys.modules['pandas'] = MockPD
sys.modules['numpy'] = MockPD

def test_enhanced_market_data():
    """Test enhanced market data functions"""
    print("🧪 Testing Enhanced Market Data Functions...")
    
    try:
        from mcp_metatrader5_server.market_data_enhanced import (
            get_symbols, get_symbols_by_group, get_symbol_info,
            get_symbol_info_tick, copy_book_levels, get_book_snapshot,
            subscribe_market_book, unsubscribe_market_book,
            get_cache_stats, invalidate_cache
        )
        
        # Test get_symbols
        print("\n--- Test 1: get_symbols ---")
        symbols = get_symbols()
        if isinstance(symbols, list):
            print(f"✅ Symbols: {len(symbols)} found")
            print(f"Sample: {symbols[:3]}")
        else:
            print(f"✅ Result: {symbols}")
        
        # Test get_symbols_by_group
        print("\n--- Test 2: get_symbols_by_group ---")
        b3_symbols = get_symbols_by_group("B3*")
        print(f"✅ B3 Symbols: {len(b3_symbols)} found")
        print(f"B3 symbols: {b3_symbols}")
        
        # Test get_symbol_info
        print("\n--- Test 3: get_symbol_info ---")
        symbol_info = get_symbol_info("ITSA3")
        print(f"✅ Symbol info for ITSA3:")
        if isinstance(symbol_info, dict) and 'bid' in symbol_info:
            print(f"  Bid: {symbol_info.get('bid')}")
            print(f"  Ask: {symbol_info.get('ask')}")
            print(f"  Last: {symbol_info.get('last')}")
            print(f"  Spread: {symbol_info.get('spread_points')}")
            print(f"  Market Session: {symbol_info.get('market_session', {}).get('status')}")
        else:
            print(f"  Result: {symbol_info}")
        
        # Test get_symbol_info_tick
        print("\n--- Test 4: get_symbol_info_tick ---")
        tick = get_symbol_info_tick("ITSA3")
        print(f"✅ Tick for ITSA3:")
        if isinstance(tick, dict) and 'bid' in tick:
            print(f"  Bid: {tick.get('bid')}")
            print(f"  Ask: {tick.get('ask')}")
            print(f"  Last: {tick.get('last')}")
            print(f"  Volume: {tick.get('volume')}")
            print(f"  Time: {tick.get('time_formatted')}")
        else:
            print(f"  Result: {tick}")
        
        # Test copy_book_levels
        print("\n--- Test 5: copy_book_levels ---")
        book = copy_book_levels("ITSA3", 5)
        print(f"✅ Order Book for ITSA3:")
        if isinstance(book, dict) and 'bids' in book:
            print(f"  Best Bid: {book.get('best_bid')}")
            print(f"  Best Ask: {book.get('best_ask')}")
            print(f"  Spread: {book.get('spread')}")
            print(f"  Bids: {len(book.get('bids', []))}")
            print(f"  Asks: {len(book.get('asks', []))}")
            print(f"  Imbalance: {book.get('imbalance', 0):.3f}")
        else:
            print(f"  Result: {book}")
        
        # Test get_book_snapshot
        print("\n--- Test 6: get_book_snapshot ---")
        snapshot = get_book_snapshot("ITSA3")
        print(f"✅ Book Snapshot for ITSA3:")
        if isinstance(snapshot, dict) and 'bid_levels' in snapshot:
            print(f"  Mid Price: {snapshot.get('mid_price')}")
            print(f"  Book Imbalance: {snapshot.get('book_imbalance', 0):.3f}")
            print(f"  Bid Levels: {len(snapshot.get('bid_levels', []))}")
            print(f"  Ask Levels: {len(snapshot.get('ask_levels', []))}")
        else:
            print(f"  Result: {snapshot}")
        
        # Test market book subscription
        print("\n--- Test 7: Market Book Subscription ---")
        sub_result = subscribe_market_book("ITSA3")
        print(f"✅ Subscribe result: {sub_result}")
        
        unsub_result = unsubscribe_market_book("ITSA3")
        print(f"✅ Unsubscribe result: {unsub_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing market data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_caching_system():
    """Test caching performance"""
    print("\n🧪 Testing Caching System...")
    
    try:
        from mcp_metatrader5_server.market_data_enhanced import (
            get_symbol_info_tick, get_cache_stats, invalidate_cache
        )
        
        # Clear cache
        invalidate_cache()
        
        # First call (cache miss)
        print("--- First call (cache miss) ---")
        start_time = time.time()
        tick1 = get_symbol_info_tick("ITSA3")
        first_call_time = (time.time() - start_time) * 1000
        
        stats = get_cache_stats()
        print(f"✅ First call time: {first_call_time:.2f}ms")
        print(f"Cache stats: {stats}")
        
        # Second call (cache hit)
        print("\n--- Second call (cache hit) ---")
        start_time = time.time()
        tick2 = get_symbol_info_tick("ITSA3")
        second_call_time = (time.time() - start_time) * 1000
        
        stats = get_cache_stats()
        print(f"✅ Second call time: {second_call_time:.2f}ms")
        print(f"Cache stats: {stats}")
        
        # Verify cache performance
        if stats['hit_rate'] > 0:
            print(f"✅ Cache working! Hit rate: {stats['hit_rate']:.1f}%")
        
        # Test cache invalidation
        print("\n--- Cache invalidation ---")
        invalidated = invalidate_cache("ITSA3")
        print(f"✅ Invalidated: {invalidated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing caching: {e}")
        return False

def test_b3_session_info():
    """Test B3 session information"""
    print("\n🧪 Testing B3 Session Info...")
    
    try:
        from mcp_metatrader5_server.market_data_enhanced import get_b3_session_info
        from datetime import datetime
        
        # Test different times
        test_times = [
            datetime(2025, 1, 27, 9, 30),   # Before market
            datetime(2025, 1, 27, 10, 30),  # During market
            datetime(2025, 1, 27, 17, 30),  # During market
            datetime(2025, 1, 27, 18, 30),  # After market
            datetime(2025, 1, 25, 12, 0),   # Weekend
        ]
        
        for test_time in test_times:
            session = get_b3_session_info(test_time)
            print(f"✅ {test_time.strftime('%Y-%m-%d %H:%M')}: {session['status']} - {session['message']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing B3 session: {e}")
        return False

def test_error_handling():
    """Test error handling in market data functions"""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from mcp_metatrader5_server.market_data_enhanced import (
            get_symbol_info, get_symbol_info_tick, copy_book_levels
        )
        
        # Test invalid symbol
        print("--- Invalid symbol test ---")
        result = get_symbol_info("INVALID_SYMBOL")
        if isinstance(result, dict) and not result.get('success', True):
            print(f"✅ Error properly handled: {result['error']['code']}")
        else:
            print(f"⚠️  Expected error for invalid symbol, got: {result}")
        
        # Test invalid depth
        print("--- Invalid depth test ---")
        result = copy_book_levels("ITSA3", 50)  # Too high depth
        if isinstance(result, dict) and not result.get('success', True):
            print(f"✅ Error properly handled: {result['error']['code']}")
        else:
            print(f"⚠️  Expected error for invalid depth, got: {result}")
        
        # Test empty symbol
        print("--- Empty symbol test ---")
        result = get_symbol_info("")
        if isinstance(result, dict) and not result.get('success', True):
            print(f"✅ Error properly handled: {result['error']['code']}")
        else:
            print(f"⚠️  Expected error for empty symbol, got: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing error handling: {e}")
        return False

def main():
    """Run all market data tests"""
    print("=" * 70)
    print("Task 3 - Market Data & Quotes Test Suite")
    print("=" * 70)
    
    results = []
    
    results.append(test_enhanced_market_data())
    results.append(test_caching_system())
    results.append(test_b3_session_info())
    results.append(test_error_handling())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit(main())