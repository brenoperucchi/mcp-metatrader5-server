<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Dividend Arbitrage Trading Strategy - Copilot Instructions

## Project Overview
This is a Python-based algorithmic trading project implementing a dividend arbitrage strategy between ON (ordinary) and PN (preferred) stocks, specifically targeting ITSA3→ITSA4 pairs.

## Code Style & Patterns
- Use type hints consistently throughout the codebase
- Follow async/await patterns for I/O operations
- Implement proper error handling with logging
- Use dataclasses for data structures
- Apply SOLID principles and clean architecture

## Key Components
1. **Indicators** (`src/indicators/`): Technical analysis tools (moving averages, z-score, level2 analysis)
2. **Data Feeds** (`src/data_feeds/`): Real-time data from MT5 (ticks, orderbook)
3. **Risk Management** (`src/risk_management/`): Trade sizing, position limits, P&L tracking
4. **Strategy Engine** (`src/strategy_engine.py`): Main orchestration logic

## Configuration Management
- All parameters are stored in YAML files under `config/`
- Use the configuration loading pattern from `strategy_engine.py`
- Validate configuration parameters on startup

## Trading Logic Patterns
- Always check risk management before opening trades
- Update indicators with new market data
- Log all trading decisions with context
- Handle market data feed interruptions gracefully

## Error Handling
- Use structured logging with different levels
- Catch and handle exceptions at appropriate levels
- Ensure graceful shutdown on system signals
- Validate data integrity before processing

## Testing Approach
- Write unit tests for all indicators
- Mock external dependencies (MT5, data feeds)
- Test risk management scenarios
- Include integration tests for strategy logic

## MT5 Integration
- Use async patterns for MT5 communication
- Handle connection failures and reconnection
- Validate market data before processing
- Implement proper order execution logic

## Performance Considerations
- Minimize object creation in hot paths
- Use efficient data structures for historical data
- Implement proper memory management for tick data
- Consider CPU usage in real-time loops

When suggesting code improvements or additions, ensure they align with these patterns and the overall architecture of the dividend arbitrage strategy.
