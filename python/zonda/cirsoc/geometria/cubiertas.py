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

import math
from functools import cached_property

from zonda.enums import TipoCubierta


class Cubierta:
    """Cubierta.

    Genera la geometria de una cubierta.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        parapeto: float = 0,
        alero: float = 0,
        bloqueo: float = 0,
    ) -> None:
        """
        Args:
            ancho: El ancho de la cubierta.
            longitud: La longitud de la cubierta.
            altura_alero: La altura de alero de la cubierta, medida desde el nivel de suelo.
            altura_cumbrera: La altura de cumbrera de la cubierta, medida desde el nivel de suelo.
            tipo_cubierta: El tipo de cubierta.
            parapeto: La dimensión del parapeto.
            alero: La dimensión del alero.
            bloqueo: El porcentaje de bloqueo del flujo de viento bajo la cubierta. Se utiliza en el caso de
                cubiertas aisladas.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_alero = altura_alero
        self.tipo_cubierta = tipo_cubierta
        if self.tipo_cubierta == TipoCubierta.PLANA:
            self.altura_cumbrera = altura_alero
        else:
            self.altura_cumbrera = altura_cumbrera
        self.parapeto = parapeto
        self.alero = alero
        self.bloqueo = bloqueo

    @property
    def con_bloqueo(self) -> bool:
        """Indica si el flujo de viento bajo la cubierta está obstruido.

        Con un bloqueo mayor al 50 % los objetos bajo el techo inhiben el
        flujo de viento (nota 2 de las Figuras 2.4-4 a 2.4-6).

        Returns:
            Verdadero si el bloqueo es mayor al 50 %.
        """
        return self.bloqueo > 50

    @cached_property
    def angulo(self) -> float:
        """Calcula el ángulo de la cubierta.

        Returns:
            El ángulo de cubierta.
        """
        pendiente = (self.altura_cumbrera - self.altura_alero) / self.ancho
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            pendiente *= 2
        angulo = math.atan(pendiente)
        return math.degrees(angulo)

    @cached_property
    def area(self) -> float:
        """Calcula el área de la cubierta.

        Returns:
            El area de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.PLANA:
            return self.ancho * self.longitud

        altura = self.altura_cumbrera - self.altura_alero
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            perimetro_frontal = 2 * math.hypot(altura, self.ancho / 2)
        else:
            perimetro_frontal = math.hypot(altura, self.ancho)
        return perimetro_frontal * self.longitud

    @cached_property
    def altura_media(self) -> float:
        """Calcula la altura media de cubierta.

        Returns:
            La altura media de cubierta.
        """
        if self.angulo <= 10:
            return self.altura_alero
        return (self.altura_alero + self.altura_cumbrera) / 2

    @cached_property
    def area_mojinete(self) -> float:
        """Calcula el area de la zona de mojinete de la pared.

        Returns:
            El area de mojinete.
        """
        return self.ancho * (self.altura_cumbrera - self.altura_alero) / 2
