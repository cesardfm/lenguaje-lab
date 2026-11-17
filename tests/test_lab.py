import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from compilador import ErrorCompilacion, analizar_lexico, compilar, construir_ast
from compilador.sintaxis import Binaria, Laberinto, Repetir

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = """laberinto "t" {
    tamaño 9 5
    sala (1,1) 7 3
    entrada (1,1)
    salida (7,3)
%s
}"""


def dibujo(fuente):
    return compilar(fuente)[0].texto()


def tipos(fuente):
    return [t.tipo for t in analizar_lexico(fuente)]


# ------------------------------------------------------------- léxico (AFD)

def test_el_afd_reconoce_cada_clase_de_token():
    assert tipos("var a = 1 + 2 * 3") == [
        "VAR", "IDENT", "IGUAL", "NUMERO", "MAS", "NUMERO", "POR", "NUMERO", "FIN"]
    assert tipos("(1,2)..(3,4) -> x") == [
        "PAR_IZQ", "NUMERO", "COMA", "NUMERO", "PAR_DER", "RANGO",
        "PAR_IZQ", "NUMERO", "COMA", "NUMERO", "PAR_DER", "FLECHA", "IDENT", "FIN"]


def test_las_palabras_clave_se_distinguen_de_los_identificadores():
    assert tipos("sala salario") == ["SALA", "IDENT", "FIN"]


def test_el_afd_ignora_comentarios():
    assert tipos("// esto sobra\nvar a = 1") == ["VAR", "IDENT", "IGUAL", "NUMERO", "FIN"]


def test_el_numero_se_convierte_a_entero():
    assert analizar_lexico("42")[0].valor == 42


@pytest.mark.parametrize("fuente, linea, columna", [
    ("var a = 1\nvar b = ?", 2, 9),
    ("var a = 1\n@", 2, 1),
])
def test_error_lexico_con_posicion(fuente, linea, columna):
    with pytest.raises(ErrorCompilacion) as e:
        analizar_lexico(fuente)
    assert e.value.fase == "léxico"
    assert (e.value.linea, e.value.columna) == (linea, columna)


def test_cadena_sin_cerrar():
    with pytest.raises(ErrorCompilacion, match="sin cerrar"):
        analizar_lexico('laberinto "sin fin {')


# -------------------------------------------------- sintaxis (gramática LL(1))

def test_la_gramatica_fija_la_precedencia():
    suma = construir_ast("var a = 1 + 2 * 3").declaraciones[0].valor
    assert isinstance(suma, Binaria) and suma.operador == "+"
    assert isinstance(suma.derecha, Binaria) and suma.derecha.operador == "*"


def test_los_parentesis_cambian_la_precedencia():
    producto = construir_ast("var a = (1 + 2) * 3").declaraciones[0].valor
    assert producto.operador == "*" and producto.izquierda.operador == "+"


def test_el_arbol_de_derivacion_conserva_la_estructura():
    arbol = construir_ast('laberinto "t" { tamaño 5 5 repetir i en 0..2 { sala (i,1) 1 1 } }')
    nodo = arbol.declaraciones[0]
    assert isinstance(nodo, Laberinto) and nodo.nombre == "t"
    assert isinstance(nodo.sentencias[1], Repetir)


def test_repetir_se_puede_anidar():
    """Por esto la gramática es de tipo 2 y no de tipo 3."""
    arbol = construir_ast('laberinto "t" { tamaño 9 9 '
                          'repetir i en 0..1 { repetir j en 0..1 { sala (i,j) 1 1 } } }')
    externo = arbol.declaraciones[0].sentencias[1]
    assert isinstance(externo.cuerpo[0], Repetir)


@pytest.mark.parametrize("fuente, esperado", [
    ('laberinto "t" { tamaño 5 }', "se esperaba"),
    ('laberinto "t" { tamaño 5 5', "falta '}'"),
    ('sala (1,1) 2 2', "solo valen 'var' y 'laberinto'"),
    ('laberinto "t" { pasillo (1,1) }', "al menos dos puntos"),
])
def test_errores_de_sintaxis(fuente, esperado):
    with pytest.raises(ErrorCompilacion, match=esperado):
        construir_ast(fuente)


# ------------------------------------------- semántica (tabla de símbolos)

