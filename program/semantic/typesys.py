from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

# ----- Nombres canónicos de tipos primitivos -----
T_INTEGER = "integer"
T_STRING  = "string"
T_BOOLEAN = "boolean"
T_NULL    = "null"
T_VOID    = "void"

# ----- Clases de tipos -----
@dataclass(frozen=True)
class Type:
    name: str
    def __str__(self) -> str: return self.name
    def is_primitive(self) -> bool:
        return self.name in {T_INTEGER, T_STRING, T_BOOLEAN, T_NULL, T_VOID}

@dataclass(frozen=True)
class ArrayType(Type):
    elem: Type | None = None
    dims: int = 1
    def __str__(self) -> str:
        if self.elem is None:
            return "[]"
        return f"{self.elem}{'[]'*self.dims}"

@dataclass(frozen=True)
class FunctionType(Type):
    params: Tuple[Type, ...] = ()
    ret: Type = Type(T_VOID)
    def __str__(self) -> str:
        args = ", ".join(str(p) for p in self.params)
        return f"({args}) -> {self.ret}"

@dataclass(frozen=True)
class ClassType(Type):
    # name == nombre de clase
    pass

# ----- Singletons útiles -----
INTEGER = Type(T_INTEGER)
STRING  = Type(T_STRING)
BOOLEAN = Type(T_BOOLEAN)
NULL    = Type(T_NULL)
VOID    = Type(T_VOID)

# ----- Predicados y helpers -----
def is_numeric(t: Type) -> bool:
    # float, extiende aquí.
    return t.name == T_INTEGER

def is_boolean(t: Type) -> bool: return t.name == T_BOOLEAN
def is_string(t: Type) -> bool:  return t.name == T_STRING

def equal_types(a: Type, b: Type) -> bool:
    # Igualdad estructural 
    if isinstance(a, ArrayType) and isinstance(b, ArrayType):
        return a.dims == b.dims and equal_types(a.elem, b.elem)  # type: ignore[arg-type]
    return a.name == b.name

# ----- Reglas de compatibilidad -----
def can_assign(dst: Type, src: Type) -> bool:
    """
    Asignación semánticamente válida:
      - Tipos exactamente iguales.
      - null asignable a referencias (arrays, clases, string).
    """
    if equal_types(dst, src):
        return True
    if isinstance(dst, ArrayType) and src.name == T_NULL:
        return True
    if isinstance(dst, ClassType) and src.name == T_NULL:
        return True
    if is_string(dst) and src.name == T_NULL:
        return True
    return False

def arithmetic_type(lhs: Type, rhs: Type) -> Optional[Type]:
    # + - * / requieren numéricos y devuelven integer
    if is_numeric(lhs) and is_numeric(rhs):
        return INTEGER
    return None

def logical_type(lhs: Type, rhs: Type) -> Optional[Type]:
    # && || requieren boolean y devuelven boolean.
    if is_boolean(lhs) and is_boolean(rhs):
        return BOOLEAN
    return None

def comparison_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Comparaciones:
      - ==, != : mismo tipo → boolean 
      - <, <=, >, >= : numéricos → boolean 
    Aquí devolvemos boolean si los operandos son comparables,
    el visitor decide si el operador es de igualdad u orden.
    """
    if equal_types(lhs, rhs):
        return BOOLEAN
    if is_numeric(lhs) and is_numeric(rhs):
        return BOOLEAN
    return None
