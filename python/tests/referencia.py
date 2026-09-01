# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>

# This file is part of Zonda.

# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

"""Matriz de casos de referencia y volcado de sus resultados.

Los archivos de ``tests/referencia/`` guardan todos los números que el programa
produce hoy para esta matriz. No afirman que los valores sean correctos según el
Reglamento: afirman que no cambiaron. Sirven para que cualquier movimiento
inadvertido al tocar el núcleo falle en los tests y aparezca en el diff de git.

Los casos no cruzan todo con todo: cada rama del cálculo -tipo de cubierta,
ángulo, alero, parapeto, figura de componentes, cerramiento, categoría,
exposición, ráfaga y topografía- aparece al menos una vez, en un archivo que se
pueda abrir y leer.

Para regenerarlos después de un cambio deliberado::

    uv run python -m tests.referencia

y revisar el diff antes de commitear.
"""

from collections.abc import Callable, Iterator
from enum import Enum
from pathlib import Path

from zonda import enums
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio

DIRECTORIO = Path(__file__).parent / "referencia"

# Un edificio de referencia sobre el que se hacen variar los parámetros que no
# dependen de la geometría.
BASE_EDIFICIO = {
    "ancho": 20,
    "longitud": 30,
    "elevacion": 0,
    "altura_alero": 6,
    "altura_cumbrera": 12,
    "tipo_cubierta": enums.TipoCubierta.DOS_AGUAS,
    "cerramiento": enums.Cerramiento.CERRADO,
    "categoria": enums.CategoriaEstructura.II,
    "velocidad": 45,
    "factor_g_simplificado": True,
    "categoria_exp": enums.CategoriaExposicion.B,
    "considerar_topografia": False,
    "alero": 1,
    "componentes_paredes": {"Viga": 10.0},
    "componentes_cubierta": {"Correa": 5.0},
}

# Alturas ralas para los edificios de gran altura: entran por la misma rama del
# Reglamento (Figura 8) sin generar una fila por metro.
ALTURAS_RALAS = (6.0, 12.0, 18.0)


def _edificio(**cambios) -> dict:
    return {**BASE_EDIFICIO, **cambios}


