from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


T_INTEGER = "integer"
T_STRING  = "string"
T_BOOLEAN = "boolean"
T_NULL    = "null"
T_VOID    = "void"


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
    
    pass


INTEGER = Type(T_INTEGER)
STRING  = Type(T_STRING)
BOOLEAN = Type(T_BOOLEAN)
NULL    = Type(T_NULL)
VOID    = Type(T_VOID)


def is_numeric(t: Type) -> bool:
    
    return t.name == T_INTEGER

def is_boolean(t: Type) -> bool: return t.name == T_BOOLEAN
def is_string(t: Type) -> bool:  return t.name == T_STRING

def equal_types(a: Optional[Type], b: Optional[Type]) -> bool:
    
    if a is None or b is None:
        print(f"[DEBUG][equal_types] ⚠️ Uno de los tipos es None → a={a}, b={b}")
        return False

    
    if isinstance(a, ArrayType) and isinstance(b, ArrayType):
        print(f"[DEBUG][equal_types] Comparando arrays: {a} vs {b}")
        return a.dims == b.dims and equal_types(a.elem, b.elem)

    res = a.name == b.name
    print(f"[DEBUG][equal_types] {a} vs {b} → {res}")
    return res

def make_array(elem: Type, dims: int = 1) -> ArrayType:
    return ArrayType(name=f"{elem.name}{'[]'*dims}", elem=elem, dims=dims)

def make_fn(params: list[Type], ret: Type) -> FunctionType:
    return FunctionType(name="function", params=tuple(params), ret=ret)



def can_assign(dst: Optional[Type], src: Optional[Type]) -> bool:
    if dst is None or src is None:
        print(f"[DEBUG][can_assign] ⚠️ dst={dst}, src={src}")
        return False

    if equal_types(dst, src):
        print(f"[DEBUG][can_assign] ✅ {src} asignable a {dst}")
        return True

    if isinstance(dst, ArrayType) and src.name == T_NULL:
        return True
    if isinstance(dst, ClassType) and src.name == T_NULL:
        return True
    if is_string(dst) and src.name == T_NULL:
        return True

    print(f"[DEBUG][can_assign] ❌ {src} NO asignable a {dst}")
    return False

def arithmetic_type(lhs: Type, rhs: Type) -> Optional[Type]:
    """
    Reglas para operaciones aritméticas y concatenación:
      - integer (+,-,*,/) integer → integer
      - string + string → string
      - string + integer → string
      - integer + string → string
    """
    
    if is_numeric(lhs) and is_numeric(rhs):
        print(f"[DEBUG][arithmetic_type] {lhs} + {rhs} → integer")
        return INTEGER

    
    if is_string(lhs) and is_string(rhs):
        print(f"[DEBUG][arithmetic_type] {lhs} + {rhs} → string")
        return STRING
    if is_string(lhs) and is_numeric(rhs):
        print(f"[DEBUG][arithmetic_type] {lhs} + {rhs} → string (string+int)")
        return STRING
    if is_numeric(lhs) and is_string(rhs):
        print(f"[DEBUG][arithmetic_type] {lhs} + {rhs} → string (int+string)")
        return STRING

    
    print(f"[DEBUG][arithmetic_type] ❌ no rule for {lhs} + {rhs}")
    return None


def logical_type(lhs: Type, rhs: Type) -> Optional[Type]:
    
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
