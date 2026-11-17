"""
Generación de código: recorre el AST y produce el laberinto dibujado.

El «código objeto» de este compilador es la rejilla de caracteres: aquí se
evalúan las expresiones, se despliegan los bucles y se excava la geometría.

Se genera en dos pasadas para que el orden de las instrucciones no importe:
primero se excava (`sala`, `pasillo`) y después se colocan las marcas
(`entrada`, `salida`). Así se puede escribir la entrada antes que el pasillo
que la contiene.
"""
from collections import deque

from . import sintaxis as S
from .errores import error_semantico

MURO, PASILLO, ENTRADA, SALIDA = "#", ".", "E", "S"

# Los movimientos del jugador y lo que suman a (x, y).
MOVIMIENTOS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0)}
NOMBRES = {"N": "norte", "S": "sur", "E": "este", "O": "oeste"}


class Entorno:
    """Valores de las variables, encadenados por ámbito."""

    def __init__(self, padre=None):
        self.padre = padre
        self.valores = {}

    def define(self, nombre, valor):
        self.valores[nombre] = valor

    def lee(self, nombre):
        if nombre in self.valores:
            return self.valores[nombre]
        return self.padre.lee(nombre) if self.padre else None


class Rejilla:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto
        self.celdas = [[MURO] * ancho for _ in range(alto)]

    def dentro(self, x, y):
        return 1 <= x <= self.ancho - 2 and 1 <= y <= self.alto - 2

    def excava(self, x, y):
        self.celdas[y][x] = PASILLO

    def pon(self, x, y, caracter):
        self.celdas[y][x] = caracter

    def es_pasillo(self, x, y):
        return self.celdas[y][x] != MURO

    def texto(self):
        return "\n".join("".join(fila) for fila in self.celdas)


class Laberinto:
    """El resultado de compilar: un laberinto dibujado."""

    def __init__(self, nombre, rejilla, descripcion=""):
        self.nombre = nombre
        self.descripcion = descripcion
        self.ancho = rejilla.ancho
        self.alto = rejilla.alto
        self.filas = [fila[:] for fila in rejilla.celdas]
        self.entrada = self._buscar(ENTRADA)
        self.salida = self._buscar(SALIDA)

    def _buscar(self, marca):
        for y, fila in enumerate(self.filas):
            for x, celda in enumerate(fila):
                if celda == marca:
                    return (x, y)
        return None

    def es_pasillo(self, x, y):
        if 0 <= y < self.alto and 0 <= x < self.ancho:
            return self.filas[y][x] != MURO
        return False

    def camino(self, desde=None, hasta=None):
        """Camino más corto entre dos casillas, como lista de movimientos.

        Búsqueda en anchura sobre las casillas transitables. Devuelve None si
        no hay camino. La usa el compilador para comprobar que el laberinto
        tenga solución, y el juego para dar pistas.
        """
        desde = desde or self.entrada
        hasta = hasta or self.salida
        if desde is None or hasta is None:
            return None
        if desde == hasta:
            return []
        padre = {desde: None}
        cola = deque([desde])
        while cola:
            actual = cola.popleft()
            for simbolo, (dx, dy) in MOVIMIENTOS.items():
                siguiente = (actual[0] + dx, actual[1] + dy)
                if siguiente in padre or not self.es_pasillo(*siguiente):
                    continue
                padre[siguiente] = (actual, simbolo)
                if siguiente == hasta:
                    ruta, nodo = [], siguiente
                    while padre[nodo] is not None:
                        anterior, simbolo = padre[nodo]
                        ruta.append(simbolo)
                        nodo = anterior
                    return list(reversed(ruta))
                cola.append(siguiente)
        return None

    def texto(self):
        return "\n".join("".join(fila) for fila in self.filas)

    def dibujar(self, jugador=None, color=True):
        """Versión bonita para la terminal: cada casilla ocupa dos columnas."""
        def pintar(codigo, texto):
            return f"\033[{codigo}m{texto}\033[0m" if color else texto

        estilos = {MURO: ("38;5;238", "██"), PASILLO: ("38;5;236", "· "),
                   ENTRADA: ("38;5;244", "E "), SALIDA: ("1;32", "S ")}
        lineas = []
        for y, fila in enumerate(self.filas):
            linea = "  "
            for x, celda in enumerate(fila):
                if jugador == (x, y):
                    linea += pintar("1;33", "@ ")
                else:
                    codigo, dibujo = estilos.get(celda, ("0", celda + " "))
                    linea += pintar(codigo, dibujo)
            lineas.append(linea)
        return "\n".join(lineas)


