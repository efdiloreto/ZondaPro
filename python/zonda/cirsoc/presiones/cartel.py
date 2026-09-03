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
from zonda.cirsoc.resultados import FilaCartel
from zonda.enums import CasoCartel

if TYPE_CHECKING:
    from zonda.cirsoc import cp, geometria
    from zonda.cirsoc.factores import Rafaga
    from zonda.enums import CategoriaExposicion, RegionCartel


class Cartel(PresionesBase):
    """Cartel.

    Determina las presiones de viento sobre un cartel de acuerdo a la
    Ec. 4.4-1: F = qh·G·Cf·As, con qh evaluada a la altura h de la Figura 4.4-1.
    """

    def __init__(
        self,
        altura: float,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: float,
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
        area: float,
        areas_regiones: dict[RegionCartel, float],
        factor_altitud: float = 1.0,
    ) -> None:
        """

        Args:
            altura: La altura h a la que se evalúa la presión dinámica: la punta
                del cartel según la Figura 4.4-1.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de Rafaga.
            factor_topografico: El factor topográfico correspondiente a la altura.
            cf: Una instancia de Cartel de cp, con los coeficientes de fuerza.
            categoria_exp: La categoría de exposición.
            area: El área total de la superficie del cartel.
            areas_regiones: El área de cada región del Caso C. Vacío cuando el
                Caso C no aplica.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        super().__init__(
            altura,
            velocidad,
            rafaga,
            factor_topografico,
            0.85,
            categoria_exp,
            factor_altitud=factor_altitud,
        )
        self.cf = cf
        self.area = area
        self.areas_regiones = areas_regiones
        self.factor_rafaga = rafaga.factor

    @cached_property
    def filas(self) -> tuple[FilaCartel, ...]:
        """Calcula las filas de resultado del cartel.

        Returns:
            Una fila para el Caso A, otra para el Caso B con su excentricidad
            y, si B/s ≥ 2, una por cada región del Caso C.
        """
        q = self.presiones_velocidad[0]
        referencia = self.cf.referencia
        factor_rafaga = float(self.factor_rafaga)

        def crear(
            caso: CasoCartel,
            cf: float,
            area: float,
            region: RegionCartel | None = None,
            excentricidad: float | None = None,
        ) -> FilaCartel:
            presion = q.valor * factor_rafaga * float(cf)
            return FilaCartel(
                q=q,
                caso=caso,
                cf=float(cf),
                factor_rafaga=factor_rafaga,
                presion=presion,
                referencia=referencia,
                area=area,
                fuerza=presion * area,
                region=region,
                excentricidad=excentricidad,
            )

        filas = [
            crear(CasoCartel.CASO_A, self.cf.cf_casos_ab, self.area),
            crear(
                CasoCartel.CASO_B,
                self.cf.cf_casos_ab,
                self.area,
                excentricidad=float(self.cf.excentricidad),
            ),
        ]
        filas.extend(
            crear(
                CasoCartel.CASO_C,
                self.cf.cf_por_region[region],
                area,
                region=region,
            )
            for region, area in self.areas_regiones.items()
        )
        return tuple(filas)

    @cached_property
    def fuerzas_totales(self) -> dict[CasoCartel, float]:
        """La fuerza total de cada caso.

        Returns:
            Cada caso con la suma de las fuerzas de sus filas.
        """
        totales: dict[CasoCartel, float] = {}
        for fila in self.filas:
            totales[fila.caso] = totales.get(fila.caso, 0.0) + fila.fuerza
        return totales

    @classmethod
    def desde_cartel(
        cls,
        cartel: geometria.Cartel,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: float,
        cf: cp.Cartel,
        categoria_exp: CategoriaExposicion,
        factor_altitud: float = 1.0,
    ) -> Cartel:
        """Crea una instancia a partir de la geometria de un Cartel.

        Args:
            cartel: Una instancia de Cartel.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de Rafaga.
            factor_topografico: El factor topográfico correspondiente a la altura.
            cf: Una instancia de Cartel de cp.
            categoria_exp: La categoría de exposición.
            factor_altitud: El factor de altitud del terreno Ke.
        """
        areas_regiones = {
            region: (fin - inicio) * cartel.altura_neta
            for region, (inicio, fin) in cf.limites_regiones.items()
        }
        return cls(
            cartel.altura_superior,
            velocidad,
            rafaga,
            factor_topografico,
            cf,
            categoria_exp,
            cartel.area,
            areas_regiones,
            factor_altitud=factor_altitud,
        )
