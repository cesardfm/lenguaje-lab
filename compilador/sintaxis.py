"""
Analizador sintáctico: tokens -> árbol de derivación (AST).

La gramática del lenguaje LAB, G = (Σ_N, Σ_T, P, S), con S = programa.
Es de **tipo 2** (independiente del contexto) en la jerarquía de Chomsky: no
puede ser tipo 3 porque `repetir` se anida, y las llaves balanceadas a
profundidad arbitraria no las reconoce ningún autómata finito.

Producciones P:

    programa    → declaracion* FIN
    declaracion → varDecl | laberinto

    varDecl     → "var" IDENT "=" expresion
    laberinto   → "laberinto" CADENA "{" sentencia* "}"

    sentencia   → texto | tamaño | sala | pasillo | entrada | salida
                | repetir | varDecl
    texto       → "texto" CADENA+
    tamaño      → "tamaño" expresion expresion
    sala        → "sala" punto expresion expresion
    pasillo     → "pasillo" punto ("->" punto)+
    entrada     → "entrada" punto
    salida      → "salida" punto
    repetir     → "repetir" IDENT "en" expresion ".." expresion
                      "{" sentencia* "}"

    punto       → "(" expresion "," expresion ")"

    expresion   → termino (("+" | "-") termino)*
    termino     → factor (("*" | "/") factor)*
    factor      → NUMERO | IDENT | "(" expresion ")" | "-" factor

La escalera expresion → termino → factor es lo que fija la precedencia y hace
la gramática **no ambigua**: `1 + 2 * 3` tiene un solo árbol de derivación.
Con un token de anticipación basta para decidir qué producción aplicar, así que
es LL(1) y se puede analizar por descenso recursivo: cada no terminal de arriba
es un método de esta clase.
"""
from .errores import error_sintactico
from .lexico import analizar


class Nodo:
    """Nodo del AST. Guarda su posición para señalar errores semánticos."""

    def __init__(self, linea=0, columna=0):
        self.linea = linea
        self.columna = columna


def _nodo(nombre, *campos):
    def __init__(self, *valores, linea=0, columna=0):
        Nodo.__init__(self, linea, columna)
        for campo, valor in zip(campos, valores):
            setattr(self, campo, valor)

    def __repr__(self):
        datos = ", ".join(f"{c}={getattr(self, c)!r}" for c in campos)
        return f"{nombre}({datos})"

    return type(nombre, (Nodo,), {"__init__": __init__, "__repr__": __repr__,
                                  "_campos": campos})


Programa  = _nodo("Programa", "declaraciones")
VarDecl   = _nodo("VarDecl", "nombre", "valor")
Laberinto = _nodo("Laberinto", "nombre", "sentencias")
Texto     = _nodo("Texto", "cadena")
Tamaño    = _nodo("Tamaño", "ancho", "alto")
Sala      = _nodo("Sala", "esquina", "ancho", "alto")
Pasillo   = _nodo("Pasillo", "puntos")
Entrada   = _nodo("Entrada", "punto")
Salida    = _nodo("Salida", "punto")
Repetir   = _nodo("Repetir", "variable", "desde", "hasta", "cuerpo")
Punto     = _nodo("Punto", "x", "y")
Num       = _nodo("Num", "valor")
Var       = _nodo("Var", "nombre")
Binaria   = _nodo("Binaria", "operador", "izquierda", "derecha")
Negacion  = _nodo("Negacion", "valor")


