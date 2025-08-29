## 🔴 CRITICAL - Task 2: Standardized Error Structure

**Epic**: #1  
**Priority**: Critical  
**Sprint**: 1 (Week 1)

### **Objective**
Implement standardized MCP-compliant error handling with predefined error codes for all MT5 operations.

### **Current State**
- ❌ No standardized error format
- ❌ Inconsistent error responses
- ❌ No MT5-specific error codes

### **Subtasks**

#### **2.1 - Define MT5 Error Codes**
- [ ] Create error code constants:
  - `MT5_NOT_INITIALIZED`: Terminal not initialized
  - `MT5_SYMBOL_NOT_FOUND`: Symbol not available
  - `MT5_INSUFFICIENT_FUNDS`: Insufficient margin
  - `MT5_TRADE_DISABLED`: Trading disabled
  - `MT5_INVALID_REQUEST`: Invalid parameters
  - `MT5_CONNECTION_LOST`: Connection failed
  - `MT5_TIMEOUT`: Operation timeout

#### **2.2 - Error Response Format**
- [ ] Implement MCP-compliant error structure:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text", 
        "text": "{\"success\": false, \"error\": {\"code\": \"MT5_ERROR_1\", \"message\": \"Description\", \"details\": \"Additional info\"}}"
      }
    ]
  }
}
```

#### **2.3 - Consistent Error Handling**
- [ ] Wrap all MT5 operations with error handling
- [ ] Map MT5 native errors to custom error codes
- [ ] Add contextual error messages

### **Acceptance Criteria**

```bash
# Error scenario test:
curl -X POST http://localhost:8000/mcp \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
       "params": {"name": "get_symbol_info", "arguments": {"symbol": "INVALID"}}}'

# Expected error response:
{
  "jsonrpc": "2.0", "id": 1,
  "result": {"content": [{"type": "text", 
    "text": "{\"success\": false, \"error\": {\"code\": \"MT5_SYMBOL_NOT_FOUND\", \"message\": \"Symbol INVALID not found\", \"details\": \"Check if symbol is available in Market Watch\"}}"}]}
}
```

### **Definition of Done**
- [ ] All error codes defined and documented
- [ ] Consistent error format across all tools
- [ ] Error mapping from MT5 native errors
- [ ] Error handling tests implemented
- [ ] Error documentation complete