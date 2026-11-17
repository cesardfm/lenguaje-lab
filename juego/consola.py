"""Jugar un laberinto en la terminal."""
import sys

from compilador.generador import NOMBRES

from . import Partida

AYUDA = """
Comandos:
  N S E O      moverte (puedes encadenar: NEES, N E E S o N-E-E-S)
  pista        hacia dónde ir
  reiniciar    volver a la entrada
  ayuda        esta ayuda
  salir        terminar

Leyenda: @ tú   E entrada   S salida   ██ muro
"""


class Juego:
    def __init__(self, laberintos):
        self.laberintos = laberintos
        self.indice = 0
        self.partida = Partida(laberintos[0])

    def cargar(self, indice):
        self.indice = indice
        laberinto = self.laberintos[indice]
        self.partida = Partida(laberinto)
        print("\n" + "=" * 52)
        print(f" {indice + 1}/{len(self.laberintos)}: {laberinto.nombre}")
        print("=" * 52)
        if laberinto.descripcion:
            print(laberinto.descripcion)
        self.mostrar()

    def mostrar(self):
        p = self.partida
        print()
        print(p.laberinto.dibujar(p.posicion, color=sys.stdout.isatty()))
        print(f"\nMovimientos: {len(p.movimientos)}   (camino más corto: {p.minimo})")

    def jugar_secuencia(self, texto):
        p = self.partida
        choques = 0
        for simbolo in p.a_simbolos(texto):
            if not p.mover(simbolo):
                choques += 1
            if p.ganada():
                break
        self.mostrar()
        if choques and not p.ganada():
            print("Chocaste con un muro" + (f" ({choques} veces)" if choques > 1 else "") + ".")
        if p.ganada():
            self.victoria()

    def victoria(self):
        p = self.partida
        estrellas = "★" * p.estrellas() + "☆" * (3 - p.estrellas())
        print(f"\n¡Llegaste a la salida!  {estrellas}")
        print(f"Movimientos: {len(p.movimientos)} (camino más corto: {p.minimo})")
        print(f"Tu recorrido: {''.join(p.movimientos)}")
        if self.indice + 1 < len(self.laberintos):
            input("\nPresiona Enter para el siguiente laberinto...")
            self.cargar(self.indice + 1)
        else:
            raise SystemExit

    def procesar(self, linea):
        linea = linea.strip()
        if not linea:
            return
        p = self.partida
        if p.es_secuencia(linea):
            self.jugar_secuencia(linea)
            return
        orden = linea.lower()
        if orden == "ayuda":
            print(AYUDA)
        elif orden == "salir":
            raise SystemExit
        elif orden == "reiniciar":
            p.reiniciar()
            self.mostrar()
        elif orden == "pista":
            sugerencia = p.pista()
            if sugerencia:
                simbolo, faltan = sugerencia
                print(f"Ve al {NOMBRES[simbolo]} ({simbolo}). "
                      f"Desde aquí te faltan {faltan} movimientos.")
            else:
                print("Desde aquí no se llega a la salida. Prueba 'reiniciar'.")
        else:
            print("No entendí. Usa N, S, E, O para moverte o escribe 'ayuda'.")

    def correr(self):
        print("Muévete con N (norte), S (sur), E (este) y O (oeste).")
        print("Escribe 'ayuda' para ver los comandos.")
        self.cargar(0)
        while True:
            try:
                linea = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\n¡Hasta luego!")
                return
            try:
                self.procesar(linea)
            except SystemExit:
                print("¡Hasta luego!")
                return
