from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from sse102.cirsoc.presiones.base import PresionesBase

if TYPE_CHECKING:
    from sse102.enums import (
        CategoriaEstructura,
        CategoriaExposicion,
    )
    from sse102.cirsoc.factores import Rafaga
    from sse102.cirsoc import cp
    from sse102.cirsoc import geometria
    from sse102.tipos import ValoresPresionesCubiertaAislada


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
        factor_topografico: float,
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
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
        self._presion_parcial = self.presiones_velocidad * self.rafaga.factor

    @cached_property
    def valores(self) -> ValoresPresionesCubiertaAislada:
        """Calcula los valores de presión sobre la cubierta aislada para cada zona.

        Returns:
            Los valores de presión.
        """
        valores_cpn = self.cpn()
        valores = defaultdict(lambda: defaultdict(dict))
        for caso, zonas in valores_cpn.items():
            for zona, cpn in zonas.items():
                if isinstance(cpn, dict):
                    for tipo, valor_cpn in cpn.items():
                        valores[caso][zona][tipo] = self._presion_parcial * valor_cpn
                else:
                    valores[caso][zona] = self._presion_parcial * cpn
        return valores

    @classmethod
    def desde_cubierta(
        cls,
        cubierta: geometria.Cubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: float,
        cpn: cp.CubiertaAislada,
        categoria_exp: CategoriaExposicion,
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
        """
        return cls(
            cubierta.altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cpn,
            categoria_exp,
        )

    def __call__(self) -> ValoresPresionesCubiertaAislada:
        return self.valores
