from __future__ import annotations

from functools import cached_property, partial
from typing import TYPE_CHECKING

import numpy as np

from sse102.enums import CategoriaEstructura, CategoriaExposicion

if TYPE_CHECKING:
    from sse102.cirsoc.factores import Rafaga
    from sse102.tipos import EscalarOArray


class PresionesBase:
    """PresionesBase.

    Clase que contiene métodos comunes para determinar las presiones sobre diferentes tipos de estructuras.
    """

    def __init__(
        self,
        alturas: EscalarOArray,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Rafaga,
        factor_topografico: EscalarOArray,
        factor_direccionalidad: float,
        categoria_exp: CategoriaExposicion,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Una instancia de la clase Ráfaga.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            factor_direccionalidad: El factor de direccionalidad correspondiente para el tipo de estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
        """
        self.alturas = alturas
        self.categoria = categoria
        self.velocidad = velocidad
        self.rafaga = rafaga
        self.factor_topografico = factor_topografico
        self.factor_direccionalidad = factor_direccionalidad
        self.categoria_exp = categoria_exp

    @cached_property
    def factor_importancia(self) -> float:
        """Calcula el factor de importancia de acuerdo a la categoría de la estructura.

        Returns:
            El factor de importancia.
        """
        factores = {
            CategoriaEstructura.I: 0.87,
            CategoriaEstructura.II: 1.0,
            CategoriaEstructura.III: 1.15,
            CategoriaEstructura.IV: 1.15,
        }
        return factores[self.categoria]

    @property
    def coeficientes_exposicion(self) -> EscalarOArray:
        """Calcula el coeficiente de exposición para la presión dinámica, Kz.

        Returns:
            Coeficiente de exposición para la presión dinámica.
        """
        kz_parcial_func = partial(
            self._kz,
            altura_limite=self._altura_limite,
            alfa=self.rafaga.constantes_exp_terreno.alfa,
            zg=self.rafaga.constantes_exp_terreno.zg,
        )
        try:
            zg_iter = (kz_parcial_func(height) for height in self.alturas)
            return np.fromiter(zg_iter, float)
        except TypeError:
            return kz_parcial_func(self.alturas)

    @property
    def presiones_velocidad(self) -> EscalarOArray:
        """Calcula las presiones de velocidad.

        Returns:
            Presiones de velocidad.
        """
        return (
            0.613
            * self.factor_direccionalidad
            * self.coeficientes_exposicion
            * self.factor_topografico
            * self.factor_importancia
            * self.velocidad ** 2
        )

    @cached_property
    def _altura_limite(self):
        return self._calcular_altura_limite(2)

    def _calcular_altura_limite(self, caso: int) -> int:
        """Calcula la altura limite inferior para el "Caso 1" en Kz" """
        if caso == 1:
            if self.categoria_exp == CategoriaExposicion.A:
                return 30
            elif self.categoria_exp == CategoriaExposicion.B:
                return 10
        return 5

    @staticmethod
    def _kz(altura: float, altura_limite: float, alfa: float, zg: float) -> float:
        """

        Args:
            altura: La altura a la que se calcula el coeficiente de
            exposición.
            altura_limite: La altura limite superior en la que el valor empieza a dejar de ser constante
                (Ver tabla en Reglamento)
            alfa: La constante "alfa" de exposición de terreno.
            zg: La constante "zg" de exposición de terreno.

        Returns:
            El coeficiente de exposición.
        """
        return 2.01 * (max(altura, altura_limite) / zg) ** (2 / alfa)
