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

"""Presión de velocidad, común a todas las estructuras."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import numpy as np

from zonda.cirsoc.resultados import PresionVelocidad
from zonda.enums import CategoriaEstructura, CategoriaExposicion

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc.factores import Rafaga


class PresionesBase:
    """PresionesBase.

    Calcula la presión de velocidad de cada altura de la estructura. Las
    alturas y sus factores topográficos llegan como arrays desde la geometría y
    la topografía, y se normalizan a secuencias de escalares: de acá en adelante
    cada altura es un valor con su coeficiente de exposición, su factor
    topográfico y su presión.
    """

    def __init__(
        self,
        alturas: float | Sequence[float] | np.ndarray,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: float | Sequence[float] | np.ndarray,
        factor_direccionalidad: float,
        categoria_exp: CategoriaExposicion,
        factor_altitud: float = 1.0,
    ) -> None:
        """

        Args:
            alturas: La altura o las alturas de la estructura donde calcular las presiones.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            factor_direccionalidad: El factor de direccionalidad correspondiente para el tipo de estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        self.alturas = tuple(float(altura) for altura in np.atleast_1d(alturas))
        self.factores_topograficos = tuple(
            float(factor)
            for factor in np.broadcast_to(factor_topografico, len(self.alturas))
        )
        self.categoria = categoria
        self.velocidad = velocidad
        self.rafaga = rafaga
        self.factor_direccionalidad = factor_direccionalidad
        self.categoria_exp = categoria_exp
        self.factor_altitud = factor_altitud

    @cached_property
    def presiones_velocidad(self) -> tuple[PresionVelocidad, ...]:
        """Calcula la presión de velocidad de cada altura.

        Returns:
            Una presión de velocidad por altura, con los factores que la componen.
        """
        return tuple(
            self._presion_velocidad(altura, factor)
            for altura, factor in zip(
                self.alturas, self.factores_topograficos, strict=True
            )
        )

    def presion_velocidad_en(self, altura: float) -> PresionVelocidad:
        """Obtiene la presión de velocidad de una de las alturas de la estructura.

        Args:
            altura: La altura buscada.

        Returns:
            La presión de velocidad de esa altura.

        Raises:
            ValueError: Cuando la altura no es una de las de la estructura.
        """
        for presion in self.presiones_velocidad:
            if presion.altura == altura:
                return presion
        raise ValueError(f"No hay presión de velocidad calculada para {altura} m.")

    def _presion_velocidad(
        self, altura: float, factor_topografico: float
    ) -> PresionVelocidad:
        """Calcula la presión de velocidad a una altura.

        Args:
            altura: La altura a la que se calcula la presión.
            factor_topografico: El factor topográfico correspondiente a esa altura.

        Returns:
            La presión de velocidad con los factores que la componen.
        """
        coeficiente_exposicion = self._coeficiente_exposicion(altura)
        valor = (
            0.613
            * self.factor_direccionalidad
            * coeficiente_exposicion
            * factor_topografico
            * self.factor_altitud
            * self.velocidad**2
        )
        return PresionVelocidad(
            altura,
            coeficiente_exposicion,
            factor_topografico,
            valor,
            self.factor_altitud,
        )

    def _coeficiente_exposicion(self, altura: float) -> float:
        """Calcula el coeficiente de exposición para la presión dinámica, Kz.

        Args:
            altura: La altura a la que se calcula el coeficiente.

        Returns:
            El coeficiente de exposición para la presión dinámica.
        """
        constantes = self.rafaga.constantes_exp_terreno
        z = min(max(altura, 5.0), constantes.zg)
        return float(2.41 * (z / constantes.zg) ** (2 / constantes.alfa))
