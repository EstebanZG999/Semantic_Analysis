from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Iterable
from semantic.symbols import Symbol

@dataclass
class Scope:
    """Ámbito semántico: mantiene un mapa nombre->símbolo y referencia al padre."""
    kind: str  # 'global' | 'class' | 'function' | 'block'
    parent: Optional['Scope'] = None
    symbols: Dict[str, Symbol] = field(default_factory=dict)

    def define(self, sym: Symbol) -> bool:
        """
        Intenta registrar 'sym' en este scope.
        Retorna False si el nombre ya existe en ESTE scope (redeclaración).
        """
        if sym.name in self.symbols:
            return False
        self.symbols[sym.name] = sym
        return True

    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Busca el símbolo por 'name' en este scope y, si no está, recorre la cadena de padres.
        """
        s: Optional[Scope] = self
        while s is not None:
            if name in s.symbols:
                return s.symbols[name]
            s = s.parent
        return None

    # Utilidades opcionales:
    def __contains__(self, name: str) -> bool:
        return name in self.symbols

    def items(self) -> Iterable[tuple[str, Symbol]]:
        return self.symbols.items()


class ScopeStack:
    """
    Pila de scopes para usar desde el TypeChecker.
    No depende de ANTLR. Persona C llama push/pop en visitProgram/visitBlock/visitFunction/visitClass.
    """
    def __init__(self, root: Optional[Scope] = None):
        self.stack: list[Scope] = [root] if root else []

    @property
    def current(self) -> Scope:
        if not self.stack:
            raise RuntimeError("ScopeStack vacío: asegúrate de push(global) antes de usarlo.")
        return self.stack[-1]

    def push(self, kind: str) -> Scope:
        parent = self.stack[-1] if self.stack else None
        new_scope = Scope(kind=kind, parent=parent)
        self.stack.append(new_scope)
        return new_scope

    def push_child(self, child: Scope) -> Scope:
        """Permite reutilizar un Scope preconstruido como hijo del actual."""
        child.parent = self.current if self.stack else None
        self.stack.append(child)
        return child

    def pop(self) -> Scope:
        if not self.stack:
            raise RuntimeError("Pop en ScopeStack vacío.")
        return self.stack.pop()

    def depth(self) -> int:
        return len(self.stack)
