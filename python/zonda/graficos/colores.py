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

"""Escala de colores para las presiones.

El valor mínimo queda azul y el máximo rojo, interpolando el matiz en HSV con la
saturación y el valor en 1. Es la escala que también dibuja la barra de
referencia de la vista 3D.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor

MATIZ_MINIMO = 0.66
MATIZ_MAXIMO = 0.0


class TablaColores:
    """Mapea un valor de presión a un color.

    Args:
        minimo: El valor que corresponde al extremo azul.
        maximo: El valor que corresponde al extremo rojo.
    """

    def __init__(self, minimo: float, maximo: float) -> None:
        self.minimo = minimo
        self.maximo = maximo

    def fraccion(self, valor: float) -> float:
        """Ubica el valor entre 0 y 1 dentro del rango, recortando los extremos.

        Los valores fuera de rango se pegan al color del extremo más cercano.
        """
        if self.maximo == self.minimo:
            return 0.0
        return min(1.0, max(0.0, (valor - self.minimo) / (self.maximo - self.minimo)))

    def color(self, valor: float) -> QColor:
        """El color que le corresponde al valor."""
        matiz = MATIZ_MINIMO + (MATIZ_MAXIMO - MATIZ_MINIMO) * self.fraccion(valor)
        return QColor.fromHsvF(matiz, 1.0, 1.0)

    def paradas(self, cantidad: int = 16) -> list[dict]:
        """Las paradas del degradado para dibujar la barra de escala en QML.

        Args:
            cantidad: Cuántas paradas generar. Con 16 el degradado ya no se ve
                escalonado.

        Returns:
            Una lista de ``{"posicion": float, "color": QColor}`` ordenada de
            arriba (máximo) hacia abajo (mínimo), que es como se apila el
            gradiente de un ``Rectangle`` de QML.
        """
        paradas = []
        for i in range(cantidad):
            fraccion = i / (cantidad - 1)
            valor = self.minimo + (self.maximo - self.minimo) * (1 - fraccion)
            paradas.append({"posicion": fraccion, "color": self.color(valor)})
        return paradas

    def etiquetas(self, cantidad: int = 4) -> list[float]:
        """Los valores rotulados en la barra, de mayor a menor.

        Con cuatro alcanza para leer la escala sin llenarla de números.
        """
        if cantidad < 2:
            return [self.maximo]
        paso = (self.maximo - self.minimo) / (cantidad - 1)
        return [self.maximo - paso * i for i in range(cantidad)]