CASOS_EDIFICIO = (
    # --- Geometrías ---
    (
        "plana",
        _edificio(tipo_cubierta=enums.TipoCubierta.PLANA, altura_cumbrera=6, alero=0),
    ),
    (
        "plana-alero",
        _edificio(tipo_cubierta=enums.TipoCubierta.PLANA, altura_cumbrera=6),
    ),
    ("dos-aguas-angulo-menor", _edificio(altura_cumbrera=7, alero=0)),
    ("dos-aguas-angulo-menor-alero", _edificio(altura_cumbrera=7)),
    ("dos-aguas-angulo-mayor", _edificio(alero=0)),
    ("dos-aguas-angulo-mayor-alero", _edificio()),
    (
        # 4.3°: entra por la Figura 7A, que sólo cubre un agua entre 3° y 10°.
        "un-agua-angulo-menor",
        _edificio(
            tipo_cubierta=enums.TipoCubierta.UN_AGUA, altura_cumbrera=7.5, alero=0
        ),
    ),
    (
        "un-agua-angulo-mayor",
        _edificio(tipo_cubierta=enums.TipoCubierta.UN_AGUA),
    ),
    (
        "un-agua-angulo-mayor-alero",
        _edificio(tipo_cubierta=enums.TipoCubierta.UN_AGUA, alero=1),
    ),
    ("parapeto", _edificio(parapeto=1.5)),
    # --- Gran altura: Figura 8 para paredes y cubierta ---
    (
        "gran-altura-plana",
        _edificio(
            tipo_cubierta=enums.TipoCubierta.PLANA,
            altura_alero=24,
            altura_cumbrera=24,
            alero=0,
            alturas_personalizadas=ALTURAS_RALAS,
        ),
    ),
    (
        "gran-altura-dos-aguas",
        _edificio(
            altura_alero=24,
            altura_cumbrera=25,
            alturas_personalizadas=ALTURAS_RALAS,
        ),
    ),
    # --- Cerramiento y presión interna ---
    (
        "cerramiento-parcial",
        _edificio(cerramiento=enums.Cerramiento.PARCIALMENTE_CERRADO),
    ),
    ("cerramiento-abierto", _edificio(cerramiento=enums.Cerramiento.ABIERTO)),
    (
        "gcpi-reducido",
        _edificio(
            cerramiento=enums.Cerramiento.PARCIALMENTE_CERRADO,
            reducir_gcpi=True,
            aberturas=(10.0, 5.0, 2.0, 1.0, 0.5),
            volumen_interno=2000.0,
        ),
    ),
    # --- Sin componentes ---
    ("sin-componentes", _edificio(componentes_paredes=None, componentes_cubierta=None)),
    # --- Categoría y exposición ---
    *(
        (f"categoria-{categoria.name}", _edificio(categoria=categoria))
        for categoria in enums.CategoriaEstructura
    ),
    *(
        (f"exposicion-{exposicion.name}", _edificio(categoria_exp=exposicion))
        for exposicion in enums.CategoriaExposicion
    ),
    # --- Factor de ráfaga calculado ---
    (
        "rafaga-rigida",
        _edificio(
            factor_g_simplificado=False,
            flexibilidad=enums.Flexibilidad.RIGIDA,
            frecuencia=1.5,
            beta=0.02,
        ),
    ),
    (
        "rafaga-flexible",
        _edificio(
            factor_g_simplificado=False,
            flexibilidad=enums.Flexibilidad.FLEXIBLE,
            frecuencia=0.8,
            beta=0.015,
        ),
    ),
    # --- Topografía ---
    *(
        (
            f"topografia-{terreno.name}",
            _edificio(
                considerar_topografia=True,
                tipo_terreno=terreno,
                altura_terreno=30,
                distancia_cresta=50,
                distancia_barlovento_sotavento=20,
            ),
        )
        for terreno in enums.TipoTerrenoTopografia
    ),
    (
        "topografia-sotavento",
        _edificio(
            considerar_topografia=True,
            altura_terreno=30,
            distancia_cresta=50,
            distancia_barlovento_sotavento=20,
            direccion=enums.DireccionTopografia.SOTAVENTO,
        ),
    ),
    # --- Alturas ---
    ("elevado", _edificio(elevacion=3)),
    (
        "alturas-personalizadas",
        _edificio(alturas_personalizadas=(1.5, 3.25, 5.75, 7.0)),
    ),
)

BASE_CARTEL = {
    "profundidad": 1,
    "ancho": 10,
    "altura_inferior": 5,
    "altura_superior": 10,
    "velocidad": 45,
    "categoria": enums.CategoriaEstructura.II,
    "factor_g_simplificado": True,
    "categoria_exp": enums.CategoriaExposicion.B,
    "considerar_topografia": False,
}

CASOS_CARTEL = (
    ("sobre-nivel-terreno", {**BASE_CARTEL}),
    ("a-nivel-terreno", {**BASE_CARTEL, "altura_inferior": 0.5, "altura_superior": 8}),
    ("parapeto", {**BASE_CARTEL, "es_parapeto": True}),
    *(
        (f"exposicion-{exposicion.name}", {**BASE_CARTEL, "categoria_exp": exposicion})
        for exposicion in enums.CategoriaExposicion
    ),
    (
        "topografia",
        {
            **BASE_CARTEL,
            "considerar_topografia": True,
            "altura_terreno": 30,
            "distancia_cresta": 50,
            "distancia_barlovento_sotavento": 20,
        },
    ),
    (
        "rafaga-flexible",
        {
            **BASE_CARTEL,
            "altura_superior": 30,
            "categoria_exp": enums.CategoriaExposicion.C,
            "factor_g_simplificado": False,
            "flexibilidad": enums.Flexibilidad.FLEXIBLE,
            "frecuencia": 0.7,
            "beta": 0.02,
        },
    ),
)

