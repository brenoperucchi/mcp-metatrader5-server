# MCP MetaTrader 5 - Capability Matrix (Análise Offline)

Análise das capacidades do servidor MCP MT5 baseada no código-fonte.

**Gerado em:** 2025-08-26 02:32:56

## 📋 Resumo

- **Total de Ferramentas:** 34
- **Total de Resources:** 6
- **Análise:** Baseada no código-fonte (offline)

## 🔧 Ferramentas Disponíveis

| Ferramenta | Parâmetros | Tipo Retorno | Descrição |
|------------|------------|--------------|-----------|
| `initialize` |  | bool | Initialize the MetaTrader 5 terminal with current configuration. |
| `shutdown` |  | bool | Shut down the connection to the MetaTrader 5 terminal. |
| `login` | login: int, password: str, server: str | bool | Log in to the MetaTrader 5 trading account. |
| `get_account_info` |  | AccountInfo | Get information about the current trading account. |
| `get_terminal_info` |  | Dict[(str, Any)] | Get information about the MetaTrader 5 terminal. |
| `get_version` |  | Dict[(str, Any)] | Get the MetaTrader 5 version. |
| `validate_demo_for_trading` |  | Dict[(str, Any)] | Validate if the connected account is a demo account before allowing trading operations. |
| `get_symbols` |  | List[str] | Get all available symbols (financial instruments) from the MetaTrader 5 terminal. |
| `get_symbols_by_group` | group: str | List[str] | Get symbols that match a specific group or pattern. |
| `get_symbol_info` | symbol: str | Dict[(str, Any)] | Get information about a specific symbol. |
| `get_symbol_info_tick` | symbol: str | Dict[(str, Any)] | Get the latest tick data for a symbol. |
| `symbol_select` | symbol: str, visible?: bool | bool | Select a symbol in the Market Watch window or remove a symbol from it. |
| `copy_rates_from_pos` | symbol: str, timeframe: int, start_pos: int, co... | List[Dict[(str, Any)]] | Get bars from a specified symbol and timeframe starting from the specified position. |
| `copy_rates_from_date` | symbol: str, timeframe: int, date_from: datetim... | List[Dict[(str, Any)]] | Get bars from a specified symbol and timeframe starting from the specified date. |
| `copy_rates_range` | symbol: str, timeframe: int, date_from: datetim... | List[Dict[(str, Any)]] | Get bars from a specified symbol and timeframe within the specified date range. |
| `copy_ticks_from_pos` | symbol: str, start_pos: int, count: int, flags?... | List[Dict[(str, Any)]] | Get ticks from a specified symbol starting from the specified position. |
| `copy_ticks_from_date` | symbol: str, date_from: datetime, count: int, f... | List[Dict[(str, Any)]] | Get ticks from a specified symbol starting from the specified date. |
| `copy_ticks_range` | symbol: str, date_from: datetime, date_to: date... | List[Dict[(str, Any)]] | Get ticks from a specified symbol within the specified date range. |
| `get_last_error` |  | Dict[(str, Any)] | Get the last error code and description. |
| `copy_book_levels` | symbol: str, depth?: int | List[Dict[(str, Any)]] | Get Level 2 market data (order book) for a specified symbol. |
| `subscribe_market_book` | symbol: str | bool | Subscribe to market book (Level 2) data for a symbol. |
| `unsubscribe_market_book` | symbol: str | bool | Unsubscribe from market book (Level 2) data for a symbol. |
| `get_book_snapshot` | symbol: str, depth?: int | Dict[(str, Any)] | Get a complete order book snapshot with bid/ask levels separated. |
| `order_send` | request: OrderRequest | OrderResult | Send an order to the trade server. |
| `order_check` | request: OrderRequest | Dict[(str, Any)] | Check if an order can be placed with the specified parameters. |
| `order_cancel` | ticket: int | Dict[(str, Any)] | Cancel a pending order. |
| `order_modify` | ticket: int, price?: Optional[float], sl?: Opti... | Dict[(str, Any)] | Modify an existing pending order. |
| `position_modify` | ticket: int, sl?: Optional[float], tp?: Optiona... | Dict[(str, Any)] | Modify Stop Loss and Take Profit of an open position. |
| `positions_get` | symbol?: Optional[str], group?: Optional[str] | List[Position] | Get open positions. |
| `positions_get_by_ticket` | ticket: int | Optional[Position] | Get an open position by its ticket. |
| `orders_get` | symbol?: Optional[str], group?: Optional[str] | List[Dict[(str, Any)]] | Get active orders. |
| `orders_get_by_ticket` | ticket: int | Optional[Dict[(str, Any)]] | Get an active order by its ticket. |
| `history_orders_get` | symbol?: Optional[str], group?: Optional[str], ... | List[HistoryOrder] | Get orders from history within the specified date range. |
| `history_deals_get` | symbol?: Optional[str], group?: Optional[str], ... | List[Deal] | Get deals from history within the specified date range. |

