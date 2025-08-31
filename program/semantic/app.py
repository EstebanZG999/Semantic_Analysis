import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from antlr4 import InputStream, CommonTokenStream
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic.type_checker import TypeChecker
from semantic.error_reporter import ErrorReporter
from semantic.scopes import GlobalScope
from semantic.symbols import FuncSymbol, ClassSymbol


def compile_code(source: str):
    input_stream = InputStream(source)
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)

    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter, GlobalScope())
    checker.visit(tree)

    return reporter, checker.scopes


def render_scope(scope, container, indent=0):
    pad = " " * (indent * 2)

    rows = []
    for _, sym in scope.items():
        rows.append({
            "Category": sym.category,
            "Name": sym.name,
            "Type": str(sym.type),
            "Line": getattr(sym, "line", 0),
            "Col": getattr(sym, "col", 0)
        })

        # Mostrar parámetros
        if isinstance(sym, FuncSymbol):
            for p in sym.params:
                rows.append({
                    "Category": "param",
                    "Name": p.name,
                    "Type": str(p.type),
                    "Line": getattr(p, "line", 0),
                    "Col": getattr(p, "col", 0)
                })
            # Mostrar funciones anidadas
            if hasattr(sym, "nested"):
                for nname, nsym in sym.nested.items():
                    rows.append({
                        "Category": "nested function",
                        "Name": nname,
                        "Type": str(nsym.type),
                        "Line": getattr(nsym, "line", 0),
                        "Col": getattr(nsym, "col", 0)
                    })
                    for np in nsym.params:
                        rows.append({
                            "Category": "param",
                            "Name": np.name,
                            "Type": str(np.type),
                            "Line": getattr(np, "line", 0),
                            "Col": getattr(np, "col", 0)
                        })

        # Mostrar clases
        if isinstance(sym, ClassSymbol):
            for fname, fsym in sym.fields.items():
                rows.append({
                    "Category": "field",
                    "Name": fname,
                    "Type": str(fsym.type),
                    "Line": getattr(fsym, "line", 0),
                    "Col": getattr(fsym, "col", 0)
                })
            for mname, msym in sym.methods.items():
                rows.append({
                    "Category": "method",
                    "Name": mname,
                    "Type": str(msym.type),
                    "Line": getattr(msym, "line", 0),
                    "Col": getattr(msym, "col", 0)
                })

    if rows:
        container.table(rows)


st.set_page_config(page_title="Compiscript IDE", layout="wide")

st.title("📝 Compiscript Mini-IDE")
st.write("Escribe tu programa en Compiscript y compílalo con un clic.")

default_code = """// Programa de ejemplo
const PI: integer = 314;
let saludo: string = "Hola mundo!";

function externo(x: integer): integer {
  function interno(y: integer): integer {
    return x + y;
  }
  return interno(5);
}

let resultado: integer = externo(10);
print("Resultado: " + resultado);
"""

code = st.text_area("Editor", default_code, height=400)

if st.button("Compile "):
    reporter, scopes = compile_code(code)

    if reporter.has_errors():
        st.error(" Errores semánticos encontrados:")
        for e in reporter:
            st.write(f"- {e}")
    else:
        st.success(" Compilación completada sin errores")

    st.subheader(" Tabla de Símbolos")
    for scope in scopes.stack:
        with st.expander(f"Scope: {scope.kind}", expanded=True):
            render_scope(scope, st)
