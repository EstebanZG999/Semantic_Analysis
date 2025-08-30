
from semantic.scopes import GlobalScope, ScopeStack
from semantic.symbols import VarSymbol, FuncSymbol, ClassSymbol, ParamSymbol
from semantic.typesys import (
    Type, INTEGER, STRING, BOOLEAN, VOID, NULL,
    can_assign, arithmetic_type, logical_type, comparison_type,
    make_array
)
from semantic.error_reporter import ErrorReporter
from CompiscriptVisitor import CompiscriptVisitor
from CompiscriptParser import CompiscriptParser


class TypeChecker(CompiscriptVisitor):
    def __init__(self, reporter: ErrorReporter, global_scope: GlobalScope | None = None):
        super().__init__()
        self.scopes = ScopeStack(global_scope or GlobalScope())
        self.reporter = reporter
        self._current_class: str | None = None

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def define_symbol(self, sym):
        if not self.scopes.current.define(sym):
            self.reporter.report(0, 0, "E_REDECL", f"Redeclaración de {sym.name}")

    def resolve_symbol(self, name, line=0, col=0):
        sym = self.scopes.current.resolve(name)
        if sym is None:
            self.reporter.report(line, col, "E_UNDEF", f"Símbolo no definido: {name}")
        return sym

    # ------------------------------------------------------------
    # Program
    # ------------------------------------------------------------
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        self.scopes.push("global")
        for stmt in ctx.statement():
            self.visit(stmt)
        self.scopes.pop()
        return None

    # ------------------------------------------------------------
    # Variables y constantes
    # ------------------------------------------------------------
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        vtype = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else VOID
        print(f"[DEBUG] Declarando variable '{name}' con tipo anotado: {vtype}")

        sym = VarSymbol(name, vtype, is_const=False, is_initialized=False)

        if ctx.initializer():
            init_t = self.visit(ctx.initializer().expression())
            print(f"[DEBUG] Inicializador de '{name}' tiene tipo: {init_t}")
            if not can_assign(vtype, init_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                    f"No se puede asignar {init_t} a {vtype}")
            sym.is_initialized = True

        self.define_symbol(sym)
        return None


    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        vtype = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else VOID
        print(f"[DEBUG] Declarando constante '{name}' con tipo anotado: {vtype}")
        init_t = self.visit(ctx.expression())
        print(f"[DEBUG] Inicializador de constante '{name}' tiene tipo: {init_t}")
        sym = VarSymbol(name, vtype, is_const=True, is_initialized=True)

        if not can_assign(vtype, init_t):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                f"No se puede asignar {init_t} a {vtype}")
        self.define_symbol(sym)
        return None



    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        exprs = ctx.expression()

        if isinstance(exprs, list) and len(exprs) == 2:
            obj_t = self.visit(exprs[0]) or VOID
            value_t = self.visit(exprs[1]) or VOID
            prop_name = ctx.Identifier().getText()
            print(f"[DEBUG] Asignación a propiedad '{prop_name}' en {obj_t} con RHS={value_t}")

            if self._current_class and isinstance(obj_t, Type) and obj_t.name == self._current_class:
                class_sym = self.scopes.current.resolve(self._current_class)
                if isinstance(class_sym, ClassSymbol):
                    field = class_sym.fields.get(prop_name) if hasattr(class_sym, "fields") else None
                    if field and not can_assign(field.type, value_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                            f"No se puede asignar {value_t} a campo {field.type}")
                    return field.type if field else VOID

            return value_t

        else:
            name = ctx.Identifier().getText()
            sym = self.resolve_symbol(name, ctx.start.line, ctx.start.column)
            target_t = (sym.type if sym else VOID) or VOID
            expr_node = exprs[0] if isinstance(exprs, list) else exprs
            value_t = self.visit(expr_node) or VOID
            print(f"[DEBUG] Asignación simple a '{name}' con LHS={target_t}, RHS={value_t}")

            if not can_assign(target_t, value_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ASSIGN",
                                    f"No se puede asignar {value_t} a {target_t}")
            return target_t


    # ------------------------------------------------------------
    # Funciones y parámetros
    # ------------------------------------------------------------
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        ret_type = self.visit(ctx.type_()) if ctx.type_() else VOID
        print(f"[DEBUG] Declarando función '{name}' con tipo de retorno {ret_type}")

        params = []
        if ctx.parameters():
            for i, p in enumerate(ctx.parameters().parameter()):
                pname = p.Identifier().getText()
                ptype = self.visit(p.type_()) if p.type_() else VOID
                print(f"[DEBUG] Parámetro {i} de '{name}': {pname}: {ptype}")
                param_sym = ParamSymbol(pname, ptype, i)
                params.append(param_sym)

        func_sym = FuncSymbol(name, type=ret_type, params=tuple(params))
        self.define_symbol(func_sym)

        # Crear scope para la función
        self.scopes.push_function(ret_type, name)
        for psym in params:
            self.define_symbol(psym)

        returns = []
        for stmt in ctx.block().statement():
            r = self.visit(stmt)
            if stmt.returnStatement():
                returns.append(r or VOID)

        self.scopes.pop()

        for rt in returns:
            if not can_assign(ret_type, rt):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN",
                                    f"Return {rt} incompatible con {ret_type}")
        return None


    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        if ctx.expression():
            ret_t = self.visit(ctx.expression())
            if ret_t is None:
                ret_t = VOID
            print(f"[DEBUG] return con tipo: {ret_t}")
            return ret_t
        print(f"[DEBUG] return vacío → void")
        return VOID

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        left_t = self.visit(ctx.multiplicativeExpr(0))
        for m in ctx.multiplicativeExpr()[1:]:
            right_t = self.visit(m)
            left_t = arithmetic_type(left_t, right_t)
        return left_t

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        left_t = self.visit(ctx.unaryExpr(0))
        for u in ctx.unaryExpr()[1:]:
            right_t = self.visit(u)
            left_t = arithmetic_type(left_t, right_t)
        return left_t

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        left_t = self.visit(ctx.additiveExpr(0))
        for a in ctx.additiveExpr()[1:]:
            right_t = self.visit(a)
            left_t = comparison_type(left_t, right_t)
        return left_t

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        left_t = self.visit(ctx.relationalExpr(0))
        for r in ctx.relationalExpr()[1:]:
            right_t = self.visit(r)
            left_t = comparison_type(left_t, right_t)
        return left_t

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        left_t = self.visit(ctx.equalityExpr(0))
        for e in ctx.equalityExpr()[1:]:
            right_t = self.visit(e)
            left_t = logical_type(left_t, right_t)
        return left_t

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        left_t = self.visit(ctx.logicalAndExpr(0))
        for e in ctx.logicalAndExpr()[1:]:
            right_t = self.visit(e)
            left_t = logical_type(left_t, right_t)
        return left_t




    def visitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))

        lhs = ctx.parentCtx  # leftHandSide

        # --- Caso: llamada a método tipo objeto.metodo(...) ---
        if hasattr(lhs, "suffixOp"):
            prim = lhs.primaryAtom()
            if prim and prim.Identifier():
                obj_name = prim.Identifier().getText()
                obj_sym = self.resolve_symbol(obj_name, ctx.start.line, ctx.start.column)
                if obj_sym and isinstance(obj_sym.type, Type):
                    class_name = obj_sym.type.name
                    class_sym = self.resolve_symbol(class_name, ctx.start.line, ctx.start.column)
                    if isinstance(class_sym, ClassSymbol):
                        # Buscar el último .Identifier antes del call
                        method_name = None
                        for suf in lhs.suffixOp():
                            if isinstance(suf, CompiscriptParser.PropertyAccessExprContext):
                                method_name = suf.Identifier().getText()
                        if not method_name:
                            method_name = "<anon>"

                        print(f"[DEBUG] Llamada a método '{method_name}' en objeto '{obj_name}' de clase {class_name}")

                        method = class_sym.methods.get(method_name)
                        if not method:
                            self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                                f"Método {method_name} no definido en {class_name}")
                            return VOID

                        if len(args) != len(method.params):
                            self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                                f"Número incorrecto de argumentos en {class_name}.{method_name}")
                        else:
                            for i, (arg_t, param) in enumerate(zip(args, method.params)):
                                if not can_assign(param.type, arg_t):
                                    self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                                        f"Argumento {i} incompatible en {class_name}.{method_name}: {arg_t} esperado {param.type}")
                        return method.type

        # --- Caso: función global ---
        if hasattr(lhs, "primaryAtom") and lhs.primaryAtom() and lhs.primaryAtom().Identifier():
            func_name = lhs.primaryAtom().Identifier().getText()
            print(f"[DEBUG] Llamada a función global '{func_name}' con {len(args)} argumentos")

            sym = self.resolve_symbol(func_name, ctx.start.line, ctx.start.column)
            if not sym or not isinstance(sym, FuncSymbol):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                    f"{func_name} no es una función")
                return VOID

            if len(args) != len(sym.params):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                    f"Número incorrecto de argumentos en llamada a {func_name}")
            else:
                for i, (arg_t, param) in enumerate(zip(args, sym.params)):
                    if not can_assign(param.type, arg_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                            f"Argumento {i} incompatible: {arg_t} esperado {param.type}")
            return sym.type

        self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                            "Llamada a algo que no es función ni método")
        return VOID


    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        sym = self.resolve_symbol(name, ctx.start.line, ctx.start.column)
        if sym:
            print(f"[DEBUG] Identificador '{name}' resuelto con tipo {sym.type}")
            if isinstance(sym, VarSymbol):
                return sym.type
            if isinstance(sym, ParamSymbol):   # soporte explícito a parámetros
                return sym.type
            if isinstance(sym, FuncSymbol):
                return sym.type
            if isinstance(sym, ClassSymbol):
                return sym.type
        return VOID





    # ------------------------------------------------------------
    # Clases
    # ------------------------------------------------------------
    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        name = ctx.Identifier(0).getText()
        csym = ClassSymbol(name, type=Type(name))
        csym.fields = {}
        csym.methods = {}
        self.define_symbol(csym)
        print(f"[DEBUG] Declarando clase '{name}'")

        prev = self._current_class
        self._current_class = name
        self.scopes.push_class(name)

        for member in ctx.classMember():
            if member.functionDeclaration():
                # Definir método
                fname = member.functionDeclaration().Identifier().getText()
                ftype = self.visit(member.functionDeclaration().type_()) if member.functionDeclaration().type_() else VOID
                params = []
                if member.functionDeclaration().parameters():
                    for i, p in enumerate(member.functionDeclaration().parameters().parameter()):
                        pname = p.Identifier().getText()
                        ptype = self.visit(p.type_()) if p.type_() else VOID
                        params.append(ParamSymbol(pname, ptype, i))
                fsym = FuncSymbol(fname, type=ftype, params=tuple(params))
                csym.methods[fname] = fsym
                print(f"[DEBUG] Método '{fname}' registrado en clase '{name}' con retorno {ftype}")

                # Procesar cuerpo igual que una función normal
                self.scopes.push_function(ftype, fname)
                for psym in params:
                    self.define_symbol(psym)
                self.visit(member.functionDeclaration().block())
                self.scopes.pop()

            elif member.variableDeclaration():
                vname = member.variableDeclaration().Identifier().getText()
                vtype = self.visit(member.variableDeclaration().typeAnnotation().type_()) if member.variableDeclaration().typeAnnotation() else VOID
                vsym = VarSymbol(vname, vtype, is_const=False, is_initialized=False)
                csym.fields[vname] = vsym
                print(f"[DEBUG] Campo '{vname}' registrado en clase '{name}' con tipo {vtype}")
                self.define_symbol(vsym)

            elif member.constantDeclaration():
                cname = member.constantDeclaration().Identifier().getText()
                ctype = self.visit(member.constantDeclaration().typeAnnotation().type_()) if member.constantDeclaration().typeAnnotation() else VOID
                csym.fields[cname] = VarSymbol(cname, ctype, is_const=True, is_initialized=True)
                print(f"[DEBUG] Constante '{cname}' registrada en clase '{name}' con tipo {ctype}")
                self.define_symbol(csym.fields[cname])

        self.scopes.pop()
        self._current_class = prev
        return None


    # ------------------------------------------------------------
    # Expresiones literales y arreglos
    # ------------------------------------------------------------
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        txt = ctx.getText()
        print(f"[DEBUG] visitLiteralExpr con texto = {txt}")

        if ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        if txt == "null":
            return NULL
        if txt in ("true", "false"):
            return BOOLEAN
        if txt.isdigit():
            return INTEGER
        if txt.startswith('"') and txt.endswith('"'):
            return STRING
        # fallback
        return VOID


    def visitArrayLiteral(self, ctx: CompiscriptParser.ArrayLiteralContext):
        elems = [self.visit(e) for e in ctx.expression()]
        print(f"[DEBUG] visitArrayLiteral con {len(elems)} elementos → {elems}")

        if not elems:
            return make_array(VOID, 1)

        elem_type = elems[0]
        for t in elems[1:]:
            if not (can_assign(elem_type, t) and can_assign(t, elem_type)):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ARRAY_ELEM",
                                     f"Tipos incompatibles en arreglo: {elem_type} y {t}")
        return make_array(elem_type, 1)

    # ------------------------------------------------------------
    # Tipos
    # ------------------------------------------------------------
    def visitThisExpr(self, ctx: CompiscriptParser.ThisExprContext):
        if not self._current_class:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_THIS",
                                "Uso de 'this' fuera de una clase")
            return VOID
        return Type(self._current_class)

    def visitNewExpr(self, ctx: CompiscriptParser.NewExprContext):
        class_name = ctx.Identifier().getText()
        print(f"[DEBUG] Creando instancia de '{class_name}'")

        sym = self.resolve_symbol(class_name, ctx.start.line, ctx.start.column)
        if not sym or not isinstance(sym, ClassSymbol):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                 f"Clase no definida: {class_name}")
            return VOID

        # Revisar argumentos contra el constructor
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                args.append(self.visit(e))

        ctor = sym.methods.get("constructor") if hasattr(sym, "methods") else None
        if ctor and isinstance(ctor, FuncSymbol):
            if len(args) != len(ctor.params):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                     f"Número incorrecto de argumentos al construir {class_name}")
            else:
                for i, (arg_t, param) in enumerate(zip(args, ctor.params)):
                    if not can_assign(param.type, arg_t):
                        self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                             f"Argumento {i} incompatible en constructor de {class_name}")
        else:
            if args:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_NEW",
                                     f"Clase {class_name} no tiene constructor que reciba argumentos")

        return Type(class_name)




    def visitType(self, ctx: CompiscriptParser.TypeContext):
        base_txt = ctx.baseType().getText()
        print(f"[DEBUG] visitType con base_txt = {base_txt}")

        if ctx.baseType().Identifier():
            # Tipo definido por el usuario (ej. clase)
            elem = Type(ctx.baseType().Identifier().getText())
        elif base_txt == "integer":
            elem = INTEGER
        elif base_txt == "string":
            elem = STRING
        elif base_txt == "boolean":
            elem = BOOLEAN
        elif base_txt == "void":
            elem = VOID
        else:
            elem = VOID

        # Manejo de arreglos
        children = list(ctx.getChildren())
        dims = (len(children) - 1) // 2
        tipo_final = make_array(elem, dims) if dims > 0 else elem
        print(f"[DEBUG] visitType devuelve: {tipo_final}")
        return tipo_final