@pytest.mark.parametrize("fuente, esperado", [
    ('laberinto "t" { tamaño 5 5 sala (z,1) 1 1 entrada (1,1) salida (3,3) }',
     "no está declarada"),
    ('laberinto "t" { tamaño 5 5 salida (3,3) }', "una 'entrada'"),
    ('laberinto "t" { tamaño 5 5 entrada (1,1) }', "una 'salida'"),
    ('laberinto "t" { entrada (1,1) salida (3,3) }', "un 'tamaño'"),
    ('laberinto "t" { tamaño 5 5 repetir i en 0..1 { entrada (1,1) } salida (3,3) }',
     "dentro de un 'repetir'"),
])
def test_reglas_semanticas(fuente, esperado):
    with pytest.raises(ErrorCompilacion, match=esperado):
        compilar(fuente)


def test_los_nombres_no_se_repiten():
    fuente = ('laberinto "t" { tamaño 5 5 entrada (1,1) salida (3,3) }\n'
              'laberinto "t" { tamaño 5 5 entrada (1,1) salida (3,3) }')
    with pytest.raises(ErrorCompilacion, match="ya hay un laberinto"):
        compilar(fuente)


def test_la_variable_del_bucle_no_escapa():
    fuente = ('laberinto "t" { tamaño 9 5 repetir i en 0..1 { sala (1,1) 1 1 } '
              'sala (i,1) 1 1 entrada (1,1) salida (3,3) }')
    with pytest.raises(ErrorCompilacion, match="'i' no está declarada"):
        compilar(fuente)


# ------------------------------------------------------------- generación

def test_salas_y_pasillos_excavan():
    assert dibujo(BASE % "") == "\n".join([
        "#########",
        "#E......#",
        "#.......#",
        "#......S#",
        "#########"])


def test_el_bucle_despliega_la_geometria():
    fuente = ('laberinto "t" { tamaño 13 5 repetir i en 0..2 { sala (1 + i * 4, 1) 3 1 } '
              'pasillo (1,1) -> (11,1) entrada (1,1) salida (11,1) }')
    assert dibujo(fuente).split("\n")[1] == "#E.........S#"


def test_las_marcas_se_colocan_despues_de_excavar():
    fuente = 'laberinto "t" { tamaño 7 5 entrada (1,1) salida (5,1) sala (1,1) 5 1 }'
    assert dibujo(fuente).split("\n")[1] == "#E...S#"


def test_la_aritmetica_se_evalua_en_compilacion():
    fuente = ('var a = 2\nlaberinto "t" { tamaño 9 5 sala (a - 1, 1) 7 3 '
              'entrada (1,1) salida (7,3) }')
    assert dibujo(fuente).split("\n")[1] == "#E......#"


@pytest.mark.parametrize("sentencia, esperado", [
    ("sala (9,1) 1 1", "fuera del área útil"),
    ("sala (1,1) 20 1", "se sale del laberinto"),
    ("pasillo (1,1) -> (3,3)", "diagonal"),
])
def test_errores_de_generacion(sentencia, esperado):
    with pytest.raises(ErrorCompilacion, match=esperado):
        compilar(BASE % sentencia)


def test_una_marca_sobre_un_muro():
    fuente = 'laberinto "t" { tamaño 9 5 sala (1,1) 2 1 entrada (1,1) salida (7,3) }'
    with pytest.raises(ErrorCompilacion, match="cae sobre un muro"):
        compilar(fuente)


def test_division_entre_cero():
    with pytest.raises(ErrorCompilacion, match="división entre cero"):
        compilar('laberinto "t" { tamaño 7 5 sala (1, 4 / 0) 1 1 '
                 'entrada (1,1) salida (3,3) }')


def test_tamaño_minimo():
    with pytest.raises(ErrorCompilacion, match="tamaño mínimo"):
        compilar('laberinto "t" { tamaño 2 2 entrada (1,1) salida (1,1) }')


# ---------------------------------------------------------------- ejemplos

def test_los_ejemplos_compilan():
    carpeta = os.path.join(RAIZ, "ejemplos")
    archivos = [f for f in os.listdir(carpeta) if f.endswith(".lab")]
    assert archivos, "no hay ejemplos"
    for nombre in archivos:
        with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
            laberintos = compilar(f.read())
        assert laberintos, nombre
        for laberinto in laberintos:
            assert "E" in laberinto.texto() and "S" in laberinto.texto()


