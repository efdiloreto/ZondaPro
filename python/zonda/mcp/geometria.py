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

"""Coordenadas de las zonas de presión, leídas de los directores sin vista.

Los directores de ``zonda.graficos.directores`` devuelven las coordenadas de
cada zona indexadas por los mismos enums que etiquetan las filas de
resultados. Instanciados con ``crear_actores=False`` no tocan la escena y los
métodos crudos (``__wrapped__``) exponen las coordenadas puras, así que un
proceso headless las puede leer sin QApplication.
"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

import numpy as np

from zonda.excepciones import ErrorLineamientos
from zonda.graficos.actores import Poligono
from zonda.graficos.colores import TablaColores
from zonda.graficos.directores import aisladas, cartel, edificio
from zonda.graficos.escena import Escena3D

if TYPE_CHECKING:
    from zonda.cirsoc.estructuras import Cartel, CubiertaAislada, Edificio
    from zonda.cirsoc.resultados import Tabla


def _normalizar(valor: Any) -> Any:
    """Convierte coordenadas y claves a tipos JSON.

    Args:
        valor: Un polígono, un array, una estructura anidada de tuplas y
            diccionarios, o un escalar.

    Returns:
        El valor convertido: los ``Enum`` (como claves) por su nombre, las
        tuplas y arrays como listas, los números de NumPy como nativos.
    """
    if isinstance(valor, Poligono):
        return valor.puntos.tolist()
    if isinstance(valor, np.ndarray):
        return valor.tolist()
    if isinstance(valor, enum.Enum):
        return valor.name
    if isinstance(valor, np.floating):
        return float(valor)
    if isinstance(valor, dict):
        return {
            (clave.name if isinstance(clave, enum.Enum) else str(clave)): _normalizar(
                item
            )
            for clave, item in valor.items()
        }
    if isinstance(valor, Iterable) and not isinstance(valor, (str, bytes)):
        return [_normalizar(item) for item in valor]
    return valor


def _tabla_colores(tabla: Tabla) -> TablaColores:
    """La tabla de colores de los extremos de presión de una tabla de resultados.

    Args:
        tabla: La tabla de resultados de la que tomar los extremos.

    Returns:
        La tabla de colores.
    """
    minimo, maximo = tabla.min_max()
    return TablaColores(minimo, maximo)


def zonas_edificio(estructura: Edificio) -> dict:
    """Las coordenadas de todas las zonas de un edificio.

    Args:
        estructura: El edificio calculado.

    Returns:
        Un diccionario con la geometría del SPRFV en ``"sprfv"`` (paredes,
        cubierta, alero y parapeto, indexados por dirección del viento) y, si
        el Reglamento da lineamientos, la de componentes en ``"componentes"``
        (paredes, cubierta, alero y parapeto, indexados por zona). La clave
        ``"componentes"`` puede faltar cuando no hay lineamientos.
    """
    escena = Escena3D()
    director_sprfv = edificio.PresionesSprfvMetodoDireccional(
        escena, _tabla_colores(estructura.resultados_sprfv), estructura
    )
    zonas = {
        "sprfv": {
            "paredes": _normalizar(director_sprfv.paredes.__wrapped__(director_sprfv)),
            "cubierta": _normalizar(
                director_sprfv.cubierta.__wrapped__(director_sprfv)
            ),
            "alero": _normalizar(director_sprfv.alero.__wrapped__(director_sprfv)),
            "parapeto": _normalizar(
                director_sprfv.parapeto.__wrapped__(director_sprfv)
            ),
        }
    }
    try:
        tabla_componentes = estructura.resultados_componentes
    except ErrorLineamientos:
        return zonas
    if not len(tabla_componentes):
        return zonas
    try:
        director_componentes = edificio.PresionesComponentes(
            escena, _tabla_colores(tabla_componentes), estructura
        )
    except ErrorLineamientos:
        return zonas
    zonas["componentes"] = {
        "paredes": _normalizar(
            director_componentes.paredes.__wrapped__(director_componentes)
        ),
        "cubierta": _normalizar(director_componentes._coords_cubierta()),
        "alero": _normalizar(director_componentes._coords_alero()),
        "parapeto": _normalizar(director_componentes._coords_parapeto()),
    }
    return zonas


def zonas_cubierta_aislada(estructura: CubiertaAislada) -> dict:
    """Las coordenadas de las zonas de una cubierta aislada.

    Args:
        estructura: La cubierta aislada calculada.

    Returns:
        Un diccionario con la geometría de las presiones normales en
        ``"presiones"`` (indexadas por dirección del viento) y, si hay
        componentes y el Reglamento da lineamientos, la de componentes en
        ``"componentes"`` (indexadas por zona).
    """
    escena = Escena3D()
    director = aisladas.Presiones(
        escena, _tabla_colores(estructura.resultados), estructura
    )
    zonas = {"presiones": _normalizar(director.cubierta.__wrapped__(director))}
    if not estructura.componentes:
        return zonas
    try:
        director_componentes = aisladas.Componentes(
            escena, _tabla_colores(estructura.resultados_componentes), estructura
        )
    except ErrorLineamientos:
        return zonas
    zonas["componentes"] = _normalizar(
        director_componentes.zonas.__wrapped__(director_componentes)
    )
    return zonas


def zonas_cartel(estructura: Cartel) -> dict:
    """Las coordenadas de las zonas de un cartel.

    Args:
        estructura: El cartel calculado.

    Returns:
        Un diccionario con las caras del cartel, la cara a barlovento y las
        regiones del Caso C, indexadas por región.
    """
    escena = Escena3D()
    director = cartel.Presiones(
        escena, _tabla_colores(estructura.resultados), estructura
    )
    return {
        "caras": _normalizar(director.caras.__wrapped__(director)),
        "cara_barlovento": _normalizar(director.cara_barlovento.__wrapped__(director)),
        "regiones_caso_c": _normalizar(director.regiones_caso_c.__wrapped__(director)),
    }
