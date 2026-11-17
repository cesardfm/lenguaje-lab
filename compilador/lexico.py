"""
Analizador léxico: convierte el texto fuente en tokens.

Está escrito como un AFD explícito. Hay una variable `estado`, un bucle que
consume un carácter por vuelta y una transición por clase de carácter. Los
estados de aceptación emiten un token y vuelven a INICIO.

        ┌──dígito──▶ NUMERO ──dígito──┐
        │               └──otro──▶ emite NUMERO (y retrocede)
        │
INICIO ─┼──letra───▶ IDENT ──letra|dígito──┐
        │               └──otro──▶ emite IDENT o palabra clave
        │
        ├──'"'─────▶ CADENA ──'"'──▶ emite CADENA
        ├──'/'─────▶ BARRA  ──'/'──▶ COMENTARIO ──salto──▶ INICIO
        ├──'.'─────▶ PUNTO  ──'.'──▶ emite RANGO
        └──'-'─────▶ GUION  ──'>'──▶ emite FLECHA   (si no, MENOS)

Σ del lenguaje: letras, dígitos, los símbolos de abajo y los espacios.
"""
from .errores import error_lexico

PALABRAS_CLAVE = {
    "laberinto", "tamaño", "sala", "pasillo", "entrada", "salida",
    "var", "repetir", "en", "texto",
}

SIMBOLOS = {
    "{": "LLAVE_IZQ", "}": "LLAVE_DER",
    "(": "PAR_IZQ",   ")": "PAR_DER",
    ",": "COMA",      "=": "IGUAL",
    "+": "MAS",       "*": "POR",      "/": "ENTRE",
}

# Estados del AFD
INICIO, NUMERO, IDENT, CADENA, BARRA, COMENTARIO, PUNTO, GUION = range(8)


class Token:
    __slots__ = ("tipo", "valor", "linea", "columna")

    def __init__(self, tipo, valor, linea, columna):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.columna = columna

    def __repr__(self):
        return f"Token({self.tipo}, {self.valor!r}, {self.linea}:{self.columna})"


def _es_letra(c):
    return c.isalpha() or c == "_"


def analizar(fuente):
    """Texto fuente -> lista de tokens, terminada en FIN."""
    tokens = []
    estado = INICIO
    i = 0
    linea = columna = 1
    inicio_linea = inicio_columna = 1
    acumulado = ""
    n = len(fuente)

    def emitir(tipo, valor):
        tokens.append(Token(tipo, valor, inicio_linea, inicio_columna))

    while i <= n:
        c = fuente[i] if i < n else "\0"

        if estado == INICIO:
            if c == "\0":
                break
            if c in " \t\r":
                i += 1; columna += 1; continue
            if c == "\n":
                i += 1; linea += 1; columna = 1; continue
            inicio_linea, inicio_columna = linea, columna
            if c.isdigit():
                estado, acumulado = NUMERO, c
            elif _es_letra(c):
                estado, acumulado = IDENT, c
            elif c == '"':
                estado, acumulado = CADENA, ""
            elif c == "/":
                estado = BARRA
            elif c == ".":
                estado = PUNTO
            elif c == "-":
                estado = GUION
            elif c in SIMBOLOS:
                emitir(SIMBOLOS[c], c)
            else:
                raise error_lexico(f"carácter inesperado {c!r}", linea, columna, fuente)
            i += 1; columna += 1

        elif estado == NUMERO:
            if c.isdigit():
                acumulado += c; i += 1; columna += 1
            elif _es_letra(c):
                raise error_lexico("un número no puede ir pegado a una letra",
                                   linea, columna, fuente)
            else:
                emitir("NUMERO", int(acumulado)); estado = INICIO

        elif estado == IDENT:
            if _es_letra(c) or c.isdigit():
                acumulado += c; i += 1; columna += 1
            else:
                if acumulado in PALABRAS_CLAVE:
                    emitir(acumulado.upper(), acumulado)
                else:
                    emitir("IDENT", acumulado)
                estado = INICIO

        elif estado == CADENA:
            if c == '"':
                emitir("CADENA", acumulado); estado = INICIO; i += 1; columna += 1
            elif c in ("\0", "\n"):
                raise error_lexico("cadena sin cerrar", inicio_linea, inicio_columna, fuente)
            else:
                acumulado += c; i += 1; columna += 1

        elif estado == BARRA:
            if c == "/":
                estado = COMENTARIO; i += 1; columna += 1
            else:
                emitir("ENTRE", "/"); estado = INICIO

        elif estado == COMENTARIO:
            if c in ("\n", "\0"):
                estado = INICIO
            else:
                i += 1; columna += 1

        elif estado == PUNTO:
            if c == ".":
                emitir("RANGO", ".."); estado = INICIO; i += 1; columna += 1
            else:
                raise error_lexico("se esperaba '..' para un rango",
                                   inicio_linea, inicio_columna, fuente)

        elif estado == GUION:
            if c == ">":
                emitir("FLECHA", "->"); estado = INICIO; i += 1; columna += 1
            else:
                emitir("MENOS", "-"); estado = INICIO

    tokens.append(Token("FIN", None, linea, columna))
    return tokens
