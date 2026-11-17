"""
Compilador del lenguaje LAB.

    texto fuente (.lab)
      → análisis léxico      (lexico.py, un AFD)        → tokens
      → análisis sintáctico  (sintaxis.py, LL(1))       → árbol de derivación
      → análisis semántico   (semantica.py)             → árbol validado
      → generación de código (generador.py)             → el laberinto
"""
from .errores import ErrorCompilacion
from .lexico import analizar as analizar_lexico
from .sintaxis import construir_ast
from .semantica import analizar as analizar_semantica
from .generador import generar

__all__ = ["compilar", "compilar_archivo", "ErrorCompilacion",
           "analizar_lexico", "construir_ast", "analizar_semantica", "generar"]


def compilar(fuente):
    """Texto en lenguaje LAB -> lista de laberintos."""
    arbol = construir_ast(fuente)
    analizar_semantica(arbol, fuente)
    return generar(arbol, fuente)


def compilar_archivo(ruta):
    with open(ruta, encoding="utf-8") as f:
        return compilar(f.read())
