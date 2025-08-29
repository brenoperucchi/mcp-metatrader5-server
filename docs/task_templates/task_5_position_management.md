## 🟠 HIGH - Task 5: Position Management Implementation

**Epic**: #1  
**Priority**: High  
**Sprint**: 2 (Week 2)

### **Objective**
Implement comprehensive position management tools for monitoring and managing open positions in B3 arbitrage trading.

### **Current State**
- ❌ Position queries not implemented
- ❌ No position history access
- ❌ Missing position filtering

### **Subtasks**

#### **5.1 - Position Queries**
- [ ] Implement `positions_get` with symbol filtering
- [ ] Support group-based position filtering
- [ ] Return complete position information

#### **5.2 - Position Details**
- [ ] Implement `positions_get_by_ticket` for specific positions
- [ ] Include profit/loss calculations
- [ ] Show position timing and duration

#### **5.3 - Active Orders**
- [ ] Implement `orders_get` for pending orders
- [ ] Support filtering by symbol and group
- [ ] Include order status and timing

#### **5.4 - Historical Data**
- [ ] Implement `history_orders_get` for order history
- [ ] Implement `history_deals_get` for trade history
- [ ] Support date range filtering

### **Acceptance Criteria**

```bash
# Current positions:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "positions_get", "arguments": {"symbol": "ITSA3"}}}'

# Expected response:
{
  "result": {"content": [{"type": "text", 
    "text": "[{\"ticket\": 123456789, \"symbol\": \"ITSA3\", \"volume\": 100, \"type\": \"POSITION_TYPE_BUY\", \"price_open\": 8.46, \"price_current\": 8.48, \"profit\": 2.00, \"time\": \"2025-01-25T10:25:00.000Z\"}]"}]}
}

# Pending orders:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "orders_get", "arguments": {}}}'
```

### **Performance Requirements**
- [ ] `positions_get`: < 100ms response time
- [ ] `orders_get`: < 100ms response time
- [ ] `history_*`: < 200ms response time

### **Definition of Done**
- [ ] All position queries working
- [ ] Historical data accessible
- [ ] Filtering and search implemented
- [ ] Performance targets met
- [ ] Data accuracy validated