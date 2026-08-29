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

"""Presiones de viento sobre un edificio.

Cada clase toma los coeficientes de presión que resolvió ``zonda.cirsoc.cp`` y
les agrega la presión de velocidad, el factor de ráfaga y la presión interna que
correspondan a su superficie. El resultado son filas planas: una por cada
coeficiente, salvo en las superficies que se resuelven altura por altura, donde
hay una fila por altura.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import numpy as np

from zonda.cirsoc.presiones.base import PresionesBase
from zonda.cirsoc.resultados import PresionVelocidad
from zonda.enums import (
    Cerramiento,
    DireccionVientoMetodoDireccionalSprfv,
    MetodoSprfv,
    ParedEdificioSprfv,
    TipoCubierta,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc import geometria
    from zonda.cirsoc.cp import edificio as clases_cp_edificio
    from zonda.cirsoc.factores import Rafaga
    from zonda.cirsoc.resultados import EntradaCp, FilaEdificio
    from zonda.enums import (
        CategoriaEstructura,
        CategoriaExposicion,
    )

GCPI_CERRAMIENTO = {
    Cerramiento.CERRADO: 0.18,
    Cerramiento.PARCIALMENTE_CERRADO: 0.55,
    Cerramiento.ABIERTO: 0.0,
}


def presion_minima(presion: float) -> float:
    """Asigna el valor de presion mínima según CIRSOC 102-05 Art. 1.4.

    Args:
        presion: El valor de presión a comparar.

    Returns:
        Maximo entre valor de presión minima y el valor de presión.
    """
    return np.sign(presion) * max(500, abs(presion))


class PresionesEdificioBase(PresionesBase):
    """Comportamiento común a todas las superficies de un edificio.

    Reúne la presión de velocidad a la altura media, la presión de velocidad de
    cada altura, el coeficiente de presión interna y la fórmula que combina todo
    con un coeficiente de presión.
    """

    #: Si la superficie distingue los dos signos de presión interna. El alero es
    #: una superficie abierta y no lo hace.
    con_presion_interna = True

    #: Si corresponde aplicar la presión mínima del Art. 1.4.
    considerar_presion_minima = False

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        cp,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: float | None = None,
        volumen_interno: float | None = None,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: La clase de coeficientes de presión de la superficie.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: El valor total de aberturas del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
        """
        super().__init__(
            alturas,
            categoria,
            velocidad,
            rafaga[DireccionVientoMetodoDireccionalSprfv.PARALELO],
            factor_topografico,
            0.85,
            categoria_exp,
        )
        self.altura_media = altura_media
        self.cerramiento = cerramiento
        self.cp = cp
        self.reducir_gcpi = reducir_gcpi
        self.aberturas_totales = aberturas_totales
        self.volumen_interno = volumen_interno
        self.factores_rafaga = {
            direccion: valor.factor for direccion, valor in rafaga.items()
        }

    @cached_property
    def q_media(self) -> PresionVelocidad:
        """La presión de velocidad a la altura media de cubierta.

        Es la que usan todas las superficies salvo la pared a barlovento, y la
        que interviene en la presión interna.

        Returns:
            La presión de velocidad con los factores que la componen.
        """
        return self.presion_velocidad_en(self.altura_media)

    @cached_property
    def factor_reduccion_gcpi(self) -> float:
        """Calcula el factor de reduccion para el coeficiente de presion interna.

        Returns:
            El factor de reduccion de gcpi.
        """
        # Anidado a proposito: combinar las condiciones da una expresion ilegible.
        if self.reducir_gcpi:  # noqa: SIM102
            if self.cerramiento == Cerramiento.PARCIALMENTE_CERRADO and (
                self.volumen_interno is not None and self.aberturas_totales
            ):  # Las aberturas totales no pueden ser "cero"
                reduccion = 0.5 * (
                    1
                    + 1
                    / (1 + self.volumen_interno / 6950 / self.aberturas_totales) ** 0.5
                )
                return min(reduccion, 1.0)
        return 1.0

    @cached_property
    def gcpi(self) -> float:
        """Calcula el coeficiente de presión interna de acuerdo al cerramiento del edificio.

        Returns:
            El coeficiente de presión interna.
        """
        return GCPI_CERRAMIENTO[self.cerramiento] * self.factor_reduccion_gcpi

    def _fila(
        self, entrada: EntradaCp, q: PresionVelocidad, factor_rafaga: float
    ) -> FilaEdificio:
        """Combina un coeficiente de presión con su presión de velocidad.

        Args:
            entrada: El coeficiente de presión con sus claves.
            q: La presión de velocidad a la que se calcula la fila.
            factor_rafaga: El factor de ráfaga.

        Returns:
            La fila de resultado.
        """
        externa = q.valor * factor_rafaga * entrada.valor
        interna = self.q_media.valor * self.gcpi
        pos, neg = externa - interna, externa + interna
        if self.considerar_presion_minima:
            pos, neg = presion_minima(pos), presion_minima(neg)
        return entrada.fila(
            q=q,
            factor_rafaga=factor_rafaga,
            gcpi=self.gcpi,
            pos=float(pos),
            neg=float(neg),
            con_presion_interna=self.con_presion_interna,
        )


