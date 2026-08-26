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

"""Accesos a Qt que los stubs declaran opcionales y en la práctica no lo son.

``itemAt`` e ``itemAtPosition`` devuelven ``None`` para una celda vacía, y
``QLayoutItem.widget()`` devuelve ``None`` cuando el item es un espaciador o un
sublayout. Los diálogos de Zonda piden posiciones que llenan ellos mismos al
armarse, así que ahí nunca es ``None``: si alguna de estas funciones levanta el
``assert``, lo que cambió es el layout, no la entrada del usuario.

Para recorrer un layout entero —donde sí hay celdas vacías— no sirven: ahí hay
que preguntar por ``None`` y seguir de largo.
"""

from __future__ import annotations

from PyQt6 import QtWidgets


def widget_de_celda(
    layout: QtWidgets.QGridLayout, fila: int, columna: int
) -> QtWidgets.QWidget:
    """El widget que ocupa una celda de un grid."""
    item = layout.itemAtPosition(fila, columna)
    assert item is not None, f"la celda ({fila}, {columna}) está vacía"
    return _widget_de_item(item)


def widget_de_indice(layout: QtWidgets.QLayout, indice: int) -> QtWidgets.QWidget:
    """El widget que está en una posición de un layout."""
    item = layout.itemAt(indice)
    assert item is not None, f"el layout no llega al índice {indice}"
    return _widget_de_item(item)


def _widget_de_item(item: QtWidgets.QLayoutItem) -> QtWidgets.QWidget:
    widget = item.widget()
    assert widget is not None, "el item del layout no es un widget"
    return widget
