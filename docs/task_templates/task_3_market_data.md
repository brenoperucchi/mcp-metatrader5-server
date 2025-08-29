## 🟠 HIGH - Task 3: Market Data & Quotes Implementation

**Epic**: #1  
**Priority**: High  
**Sprint**: 2 (Week 2)

### **Objective**
Implement real-time market data tools for ITSA3/ITSA4 trading with proper caching and performance optimization.

### **Current State**
- ❌ Tools hardcoded without real MT5 connection
- ❌ No real-time data implementation
- ❌ No caching mechanism

### **Subtasks**

#### **3.1 - Symbol Info with Real Data**
- [ ] Implement `get_symbol_info` with actual MT5 connection
- [ ] Return bid/ask/last/volume/time data
- [ ] Support ITSA3/ITSA4 and other B3 symbols

#### **3.2 - Real-time Tick Data**
- [ ] Implement `get_symbol_info_tick` for live quotes
- [ ] Ensure sub-second data freshness
- [ ] Handle market hours and offline states

#### **3.3 - Order Book (Level 2)**
- [ ] Implement `copy_book_levels` for market depth
- [ ] Return structured bids/asks arrays
- [ ] Support configurable depth (5-10 levels)

#### **3.4 - Smart Caching**
- [ ] Implement 100ms cache for quotes (10 FPS)
- [ ] Cache invalidation on market events
- [ ] Memory-efficient caching strategy

#### **3.5 - B3 Symbol Testing**
- [ ] Test with real ITSA3/ITSA4 symbols
- [ ] Validate data format and accuracy
- [ ] Handle symbol availability checks

### **Acceptance Criteria**

```bash
# ITSA3 real-time quote:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "get_symbol_info_tick", "arguments": {"symbol": "ITSA3"}}}'

# Expected response:
{
  "result": {"content": [{"type": "text", 
    "text": "{\"bid\": 8.45, \"ask\": 8.47, \"last\": 8.46, \"volume\": 15420, \"time\": \"2025-01-25T10:30:00.000Z\"}"}]}
}

# Level 2 data:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "copy_book_levels", "arguments": {"symbol": "ITSA3", "depth": 5}}}'
```

### **Performance Requirements**
- [ ] `get_symbol_info`: < 50ms response time
- [ ] `get_symbol_info_tick`: < 50ms response time  
- [ ] `copy_book_levels`: < 100ms response time
- [ ] Cache hit rate: > 80% for frequently accessed symbols

### **Definition of Done**
- [ ] Real-time data flowing from MT5
- [ ] All performance SLAs met
- [ ] Caching mechanism working
- [ ] ITSA3/ITSA4 fully supported
- [ ] Error handling for offline markets