class CubiertaSprfvMetodoDireccional(PresionesEdificioBase):
    """CubiertaSprfvMetodoDireccional.

    Determina las presiones de cubierta para SPRFV usando el método direccional.
    """

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Calcula las presiones de la cubierta.

        Todas se resuelven con la presión de velocidad a la altura media.

        Returns:
            Una fila por cada coeficiente de presión.
        """
        return tuple(
            self._fila(entrada, self.q_media, self.factores_rafaga[entrada.direccion])
            for entrada in self.cp.entradas
        )


class AleroSprfvMetodoDireccional(CubiertaSprfvMetodoDireccional):
    """AleroSprfvMetodoDireccional.

    Determina las presiones del alero para SPRFV usando el método direccional.

    El alero es una superficie abierta: se construye siempre como tal, de modo
    que el coeficiente de presión interna es cero y ambos signos coinciden.
    """

    con_presion_interna = False

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cp,
        categoria_exp: CategoriaExposicion,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cp: La clase de coeficientes de presión del alero.
            categoria_exp: La categoría de exposición al viento de la estructura.
        """
        super().__init__(
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            Cerramiento.ABIERTO,
            cp,
            categoria_exp,
        )


class ParedesSprfvMetodoDireccional(PresionesEdificioBase):
    """ParedesSprfvMetodoDireccional.

    Determina las presiones de paredes para SPRFV usando el método direccional.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        altura_alero: float,
        tipo_cubierta: TipoCubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        cp,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: float | None = None,
        volumen_interno: float | None = None,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: La clase de coeficientes de presión de las paredes.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: El valor total de aberturas del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
        """
        super().__init__(
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp,
            categoria_exp,
            reducir_gcpi,
            aberturas_totales,
            volumen_interno,
        )
        self.altura_alero = altura_alero
        self.tipo_cubierta = tipo_cubierta

    def _q_barlovento(
        self, direccion: DireccionVientoMetodoDireccionalSprfv
    ) -> tuple[PresionVelocidad, ...]:
        """Las presiones de velocidad de la pared a barlovento.

        Con el viento normal a la cumbrera la presión se toma hasta la altura de
        alero, salvo en cubiertas a un agua, donde se toma hasta la cumbrera.

        Args:
            direccion: La dirección del viento.

        Returns:
            Una presión de velocidad por cada altura considerada.
        """
        if (
            direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
            and self.tipo_cubierta != TipoCubierta.UN_AGUA
        ):
            return tuple(
                q for q in self.presiones_velocidad if q.altura <= self.altura_alero
            )
        return self.presiones_velocidad

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Calcula las presiones de las paredes.

        La pared a barlovento recibe la presión de velocidad de cada altura; las
        demás, la de la altura media de cubierta.

        Returns:
            Las filas de todas las paredes.
        """
        filas = []
        for entrada in self.cp.entradas:
            factor_rafaga = self.factores_rafaga[entrada.direccion]
            if entrada.pared == ParedEdificioSprfv.BARLOVENTO:
                filas += [
                    self._fila(entrada, q, factor_rafaga)
                    for q in self._q_barlovento(entrada.direccion)
                ]
            else:
                filas.append(self._fila(entrada, self.q_media, factor_rafaga))
        return tuple(filas)


class ComponentesBase(PresionesEdificioBase):
    """Comportamiento común de componentes y revestimientos.

    El factor de ráfaga no interviene, se aplica la presión mínima del
    Reglamento y el coeficiente de exposición usa la altura límite del "Caso 1".

    Se combina con la clase del SPRFV de cada superficie, que es la que aporta
    el constructor.
    """

    considerar_presion_minima = True

    @cached_property
    def _altura_limite(self):
        return self._calcular_altura_limite(1)

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Calcula las presiones sobre los componentes.

        Returns:
            Una fila por cada coeficiente de presión.
        """
        return tuple(
            self._fila(entrada, self.q_media, 1.0) for entrada in self.cp.entradas
        )


