## 🟡 MEDIUM - Task 6: Demo Account Validation & Safety

**Epic**: #1  
**Priority**: Medium  
**Sprint**: 3 (Week 3)

### **Objective**
Implement mandatory demo account validation to prevent accidental real trading during development and testing.

### **Current State**
- ❌ No account type validation
- ❌ Risk of real trading
- ❌ No safety mechanisms

### **Subtasks**

#### **6.1 - Demo Validation Tool**
- [ ] Implement `validate_demo_for_trading` mandatory check
- [ ] Return account type and trading permissions
- [ ] Add safety warnings for demo mode

#### **6.2 - Automatic Real Account Blocking**
- [ ] Block all trading operations on REAL accounts
- [ ] Allow only market data on REAL accounts
- [ ] Configurable bypass for authorized real trading

#### **6.3 - Visual Demo Warnings**
- [ ] Add demo mode indicators in responses
- [ ] Log all trading attempts with account type
- [ ] Clear messaging about demo limitations

#### **6.4 - Development Configuration**
- [ ] Configuration flag for demo-only mode
- [ ] Environment-based trading restrictions
- [ ] Developer override with explicit authorization

### **Acceptance Criteria**

```bash
# Demo validation check:
curl -X POST http://localhost:8000/mcp \
  -d '{"method": "tools/call", "params": {"name": "validate_demo_for_trading", "arguments": {}}}'

# Expected demo response:
{
  "result": {"content": [{"type": "text", 
    "text": "{\"is_demo\": true, \"account_type\": \"DEMO\", \"trading_allowed\": true, \"warning\": \"Trading operations are in DEMO mode\"}"}]}
}

# Real account should be blocked:
{
  "result": {"content": [{"type": "text", 
    "text": "{\"success\": false, \"error\": {\"code\": \"MT5_REAL_TRADING_BLOCKED\", \"message\": \"Real trading blocked for safety\", \"details\": \"Enable real trading in configuration if authorized\"}}"}]}
}
```

### **Safety Requirements**
- [ ] 100% blocking of real trading without explicit override
- [ ] All trading tools must call validation first
- [ ] Audit log of all trading attempts
- [ ] Clear documentation of safety measures

### **Definition of Done**
- [ ] Demo validation working for all trading tools
- [ ] Real account trading blocked by default
- [ ] Configuration options implemented
- [ ] Safety tests passing
- [ ] Documentation updated with safety procedures