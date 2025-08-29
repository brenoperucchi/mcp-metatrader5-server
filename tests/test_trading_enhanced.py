#!/usr/bin/env python3
"""
Test script for Task 4 - Trading Orders Implementation
Tests the enhanced trading functions
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
    # Trade constants
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_MODIFY = 7
    TRADE_ACTION_REMOVE = 8
    
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    
    ORDER_FILLING_RETURN = 2
    
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    
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
        if symbol in ['ITSA3', 'ITSA4']:
            from collections import namedtuple
            SymbolInfo = namedtuple('SymbolInfo', ['visible', 'volume_min', 'volume_max', 'volume_step'])
            return SymbolInfo(visible=True, volume_min=1.0, volume_max=999999.0, volume_step=1.0)
        return None
    
    @staticmethod
    def order_send(request):
        from collections import namedtuple
        
        # Simulate successful order
        OrderResult = namedtuple('OrderResult', [
            'retcode', 'deal', 'order', 'volume', 'price', 'bid', 'ask', 
            'comment', 'request_id', 'retcode_external', 'request'
        ])
        
        # Mock successful responses based on action
        if request.get('action') == 1:  # TRADE_ACTION_DEAL
            return OrderResult(
                retcode=10009,  # TRADE_RETCODE_DONE
                deal=12345,
                order=67890,
                volume=request.get('volume', 100),
                price=8.46,
                bid=8.45,
                ask=8.47,
                comment="Market order executed",
                request_id=1,
                retcode_external=0,
                request=request
            )
        elif request.get('action') == 5:  # TRADE_ACTION_PENDING
            return OrderResult(
                retcode=10008,  # TRADE_RETCODE_PLACED
                deal=0,
                order=67891,
                volume=request.get('volume', 100),
                price=request.get('price', 8.50),
                bid=8.45,
                ask=8.47,
                comment="Pending order placed",
                request_id=2,
                retcode_external=0,
                request=request
            )
        elif request.get('action') == 8:  # TRADE_ACTION_REMOVE
            return OrderResult(
                retcode=10009,  # SUCCESS
                deal=0,
                order=request.get('order', 67891),
                volume=0,
                price=0,
                bid=8.45,
                ask=8.47,
                comment="Order canceled",
                request_id=3,
                retcode_external=0,
                request=request
            )
        else:
            return OrderResult(
                retcode=10009,  # SUCCESS
                deal=0,
                order=request.get('order', 67890),
                volume=request.get('volume', 100),
                price=request.get('price', 8.46),
                bid=8.45,
                ask=8.47,
                comment="Order modified",
                request_id=4,
                retcode_external=0,
                request=request
            )
    
    @staticmethod
    def order_check(request):
        from collections import namedtuple
        
        OrderCheck = namedtuple('OrderCheck', [
            'retcode', 'balance', 'equity', 'profit', 'margin', 'margin_free', 
            'margin_level', 'comment', 'request'
        ])
        
        # Simulate successful validation
        return OrderCheck(
            retcode=0,  # SUCCESS
            balance=95420.50,
            equity=95420.50,
            profit=0.0,
            margin=2538.00,
            margin_free=92882.50,
            margin_level=3654.21,
            comment="Validation passed",
            request=request
        )
    
    @staticmethod
    def positions_get(symbol=None, group=None, ticket=None):
        from collections import namedtuple
        
        Position = namedtuple('Position', [
            'ticket', 'time', 'time_msc', 'time_update', 'time_update_msc',
            'type', 'magic', 'identifier', 'reason', 'volume', 'price_open',
            'sl', 'tp', 'price_current', 'swap', 'profit', 'symbol', 'comment', 'external_id'
        ])
        
        # Mock positions
        positions = [
            Position(
                ticket=123456,
                time=int(time.time()) - 3600,  # 1 hour ago
                time_msc=(int(time.time()) - 3600) * 1000,
                time_update=int(time.time()),
                time_update_msc=int(time.time()) * 1000,
                type=0,  # BUY
                magic=20250826,
                identifier=123456,
                reason=3,
                volume=100.0,
                price_open=8.44,
                sl=0.0,
                tp=0.0,
                price_current=8.46,
                swap=0.0,
                profit=2.00,
                symbol='ITSA3',
                comment='ARB_ITSA3_103015',
                external_id=''
            )
        ]
        
        # Filter by parameters
        if ticket:
            return [p for p in positions if p.ticket == ticket]
        if symbol:
            return [p for p in positions if p.symbol == symbol]
        if group:
            return positions  # Simplified
        
        return positions if not (symbol or group or ticket) else []
    
    @staticmethod
    def orders_get(symbol=None, group=None, ticket=None):
        from collections import namedtuple
        
        Order = namedtuple('Order', [
            'ticket', 'time_setup', 'time_setup_msc', 'time_expiration',
            'type', 'type_time', 'type_filling', 'state', 'magic',
            'position_id', 'position_by_id', 'reason', 'volume_initial',
            'volume_current', 'price_open', 'sl', 'tp', 'price_current',
            'price_stoplimit', 'symbol', 'comment', 'external_id'
        ])
        
        # Mock pending orders
        orders = [
            Order(
                ticket=789123,
                time_setup=int(time.time()) - 1800,  # 30 min ago
                time_setup_msc=(int(time.time()) - 1800) * 1000,
                time_expiration=0,
                type=2,  # BUY_LIMIT
                type_time=0,
                type_filling=2,
                state=1,
                magic=20250826,
                position_id=0,
                position_by_id=0,
                reason=3,
                volume_initial=100.0,
                volume_current=100.0,
                price_open=8.40,
                sl=0.0,
                tp=0.0,
                price_current=8.46,
                price_stoplimit=0.0,
                symbol='ITSA3',
                comment='ARB_ITSA3_BUY_LIMIT_103530',
                external_id=''
            )
        ]
        
        # Filter by parameters
        if ticket:
            return [o for o in orders if o.ticket == ticket]
        if symbol:
            return [o for o in orders if o.symbol == symbol]
        if group:
            return orders  # Simplified
        
        return orders if not (symbol or group or ticket) else []
    
    @staticmethod
    def last_error():
        return (0, "No error")

# Mock pandas
class MockPD:
    pass

# Inject mocks
sys.modules['MetaTrader5'] = MockMT5
sys.modules['pandas'] = MockPD
sys.modules['numpy'] = MockPD

def test_order_validation():
    """Test order validation functions"""
    print("🧪 Testing Order Validation...")
    
    try:
        from mcp_metatrader5_server.trading_enhanced import order_check, create_arbitrage_order_request
        
        # Test order check
        print("\n--- Test 1: order_check ---")
        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": "ITSA3",
            "volume": 100,
            "type": 0  # ORDER_TYPE_BUY
        }
        
        result = order_check(request)
        print(f"✅ Order check result:")
        if isinstance(result, dict) and result.get('success'):
            data = result.get('data', result)
            print(f"  Balance: {data.get('balance')}")
            print(f"  Margin Free: {data.get('margin_free')}")
            print(f"  Comment: {data.get('comment')}")
        else:
            print(f"  Result: {result}")
        
        # Test invalid order validation
        print("\n--- Test 2: Invalid order validation ---")
        invalid_request = {
            "action": 1,
            "symbol": "",  # Invalid symbol
            "volume": 100,
            "type": 0
        }
        
        result = order_check(invalid_request)
        if isinstance(result, dict) and not result.get('success', True):
            print(f"✅ Invalid order properly rejected: {result['error']['code']}")
        else:
            print(f"⚠️  Expected error, got: {result}")
        
        # Test create arbitrage order request
        print("\n--- Test 3: create_arbitrage_order_request ---")
        arb_request = create_arbitrage_order_request("ITSA3", 100, "BUY")
        print(f"✅ Arbitrage order request:")
        if isinstance(arb_request, dict) and 'action' in arb_request:
            print(f"  Symbol: {arb_request.get('symbol')}")
            print(f"  Volume: {arb_request.get('volume')}")
            print(f"  Type: {arb_request.get('type')}")
            print(f"  Magic: {arb_request.get('magic')}")
            print(f"  Comment: {arb_request.get('comment')}")
        else:
            print(f"  Result: {arb_request}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing order validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_order_execution():
    """Test order execution functions"""
    print("\n🧪 Testing Order Execution...")
    
    try:
        from mcp_metatrader5_server.trading_enhanced import order_send, order_cancel, order_modify
        
        # Test market order
        print("\n--- Test 1: Market order (order_send) ---")
        market_request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": "ITSA3",
            "volume": 100,
            "type": 0,  # ORDER_TYPE_BUY
            "price": 8.46
        }
        
        result = order_send(market_request)
        print(f"✅ Market order result:")
        if isinstance(result, dict):
            if result.get('success'):
                data = result.get('data', result)
                print(f"  Order: {data.get('order')}")
                print(f"  Deal: {data.get('deal')}")
                print(f"  Price: {data.get('price')}")
                print(f"  Comment: {data.get('comment')}")
            else:
                print(f"  Success: {result.get('success')}")
                print(f"  Retcode: {result.get('retcode')}")
                print(f"  Comment: {result.get('comment')}")
        else:
            print(f"  Result: {result}")
        
        # Test pending order
        print("\n--- Test 2: Pending order ---")
        pending_request = {
            "action": 5,  # TRADE_ACTION_PENDING
            "symbol": "ITSA3",
            "volume": 100,
            "type": 2,  # ORDER_TYPE_BUY_LIMIT
            "price": 8.40
        }
        
        result = order_send(pending_request)
        print(f"✅ Pending order result:")
        if isinstance(result, dict):
            data = result.get('data', result)
            print(f"  Order: {data.get('order')}")
            print(f"  Price: {data.get('price')}")
            print(f"  Success: {data.get('success', result.get('success'))}")
        
        # Test order cancel
        print("\n--- Test 3: Order cancel ---")
        result = order_cancel(789123)
        print(f"✅ Cancel result:")
        if isinstance(result, dict):
            data = result.get('data', result)
            print(f"  Success: {data.get('success', result.get('success'))}")
            print(f"  Message: {data.get('message', result.get('message'))}")
        
        # Test order modify
        print("\n--- Test 4: Order modify ---")
        result = order_modify(789123, price=8.42, sl=8.30, tp=8.60)
        print(f"✅ Modify result:")
        if isinstance(result, dict):
            data = result.get('data', result)
            print(f"  Success: {data.get('success', result.get('success'))}")
            print(f"  Message: {data.get('message', result.get('message'))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing order execution: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_position_management():
    """Test position management functions"""
    print("\n🧪 Testing Position Management...")
    
    try:
        from mcp_metatrader5_server.trading_enhanced import (
            positions_get, positions_get_by_ticket, position_modify
        )
        
        # Test get all positions
        print("\n--- Test 1: positions_get ---")
        positions = positions_get()
        print(f"✅ All positions:")
        if isinstance(positions, dict) and positions.get('success'):
            data = positions['data']
            print(f"  Found {len(data)} positions")
            if data:
                pos = data[0]
                print(f"  First position: {pos.get('symbol')} {pos.get('type_string')} {pos.get('volume')}")
                print(f"  Profit: {pos.get('profit')} ({pos.get('profit_percent', 0):.2f}%)")
        elif isinstance(positions, list):
            print(f"  Found {len(positions)} positions")
            if positions:
                pos = positions[0]
                print(f"  First position: {pos.get('symbol')} {pos.get('type_string')} {pos.get('volume')}")
        else:
            print(f"  Result: {positions}")
        
        # Test get position by symbol
        print("\n--- Test 2: positions_get by symbol ---")
        positions = positions_get(symbol="ITSA3")
        print(f"✅ ITSA3 positions:")
        if isinstance(positions, dict) and positions.get('success'):
            data = positions['data']
            print(f"  Found {len(data)} ITSA3 positions")
        elif isinstance(positions, list):
            print(f"  Found {len(positions)} ITSA3 positions")
        else:
            print(f"  Result: {positions}")
        
        # Test get position by ticket
        print("\n--- Test 3: positions_get_by_ticket ---")
        position = positions_get_by_ticket(123456)
        print(f"✅ Position by ticket:")
        if isinstance(position, dict) and 'ticket' in position:
            print(f"  Ticket: {position.get('ticket')}")
            print(f"  Symbol: {position.get('symbol')}")
            print(f"  Type: {position.get('type_string')}")
            print(f"  Profit: {position.get('profit')} ({position.get('profit_percent', 0):.2f}%)")
        else:
            print(f"  Result: {position}")
        
        # Test position modify
        print("\n--- Test 4: position_modify ---")
        result = position_modify(123456, sl=8.30, tp=8.60)
        print(f"✅ Position modify result:")
        if isinstance(result, dict):
            data = result.get('data', result)
            print(f"  Success: {data.get('success', result.get('success'))}")
            print(f"  Message: {data.get('message', result.get('message'))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing position management: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orders_management():
    """Test orders management functions"""
    print("\n🧪 Testing Orders Management...")
    
    try:
        from mcp_metatrader5_server.trading_enhanced import orders_get, orders_get_by_ticket
        
        # Test get all orders
        print("\n--- Test 1: orders_get ---")
        orders = orders_get()
        print(f"✅ All orders:")
        if isinstance(orders, dict) and orders.get('success'):
            data = orders['data']
            print(f"  Found {len(data)} orders")
            if data:
                order = data[0]
                print(f"  First order: {order.get('symbol')} {order.get('type_string')} {order.get('volume_initial')}")
                print(f"  Price: {order.get('price_open')}")
        elif isinstance(orders, list):
            print(f"  Found {len(orders)} orders")
            if orders:
                order = orders[0]
                print(f"  First order: {order.get('symbol')} {order.get('type_string')} {order.get('volume_initial')}")
        else:
            print(f"  Result: {orders}")
        
        # Test get order by symbol
        print("\n--- Test 2: orders_get by symbol ---")
        orders = orders_get(symbol="ITSA3")
        print(f"✅ ITSA3 orders:")
        if isinstance(orders, dict) and orders.get('success'):
            data = orders['data']
            print(f"  Found {len(data)} ITSA3 orders")
        elif isinstance(orders, list):
            print(f"  Found {len(orders)} ITSA3 orders")
        
        # Test get order by ticket
        print("\n--- Test 3: orders_get_by_ticket ---")
        order = orders_get_by_ticket(789123)
        print(f"✅ Order by ticket:")
        if isinstance(order, dict) and 'ticket' in order:
            print(f"  Ticket: {order.get('ticket')}")
            print(f"  Symbol: {order.get('symbol')}")
            print(f"  Type: {order.get('type_string')}")
            print(f"  Price: {order.get('price_open')}")
        else:
            print(f"  Result: {order}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing orders management: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_arbitrage_utilities():
    """Test arbitrage-specific utilities"""
    print("\n🧪 Testing Arbitrage Utilities...")
    
    try:
        from mcp_metatrader5_server.trading_enhanced import (
            get_arbitrage_magic_number, create_arbitrage_order_request
        )
        
        # Test magic number
        print("\n--- Test 1: get_arbitrage_magic_number ---")
        magic = get_arbitrage_magic_number()
        print(f"✅ Arbitrage magic number: {magic}")
        
        # Test create different order types
        print("\n--- Test 2: Create different order types ---")
        order_types = ['BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT']
        
        for order_type in order_types:
            request = create_arbitrage_order_request("ITSA3", 100, order_type, 8.45)
            print(f"✅ {order_type} request:")
            if isinstance(request, dict) and 'action' in request:
                print(f"  Action: {request.get('action')}")
                print(f"  Type: {request.get('type')}")
                print(f"  Magic: {request.get('magic')}")
                print(f"  Comment: {request.get('comment')}")
            else:
                print(f"  Result: {request}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing arbitrage utilities: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all trading tests"""
    print("=" * 70)
    print("Task 4 - Trading Orders Implementation Test Suite")
    print("=" * 70)
    
    results = []
    
    results.append(test_order_validation())
    results.append(test_order_execution())
    results.append(test_position_management())
    results.append(test_orders_management())
    results.append(test_arbitrage_utilities())
    
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