## 📚 Resources Disponíveis

| Resource | URI Pattern | Descrição |
|----------|-------------|-----------|
| `get_timeframes` | `mt5://timeframes` | Get information about available timeframes in MetaTrader 5. |
| `get_tick_flags` | `mt5://tick_flags` | Get information about tick flags in MetaTrader 5. |
| `get_order_types` | `mt5://order_types` | Get information about order types in MetaTrader 5. |
| `get_order_filling_types` | `mt5://order_filling_types` | Get information about order filling types in MetaTrader 5. |
| `get_order_time_types` | `mt5://order_time_types` | Get information about order time types in MetaTrader 5. |
| `get_trade_actions` | `mt5://trade_actions` | Get information about trade request actions in MetaTrader 5. |

## 🎯 Mapeamento para Requisitos Etapa 2

| Requisito Etapa 2 | Ferramentas MCP Disponíveis | Status | Observações |
|------------------|----------------------------|--------|-------------|
| get_quotes | `get_symbol_info_tick`, `get_symbol_info` | ✅ | Bid/Ask/Last via symbol_info_tick |
| get_ticks | `get_symbol_info_tick`, `copy_rates_from_pos` | ✅ | Histórico + tempo real |
| get_positions | Nenhuma encontrada | ❌ | 🚨 Crítico para trading |
| get_orders | `orders_get` | ✅ | 🚨 Crítico para trading |
| place_order | `order_send` | ✅ | 🚨 Crítico para trading |
| cancel_order | `order_cancel` | ✅ | 🚨 Crítico para trading |

## 🔍 Análise de Gaps

### 🔴 Funcionalidades Críticas Ausentes
- **get_positions**: Necessário para Etapa 2

### 📊 Cobertura de Requisitos

- **Cobertura atual**: 83%
- **Requisitos atendidos**: 5/6
- **Gaps críticos**: 1

### 🛠️ Ferramentas de Suporte Disponíveis

Ferramentas auxiliares identificadas:
- `initialize`: Initialize the MetaTrader 5 terminal with current configuration.
- `shutdown`: Shut down the connection to the MetaTrader 5 terminal.
- `login`: Log in to the MetaTrader 5 trading account.
- `get_account_info`: Get information about the current trading account.
- `get_terminal_info`: Get information about the MetaTrader 5 terminal.
- `get_version`: Get the MetaTrader 5 version.
- `validate_demo_for_trading`: Validate if the connected account is a demo account before allowing trading operations.
- `get_symbols`: Get all available symbols (financial instruments) from the MetaTrader 5 terminal.
- `get_symbols_by_group`: Get symbols that match a specific group or pattern.
- `symbol_select`: Select a symbol in the Market Watch window or remove a symbol from it.
- ... e mais 18 ferramentas

## ✅ Decisão Preliminar

**STATUS: 🟡 AJUSTAR**


🟡 **AJUSTAR**: 1 funcionalidades críticas ausentes.

**Próximos passos:**
- Implementar funcionalidades ausentes: get_positions
- Testar integração com todas as ferramentas
- Validar performance e confiabilidade


## 💡 Próximos Passos

1. **Iniciar servidor MCP** para testes online
2. **Executar testes funcionais** de todas as ferramentas
3. **Benchmark de performance** das operações críticas
4. **Validar mapeamento B3** (ITSA3/ITSA4)
5. **Implementar gaps identificados** se necessário

---

*Esta análise foi baseada no código-fonte. Execute testes online para validação completa.*
