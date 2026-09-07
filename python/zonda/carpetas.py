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

"""La última carpeta donde se abrió o guardó un proyecto.

Los diálogos de archivo de los módulos y de la bienvenida abren en esta carpeta
en lugar de en una arbitraria. La primera vez —cuando todavía no se recordó
ninguna— se usa la carpeta Documentos del sistema, como ya hace la exportación
del reporte.

La carpeta vive en ``QSettings``, así que sobrevive entre sesiones sin dejar
ningún archivo de índice dando vueltas por el disco. Si la carpeta recordada ya
no existe —un disco externo desconectado, una carpeta de red que hoy no
responde— se vuelve a caer a Documentos en lugar de abrir el diálogo en un lugar
imposible.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore

GRUPO_SETTINGS = "carpetas"
"""El grupo de ``QSettings`` donde se guarda la última carpeta."""

CLAVE = "ultima"
"""La clave, dentro del grupo, con la ruta de la última carpeta."""


def _documentos() -> str:
    """La carpeta Documentos del sistema, como destino inicial por defecto."""
    return QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.DocumentsLocation
    )


def ultima() -> str:
    """La última carpeta usada, o la de Documentos si no hay ninguna.

    Si la carpeta guardada ya no existe se la descarta en el momento de leerla,
    sin borrarla: puede estar en un disco desconectado y volver más adelante.

    Returns: La carpeta, para pasar como directorio inicial al diálogo.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    valor = settings.value(CLAVE, "")
    settings.endGroup()

    if valor and Path(str(valor)).is_dir():
        return str(valor)
    return _documentos()


def recordar(ruta: str | Path) -> None:
    """Anota la carpeta del archivo recién abierto o guardado.

    Args:
        ruta: El archivo; se guarda la carpeta que lo contiene.
    """
    carpeta = str(Path(ruta).expanduser().resolve().parent)
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    settings.setValue(CLAVE, carpeta)
    settings.endGroup()
    settings.sync()
