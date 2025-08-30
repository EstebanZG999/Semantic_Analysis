import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from semantic.type_checker import TypeChecker
from semantic.error_reporter import ErrorReporter

def main(argv):
    if len(argv) < 2:
        print("Uso: python Driver.py <archivo.cps>")
        return

    input_stream = FileStream(argv[1], encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)

    tree = parser.program()

    reporter = ErrorReporter()
    checker = TypeChecker(reporter)

    checker.visit(tree)

    # 5. Reportar resultados
    if reporter.has_errors():
        print(" Errores semánticos encontrados:")
        for e in reporter:
            print("   ", e)
    else:
        print(" Análisis semántico completado sin errores.")

if __name__ == "__main__":
    main(sys.argv)
