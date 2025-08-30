
from semantic.typesys import make_fn, FunctionType
from semantic.scopes import GlobalScope, ScopeStack
from semantic.symbols import VarSymbol, FuncSymbol, ClassSymbol, ParamSymbol
from semantic.typesys import (
    Type, INTEGER, STRING, BOOLEAN, VOID, NULL,
    ArrayType,   
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

    
    
    
    def define_symbol(self, sym):
        if not self.scopes.current.define(sym):
            self.reporter.report(0, 0, "E_REDECL", f"Redeclaración de {sym.name}")

    def resolve_symbol(self, name, line=0, col=0):
        if name in ("integer", "string", "boolean", "void"):
            return None

        sym = self.scopes.current.resolve(name)
        if sym is None:
            self.reporter.report(line, col, "E_UNDEF", f"Símbolo no definido: {name}")
        return sym


    
    
    
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        self.scopes.push("global")
        for stmt in ctx.statement():
            self.visit(stmt)
        self.scopes.pop()
        return None

    
    
    
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        vtype = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else VOID
        print(f"[DEBUG] Declarando variable '{name}' con tipo anotado: {vtype}")

        sym = VarSymbol(name, vtype, is_const=False, is_initialized=False)

        if ctx.initializer():
            init_t = self.visit(ctx.initializer().expression())
            print(f"[DEBUG] Inicializador de '{name}' tiene tipo: {init_t}")
            print(f"[DEBUG] Comparando vtype={vtype}, init_t={init_t}")  
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


    
    
    

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        ret_type = self.visit(ctx.type_()) if ctx.type_() else VOID
        print(f"[DEBUG] Declarando función '{name}' con tipo de retorno anotado: {ret_type}")

        params = []
        if ctx.parameters():
            for i, p in enumerate(ctx.parameters().parameter()):
                pname = p.Identifier().getText()
                ptype = self.visit(p.type_()) if p.type_() else VOID
                print(f"[DEBUG] Parámetro {i} de '{name}': {pname}: {ptype}")
                param_sym = ParamSymbol(pname, ptype, i)
                params.append(param_sym)

        
        func_type = make_fn([p.type for p in params], ret_type)
        func_sym = FuncSymbol(name, type=func_type, params=tuple(params))
        self.define_symbol(func_sym)
        print(f"[DEBUG] Registrando función {name} con type={func_type} y params={func_sym.params}")

        
        self.scopes.push_function(ret_type, name)
        for psym in params:
            self.define_symbol(psym)

        
        returns = []
        for stmt in ctx.block().statement():
            r = self.visit(stmt)
            if stmt.returnStatement():
                returns.append(r or VOID)

        self.scopes.pop()

        if not returns and ret_type != VOID:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN",
                                f"Función {name} sin return pero declarada {ret_type}")

        for rt in returns:
            print(f"[DEBUG] Revisando return de {name}: {rt}")
            if not can_assign(ret_type, rt):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_RETURN",
                                    f"Return {rt} incompatible con {ret_type}")

        print(f"[DEBUG] Función {name} finalizada con tipo {func_type}")
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
        left_t = self.visit(ctx.multiplicativeExpr(0)) or VOID
        for m in ctx.multiplicativeExpr()[1:]:
            right_t = self.visit(m) or VOID
            print(f"[DEBUG] visitAdditiveExpr: {left_t} + {right_t}")
            result = arithmetic_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ADD",
                                    f"No se puede aplicar '+' o '-' entre {left_t} y {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        left_t = self.visit(ctx.unaryExpr(0)) or VOID
        for u in ctx.unaryExpr()[1:]:
            right_t = self.visit(u) or VOID
            print(f"[DEBUG] visitMultiplicativeExpr: {left_t} * {right_t}")
            result = arithmetic_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_MUL",
                                    f"No se puede aplicar '*', '/' o '%' entre {left_t} y {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        left_t = self.visit(ctx.additiveExpr(0)) or VOID
        for a in ctx.additiveExpr()[1:]:
            right_t = self.visit(a) or VOID
            print(f"[DEBUG] visitRelationalExpr: {left_t} ? {right_t}")
            result = comparison_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_REL",
                                    f"No se puede comparar {left_t} con {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        left_t = self.visit(ctx.relationalExpr(0)) or VOID
        for r in ctx.relationalExpr()[1:]:
            right_t = self.visit(r) or VOID
            print(f"[DEBUG] visitEqualityExpr: {left_t} == {right_t}")
            result = comparison_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_EQ",
                                    f"No se puede aplicar '==' o '!=' entre {left_t} y {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        left_t = self.visit(ctx.equalityExpr(0)) or VOID
        for e in ctx.equalityExpr()[1:]:
            right_t = self.visit(e) or VOID
            print(f"[DEBUG] visitLogicalAndExpr: {left_t} && {right_t}")
            result = logical_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_AND",
                                    f"Operador '&&' requiere boolean, no {left_t} y {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        left_t = self.visit(ctx.logicalAndExpr(0)) or VOID
        for e in ctx.logicalAndExpr()[1:]:
            right_t = self.visit(e) or VOID
            print(f"[DEBUG] visitLogicalOrExpr: {left_t} || {right_t}")
            result = logical_type(left_t, right_t)
            if result is None:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_OR",
                                    f"Operador '||' requiere boolean, no {left_t} y {right_t}")
                left_t = VOID
            else:
                left_t = result
        return left_t




    def visitCallExpr(self, ctx: CompiscriptParser.CallExprContext):
        args = []
        if ctx.arguments():
            for e in ctx.arguments().expression():
                arg_t = self.visit(e) or VOID
                args.append(arg_t)
        print(f"[DEBUG] Argumentos en llamada: {args}")

        lhs = ctx.parentCtx
        if not isinstance(lhs, CompiscriptParser.LeftHandSideContext):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                                "Contexto inválido en llamada")
            return VOID

        
        if lhs.primaryAtom() and lhs.primaryAtom().Identifier():
            func_name = lhs.primaryAtom().Identifier().getText()
            print(f"[DEBUG] Llamada a función global '{func_name}' con {len(args)} argumentos")

            sym = self.resolve_symbol(func_name, ctx.start.line, ctx.start.column)
            print(f"[DEBUG] Resolviendo llamada a {func_name}, sym={sym}, sym.type={getattr(sym, 'type', None)}")

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

            
            if isinstance(sym.type, FunctionType):
                print(f"[DEBUG] Retornando type {sym.type.ret} de función {func_name}")
                return sym.type.ret
            return sym.type

        
        if lhs.primaryAtom() and lhs.suffixOp():
            obj_name = lhs.primaryAtom().getText()
            obj_sym = self.resolve_symbol(obj_name, ctx.start.line, ctx.start.column)
            if obj_sym and isinstance(obj_sym.type, Type):
                class_name = obj_sym.type.name
                class_sym = self.resolve_symbol(class_name, ctx.start.line, ctx.start.column)
                if isinstance(class_sym, ClassSymbol):
                    method_name = lhs.suffixOp()[-1].Identifier().getText()
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

                    if isinstance(method.type, FunctionType):
                        print(f"[DEBUG] Retornando type {method.type.ret} de método {method_name}")
                        return method.type.ret
                    return method.type

        
        self.reporter.report(ctx.start.line, ctx.start.column, "E_CALL",
                            "Llamada a algo que no es función ni método")
        return VOID

    




    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        if name == "integer":
            return INTEGER
        if name == "string":
            return STRING
        if name == "boolean":
            return BOOLEAN
        if name == "void":
            return VOID

        sym = self.resolve_symbol(name, ctx.start.line, ctx.start.column)
        if sym:
            print(f"[DEBUG] Identificador '{name}' resuelto con tipo {sym.type}")
            if isinstance(sym, VarSymbol):
                return sym.type
            if isinstance(sym, ParamSymbol):
                return sym.type
            if isinstance(sym, FuncSymbol):
                return sym.type
            if isinstance(sym, ClassSymbol):
                return sym.type
        return VOID







    
    
    
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
        
        return VOID


    def visitArrayLiteral(self, ctx: CompiscriptParser.ArrayLiteralContext):
        elems = [self.visit(e) for e in ctx.expression()]
        print(f"[DEBUG] visitArrayLiteral con {len(elems)} elementos → {elems}")

        if not elems:
            return make_array(VOID, 1)

        elem_type = elems[0]

        
        if all(isinstance(t, Type) and t.name.endswith("[]") for t in elems):
            
            base = elems[0]
            if isinstance(base, ArrayType):
                return make_array(base.elem, base.dims + 1)

        
        for t in elems[1:]:
            if not (can_assign(elem_type, t) and can_assign(t, elem_type)):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_ARRAY_ELEM",
                                    f"Tipos incompatibles en arreglo: {elem_type} y {t}")
        return make_array(elem_type, 1)


    
    
    
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

        
        children = list(ctx.getChildren())
        dims = (len(children) - 1) // 2
        tipo_final = make_array(elem, dims) if dims > 0 else elem
        print(f"[DEBUG] visitType devuelve: {tipo_final}")
        return tipo_final

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_t = self.visit(ctx.expression())
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_IF",
                                f"Condición de if debe ser boolean, no {cond_t}")
        self.visit(ctx.block(0))
        if ctx.block(1):  
            self.visit(ctx.block(1))
        return None

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_t = self.visit(ctx.expression())
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_WHILE",
                                f"Condición de while debe ser boolean, no {cond_t}")
        self.scopes.push("loop")
        self.visit(ctx.block())
        self.scopes.pop()
        return None

    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        self.scopes.push("loop")
        self.visit(ctx.block())
        self.scopes.pop()
        cond_t = self.visit(ctx.expression())
        if cond_t != BOOLEAN:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_DOWHILE",
                                f"Condición de do-while debe ser boolean, no {cond_t}")
        return None


    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        self.scopes.push("loop")

        
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())

        
        if ctx.expression(0):
            cond_t = self.visit(ctx.expression(0))
            if cond_t != BOOLEAN:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_FOR",
                                    f"Condición de for debe ser boolean, no {cond_t}")

        
        if ctx.expression(1):
            self.visit(ctx.expression(1))

        self.visit(ctx.block())
        self.scopes.pop()
        return None

    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        iter_t = self.visit(ctx.expression())
        if not iter_t.name.endswith("[]"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_FOREACH",
                                f"foreach requiere un arreglo, no {iter_t}")
            elem_t = VOID
        else:
            elem_t = Type(iter_t.name[:-2])  

        var_name = ctx.Identifier().getText()
        sym = VarSymbol(var_name, elem_t, is_const=False, is_initialized=True)
        self.define_symbol(sym)

        self.scopes.push("loop")
        self.visit(ctx.block())
        self.scopes.pop()
        return None


    def visitSwitchStatement(self, ctx: CompiscriptParser.SwitchStatementContext):
        control_t = self.visit(ctx.expression())
        self.scopes.push("switch")

        for case in ctx.switchCase():
            case_t = self.visit(case.expression())
            if not can_assign(control_t, case_t):
                self.reporter.report(ctx.start.line, ctx.start.column, "E_SWITCH",
                                    f"case {case_t} incompatible con switch {control_t}")
            for stmt in case.statement():
                self.visit(stmt)

        if ctx.defaultCase():
            for stmt in ctx.defaultCase().statement():
                self.visit(stmt)

        self.scopes.pop()
        return None

    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        if not self.scopes.inside("loop") and not self.scopes.inside("switch"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_BREAK",
                                "break solo se permite en bucles o switch")
        return None

    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        if not self.scopes.inside("loop"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_CONTINUE",
                                "continue solo se permite en bucles")
        return None

    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        self.visit(ctx.block(0))  

        self.scopes.push("catch")
        err_name = ctx.Identifier().getText()
        self.define_symbol(VarSymbol(err_name, STRING, is_const=False, is_initialized=True))
        self.visit(ctx.block(1))  
        self.scopes.pop()
        return None

    def visitIndexExpr(self, ctx: CompiscriptParser.IndexExprContext):
        print(f"[DEBUG] visitIndexExpr → {ctx.getText()}")

        
        lhs_ctx = ctx.parentCtx.primaryAtom()
        if lhs_ctx and lhs_ctx.Identifier():
            arr_name = lhs_ctx.Identifier().getText()
            arr_sym = self.resolve_symbol(arr_name, ctx.start.line, ctx.start.column)
            arr_t = arr_sym.type if arr_sym else VOID
        else:
            arr_t = VOID

        
        idx_t = self.visit(ctx.expression()) or VOID
        print(f"[DEBUG] Indexing {arr_t} con índice tipo {idx_t}")

        if idx_t != INTEGER:
            self.reporter.report(ctx.start.line, ctx.start.column, "E_INDEX",
                                f"Índice debe ser integer, no {idx_t}")

        
        if not isinstance(arr_t, Type) or not arr_t.name.endswith("[]"):
            self.reporter.report(ctx.start.line, ctx.start.column, "E_INDEX",
                                f"El objeto {arr_t} no es indexable")
            return VOID

        
        elem_t = Type(arr_t.name[:-2])  
        print(f"[DEBUG] Resultado de indexación: {elem_t}")
        return elem_t
    




    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:  
            op = ctx.getChild(0).getText()
            t = self.visit(ctx.unaryExpr())
            if op == "-" and t != INTEGER:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_UNARY",
                                    f"Operador '-' solo válido para integer, no {t}")
                return VOID
            if op == "!" and t != BOOLEAN:
                self.reporter.report(ctx.start.line, ctx.start.column, "E_UNARY",
                                    f"Operador '!' solo válido para boolean, no {t}")
                return VOID
            return t
        else:
            return self.visit(ctx.primaryExpr())

    def visitPropertyAccessExpr(self, ctx: CompiscriptParser.PropertyAccessExprContext):
        
        lhs_ctx = ctx.parentCtx
        if not isinstance(lhs_ctx, CompiscriptParser.LeftHandSideContext):
            print("[DEBUG] PropertyAccessExpr sin LeftHandSide padre válido")
            return VOID

        
        obj_ctx = lhs_ctx.primaryAtom()
        obj_t = self.visit(obj_ctx) or VOID

        prop_name = ctx.Identifier().getText()
        print(f"[DEBUG] Acceso a propiedad '{prop_name}' en {obj_t}")

        if isinstance(obj_t, Type):
            class_sym = self.resolve_symbol(obj_t.name, ctx.start.line, ctx.start.column)
            if isinstance(class_sym, ClassSymbol):
                
                if prop_name in class_sym.fields:
                    return class_sym.fields[prop_name].type
                
                if prop_name in class_sym.methods:
                    method = class_sym.methods[prop_name]
                    return method.type if method else VOID
        return VOID



