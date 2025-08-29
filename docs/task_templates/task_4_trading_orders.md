## 🟠 HIGH - Task 4: Trading Orders Implementation

**Epic**: #1  
**Priority**: High  
**Sprint**: 2 (Week 2)

### **Objective**
Implement complete trading order functionality including send, check, modify, and cancel operations for B3 arbitrage trading.

### **Current State**
- ❌ Order operations not connected to real MT5
- ❌ No order validation
- ❌ Missing order management tools

### **Subtasks**

#### **4.1 - Order Send Functionality**
- [ ] Implement `order_send` with real MT5 connection
- [ ] Support market and pending orders
- [ ] Handle ITSA3/ITSA4 specific parameters

#### **4.2 - Pre-send Validation**
- [ ] Implement `order_check` for pre-validation
- [ ] Check margin requirements
- [ ] Validate order parameters

#### **4.3 - Order Management**
- [ ] Implement `order_cancel` for pending orders
- [ ] Implement `order_modify` for price/SL/TP changes
- [ ] Support magic numbers and comments

#### **4.4 - Position Management** 
- [ ] Implement `position_modify` for SL/TP updates
- [ ] Support partial position modifications
- [ ] Handle position-specific operations

#### **4.5 - Trading Context**
- [ ] Support custom magic numbers for arbitrage
- [ ] Add meaningful order comments
- [ ] Implement trading session validation

### **Acceptance Criteria**

```bash
# Order validation:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "order_check", 
       "arguments": {"request": {"symbol": "ITSA3", "volume": 100, "type": 0}}}}'

# Expected validation response:
{
  "result": {"content": [{"type": "text", 
    "text": "{\"retcode\": 0, \"balance\": 95420.50, \"margin\": 2538.00, \"margin_free\": 92882.50, \"comment\": \"Valid order\"}"}]}
}

# Order execution:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "order_send",
       "arguments": {"request": {"action": "TRADE_ACTION_DEAL", "symbol": "ITSA3", "volume": 100, "type": "ORDER_TYPE_BUY", "price": 8.46}}}}'
```

### **Performance Requirements**
- [ ] `order_check`: < 100ms response time
- [ ] `order_send`: < 200ms response time
- [ ] `order_modify`: < 150ms response time

### **Definition of Done**
- [ ] All order operations functional in demo
- [ ] Pre-validation working correctly
- [ ] Order management tools implemented
- [ ] Performance SLAs met
- [ ] Integration tests passing