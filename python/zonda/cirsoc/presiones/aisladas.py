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
from zonda.cirsoc.resultados import FilaCubiertaAislada

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc import cp, geometria
    from zonda.cirsoc.factores import Rafaga
    from zonda.enums import (
        CategoriaEstructura,
        CategoriaExposicion,
    )


class CubiertaAislada(PresionesBase):
    """CubiertaAislada.

    Determina las presiones de viento sobre una cubierta Aislada.
    """

    def __init__(
        self,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
        coeficiente_friccion: float = 0.0,
    ) -> None:
        """
        Args:
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            cpn: Una instancia de CubiertaAislada.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            coeficiente_friccion: El coeficiente de fricción de la superficie de cubierta.
        """
        super().__init__(
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
        )
        self.cpn = cpn
        self.altura_media = altura_media
        self.coeficiente_friccion = coeficiente_friccion
        # La cubierta aislada se resuelve a una sola altura.
        self.q = self.presion_velocidad_en(altura_media)
        self._presion_parcial = self.q.valor * self.rafaga.factor

    @cached_property
    def filas(self) -> tuple[FilaCubiertaAislada, ...]:
        """Calcula las presiones sobre la cubierta aislada.

        Returns:
            Una fila por cada combinación de tipo de presión, zona y extremo.
        """
        factor_rafaga = float(self.rafaga.factor)
        filas = []
        for entrada in self.cpn.entradas:
            presion = float(self._presion_parcial * entrada.valor)
            filas.append(
                FilaCubiertaAislada(
                    tipo=entrada.tipo,
                    extremo=entrada.extremo,
                    q=self.q,
                    cpn=entrada.valor,
                    factor_rafaga=factor_rafaga,
                    presion=presion,
                    presion_friccion=presion * self.coeficiente_friccion,
                    referencia=entrada.referencia,
                    zona=entrada.zona,
                )
            )
        return tuple(filas)

    @classmethod
    def desde_cubierta(
        cls,
        cubierta: geometria.Cubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
        coeficiente_friccion: float = 0.0,
    ) -> CubiertaAislada:
        """Crea una instancia a partir de la geometria de una cubierta.

        Args:
            cubierta: Una instancia de Cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            cpn: Una instancia de CubiertaAislada.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            coeficiente_friccion: El coeficiente de fricción de la superficie de cubierta.
        """
        return cls(
            cubierta.altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cpn,
            categoria_exp,
            coeficiente_friccion,
        )