class Parser:
    def __init__(self, tokens, fuente):
        self.tokens = tokens
        self.fuente = fuente
        self.i = 0

    # -- utilidades -------------------------------------------------------
    @property
    def actual(self):
        return self.tokens[self.i]

    def mira(self, *tipos):
        return self.actual.tipo in tipos

    def avanza(self):
        token = self.actual
        self.i += 1
        return token

    def acepta(self, tipo):
        return self.avanza() if self.mira(tipo) else None

    def espera(self, tipo, descripcion):
        if self.mira(tipo):
            return self.avanza()
        hallado = self.actual.valor if self.actual.valor is not None else "fin de archivo"
        raise error_sintactico(f"se esperaba {descripcion} y se encontró {hallado!r}",
                               self.actual.linea, self.actual.columna, self.fuente)

    # -- producciones -----------------------------------------------------
    def programa(self):
        declaraciones = []
        while not self.mira("FIN"):
            declaraciones.append(self.declaracion())
        return Programa(declaraciones)

    def declaracion(self):
        if self.mira("VAR"):
            return self.var_decl()
        if self.mira("LABERINTO"):
            return self.laberinto()
        raise error_sintactico("en el nivel superior solo valen 'var' y 'laberinto'",
                               self.actual.linea, self.actual.columna, self.fuente)

    def var_decl(self):
        inicio = self.espera("VAR", "'var'")
        nombre = self.espera("IDENT", "un nombre de variable")
        self.espera("IGUAL", "'='")
        return VarDecl(nombre.valor, self.expresion(),
                       linea=inicio.linea, columna=inicio.columna)

    def laberinto(self):
        inicio = self.espera("LABERINTO", "'laberinto'")
        nombre = self.espera("CADENA", "el nombre entre comillas")
        self.espera("LLAVE_IZQ", "'{'")
        sentencias = []
        while not self.mira("LLAVE_DER"):
            if self.mira("FIN"):
                raise error_sintactico("falta '}' para cerrar el laberinto",
                                       inicio.linea, inicio.columna, self.fuente)
            sentencias.append(self.sentencia())
        self.espera("LLAVE_DER", "'}'")
        return Laberinto(nombre.valor, sentencias,
                         linea=inicio.linea, columna=inicio.columna)

    def sentencia(self):
        t = self.actual
        if t.tipo == "TEXTO":
            self.avanza()
            partes = [self.espera("CADENA", "el texto entre comillas").valor]
            while self.mira("CADENA"):
                partes.append(self.avanza().valor)
            return Texto("\n".join(partes), linea=t.linea, columna=t.columna)
        if t.tipo == "TAMAÑO":
            self.avanza()
            return Tamaño(self.expresion(), self.expresion(),
                          linea=t.linea, columna=t.columna)
        if t.tipo == "SALA":
            self.avanza()
            return Sala(self.punto(), self.expresion(), self.expresion(),
                        linea=t.linea, columna=t.columna)
        if t.tipo == "PASILLO":
            self.avanza()
            puntos = [self.punto()]
            while self.acepta("FLECHA"):
                puntos.append(self.punto())
            if len(puntos) < 2:
                raise error_sintactico("un pasillo necesita al menos dos puntos: (a) -> (b)",
                                       t.linea, t.columna, self.fuente)
            return Pasillo(puntos, linea=t.linea, columna=t.columna)
        if t.tipo == "ENTRADA":
            self.avanza()
            return Entrada(self.punto(), linea=t.linea, columna=t.columna)
        if t.tipo == "SALIDA":
            self.avanza()
            return Salida(self.punto(), linea=t.linea, columna=t.columna)
        if t.tipo == "REPETIR":
            return self.repetir()
        if t.tipo == "VAR":
            return self.var_decl()
        raise error_sintactico(f"instrucción desconocida {t.valor!r}",
                               t.linea, t.columna, self.fuente)

    def repetir(self):
        inicio = self.espera("REPETIR", "'repetir'")
        variable = self.espera("IDENT", "el nombre de la variable del bucle")
        self.espera("EN", "'en'")
        desde = self.expresion()
        self.espera("RANGO", "'..'")
        hasta = self.expresion()
        self.espera("LLAVE_IZQ", "'{'")
        cuerpo = []
        while not self.mira("LLAVE_DER"):
            if self.mira("FIN"):
                raise error_sintactico("falta '}' para cerrar el repetir",
                                       inicio.linea, inicio.columna, self.fuente)
            cuerpo.append(self.sentencia())
        self.espera("LLAVE_DER", "'}'")
        return Repetir(variable.valor, desde, hasta, cuerpo,
                       linea=inicio.linea, columna=inicio.columna)

    def punto(self):
        inicio = self.espera("PAR_IZQ", "'(' para abrir una coordenada")
        x = self.expresion()
        self.espera("COMA", "',' entre las dos coordenadas")
        y = self.expresion()
        self.espera("PAR_DER", "')'")
        return Punto(x, y, linea=inicio.linea, columna=inicio.columna)

    def expresion(self):
        nodo = self.termino()
        while self.mira("MAS", "MENOS"):
            op = self.avanza()
            nodo = Binaria(op.valor, nodo, self.termino(),
                           linea=op.linea, columna=op.columna)
        return nodo

    def termino(self):
        nodo = self.factor()
        while self.mira("POR", "ENTRE"):
            op = self.avanza()
            nodo = Binaria(op.valor, nodo, self.factor(),
                           linea=op.linea, columna=op.columna)
        return nodo

    def factor(self):
        t = self.actual
        if t.tipo == "NUMERO":
            self.avanza()
            return Num(t.valor, linea=t.linea, columna=t.columna)
        if t.tipo == "IDENT":
            self.avanza()
            return Var(t.valor, linea=t.linea, columna=t.columna)
        if t.tipo == "MENOS":
            self.avanza()
            return Negacion(self.factor(), linea=t.linea, columna=t.columna)
        if t.tipo == "PAR_IZQ":
            self.avanza()
            nodo = self.expresion()
            self.espera("PAR_DER", "')'")
            return nodo
        raise error_sintactico("se esperaba un número, una variable o '('",
                               t.linea, t.columna, self.fuente)


def construir_ast(fuente):
    return Parser(analizar(fuente), fuente).programa()