class CubiertaComponentes(ComponentesBase, CubiertaSprfvMetodoDireccional):
    """CubiertaComponentes.

    Determina las presiones para componentes y revestimientos de cubierta.
    """


class AleroComponentes(ComponentesBase, AleroSprfvMetodoDireccional):
    """AleroComponentes.

    Determina las presiones para componentes y revestimientos del alero.
    """


class ParedesComponentes(ComponentesBase, ParedesSprfvMetodoDireccional):
    """ParedesComponentes.

    Determina las presiones para componentes y revestimientos de paredes.

    Con la Figura 8 del Reglamento los coeficientes se discriminan por pared, y
    los de la pared a barlovento se resuelven altura por altura.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Con la Figura 8 el cálculo no aplica la presión mínima del Art. 1.4.
        # Es el único componente que queda afuera y parece un descuido -la rama
        # original llamaba a la fórmula con los argumentos corridos y sin pedir
        # la presión mínima-, pero cambiarlo cambia resultados, así que se
        # mantiene hasta verificarlo contra el Reglamento.
        self.considerar_presion_minima = self.cp.referencia != "Figura 8"

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Calcula las presiones sobre los componentes de las paredes.

        Returns:
            Una fila por cada coeficiente, o una por altura en la pared a
            barlovento cuando la figura del Reglamento la discrimina.
        """
        filas = []
        for entrada in self.cp.entradas:
            if entrada.pared == ParedEdificioSprfv.BARLOVENTO:
                filas += [self._fila(entrada, q, 1.0) for q in self.presiones_velocidad]
            else:
                filas.append(self._fila(entrada, self.q_media, 1.0))
        return tuple(filas)


class Cubierta:
    """Cubierta.

    Determina las presiones de viento sobre una cubierta de edificio para SPRFV y Componentes y Revestimientos.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Cubierta,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: float | None = None,
        volumen_interno: float | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Cubierta.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: El valor total de aberturas del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv != MetodoSprfv.DIRECCIONAL:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        comunes = (
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
        )
        finales = (categoria_exp, reducir_gcpi, aberturas_totales, volumen_interno)
        self.sprfv = CubiertaSprfvMetodoDireccional(*comunes, cp.sprfv, *finales)
        self.componentes = CubiertaComponentes(*comunes, cp.componentes, *finales)

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Las presiones del SPRFV seguidas por las de componentes."""
        return (*self.sprfv.filas, *self.componentes.filas)


class Alero:
    """Alero.

    Determina las presiones de viento sobre un alero de edificio para SPRFV y Componentes y Revestimientos.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cp: clases_cp_edificio.Alero,
        categoria_exp: CategoriaExposicion,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cp: Un instancia de Alero.
            categoria_exp: La categoría de exposición al viento de la estructura.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv != MetodoSprfv.DIRECCIONAL:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        comunes = (
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
        )
        self.sprfv = AleroSprfvMetodoDireccional(*comunes, cp.sprfv, categoria_exp)
        self.componentes = AleroComponentes(*comunes, cp.componentes, categoria_exp)

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Las presiones del SPRFV seguidas por las de componentes."""
        return (*self.sprfv.filas, *self.componentes.filas)


