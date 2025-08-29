## 🔴 CRITICAL - Task 1: Implement `tools/call` Method

**Epic**: #1  
**Priority**: Critical  
**Sprint**: 1 (Week 1)

### **Objective**
Implement MCP-compliant `tools/call` method to handle all 34 existing tools through proper MCP protocol.

### **Current State**
- ✅ 34 tools exposed via `tools/list`
- ❌ `tools/call` method missing
- ❌ Non-MCP compliant response format

### **Subtasks**

#### **1.1 - Add `tools/call` Handler**
- [ ] Add POST handler for `tools/call` method in HTTP server
- [ ] Parse `name` and `arguments` parameters
- [ ] Route to appropriate tool function

#### **1.2 - Map Existing Tools**  
- [ ] Map all 34 tools from hardcoded list to callable functions
- [ ] Create function registry/dispatcher
- [ ] Handle parameter validation

#### **1.3 - MCP Response Format**
- [ ] Implement MCP-compliant response structure:
```json
{
  "jsonrpc": "2.0",
  "id": 1, 
  "result": {
    "content": [
      {
        "type": "text",
        "text": "JSON stringified result"
      }
    ]
  }
}
```

#### **1.4 - Unit Tests**
- [ ] Test `tools/call` for each tool category
- [ ] Test parameter validation
- [ ] Test error scenarios

### **Acceptance Criteria**

```bash
# Must work:
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", 
       "params": {"name": "get_account_info", "arguments": {}}}'

# Expected response:
{
  "jsonrpc": "2.0", "id": 1,
  "result": {"content": [{"type": "text", "text": "{\"login\": 123456, ...}"}]}
}
```

### **Technical Notes**
- Current server: `fork_mcp/run_http_server.py`
- Tools list: Line 109-149 (34 tools)
- Need to connect to actual MT5 functions in server modules

### **Definition of Done**
- [ ] All 34 tools callable via `tools/call`
- [ ] MCP-compliant response format
- [ ] Error handling implemented
- [ ] Unit tests passing
- [ ] Integration test with Claude CLI working