# ---------------------------------------------- el laberinto se puede jugar

from juego import Partida  # noqa: E402


def test_el_compilador_rechaza_un_laberinto_sin_solucion():
    """Si no hay camino de la entrada a la salida, no se podría jugar."""
    fuente = ('laberinto "t" { tamaño 11 5 sala (1,1) 2 1 sala (8,3) 2 1 '
              'entrada (1,1) salida (9,3) }')
    with pytest.raises(ErrorCompilacion, match="no tiene solución"):
        compilar(fuente)


def test_el_camino_mas_corto_lleva_de_la_entrada_a_la_salida():
    laberinto = compilar(BASE % "")[0]
    ruta = laberinto.camino()
    assert ruta
    partida = Partida(laberinto)
    for simbolo in ruta:
        assert partida.mover(simbolo), "la ruta atraviesa un muro"
    assert partida.ganada()


def test_chocar_con_un_muro_no_mueve():
    partida = Partida(compilar(BASE % "")[0])
    assert partida.posicion == (1, 1)
    assert partida.mover("N") is False          # arriba hay muro
    assert partida.posicion == (1, 1)
    assert partida.mover("E") is True
    assert partida.posicion == (2, 1)


def test_las_pistas_llevan_al_final():
    partida = Partida(compilar(BASE % "")[0])
    pasos = 0
    while not partida.ganada() and pasos < 200:
        simbolo, faltan = partida.pista()
        partida.mover(simbolo)
        pasos += 1
    assert partida.ganada()
    assert pasos == partida.minimo


def test_reiniciar_vuelve_a_la_entrada():
    partida = Partida(compilar(BASE % "")[0])
    partida.mover("E")
    partida.reiniciar()
    assert partida.posicion == partida.laberinto.entrada
    assert partida.movimientos == []


def test_la_secuencia_de_movimientos_se_valida():
    assert Partida.es_secuencia("NEES")
    assert Partida.es_secuencia("N E E S")
    assert Partida.es_secuencia("N-E-E-S")
    assert not Partida.es_secuencia("NXES")
    assert Partida.a_simbolos("n-e e s") == ["N", "E", "E", "S"]


def test_la_plantilla_de_lab_nuevo_es_jugable(tmp_path):
    """Lo que crea 'lab nuevo' tiene que poderse jugar tal cual."""
    import importlib.util
    ruta_lab = os.path.join(RAIZ, "lab")
    spec = importlib.util.spec_from_loader("herramienta",
                                           importlib.machinery.SourceFileLoader("herramienta", ruta_lab))
    herramienta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(herramienta)

    destino = tmp_path / "nuevo.lab"
    destino.write_text(herramienta.PLANTILLA.format(nombre="nuevo.lab"), encoding="utf-8")
    laberinto = compilar(destino.read_text(encoding="utf-8"))[0]

    partida = Partida(laberinto)
    for simbolo in laberinto.camino():
        assert partida.mover(simbolo)
    assert partida.ganada()


def test_todos_los_ejemplos_son_jugables():
    carpeta = os.path.join(RAIZ, "ejemplos")
    for nombre in os.listdir(carpeta):
        if not nombre.endswith(".lab"):
            continue
        with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
            for laberinto in compilar(f.read()):
                partida = Partida(laberinto)
                for simbolo in laberinto.camino():
                    assert partida.mover(simbolo), nombre
                assert partida.ganada(), nombre


# ------------------------------------------- los ejemplos de error fallan

ERRORES = {"lexico.lab": "léxico", "sintactico.lab": "sintáctico",
           "semantico.lab": "semántico", "sin-solucion.lab": "semántico"}


@pytest.mark.parametrize("nombre, fase", sorted(ERRORES.items()))
def test_los_ejemplos_de_error_fallan_en_su_fase(nombre, fase):
    """Cada archivo de ejemplos/errores/ demuestra una clase de error."""
    ruta = os.path.join(RAIZ, "ejemplos", "errores", nombre)
    with open(ruta, encoding="utf-8") as f:
        with pytest.raises(ErrorCompilacion) as e:
            compilar(f.read())
    assert e.value.fase == fase


def test_estan_todos_los_ejemplos_de_error():
    carpeta = os.path.join(RAIZ, "ejemplos", "errores")
    assert sorted(os.listdir(carpeta)) == sorted(ERRORES)
