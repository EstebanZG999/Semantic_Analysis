# program/semantic/error_reporter.py

class ErrorReporter:
    """
    Recolector simple de errores semánticos.
    Cada error incluye: línea, columna, código y mensaje.
    """

    def __init__(self):
        self.errors: list[str] = []

    def report(self, line: int, col: int, code: str, msg: str):
        """
        Registra un error con su posición y mensaje.
        """
        err = f"[{line}:{col}] {code}: {msg}"
        self.errors.append(err)

    def has_errors(self) -> bool:
        """
        True si se registraron errores.
        """
        return len(self.errors) > 0

    def count(self) -> int:
        """
        Número de errores registrados.
        """
        return len(self.errors)

    def clear(self):
        """
        Limpia la lista de errores.
        """
        self.errors.clear()

    def __iter__(self):
        return iter(self.errors)

    def __str__(self):
        if not self.errors:
            return "No hay errores."
        return "\n".join(self.errors)
