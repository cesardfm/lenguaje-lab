"""
Análisis semántico: lo que la gramática no puede comprobar.

La gramática acepta `sala (z,1) 3 3` porque *sintácticamente* está bien escrito,
aunque `z` no exista. Eso se detecta aquí, con dos trabajos:

  1. Resolución de nombres mediante una **tabla de símbolos por ámbito**. Cada
     laberinto y cada `repetir` abren uno nuevo, encadenado al de fuera, de modo
     que la variable de un bucle no se escapa de él.
  2. Reglas del lenguaje: todo laberinto necesita un `tamaño`, exactamente una
     `entrada` y al menos una `salida`, y los nombres no se repiten.
"""
from . import sintaxis as S
from .errores import error_semantico


class Ambito:
    """Tabla de símbolos encadenada."""

    def __init__(self, padre=None):
        self.padre = padre
        self.nombres = set()

    def declarar(self, nombre):
        self.nombres.add(nombre)

    def existe(self, nombre):
        if nombre in self.nombres:
            return True
        return self.padre.existe(nombre) if self.padre else False


class Analizador:
    def __init__(self, fuente):
        self.fuente = fuente
        self.nombres = {}

    def error(self, nodo, mensaje):
        return error_semantico(mensaje, nodo.linea, nodo.columna, self.fuente)

    def programa(self, arbol):
        global_ = Ambito()
        for declaracion in arbol.declaraciones:
            if isinstance(declaracion, S.VarDecl):
                self.expresion(declaracion.valor, global_)
                global_.declarar(declaracion.nombre)
            else:
                self.laberinto(declaracion, global_)
        return arbol

    def laberinto(self, nodo, padre):
        if nodo.nombre in self.nombres:
            raise self.error(nodo, f"ya hay un laberinto llamado {nodo.nombre!r} "
                                   f"(línea {self.nombres[nodo.nombre]})")
        self.nombres[nodo.nombre] = nodo.linea

        conteo = {"tamaño": 0, "entrada": 0, "salida": 0, "texto": 0}
        self.sentencias(nodo.sentencias, Ambito(padre), conteo, en_bucle=False)

        if conteo["tamaño"] != 1:
            raise self.error(nodo, f"el laberinto necesita exactamente un 'tamaño' "
                                   f"(tiene {conteo['tamaño']})")
        if conteo["entrada"] != 1:
            raise self.error(nodo, f"el laberinto necesita exactamente una 'entrada' "
                                   f"(tiene {conteo['entrada']})")
        if conteo["salida"] < 1:
            raise self.error(nodo, "el laberinto necesita al menos una 'salida'")
        if conteo["texto"] > 1:
            raise self.error(nodo, "solo puede haber un 'texto' por laberinto")

    def sentencias(self, lista, ambito, conteo, en_bucle):
        for sentencia in lista:
            self.sentencia(sentencia, ambito, conteo, en_bucle)

    def sentencia(self, nodo, ambito, conteo, en_bucle):
        if isinstance(nodo, S.VarDecl):
            self.expresion(nodo.valor, ambito)
            ambito.declarar(nodo.nombre)
            return
        if isinstance(nodo, S.Repetir):
            self.expresion(nodo.desde, ambito)
            self.expresion(nodo.hasta, ambito)
            interno = Ambito(ambito)
            interno.declarar(nodo.variable)
            self.sentencias(nodo.cuerpo, interno, conteo, en_bucle=True)
            return
        if isinstance(nodo, S.Texto):
            conteo["texto"] += 1
            return
        if isinstance(nodo, (S.Tamaño, S.Entrada, S.Salida)):
            clave = {S.Tamaño: "tamaño", S.Entrada: "entrada",
                     S.Salida: "salida"}[type(nodo)]
            if en_bucle:
                raise self.error(nodo, f"'{clave}' no puede ir dentro de un 'repetir': "
                                       "se aplicaría varias veces")
            conteo[clave] += 1
            if isinstance(nodo, S.Tamaño):
                self.expresion(nodo.ancho, ambito)
                self.expresion(nodo.alto, ambito)
            else:
                self.punto(nodo.punto, ambito)
            return
        if isinstance(nodo, S.Sala):
            self.punto(nodo.esquina, ambito)
            self.expresion(nodo.ancho, ambito)
            self.expresion(nodo.alto, ambito)
            return
        if isinstance(nodo, S.Pasillo):
            for punto in nodo.puntos:
                self.punto(punto, ambito)
            return
        raise self.error(nodo, f"instrucción no reconocida: {type(nodo).__name__}")

    def punto(self, nodo, ambito):
        self.expresion(nodo.x, ambito)
        self.expresion(nodo.y, ambito)

    def expresion(self, nodo, ambito):
        if isinstance(nodo, S.Num):
            return
        if isinstance(nodo, S.Var):
            if not ambito.existe(nodo.nombre):
                raise self.error(nodo, f"la variable {nodo.nombre!r} no está declarada")
            return
        if isinstance(nodo, S.Binaria):
            self.expresion(nodo.izquierda, ambito)
            self.expresion(nodo.derecha, ambito)
            return
        if isinstance(nodo, S.Negacion):
            self.expresion(nodo.valor, ambito)
            return
        raise self.error(nodo, "expresión no reconocida")


def analizar(arbol, fuente):
    return Analizador(fuente).programa(arbol)
