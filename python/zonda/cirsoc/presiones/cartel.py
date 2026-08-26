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
from typing import TYPE_CHECKING

from zonda.cirsoc.presiones.base import PresionesBase

if TYPE_CHECKING:
    import numpy as np

    from zonda.cirsoc import cp, geometria
    from zonda.cirsoc.factores import Rafaga
    from zonda.enums import CategoriaEstructura, CategoriaExposicion


class Cartel(PresionesBase):
    """Cartel.

    Determina las presiones de viento sobre un cartel.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        areas_parciales: tuple[float, ...],
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: np.ndarray,
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
    ) -> None:
        """

        Args:
            alturas: Las alturas donde calcular las presiones sobre el cartel.
            areas_parciales: Las areas entre las alturas consideradas.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de Rafaga.
            factor_topografico: Los factores topográficos correspondientes a cada altura de la estructura.
            cf: Una instancia de cartel.
            categoria_exp: La categoría de exposición.
        """
        super().__init__(
            alturas,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
        )
        self.areas_parciales = areas_parciales
        self.cf = cf
        self.factor_rafaga = rafaga.factor

    @cached_property
    def valores(self) -> np.ndarray:
        """Calcula los valores de presión para el cartel para cada altura.

        Returns:
            Los valores de presión.
        """
        return self.presiones_velocidad * self.factor_rafaga * self.cf()

    @cached_property
    def fuerzas_parciales(self) -> np.ndarray:
        """Calcula las fuerzas (presión x área) en cada altura.

        Returns:
            Los valores de fuerza.
        """
        return self.valores[1:] * self.areas_parciales

    @cached_property
    def fuerza_total(self) -> float:
        """Calcula la fuerza total sobre el cartel.

        Returns:
            La fuerza total.
        """
        return self.fuerzas_parciales.sum()

    @classmethod
    def desde_cartel(
        cls,
        cartel: geometria.Cartel,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: np.ndarray,
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
    ) -> Cartel:
        """Crea una instancia a partir de la geometria de un Cartel.

        Args:
            cartel: Una instancia de Cartel.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de Rafaga.
            factor_topografico: Los factores topográficos correspondientes a cada altura de la estructura.
            cf: Una instancia de cartel.
            categoria_exp: La categoría de exposición.
        """
        return cls(
            cartel.alturas,
            cartel.areas_parciales,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cf,
            categoria_exp,
        )

    def __call__(self) -> np.ndarray:
        return self.valores
