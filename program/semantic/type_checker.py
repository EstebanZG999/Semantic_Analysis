from semantic.scopes import GlobalScope, BlockScope, ScopeStack

class TypeChecker:
    def __init__(self, global_scope: GlobalScope|None=None):
        self.scopes = ScopeStack(global_scope or GlobalScope())

    # visitProgram: trabaja en el global existente
    def visitProgram(self, program_node):
        # Aquí C iterará nodos top-level (clases, funciones, vars)
        # y usará self.scopes.current para definir símbolos.
        # Ejemplo conceptual (no ANTLR):
        # for decl in program_node.decls: self.visit(decl)
        return None

    # visitBlock: abre y cierra block scope
    def visitBlock(self, block_node):
        self.scopes.push('block')
        # for stmt in block_node.statements: self.visit(stmt)
        self.scopes.pop()
        return None

    # Helpers extra para C (opcional)
    def enter_function(self, return_type, name=None):
        return self.scopes.push_function(return_type, name)

    def exit_scope(self):
        return self.scopes.pop()

    def enter_class(self, class_name):
        return self.scopes.push_class(class_name)
