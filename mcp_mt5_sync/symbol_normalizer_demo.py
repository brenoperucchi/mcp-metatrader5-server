#!/usr/bin/env python3
"""
E2.3 - Demonstração do Symbol Normalizer com MCP
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.b3_symbol_normalizer import (
    B3SymbolNormalizer,
    normalize_symbol,
    is_valid_pair,
    get_pair_for_symbol,
    format_symbol
)
import asyncio
import aiohttp
import json
from typing import Dict, Any

class MCPSymbolValidator:
    """Validador de símbolos via MCP"""
    
    def __init__(self, server_url: str = "192.168.0.125:8000"):
        self.server_url = server_url
        self.rpc_url = f"http://{server_url}/mcp"
        self.normalizer = B3SymbolNormalizer()
        self.request_id = 1
    
    async def check_symbol_availability(self, symbol: str) -> Dict[str, Any]:
        """Verifica disponibilidade de símbolo no MCP"""
        # Normalizar símbolo
        normalized = self.normalizer.normalize(symbol)
        if not normalized:
            return {
                "success": False,
                "error": f"Invalid symbol format: {symbol}",
                "original": symbol,
                "normalized": None
            }
        
        # Testar no MCP
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": "get_symbol_info",
                "arguments": {"symbol": normalized.normalized}
            }
        }
        self.request_id += 1
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if "error" in result:
                            return {
                                "success": False,
                                "error": result["error"]["message"],
                                "original": symbol,
                                "normalized": normalized.normalized,
                                "formats": {
                                    "b3": normalized.b3_format,
                                    "mt5": normalized.mt5_format,
                                    "bloomberg": normalized.bloomberg_format
                                }
                            }
                        
                        return {
                            "success": True,
                            "original": symbol,
                            "normalized": normalized.normalized,
                            "base": normalized.base,
                            "type": normalized.type.value,
                            "pair_symbol": normalized.get_pair_symbol(),
                            "formats": {
                                "b3": normalized.b3_format,
                                "mt5": normalized.mt5_format,
                                "bloomberg": normalized.bloomberg_format
                            },
                            "mcp_data": result.get("result", {}).get("content", {})
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "original": symbol,
                            "normalized": normalized.normalized
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original": symbol,
                "normalized": normalized.normalized if normalized else None
            }

def demonstrate_normalization():
    """Demonstra capacidades de normalização"""
    print("="*60)
    print("🔤 B3 SYMBOL NORMALIZER - DEMONSTRAÇÃO")
    print("="*60)
    
    normalizer = B3SymbolNormalizer()
    
    # Diferentes formatos de entrada
    test_symbols = [
        # Formatos básicos
        "ITSA3",           # B3 padrão
        "ITSA4",           # B3 padrão PN
        "itsa3",           # Lowercase
        "ITSA3.SA",        # MetaTrader
        "ITSA4.BOVESPA",   # MetaTrader alternativo
        "ITSA3 BZ",        # Bloomberg
        "BOVESPA:ITSA3",   # Com exchange
        "B3:ITSA4",        # Com exchange
        "ITSA-3",          # Com hífen
        "ITSA_4",          # Com underscore
        "ITAUSA ON",       # Nome longo
        "ITAUSA PN",       # Nome longo PN
        # Outros símbolos
        "PETR3",
        "PETR4",
        "VALE3",
        "BBDC4",
        "KLBN11",          # UNIT
        "USIM5",           # PNA
        "ELET6",           # PNB
        # Inválidos
        "INVALID",
        "XXXX9",
        "123456",
    ]
    
    print("\n📋 NORMALIZAÇÃO DE SÍMBOLOS")
    print("-"*60)
    print(f"{'Original':<20} {'Normalizado':<12} {'Base':<8} {'Tipo':<8} {'Par':<8}")
    print("-"*60)
    
    for symbol in test_symbols:
        norm = normalizer.normalize(symbol)
        if norm:
            print(f"{symbol:<20} {norm.normalized:<12} {norm.base:<8} {norm.type.value:<8} {norm.get_pair_symbol() or '-':<8}")
        else:
            print(f"{symbol:<20} {'INVÁLIDO':<12} {'-':<8} {'-':<8} {'-':<8}")
    
    # Pares de arbitragem
    print("\n🔄 PARES DE ARBITRAGEM DISPONÍVEIS")
    print("-"*60)
    pairs = normalizer.get_arbitrage_pairs()
    for i, (on, pn) in enumerate(pairs[:10], 1):  # Primeiros 10
        print(f"{i:2d}. {on} ⇄ {pn}")
    
    # Validação de pares
    print("\n✅ VALIDAÇÃO DE PARES")
    print("-"*60)
    test_pairs = [
        ("ITSA3", "ITSA4"),     # Válido
        ("PETR3", "PETR4"),     # Válido
        ("ITSA3.SA", "ITSA4"),  # Válido (formatos diferentes)
        ("ITSA3", "PETR4"),     # Inválido (bases diferentes)
        ("ITSA3", "ITSA3"),     # Inválido (mesmo símbolo)
        ("KLBN11", "KLBN3"),    # Inválido (UNIT com ON)
    ]
    
    for sym1, sym2 in test_pairs:
        valid = normalizer.validate_pair(sym1, sym2)
        status = "✅ Válido" if valid else "❌ Inválido"
        print(f"{sym1:<10} + {sym2:<10} = {status}")
    
    # Formatação para diferentes fontes
    print("\n📐 FORMATAÇÃO PARA DIFERENTES FONTES")
    print("-"*60)
    symbol = "ITSA3"
    sources = ["b3", "mt5", "bloomberg"]
    
    for source in sources:
        formatted = normalizer.format_for_source(symbol, source)
        print(f"{source:<12}: {formatted}")
    
    # Cache
    print("\n💾 ESTATÍSTICAS DO CACHE")
    print("-"*60)
    print(f"Símbolos em cache: {len(normalizer.cache)}")
    print(f"Primeiros 5: {list(normalizer.cache.keys())[:5]}")

async def test_mcp_integration():
    """Testa integração com MCP"""
    print("\n" + "="*60)
    print("🔌 TESTE DE INTEGRAÇÃO COM MCP")
    print("="*60)
    
    validator = MCPSymbolValidator()
    
    # Símbolos para testar
    test_symbols = [
        "ITSA3",       # Formato B3
        "ITSA4.SA",    # Formato MT5
        "PETR-3",      # Formato hífen
        "VALE_3",      # Formato underscore
        "ITAUSA PN",   # Nome longo
        "INVALID",     # Inválido
    ]
    
    print("\n📡 Validando símbolos no servidor MCP...")
    print("-"*60)
    
    for symbol in test_symbols:
        result = await validator.check_symbol_availability(symbol)
        
        if result["success"]:
            print(f"✅ {symbol:<15} → {result['normalized']:<8} ({result['type']})")
            if result.get("pair_symbol"):
                print(f"   Par disponível: {result['pair_symbol']}")
            if result.get("mcp_data"):
                data = result["mcp_data"]
                if isinstance(data, dict) and "bid" in data:
                    print(f"   Cotação: Bid={data.get('bid')} Ask={data.get('ask')}")
        else:
            if result.get("normalized"):
                print(f"⚠️  {symbol:<15} → {result['normalized']:<8} (MCP: {result['error']})")
            else:
                print(f"❌ {symbol:<15} → Formato inválido")
    
    print("\n📊 Formatos disponíveis para exportação:")
    print("-"*60)
    
    # Mostrar diferentes formatos
    norm_result = await validator.check_symbol_availability("ITSA3")
    if norm_result["success"] and "formats" in norm_result:
        for format_name, format_value in norm_result["formats"].items():
            print(f"{format_name:<12}: {format_value}")

def main():
    """Função principal"""
    print("🚀 E2.3 - NORMALIZAÇÃO DE SÍMBOLOS B3")
    print("="*60)
    
    # 1. Demonstração de normalização
    demonstrate_normalization()
    
    # 2. Teste de integração com MCP (se disponível)
    try:
        print("\n🔗 Testando conexão com MCP...")
        asyncio.run(test_mcp_integration())
    except Exception as e:
        print(f"\n⚠️  Servidor MCP não disponível: {e}")
        print("   Execute apenas com servidor MCP ativo")
    
    print("\n✅ Demonstração concluída!")

if __name__ == "__main__":
    main()