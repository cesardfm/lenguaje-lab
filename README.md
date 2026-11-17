# LAB — un lenguaje para programar laberintos

Escribes un programa, el compilador lo traduce y sale un laberinto que puedes jugar.

```
mi.lab  ──compilador──▶  laberinto  ──juego──▶  lo recorres
```

```
var margen = 1

laberinto "La casa" {
    tamaño 17 9
    repetir i en 0..2 {
        sala    (margen + i * 5, 1) 4 3
        pasillo (margen + 1 + i * 5, 4) -> (margen + 1 + i * 5, 7)
    }
    pasillo (2, 7) -> (14, 7)
    entrada (1, 1)
    salida  (14, 3)
}
```

```
#################
#E...#....#....##
#....#....#....##
#....#....#...S##
##.###.####.#####
##...........####
#################
```

## Uso

    ./lab nuevo mi.lab        crea una plantilla
    ./lab jugar mi.lab        compila y lo juegas
    ./lab compilar mi.lab     compila y dibuja
    ./lab compilar mi.lab -o mi.txt
    ./lab tokens mi.lab       análisis léxico
    ./lab arbol mi.lab        árbol de derivación

La especificación del lenguaje, con la gramática formal, está en
**[LENGUAJE.md](LENGUAJE.md)**.

## El compilador

    texto fuente (.lab)
      → análisis léxico       un AFD                    → tokens
      → análisis sintáctico   gramática LL(1)           → árbol de derivación
      → análisis semántico    tabla de símbolos         → árbol validado
      → generación de código                            → el laberinto

| Fase | Archivo | Concepto del curso |
|---|---|---|
| Léxico | `compilador/lexico.py` | **AFD** escrito como estado + bucle + transiciones; las clases de token son **expresiones regulares** |
| Sintáctico | `compilador/sintaxis.py` | **G = (Σ_N, Σ_T, P, S)** de **tipo 2**, no ambigua y LL(1); produce el **árbol de derivación** |
| Semántico | `compilador/semantica.py` | **tabla de símbolos** por ámbito |
| Generación | `compilador/generador.py` | evalúa las expresiones y excava la rejilla |

Como paso final el compilador comprueba, con una búsqueda en anchura, que exista
camino de la entrada a la salida: **un laberinto sin solución no compila**, así
que todo lo que compila se puede jugar.

Los errores llevan fase, línea, columna y un señalador:

    mal.lab:

    [semántico] línea 3, columna 11: la variable 'z' no está declarada
          sala (z, 1) 3 3
                ^

## Estructura

    lab              la herramienta
    LENGUAJE.md      la especificación del lenguaje
    ejemplos/        programas en LAB (.lab)
    compilador/      las cuatro fases
    juego/           recorrer un laberinto ya compilado
    tests/           las pruebas

## Pruebas

    python3 -m venv .venv && .venv/bin/pip install pytest
    .venv/bin/python -m pytest

Solo biblioteca estándar: compilar y ejecutar no necesita instalar nada.