BASE_CUBIERTA_AISLADA = {
    "ancho": 10,
    "longitud": 20,
    "altura_alero": 5,
    "altura_cumbrera": 6.5,
    "altura_bloqueo": 0,
    "posicion_bloqueo": enums.PosicionBloqueoCubierta.ALERO_BAJO,
    "tipo_cubierta": enums.TipoCubierta.DOS_AGUAS,
    "coeficiente_friccion": 0.02,
    "velocidad": 45,
    "categoria": enums.CategoriaEstructura.II,
    "categoria_exp": enums.CategoriaExposicion.B,
    "considerar_topografia": False,
}

CASOS_CUBIERTA_AISLADA = (
    ("dos-aguas", {**BASE_CUBIERTA_AISLADA}),
    ("dos-aguas-bloqueada", {**BASE_CUBIERTA_AISLADA, "altura_bloqueo": 1.5}),
    ("dos-aguas-angulo-grande", {**BASE_CUBIERTA_AISLADA, "altura_cumbrera": 9}),
    (
        "un-agua-alero-bajo",
        {**BASE_CUBIERTA_AISLADA, "tipo_cubierta": enums.TipoCubierta.UN_AGUA},
    ),
    (
        "un-agua-alero-alto",
        {
            **BASE_CUBIERTA_AISLADA,
            "tipo_cubierta": enums.TipoCubierta.UN_AGUA,
            "altura_bloqueo": 1.5,
            "posicion_bloqueo": enums.PosicionBloqueoCubierta.ALERO_ALTO,
        },
    ),
    (
        "topografia",
        {
            **BASE_CUBIERTA_AISLADA,
            "considerar_topografia": True,
            "altura_terreno": 30,
            "distancia_cresta": 50,
            "distancia_barlovento_sotavento": 20,
        },
    ),
)

#: Las columnas de cada archivo: el encabezado y de dónde sale el valor.
COLUMNAS_EDIFICIO = (
    ("zona", lambda fila: fila.zona),
    ("sistema", lambda fila: fila.sistema),
    ("direccion", lambda fila: fila.direccion),
    ("pared", lambda fila: fila.pared),
    ("posicion", lambda fila: fila.posicion),
    ("caso_presion", lambda fila: fila.caso),
    ("componente", lambda fila: fila.componente),
    ("zona_componente", lambda fila: fila.zona_componente),
    ("rango", lambda fila: fila.rango),
    ("referencia", lambda fila: fila.referencia),
    ("altura", lambda fila: fila.q.altura),
    ("kz", lambda fila: fila.q.kz),
    ("kzt", lambda fila: fila.q.kzt),
    ("q", lambda fila: fila.q.valor),
    ("cp", lambda fila: fila.cp),
    ("rafaga", lambda fila: fila.factor_rafaga),
    ("gcpi", lambda fila: fila.gcpi),
    ("pos", lambda fila: fila.pos),
    ("neg", lambda fila: fila.neg),
)

COLUMNAS_CARTEL = (
    ("altura", lambda fila: fila.q.altura),
    ("kz", lambda fila: fila.q.kz),
    ("kzt", lambda fila: fila.q.kzt),
    ("q", lambda fila: fila.q.valor),
    ("cf", lambda fila: fila.cf),
    ("rafaga", lambda fila: fila.factor_rafaga),
    ("presion", lambda fila: fila.presion),
    ("area_parcial", lambda fila: fila.area_parcial),
    ("fuerza", lambda fila: fila.fuerza),
)

COLUMNAS_CUBIERTA_AISLADA = (
    ("tipo", lambda fila: fila.tipo),
    ("zona", lambda fila: fila.zona),
    ("extremo", lambda fila: fila.extremo),
    ("altura", lambda fila: fila.q.altura),
    ("kz", lambda fila: fila.q.kz),
    ("kzt", lambda fila: fila.q.kzt),
    ("q", lambda fila: fila.q.valor),
    ("cpn", lambda fila: fila.cpn),
    ("rafaga", lambda fila: fila.factor_rafaga),
    ("presion", lambda fila: fila.presion),
    ("friccion", lambda fila: fila.presion_friccion),
)


