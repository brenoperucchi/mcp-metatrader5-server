"""
Configurações do MetaTrader 5 para diferentes mercados
"""
import os
from dataclasses import dataclass
from typing import Dict

@dataclass
class MT5Config:
    """Configuração do MetaTrader 5"""
    name: str
    market_type: str
    mt5_path: str
    account: int
    server: str
    password: str = ""
    portable: bool = False
    
    def __str__(self):
        return f"{self.name} ({self.market_type})"

# Configurações disponíveis
MT5_CONFIGS: Dict[str, MT5Config] = {
    "b3": MT5Config(
        name="B3 - Ações Brasileiras", 
        market_type="B3",
        mt5_path=r"D:\Files\MetaTraders\MT5-Python\MetaTrader XPDEMO 82033102 Ticks\terminal64.exe",
        account=72033102,  # Conta demo B3
        server="XPMT5-DEMO",
        portable=True
    ),
    "forex": MT5Config(
        name="Forex - Mercado Global",
        market_type="Forex", 
        mt5_path=r"D:\Files\MetaTraders\MT5-Python\MetaTrader XPDEMO 82033102 Ticks\terminal64.exe",
        account=72033102,  # Conta demo Forex
        server="XPMT5-DEMO",
        portable=True
    )
}

def get_config(config_name: str) -> MT5Config:
    """Obtém uma configuração específica"""
    if config_name not in MT5_CONFIGS:
        raise ValueError(f"Configuração '{config_name}' não encontrada. Disponíveis: {list(MT5_CONFIGS.keys())}")
    return MT5_CONFIGS[config_name]

def list_configs() -> Dict[str, Dict[str, str]]:
    """Lista todas as configurações disponíveis"""
    result = {}
    for key, config in MT5_CONFIGS.items():
        result[key] = {
            "name": config.name,
            "market_type": config.market_type,
            "account": str(config.account),
            "server": config.server
        }
    return result