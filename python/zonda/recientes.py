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

"""Los últimos proyectos abiertos, para ofrecerlos en la bienvenida.

Se anota una ruta cada vez que un módulo abre o guarda un archivo, que son los
dos momentos en que alguien eligió ese archivo. El historial vive en
``QSettings``, así que sobrevive entre sesiones sin dejar ningún archivo de
índice dando vueltas por el disco.

Al leerlo se saltean los que ya no están, pero **no se los borra**: un proyecto
en un disco externo desconectado, o en una carpeta de red que hoy no responde,
tiene que volver a la lista cuando el disco vuelva.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore

GRUPO_SETTINGS = "recientes"
"""El grupo de ``QSettings`` donde se guarda el historial."""

CLAVE = "archivos"
"""La clave, dentro del grupo, con la lista de rutas."""

MAXIMO = 6
"""Cuántos proyectos se recuerdan.

Los que entran en la bienvenida sin que la lista se coma la pantalla. Más que
esto deja de ser un atajo y pasa a ser algo que hay que leer.
"""


def _leer() -> list[str]:
    """Las rutas guardadas, tal como están en ``QSettings``.

    Returns: Las rutas, de la más reciente a la más vieja.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    valor = settings.value(CLAVE, [])
    settings.endGroup()

    # Una lista de un solo elemento vuelve de QSettings como una cadena suelta,
    # no como lista de uno. Sin este caso, un historial de un solo proyecto se
    # leeria como una ruta por caracter.
    if isinstance(valor, str):
        return [valor] if valor else []
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor if str(item)]


def _escribir(rutas: list[str]) -> None:
    """Reemplaza el historial.

    Args:
        rutas: Las rutas a guardar, de la más reciente a la más vieja.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    settings.setValue(CLAVE, rutas)
    settings.endGroup()
    settings.sync()


def registrar(ruta: str | Path) -> None:
    """Anota un proyecto como el más reciente.

    Si ya estaba en el historial sube al principio en lugar de duplicarse. La
    ruta se guarda absoluta porque la bienvenida no comparte el directorio de
    trabajo con el módulo que abrió el archivo.

    Args:
        ruta: El archivo que se acaba de abrir o guardar.
    """
    absoluta = str(Path(ruta).expanduser().resolve())

    rutas = [item for item in _leer() if item != absoluta]
    rutas.insert(0, absoluta)
    _escribir(rutas[:MAXIMO])


def listar() -> tuple[Path, ...]:
    """Los proyectos recientes que todavía existen.

    Returns: Las rutas, de la más reciente a la más vieja.
    """
    return tuple(ruta for item in _leer() if (ruta := Path(item)).is_file())


def olvidar_todo() -> None:
    """Borra el historial entero."""
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    settings.remove(CLAVE)
    settings.endGroup()
    settings.sync()