class Paredes:
    """Paredes.

    Determina las presiones de viento sobre las paredes de edificio para SPRFV y Componentes y Revestimientos.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        altura_alero: float,
        tipo_cubierta: TipoCubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Paredes,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: float | None = None,
        volumen_interno: float | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Paredes.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: El valor total de aberturas del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv != MetodoSprfv.DIRECCIONAL:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        comunes = (
            alturas,
            altura_media,
            altura_alero,
            tipo_cubierta,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
        )
        finales = (categoria_exp, reducir_gcpi, aberturas_totales, volumen_interno)
        self.sprfv = ParedesSprfvMetodoDireccional(*comunes, cp.sprfv, *finales)
        self.componentes = ParedesComponentes(*comunes, cp.componentes, *finales)

    @cached_property
    def filas(self) -> tuple[FilaEdificio, ...]:
        """Las presiones del SPRFV seguidas por las de componentes."""
        return (*self.sprfv.filas, *self.componentes.filas)


class Edificio:
    """Edificio.

    Determina las presiones de viento sobre un edificio para SPRFV y Componentes y Revestimientos.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        altura_alero: float,
        tipo_cubierta: TipoCubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Edificio,
        categoria_exp: CategoriaExposicion,
        alero: float = 0,
        reducir_gcpi: bool = False,
        aberturas_totales: float | None = None,
        volumen_interno: float | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ):
        """

        Args:
            alturas: Las alturas de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Edificio.
            categoria_exp: La categoría de exposición al viento de la estructura.
            alero: La dimensión del alero.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: El valor total de aberturas del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        self.cubierta = Cubierta(
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp.cubierta,
            categoria_exp,
            reducir_gcpi,
            aberturas_totales,
            volumen_interno,
            metodo_sprfv,
        )
        self.paredes = Paredes(
            alturas,
            altura_media,
            altura_alero,
            tipo_cubierta,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp.paredes,
            categoria_exp,
            reducir_gcpi,
            aberturas_totales,
            volumen_interno,
            metodo_sprfv,
        )
        if alero:
            self.alero = Alero(
                alturas,
                altura_media,
                categoria,
                velocidad,
                rafaga,
                factor_topografico,
                cp.alero,
                categoria_exp,
                metodo_sprfv,
            )

    @cached_property
    def filas_sprfv(self) -> tuple[FilaEdificio, ...]:
        """Las presiones del sistema principal resistente a la fuerza del viento.

        Returns:
            Las filas de paredes, cubierta y alero.
        """
        filas = (*self.paredes.sprfv.filas, *self.cubierta.sprfv.filas)
        alero: Alero | None = getattr(self, "alero", None)
        if alero is not None:
            filas += alero.sprfv.filas
        return filas

    @cached_property
    def filas_componentes(self) -> tuple[FilaEdificio, ...]:
        """Las presiones sobre componentes y revestimientos.

        Returns:
            Las filas de paredes, cubierta y alero.

        Raises:
            ErrorLineamientos: Cuando la geometría excede el alcance del
                Reglamento para componentes y revestimientos.
        """
        filas = (*self.paredes.componentes.filas, *self.cubierta.componentes.filas)
        alero: Alero | None = getattr(self, "alero", None)
        if alero is not None:
            filas += alero.componentes.filas
        return filas

    @classmethod
    def desde_edificio(
        cls,
        edificio: geometria.Edificio,
        cp: clases_cp_edificio.Edificio,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: Sequence[float],
        cerramiento: Cerramiento,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> Edificio:
        """Crea una instancia desde la geometria de un edificio.

        Args:
            edificio: Una instancia de Edificio.
            cp: Un instancia de Edificio.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: Los factores topográficos correspondientes a las alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        return cls(
            edificio.alturas,
            edificio.cubierta.altura_media,
            edificio.cubierta.altura_alero,
            edificio.tipo_cubierta,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp,
            categoria_exp,
            edificio.cubierta.alero,
            reducir_gcpi,
            edificio.abertura_total,
            edificio.volumen_interno,
            metodo_sprfv,
        )
