"""
Global registry for tick persister instance.

This module acts as a singleton to share the tick persister instance
between mcp_mt5_server.py and market_data.py without circular imports.
"""

# Global tick persister instance
_tick_persister_instance = None


def set_tick_persister(persister):
    """Set the global tick persister instance"""
    global _tick_persister_instance
    _tick_persister_instance = persister


def get_tick_persister():
    """Get the global tick persister instance"""
    return _tick_persister_instance
