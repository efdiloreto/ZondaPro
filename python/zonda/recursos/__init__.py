# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

"""Acceso a los recursos empaquetados de Zonda.

Reemplaza al módulo que generaba ``pyrcc5``: Qt6 eliminó el compilador de
recursos y PyQt6 no provee ningún equivalente, así que los archivos se leen
directamente del paquete con :mod:`importlib.resources` en lugar de estar
embebidos en un módulo de Python.

``recursos.qrc`` se conserva como manifiesto. Sigue definiendo con qué alias se
referencia cada archivo desde el código (``iconos/regla.png``) y dónde vive
realmente dentro del paquete (``iconos/toolbar-graficos/regla.png``), de manera
que las claves usadas en los widgets no cambian.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from functools import cache
from importlib.resources import files
from pathlib import Path

from PyQt6 import QtGui

# Los recursos siempre se distribuyen como archivos sueltos (instalación normal
# o bundle de PyInstaller), nunca dentro de un zip, por lo que `files` devuelve
# una ruta real del sistema de archivos.
_DIRECTORIO = Path(str(files(__name__)))

_MANIFIESTO = _DIRECTORIO / "recursos.qrc"


@cache
def _alias() -> dict[str, str]:
    """Mapea cada alias del manifiesto a su ruta relativa dentro del paquete."""
    mapa = {}
    for recurso in ET.parse(_MANIFIESTO).getroot().iterfind("qresource"):
        prefijo = recurso.get("prefix", "")
        for archivo in recurso.iterfind("file"):
            ruta_relativa = archivo.text or ""
            nombre = archivo.get("alias") or Path(ruta_relativa).name
            mapa[f"{prefijo}/{nombre}"] = ruta_relativa
    return mapa


def ruta(clave: str) -> Path:
    """Devuelve la ruta absoluta de un recurso.

    Args:
        clave: El alias del recurso, por ejemplo ``iconos/regla.png``. Se acepta
            también el prefijo ``:/`` que usaba el sistema de recursos de Qt.

    Raises:
        FileNotFoundError: Si el alias no está declarado en el manifiesto.

    Returns:
        La ruta al archivo dentro del paquete.
    """
    clave = clave.removeprefix(":/")
    try:
        return _DIRECTORIO / _alias()[clave]
    except KeyError:
        raise FileNotFoundError(
            f"El recurso '{clave}' no está declarado en {_MANIFIESTO.name}."
        ) from None


def directorio(nombre: str) -> Path:
    """Devuelve la ruta de un subdirectorio de recursos.

    Args:
        nombre: El nombre del subdirectorio, por ejemplo ``plantillas``.

    Raises:
        FileNotFoundError: Si el subdirectorio no existe.

    Returns:
        La ruta al subdirectorio.
    """
    ruta_directorio = _DIRECTORIO / nombre
    if not ruta_directorio.is_dir():
        raise FileNotFoundError(f"No existe el directorio de recursos '{nombre}'.")
    return ruta_directorio


def texto(clave: str, encoding: str = "utf-8") -> str:
    """Lee un recurso de texto.

    Args:
        clave: El alias del recurso.
        encoding: La codificación con la que se lee el archivo.

    Returns:
        El contenido del archivo.
    """
    return ruta(clave).read_text(encoding=encoding)


def icono(clave: str) -> QtGui.QIcon:
    """Crea un ícono a partir de un recurso.

    Args:
        clave: El alias del recurso.

    Returns:
        El ícono.
    """
    return QtGui.QIcon(str(ruta(clave)))


def pixmap(clave: str) -> QtGui.QPixmap:
    """Crea un pixmap a partir de un recurso.

    Args:
        clave: El alias del recurso.

    Returns:
        El pixmap.
    """
    return QtGui.QPixmap(str(ruta(clave)))
