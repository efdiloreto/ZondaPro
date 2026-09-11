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

"""Serialización de resultados a estructuras JSON.

Convierte las filas de ``zonda.cirsoc.resultados`` en diccionarios aptos para
un cliente MCP. Los ``Enum`` viajan por su nombre -igual que en el formato de
proyecto ``.zda``- para que un cliente pueda leer las claves sin conocer las
clases.
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any

from zonda.cirsoc.resultados import Tabla

UNIDADES = {
    "presion": "N/m2",
    "velocidad": "m/s",
    "longitud": "m",
    "area": "m2",
    "fuerza": "N",
}
"""Las unidades de los valores de los resultados."""

SISTEMA_COORDENADAS = (
    "X: ancho, de 0 a ancho; Y: altura sobre el suelo (incluye la elevación); "
    "Z: longitud, negativa (de 0 a -longitud)."
)
"""La descripción del sistema de coordenadas de las zonas."""


def serializar_valor(valor: Any) -> Any:
    """Serializa un valor a tipos JSON.

    Args:
        valor: El valor a serializar.

    Returns:
        El valor convertido: los ``Enum`` por su nombre, las tuplas y listas
        como listas, las dataclasses como diccionarios.
    """
    if isinstance(valor, enum.Enum):
        return valor.name
    if isinstance(valor, dict):
        return {
            (
                clave.name if isinstance(clave, enum.Enum) else str(clave)
            ): serializar_valor(item)
            for clave, item in valor.items()
        }
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {
            campo.name: serializar_valor(getattr(valor, campo.name))
            for campo in dataclasses.fields(valor)
        }
    if isinstance(valor, (tuple, list)):
        return [serializar_valor(item) for item in valor]
    if isinstance(valor, (bool, int, float, str)) or valor is None:
        return valor
    raise TypeError(f"No se puede serializar el valor: {valor!r}")


def serializar_tabla(tabla: Tabla) -> list[dict]:
    """Serializa una tabla de resultados a una lista de diccionarios.

    Args:
        tabla: La tabla de resultados.

    Returns:
        Una lista con un diccionario por fila.
    """
    return [
        {
            campo.name: serializar_valor(getattr(fila, campo.name))
            for campo in dataclasses.fields(fila)
        }
        for fila in tabla.filas
    ]


def referencias(tabla: Tabla) -> list[str]:
    """Las referencias del Reglamento que usa la tabla, sin repetir.

    Args:
        tabla: La tabla de resultados.

    Returns:
        Las referencias en orden de aparición.
    """
    return list(dict.fromkeys(fila.referencia for fila in tabla.filas))