def _texto(valor) -> str:
    """Convierte un valor de una fila a su representación en el archivo.

    Args:
        valor: El valor a convertir.

    Returns:
        El texto de la celda.
    """
    if valor is None:
        return "-"
    if isinstance(valor, Enum):
        return valor.name
    if isinstance(valor, tuple):
        return "/".join(f"{numero:.4f}" for numero in valor)
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def _tablas_edificio() -> Iterator[tuple[str, object]]:
    """Las tablas de resultado de cada caso de edificio.

    El SPRFV y los componentes van por separado porque el Reglamento puede no
    proveer lineamientos para los segundos.

    Yields:
        El nombre de la tabla y sus filas.
    """
    for nombre, parametros in CASOS_EDIFICIO:
        edificio = Edificio(**parametros)
        yield f"{nombre}/sprfv", edificio.resultados_sprfv
        yield f"{nombre}/componentes", edificio.resultados_componentes


def _tablas_cartel() -> Iterator[tuple[str, object]]:
    """Las tablas de resultado de cada caso de cartel.

    Yields:
        El nombre de la tabla y sus filas.
    """
    for nombre, parametros in CASOS_CARTEL:
        yield nombre, Cartel(**parametros).resultados


def _tablas_cubierta_aislada() -> Iterator[tuple[str, object]]:
    """Las tablas de resultado de cada caso de cubierta aislada.

    Yields:
        El nombre de la tabla y sus filas.
    """
    for nombre, parametros in CASOS_CUBIERTA_AISLADA:
        yield nombre, CubiertaAislada(**parametros).resultados


#: Cada archivo de referencia: sus tablas y sus columnas.
ARCHIVOS: dict[str, tuple[Callable, tuple]] = {
    "edificio": (_tablas_edificio, COLUMNAS_EDIFICIO),
    "cartel": (_tablas_cartel, COLUMNAS_CARTEL),
    "cubierta-aislada": (_tablas_cubierta_aislada, COLUMNAS_CUBIERTA_AISLADA),
}


def generar(nombre: str) -> list[str]:
    """Calcula los resultados de un archivo de referencia.

    Args:
        nombre: El nombre del archivo, sin extensión.

    Returns:
        Las líneas del archivo, empezando por el encabezado.
    """
    tablas, columnas = ARCHIVOS[nombre]
    encabezados = tuple(encabezado for encabezado, _ in columnas)
    lineas = ["\t".join(("caso", *encabezados))]
    for nombre_tabla, tabla in tablas():
        for fila in tabla:
            celdas = (_texto(obtener(fila)) for _, obtener in columnas)
            lineas.append("\t".join((nombre_tabla, *celdas)))
    return lineas


def leer(nombre: str) -> list[str]:
    """Lee un archivo de referencia.

    Args:
        nombre: El nombre del archivo, sin extensión.

    Returns:
        Las líneas del archivo.
    """
    return (DIRECTORIO / f"{nombre}.tsv").read_text().splitlines()


def escribir(nombre: str, lineas: list[str]) -> None:
    """Escribe un archivo de referencia.

    Args:
        nombre: El nombre del archivo, sin extensión.
        lineas: Las líneas a escribir.
    """
    DIRECTORIO.mkdir(exist_ok=True)
    (DIRECTORIO / f"{nombre}.tsv").write_text("\n".join(lineas) + "\n")


def main() -> None:
    """Regenera todos los archivos de referencia."""
    for nombre in ARCHIVOS:
        lineas = generar(nombre)
        escribir(nombre, lineas)
        print(f"{nombre}.tsv: {len(lineas) - 1} filas")


if __name__ == "__main__":
    main()
