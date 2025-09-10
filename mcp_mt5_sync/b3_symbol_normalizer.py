#!/usr/bin/env python3
"""
E2.3 - B3 Symbol Normalizer
Normalização e padronização de símbolos da B3 entre diferentes fontes
"""

import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SymbolType(Enum):
    """Tipos de ações na B3"""
    ON = "ON"  # Ordinária
    PN = "PN"  # Preferencial
    PNA = "PNA"  # Preferencial Classe A
    PNB = "PNB"  # Preferencial Classe B
    PNC = "PNC"  # Preferencial Classe C
    PND = "PND"  # Preferencial Classe D
    UNIT = "UNIT"  # Unit
    BDR = "BDR"  # Brazilian Depositary Receipt
    FII = "FII"  # Fundo Imobiliário
    ETF = "ETF"  # Exchange Traded Fund

@dataclass
class NormalizedSymbol:
    """Símbolo normalizado com metadados"""
    raw: str  # Símbolo original
    base: str  # Código base (ex: ITSA)
    suffix: int  # Número do sufixo (3, 4, 11, etc)
    type: SymbolType  # Tipo de ação
    normalized: str  # Formato normalizado (ex: ITSA3)
    mt5_format: str  # Formato MetaTrader 5
    bloomberg_format: str  # Formato Bloomberg
    b3_format: str  # Formato B3 oficial
    
    @property
    def is_pair_tradeable(self) -> bool:
        """Verifica se tem par ON/PN para arbitragem"""
        return self.type in [SymbolType.ON, SymbolType.PN]
    
    def get_pair_symbol(self) -> str:
        """Retorna símbolo do par ON/PN"""
        if self.type == SymbolType.ON:
            return f"{self.base}4"  # ON (3) -> PN (4)
        elif self.type == SymbolType.PN:
            return f"{self.base}3"  # PN (4) -> ON (3)
        return None

