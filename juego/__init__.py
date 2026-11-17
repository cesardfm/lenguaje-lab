"""
El juego: recorrer un laberinto ya compilado.

No sabe nada del lenguaje ni del compilador. Recibe un laberinto y lo deja
jugar.
"""
import re

from compilador.generador import MOVIMIENTOS, NOMBRES, SALIDA

# Una secuencia de movimientos: letras N, S, E, O separadas opcionalmente por
# espacios, comas o guiones. Ej: "NEES", "N E E S", "N-E-E-S".
PATRON = re.compile(r"^[NSEO](?:[\s,\-]*[NSEO])*$", re.IGNORECASE)


class Partida:
    def __init__(self, laberinto):
        self.laberinto = laberinto
        self.posicion = laberinto.entrada
        self.movimientos = []
        self.minimo = len(laberinto.camino() or [])

    @staticmethod
    def es_secuencia(texto):
        return bool(PATRON.match(texto.strip()))

    @staticmethod
    def a_simbolos(texto):
        return [c for c in texto.upper() if c in MOVIMIENTOS]

    def mover(self, simbolo):
        """Devuelve True si se movió, False si chocó con un muro."""
        dx, dy = MOVIMIENTOS[simbolo]
        destino = (self.posicion[0] + dx, self.posicion[1] + dy)
        if not self.laberinto.es_pasillo(*destino):
            return False
        self.posicion = destino
        self.movimientos.append(simbolo)
        return True

    def ganada(self):
        return self.posicion == self.laberinto.salida

    def reiniciar(self):
        self.posicion = self.laberinto.entrada
        self.movimientos = []

    def pista(self):
        """El siguiente movimiento por el camino más corto, y lo que falta."""
        ruta = self.laberinto.camino(self.posicion, self.laberinto.salida)
        if not ruta:
            return None
        return ruta[0], len(ruta)

    def estrellas(self):
        hechos = len(self.movimientos)
        if hechos <= self.minimo:
            return 3
        if hechos <= self.minimo * 1.5:
            return 2
        return 1
