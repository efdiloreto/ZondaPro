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

import numpy as np

from zonda.cirsoc.presiones.base import PresionesBase
from zonda.cirsoc.resultados import FilaCartel

if TYPE_CHECKING:
    from collections.abc import Sequence

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
        factor_topografico: Sequence[float],
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
        factor_altitud: float = 1.0,
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
            factor_altitud: El factor de altitud del terreno Ke.
        """
        super().__init__(
            alturas,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
            factor_altitud=factor_altitud,
        )
        self.areas_parciales = areas_parciales
        self.cf = cf
        self.factor_rafaga = rafaga.factor

    @cached_property
    def valores(self) -> tuple[float, ...]:
        """Calcula los valores de presión para el cartel para cada altura.

        Returns:
            Los valores de presión.
        """
        return tuple(
            float(q.valor * self.factor_rafaga * self.cf())
            for q in self.presiones_velocidad
        )

    @cached_property
    def fuerzas_parciales(self) -> tuple[float, ...]:
        """Calcula las fuerzas (presión x área) en cada tramo entre alturas.

        Returns:
            Los valores de fuerza.
        """
        return tuple(
            presion * area
            for presion, area in zip(
                self.valores[1:], self.areas_parciales, strict=True
            )
        )

    @cached_property
    def filas(self) -> tuple[FilaCartel, ...]:
        """Calcula las presiones sobre el cartel.

        Returns:
            Una fila por cada altura. El área parcial y la fuerza corresponden
            al tramo que arranca en la altura anterior, así que la primera fila
            no las tiene.
        """
        cf = float(self.cf())
        factor_rafaga = float(self.factor_rafaga)
        return tuple(
            FilaCartel(
                q=q,
                cf=cf,
                factor_rafaga=factor_rafaga,
                presion=presion,
                referencia="Tabla 11",
                area_parcial=None
                if indice == 0
                else float(self.areas_parciales[indice - 1]),
                fuerza=None
                if indice == 0
                else float(self.fuerzas_parciales[indice - 1]),
            )
            for indice, (q, presion) in enumerate(
                zip(self.presiones_velocidad, self.valores, strict=True)
            )
        )

    @cached_property
    def fuerza_total(self) -> float:
        """Calcula la fuerza total sobre el cartel.

        Returns:
            La fuerza total.
        """
        return sum(self.fuerzas_parciales)

    @classmethod
    def desde_cartel(
        cls,
        cartel: geometria.Cartel,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
        factor_altitud: float = 1.0,
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
            factor_altitud: El factor de altitud del terreno Ke.
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
            factor_altitud=factor_altitud,
        )
