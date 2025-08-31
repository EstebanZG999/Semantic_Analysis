import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from antlr4 import InputStream, CommonTokenStream
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic.type_checker import TypeChecker
from semantic.error_reporter import ErrorReporter
from semantic.scopes import GlobalScope


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



st.set_page_config(page_title="Compiscript IDE", layout="wide")

st.title(" Compiscript Mini-IDE")
st.write("Escribe tu programa en Compiscript y compílalo con un clic.")

default_code = """// Programa de ejemplo
const PI: integer = 314;
let saludo: string = "Hola mundo!";

function multiplicar(a: integer, b: integer): integer {
  return a * b;
}

let resultado: integer = multiplicar(6, 7);
print("Resultado: " + resultado);
"""

code = st.text_area("Editor", default_code, height=400)

if st.button("Compile 🚀"):
    reporter, scopes = compile_code(code)

    if reporter.has_errors():
        st.error(" Errores semánticos encontrados:")
        for e in reporter:
            st.write(f"- {e}")
    else:
        st.success(" Compilación completada sin errores")

    
    for scope in scopes.stack:
        st.subheader(f"Scope: {scope.kind}")
        rows = [
            {
                "Category": sym.category,
                "Name": sym.name,
                "Type": str(sym.type),
                "Line": sym.line,
                "Col": sym.col
            }
            for _, sym in scope.items()
        ]
        st.table(rows)
