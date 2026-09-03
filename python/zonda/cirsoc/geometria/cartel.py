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

from __future__ import annotations

from functools import cached_property

import numpy as np


class Cartel:
    """Cartel

    Genera la geometria de un cartel.
    """

    def __init__(
        self,
        profundidad: float,
        ancho: float,
        altura_inferior: float,
        altura_superior: float,
    ) -> None:
        """
        Args:
            profundidad: La profundidad del cartel.
            ancho: El ancho del cartel.
            altura_inferior: La altura desde el suelo desde donde se consideran las presiones del viento sobre el cartel.
            altura_superior: La altura superior del cartel.
        """
        self.profundidad = profundidad
        self.ancho = ancho
        self.altura_inferior = altura_inferior
        self.altura_superior = altura_superior

    @cached_property
    def altura_neta(self) -> float:
        """Calcula la altura de la superficie del cartel donde pega el viento.

        Returns:
            La altura neta.
        """
        return self.altura_superior - self.altura_inferior

    @cached_property
    def area(self) -> float:
        """Calcula el area del cartel.

        Returns:
            El area del cartel.
        """
        return self.ancho * self.altura_neta

    @cached_property
    def altura_media(self) -> float:
        """Calcula la altura media del cartel.

        Returns:
            La altura media.
        """
        return (self.altura_inferior + self.altura_superior) / 2

    @cached_property
    def alturas(self) -> np.ndarray:
        """Las alturas donde se evalúa la presión dinámica.

        De acuerdo a la Ec. 4.4-1, la presión dinámica qh se evalúa a la altura
        h que define la Figura 4.4-1: la punta del cartel.

        Returns:
            Un array con la altura superior.
        """
        return np.array([self.altura_superior])
