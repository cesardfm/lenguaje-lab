"""Errores del compilador, con fase, posición y señalador en la línea."""


class ErrorCompilacion(Exception):
    """Error en cualquier fase: léxica, sintáctica o semántica."""

    def __init__(self, fase, mensaje, linea, columna, fuente=None):
        self.fase = fase
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        self.fuente = fuente
        super().__init__(str(self))

    def __str__(self):
        cabecera = f"[{self.fase}] línea {self.linea}, columna {self.columna}: {self.mensaje}"
        if not self.fuente:
            return cabecera
        lineas = self.fuente.split("\n")
        if not 1 <= self.linea <= len(lineas):
            return cabecera
        return f"{cabecera}\n  {lineas[self.linea - 1]}\n  {' ' * (self.columna - 1)}^"


def error_lexico(mensaje, linea, columna, fuente=None):
    return ErrorCompilacion("léxico", mensaje, linea, columna, fuente)


def error_sintactico(mensaje, linea, columna, fuente=None):
    return ErrorCompilacion("sintáctico", mensaje, linea, columna, fuente)


def error_semantico(mensaje, linea, columna, fuente=None):
    return ErrorCompilacion("semántico", mensaje, linea, columna, fuente)
