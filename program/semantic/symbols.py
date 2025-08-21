from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple
from .typesys import Type, FunctionType

@dataclass
class Symbol:
    name: str
    type: Type

@dataclass
class VarSymbol(Symbol):
    is_const: bool = False
    is_initialized: bool = False

@dataclass
class ParamSymbol(Symbol):
    index: int = 0  # posición en la lista de parámetros

@dataclass
class FuncSymbol(Symbol):
    type: FunctionType 
    params: Tuple[ParamSymbol, ...] = field(default_factory=tuple)

@dataclass
class ClassSymbol(Symbol):
    # type.name == nombre de la clase
    fields: Dict[str, VarSymbol] = field(default_factory=dict)
    methods: Dict[str, FuncSymbol] = field(default_factory=dict)
