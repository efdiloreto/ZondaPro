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

from zonda.cirsoc.presiones.base import PresionesBase, presion_minima
from zonda.cirsoc.resultados import (
    FilaComponentesCubiertaAislada,
    FilaCubiertaAislada,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc import cp, geometria
    from zonda.cirsoc.factores import Rafaga
    from zonda.enums import CategoriaExposicion


class CubiertaAislada(PresionesBase):
    """CubiertaAislada.

    Determina las presiones de viento sobre una cubierta Aislada.
    """

    def __init__(
        self,
        altura_media: float,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
        coeficiente_friccion: float = 0.0,
        factor_altitud: float = 1.0,
    ) -> None:
        """
        Args:
            altura_media: La altura media de la cubierta.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            cpn: Una instancia de CubiertaAislada.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            coeficiente_friccion: El coeficiente de empuje por fricción de la superficie, según la Tabla 2.4-1.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        super().__init__(
            altura_media,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
            factor_altitud=factor_altitud,
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
            Una fila por cada combinación de dirección de viento, caso de
            carga y zona.
        """
        factor_rafaga = float(self.rafaga.factor)
        # La fricción actúa sobre la superficie superior e inferior con flujo
        # de viento libre, y sólo sobre la superior con el flujo obstruido
        # (artículo 2.4.3.1). El valor queda por unidad de área en planta.
        superficies_friccion = 1 if self.cpn.con_bloqueo else 2
        presion_friccion = (
            float(self.q.valor) * self.coeficiente_friccion * superficies_friccion
        )
        filas = []
        for entrada in self.cpn.entradas:
            presion = float(self._presion_parcial * entrada.valor)
            filas.append(
                FilaCubiertaAislada(
                    direccion=entrada.direccion,
                    caso=entrada.caso,
                    q=self.q,
                    cpn=entrada.valor,
                    factor_rafaga=factor_rafaga,
                    presion=presion,
                    presion_friccion=presion_friccion,
                    referencia=entrada.referencia,
                    zona=entrada.zona,
                )
            )
        return tuple(filas)

    @classmethod
    def desde_cubierta(
        cls,
        cubierta: geometria.Cubierta,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
        coeficiente_friccion: float = 0.0,
        factor_altitud: float = 1.0,
    ) -> CubiertaAislada:
        """Crea una instancia a partir de la geometria de una cubierta.

        Args:
            cubierta: Una instancia de Cubierta.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            cpn: Una instancia de CubiertaAislada.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            coeficiente_friccion: El coeficiente de empuje por fricción de la superficie, según la Tabla 2.4-1.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        return cls(
            cubierta.altura_media,
            velocidad,
            rafaga,
            factor_topografico,
            cpn,
            categoria_exp,
            coeficiente_friccion,
            factor_altitud=factor_altitud,
        )


class ComponentesCubiertaAislada(PresionesBase):
    """ComponentesCubiertaAislada.

    Determina las presiones de viento sobre componentes y revestimientos de
    una cubierta aislada, Figuras 5.5-1 a 5.5-3 del Reglamento.

    Los coeficientes C_N son presiones netas (contribuciones de las
    superficies superior e inferior), así que no interviene la presión
    interna: la presión de cada fila es p = q_h G C_N, con la presión de
    velocidad calculada a la altura media de la cubierta y el mínimo del
    Art. 5.2.2 aplicado a cada signo.
    """

    def __init__(
        self,
        altura_media: float,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: Sequence[float],
        cpn: cp.ComponentesCubiertaAislada,
        categoria_exp: CategoriaExposicion,
        factor_altitud: float = 1.0,
    ) -> None:
        """
        Args:
            altura_media: La altura media de la cubierta.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cpn: Una instancia de ComponentesCubiertaAislada.
            categoria_exp: La categoría de exposición al viento de la estructura.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        super().__init__(
            altura_media,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
            factor_altitud=factor_altitud,
        )
        self.cpn = cpn
        # La cubierta aislada se resuelve a una sola altura.
        self.q = self.presion_velocidad_en(altura_media)
        self._presion_parcial = self.q.valor * self.rafaga.factor

    @cached_property
    def filas(self) -> tuple[FilaComponentesCubiertaAislada, ...]:
        """Calcula las presiones sobre los componentes.

        Returns:
            Una fila por cada combinación de componente, zona y signo del
            coeficiente, con la presión mínima del Art. 5.2.2 aplicada. Vacía
            si no se cargaron componentes.
        """
        factor_rafaga = float(self.rafaga.factor)
        return tuple(
            FilaComponentesCubiertaAislada(
                componente=entrada.componente,
                zona_componente=entrada.zona_componente,
                tipo_presion=entrada.tipo_presion,
                q=self.q,
                cpn=entrada.valor,
                factor_rafaga=factor_rafaga,
                presion=float(presion_minima(self._presion_parcial * entrada.valor)),
                referencia=entrada.referencia,
                distancia_a=entrada.distancia_a,
            )
            for entrada in self.cpn.entradas
        )