class Generador:
    def __init__(self, fuente):
        self.fuente = fuente

    def error(self, nodo, mensaje):
        return error_semantico(mensaje, nodo.linea, nodo.columna, self.fuente)

    # -- expresiones ------------------------------------------------------
    def evaluar(self, nodo, entorno):
        if isinstance(nodo, S.Num):
            return nodo.valor
        if isinstance(nodo, S.Var):
            return entorno.lee(nodo.nombre)
        if isinstance(nodo, S.Negacion):
            return -self.evaluar(nodo.valor, entorno)
        izquierda = self.evaluar(nodo.izquierda, entorno)
        derecha = self.evaluar(nodo.derecha, entorno)
        if nodo.operador == "+":
            return izquierda + derecha
        if nodo.operador == "-":
            return izquierda - derecha
        if nodo.operador == "*":
            return izquierda * derecha
        if derecha == 0:
            raise self.error(nodo, "división entre cero")
        return izquierda // derecha

    def coordenada(self, nodo, entorno, rejilla, que):
        x = self.evaluar(nodo.x, entorno)
        y = self.evaluar(nodo.y, entorno)
        if not rejilla.dentro(x, y):
            raise self.error(nodo, f"{que} en ({x}, {y}) queda fuera del área útil "
                                   f"(x entre 1 y {rejilla.ancho - 2}, "
                                   f"y entre 1 y {rejilla.alto - 2})")
        return x, y

    # -- programa ---------------------------------------------------------
    def programa(self, arbol):
        entorno = Entorno()
        laberintos = []
        for declaracion in arbol.declaraciones:
            if isinstance(declaracion, S.VarDecl):
                entorno.define(declaracion.nombre, self.evaluar(declaracion.valor, entorno))
            else:
                laberintos.append(self.laberinto(declaracion, entorno))
        return laberintos

    def laberinto(self, nodo, padre):
        entorno = Entorno(padre)
        descripcion = next((s.cadena for s in nodo.sentencias
                            if isinstance(s, S.Texto)), "")
        tamaño = next(s for s in nodo.sentencias if isinstance(s, S.Tamaño))
        ancho = self.evaluar(tamaño.ancho, entorno)
        alto = self.evaluar(tamaño.alto, entorno)
        if ancho < 3 or alto < 3:
            raise self.error(tamaño, f"el tamaño mínimo es 3 x 3 "
                                     f"(se pidió {ancho} x {alto})")

        rejilla = Rejilla(ancho, alto)
        marcas = []
        self.ejecutar(nodo.sentencias, entorno, rejilla, marcas)

        ocupadas = {}
        for tipo, (x, y), origen in marcas:
            nombre = "la entrada" if tipo == ENTRADA else "la salida"
            if not rejilla.es_pasillo(x, y):
                raise self.error(origen, f"{nombre} en ({x}, {y}) cae sobre un muro: "
                                         "abre ahí una 'sala' o un 'pasillo'")
            if (x, y) in ocupadas:
                raise self.error(origen, f"{nombre} en ({x}, {y}) cae encima de "
                                         f"{ocupadas[(x, y)]}")
            ocupadas[(x, y)] = nombre
            rejilla.pon(x, y, tipo)

        laberinto = Laberinto(nodo.nombre, rejilla, descripcion)
        if laberinto.camino() is None:
            raise self.error(nodo, f"el laberinto {nodo.nombre!r} no tiene solución: "
                                   "no hay camino de la entrada a la salida")
        return laberinto

    def ejecutar(self, sentencias, entorno, rejilla, marcas):
        for sentencia in sentencias:
            self.sentencia(sentencia, entorno, rejilla, marcas)

    def sentencia(self, nodo, entorno, rejilla, marcas):
        if isinstance(nodo, (S.Texto, S.Tamaño)):
            return
        if isinstance(nodo, S.VarDecl):
            entorno.define(nodo.nombre, self.evaluar(nodo.valor, entorno))
            return
        if isinstance(nodo, S.Repetir):
            desde = self.evaluar(nodo.desde, entorno)
            hasta = self.evaluar(nodo.hasta, entorno)
            if hasta - desde > 10000:
                raise self.error(nodo, "el bucle repetiría más de 10 000 veces")
            for valor in range(desde, hasta + 1):
                interno = Entorno(entorno)
                interno.define(nodo.variable, valor)
                self.ejecutar(nodo.cuerpo, interno, rejilla, marcas)
            return
        if isinstance(nodo, S.Sala):
            x, y = self.coordenada(nodo.esquina, entorno, rejilla, "la sala")
            ancho = self.evaluar(nodo.ancho, entorno)
            alto = self.evaluar(nodo.alto, entorno)
            if ancho < 1 or alto < 1:
                raise self.error(nodo, f"una sala necesita ancho y alto positivos "
                                       f"(se pidió {ancho} x {alto})")
            if not rejilla.dentro(x + ancho - 1, y + alto - 1):
                raise self.error(nodo, f"la sala de {ancho} x {alto} desde ({x}, {y}) "
                                       "se sale del laberinto")
            for fila in range(y, y + alto):
                for columna in range(x, x + ancho):
                    rejilla.excava(columna, fila)
            return
        if isinstance(nodo, S.Pasillo):
            puntos = [self.coordenada(p, entorno, rejilla, "el pasillo")
                      for p in nodo.puntos]
            for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
                if x1 != x2 and y1 != y2:
                    raise self.error(nodo, f"los pasillos van en línea recta, y de "
                                           f"({x1}, {y1}) a ({x2}, {y2}) hay diagonal")
                for columna in range(min(x1, x2), max(x1, x2) + 1):
                    for fila in range(min(y1, y2), max(y1, y2) + 1):
                        rejilla.excava(columna, fila)
            return
        if isinstance(nodo, S.Entrada):
            marcas.append((ENTRADA, self.coordenada(nodo.punto, entorno, rejilla,
                                                    "la entrada"), nodo))
            return
        if isinstance(nodo, S.Salida):
            marcas.append((SALIDA, self.coordenada(nodo.punto, entorno, rejilla,
                                                   "la salida"), nodo))
            return
        raise self.error(nodo, f"no sé generar {type(nodo).__name__}")


def generar(arbol, fuente):
    return Generador(fuente).programa(arbol)