class B3SymbolNormalizer:
    """Normalizador de símbolos B3"""
    
    # Mapeamento de sufixos para tipos
    SUFFIX_TYPE_MAP = {
        3: SymbolType.ON,
        4: SymbolType.PN,
        5: SymbolType.PNA,
        6: SymbolType.PNB,
        7: SymbolType.PNC,
        8: SymbolType.PND,
        11: SymbolType.UNIT,
        # BDRs geralmente terminam em 31-39
        31: SymbolType.BDR,
        32: SymbolType.BDR,
        33: SymbolType.BDR,
        34: SymbolType.BDR,
        35: SymbolType.BDR,
        39: SymbolType.BDR,
    }
    
    # Símbolos conhecidos com pares ON/PN
    KNOWN_PAIRS = {
        "ITSA": (3, 4),  # ITSA3/ITSA4
        "PETR": (3, 4),  # PETR3/PETR4
        "VALE": (3, None),  # VALE3 (sem PN)
        "BBDC": (3, 4),  # BBDC3/BBDC4
        "BBAS": (3, None),  # BBAS3 (sem PN)
        "ITUB": (3, 4),  # ITUB3/ITUB4
        "ABEV": (3, None),  # ABEV3 (sem PN)
        "GGBR": (3, 4),  # GGBR3/GGBR4
        "CSNA": (3, None),  # CSNA3 (sem PN)
        "USIM": (3, 5),  # USIM3/USIM5 (PNA)
        "GOAU": (3, 4),  # GOAU3/GOAU4
        "KLBN": (3, 4, 11),  # KLBN3/KLBN4/KLBN11
        "SUZB": (3, None),  # SUZB3 (sem PN)
        "VIVT": (3, 4),  # VIVT3/VIVT4
        "CMIG": (3, 4),  # CMIG3/CMIG4
        "ELET": (3, 6),  # ELET3/ELET6
        "EMBR": (3, None),  # EMBR3 (sem PN)
        "BRAP": (3, 4),  # BRAP3/BRAP4
        "TAEE": (3, 4, 11),  # TAEE3/TAEE4/TAEE11
        "SANB": (3, 4, 11),  # SANB3/SANB4/SANB11
    }
    
    # Padrões de regex para diferentes formatos
    PATTERNS = {
        # B3 padrão: ITSA3, PETR4, VALE3
        "b3_standard": re.compile(r'^([A-Z]{4})(\d{1,2})$'),
        
        # MetaTrader: ITSA3.SA, PETR4.BOVESPA
        "mt5_format": re.compile(r'^([A-Z]{4})(\d{1,2})\.([A-Z]+)$'),
        
        # Bloomberg: ITSA3 BZ, PETR4 BS
        "bloomberg": re.compile(r'^([A-Z]{4})(\d{1,2})\s+([A-Z]{2})$'),
        
        # Com exchange: BOVESPA:ITSA3, B3:PETR4
        "exchange_prefix": re.compile(r'^([A-Z0-9]+):([A-Z]{4})(\d{1,2})$'),
        
        # Formato longo: ITAUSA PN, PETROBRAS ON
        "long_name": re.compile(r'^([A-Z]+)\s+(ON|PN|PNA|PNB|UNIT)$'),
        
        # Formato com hífen: ITSA-3, PETR-4
        "hyphen": re.compile(r'^([A-Z]{4})-(\d{1,2})$'),
        
        # Formato com underscore: ITSA_3, PETR_4
        "underscore": re.compile(r'^([A-Z]{4})_(\d{1,2})$'),
    }
    
    # Mapeamento de nomes longos para códigos
    LONG_NAME_MAP = {
        "ITAUSA": "ITSA",
        "PETROBRAS": "PETR",
        "VALE": "VALE",
        "BRADESCO": "BBDC",
        "BRASIL": "BBAS",
        "ITAU": "ITUB",
        "AMBEV": "ABEV",
        "GERDAU": "GGBR",
        "SIDERURGICA": "CSNA",
        "USIMINAS": "USIM",
        "METALURGICA": "GOAU",
        "KLABIN": "KLBN",
        "SUZANO": "SUZB",
        "TELEFONICA": "VIVT",
        "CEMIG": "CMIG",
        "ELETROBRAS": "ELET",
        "EMBRAER": "EMBR",
        "BRADESPAR": "BRAP",
        "TAESA": "TAEE",
        "SANTANDER": "SANB",
    }
    
    def __init__(self):
        self.cache: Dict[str, NormalizedSymbol] = {}
        
    def normalize(self, symbol: str) -> Optional[NormalizedSymbol]:
        """Normaliza símbolo de qualquer formato para padrão B3"""
        if not symbol:
            return None
            
        # Verificar cache
        if symbol in self.cache:
            return self.cache[symbol]
        
        # Limpar e preparar símbolo
        clean_symbol = symbol.strip().upper()
        
        # Tentar cada padrão
        result = None
        
        # 1. B3 padrão
        match = self.PATTERNS["b3_standard"].match(clean_symbol)
        if match:
            result = self._create_normalized(match.group(1), int(match.group(2)), clean_symbol)
        
        # 2. MetaTrader format
        if not result:
            match = self.PATTERNS["mt5_format"].match(clean_symbol)
            if match:
                result = self._create_normalized(match.group(1), int(match.group(2)), clean_symbol)
        
        # 3. Bloomberg format
        if not result:
            match = self.PATTERNS["bloomberg"].match(clean_symbol)
            if match:
                result = self._create_normalized(match.group(1), int(match.group(2)), clean_symbol)
        
        # 4. Exchange prefix
        if not result:
            match = self.PATTERNS["exchange_prefix"].match(clean_symbol)
            if match:
                result = self._create_normalized(match.group(2), int(match.group(3)), clean_symbol)
        
        # 5. Hyphen format
        if not result:
            match = self.PATTERNS["hyphen"].match(clean_symbol)
            if match:
                result = self._create_normalized(match.group(1), int(match.group(2)), clean_symbol)
        
        # 6. Underscore format
        if not result:
            match = self.PATTERNS["underscore"].match(clean_symbol)
            if match:
                result = self._create_normalized(match.group(1), int(match.group(2)), clean_symbol)
        
        # 7. Long name format
        if not result:
            match = self.PATTERNS["long_name"].match(clean_symbol)
            if match:
                long_name = match.group(1)
                type_str = match.group(2)
                
                # Mapear nome longo para código
                base_code = self.LONG_NAME_MAP.get(long_name)
                if base_code:
                    # Determinar sufixo baseado no tipo
                    suffix = self._type_to_suffix(base_code, type_str)
                    if suffix:
                        result = self._create_normalized(base_code, suffix, clean_symbol)
        
        # Cachear resultado
        if result:
            self.cache[symbol] = result
            
        return result
    
    def _create_normalized(self, base: str, suffix: int, raw: str) -> NormalizedSymbol:
        """Cria objeto NormalizedSymbol"""
        symbol_type = self.SUFFIX_TYPE_MAP.get(suffix, SymbolType.ON)
        
        normalized = f"{base}{suffix}"
        
        return NormalizedSymbol(
            raw=raw,
            base=base,
            suffix=suffix,
            type=symbol_type,
            normalized=normalized,
            mt5_format=f"{normalized}.SA",
            bloomberg_format=f"{normalized} BZ",
            b3_format=normalized
        )
    
    def _type_to_suffix(self, base: str, type_str: str) -> Optional[int]:
        """Converte string de tipo para sufixo numérico"""
        if base not in self.KNOWN_PAIRS:
            return None
            
        known = self.KNOWN_PAIRS[base]
        
        if type_str == "ON" and known[0]:
            return known[0]  # Geralmente 3
        elif type_str == "PN" and len(known) > 1 and known[1]:
            return known[1]  # Geralmente 4
        elif type_str == "UNIT" and len(known) > 2 and known[2]:
            return known[2]  # Geralmente 11
        elif type_str == "PNA":
            return 5
        elif type_str == "PNB":
            return 6
        
        return None
    
    def get_arbitrage_pairs(self) -> List[Tuple[str, str]]:
        """Retorna lista de pares ON/PN disponíveis para arbitragem"""
        pairs = []
        for base, suffixes in self.KNOWN_PAIRS.items():
            if len(suffixes) >= 2 and suffixes[0] and suffixes[1]:
                on_symbol = f"{base}{suffixes[0]}"
                pn_symbol = f"{base}{suffixes[1]}"
                pairs.append((on_symbol, pn_symbol))
        return pairs
    
    def validate_pair(self, symbol1: str, symbol2: str) -> bool:
        """Valida se dois símbolos formam um par ON/PN válido"""
        norm1 = self.normalize(symbol1)
        norm2 = self.normalize(symbol2)
        
        if not norm1 or not norm2:
            return False
        
        # Devem ter mesma base
        if norm1.base != norm2.base:
            return False
        
        # Um deve ser ON e outro PN
        types = {norm1.type, norm2.type}
        return types == {SymbolType.ON, SymbolType.PN}
    
    def format_for_source(self, symbol: str, source: str) -> Optional[str]:
        """Formata símbolo para fonte específica"""
        norm = self.normalize(symbol)
        if not norm:
            return None
        
        source_lower = source.lower()
        
        if source_lower in ["mt5", "metatrader", "metatrader5"]:
            return norm.mt5_format
        elif source_lower in ["bloomberg", "bbg"]:
            return norm.bloomberg_format
        elif source_lower in ["b3", "bovespa", "brasil"]:
            return norm.b3_format
        else:
            return norm.normalized
    
    def bulk_normalize(self, symbols: List[str]) -> Dict[str, NormalizedSymbol]:
        """Normaliza lista de símbolos"""
        results = {}
        for symbol in symbols:
            norm = self.normalize(symbol)
            if norm:
                results[symbol] = norm
        return results


# Singleton instance
_normalizer_instance = None

def get_normalizer() -> B3SymbolNormalizer:
    """Retorna instância singleton do normalizador"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = B3SymbolNormalizer()
    return _normalizer_instance


# Funções de conveniência
def normalize_symbol(symbol: str) -> Optional[str]:
    """Normaliza símbolo para formato B3 padrão"""
    normalizer = get_normalizer()
    result = normalizer.normalize(symbol)
    return result.normalized if result else None

def is_valid_pair(symbol1: str, symbol2: str) -> bool:
    """Verifica se dois símbolos formam par ON/PN válido"""
    return get_normalizer().validate_pair(symbol1, symbol2)

def get_pair_for_symbol(symbol: str) -> Optional[str]:
    """Retorna o par ON/PN para um símbolo"""
    normalizer = get_normalizer()
    norm = normalizer.normalize(symbol)
    return norm.get_pair_symbol() if norm else None

def format_symbol(symbol: str, target: str = "b3") -> Optional[str]:
    """Formata símbolo para formato específico"""
    return get_normalizer().format_for_source(symbol, target)