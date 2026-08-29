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

"""Modelo tabular de resultados.

El núcleo calcula sus valores en estructuras anidadas cuya forma refleja las
condicionales del Reglamento: un diccionario por dirección de viento, otro por
posición de cubierta, un array cuando la superficie se divide en zonas y un
escalar cuando no. Cada consumidor -el reporte, la vista 3D, las tablas de la
interfaz- terminaba recorriendo ese árbol y repitiendo las mismas condicionales.

Este módulo lo proyecta a una tabla plana. Cada fila se identifica por sus
claves (dirección, pared, zona, componente, ...) y lleva todos los números que
hacen falta para dibujar una línea de tabla o pintar un actor. Los consumidores
filtran y agrupan en vez de navegar.

Las filas no recalculan nada: leen los valores que ya produjeron las clases de
``zonda.cirsoc.presiones``, así que los números son por construcción los mismos
que devolvía el árbol anidado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    ExtremoPresion,
    ParedEdificioSprfv,
    SistemaResistente,
    TipoPresionCubiertaAislada,
    ZonaComponenteCubiertaEdificio,
    ZonaComponenteParedEdificio,
    ZonaEdificio,
    ZonaPresionCubiertaAislada,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from zonda.enums import (
        PosicionCubiertaAleroSprfv,
        TipoPresionCubiertaBarloventoSprfv,
    )


@dataclass(frozen=True, slots=True)
class PresionVelocidad:
    """La presión dinámica a una altura, junto con los factores que la componen.

    Reemplaza a los tres arrays paralelos (alturas, coeficientes de exposición,
    factores topográficos) que había que indexar en conjunto para armar una
    línea de tabla.
    """

    altura: float
    kz: float
    kzt: float
    valor: float
    ke: float = 1.0


@dataclass(frozen=True, slots=True)
class FilaEdificio:
    """Una línea de resultado de edificio.

    Los campos opcionales son las claves que no aplican a la fila: una pared a
    sotavento no tiene rango de zona, una zona de cubierta no tiene componente.
    """

    zona: ZonaEdificio
    sistema: SistemaResistente
    q: PresionVelocidad
    cp: float
    factor_rafaga: float
    gcpi: float
    pos: float
    neg: float
    referencia: str
    con_presion_interna: bool = True
    direccion: DireccionVientoMetodoDireccionalSprfv | None = None
    pared: ParedEdificioSprfv | None = None
    posicion: PosicionCubiertaAleroSprfv | None = None
    caso: TipoPresionCubiertaBarloventoSprfv | None = None
    componente: str | None = None
    zona_componente: (
        ZonaComponenteParedEdificio | ZonaComponenteCubiertaEdificio | None
    ) = None
    rango: tuple[float, float] | None = None
    distancia_a: float | None = None

    @property
    def presiones(self) -> tuple[float, ...]:
        """Los valores de presión de la fila, para escalas de color y extremos."""
        if self.con_presion_interna:
            return (self.pos, self.neg)
        return (self.pos,)

    def presion(self, indice_gcpi: int = 0) -> float:
        """La presión para el signo de presión interna pedido.

        Args:
            indice_gcpi: 0 para presión interna positiva, 1 para negativa.

        Returns:
            La presión. En las superficies sin presión interna, como el alero,
            ambas coinciden.
        """
        return self.neg if indice_gcpi else self.pos


@dataclass(frozen=True, slots=True)
class EntradaCp:
    """Un coeficiente de presión junto con las claves que lo identifican.

    Es lo que produce ``zonda.cirsoc.cp``: la selección de figuras y tablas del
    Reglamento, ya resuelta, en la misma forma plana que el resultado final.
    ``zonda.cirsoc.presiones`` le agrega los números y devuelve una `FilaEdificio`.
    """

    zona: ZonaEdificio
    sistema: SistemaResistente
    valor: float
    referencia: str
    direccion: DireccionVientoMetodoDireccionalSprfv | None = None
    pared: ParedEdificioSprfv | None = None
    posicion: PosicionCubiertaAleroSprfv | None = None
    caso: TipoPresionCubiertaBarloventoSprfv | None = None
    componente: str | None = None
    zona_componente: (
        ZonaComponenteParedEdificio | ZonaComponenteCubiertaEdificio | None
    ) = None
    rango: tuple[float, float] | None = None
    distancia_a: float | None = None

    def fila(
        self,
        *,
        q: PresionVelocidad,
        factor_rafaga: float,
        gcpi: float,
        pos: float,
        neg: float,
        con_presion_interna: bool = True,
    ) -> FilaEdificio:
        """Combina el coeficiente con los números de presión.

        Args:
            q: La presión de velocidad con la que se calculó la fila.
            factor_rafaga: El factor de ráfaga aplicado.
            gcpi: El coeficiente de presión interna aplicado.
            pos: La presión con presión interna positiva.
            neg: La presión con presión interna negativa.
            con_presion_interna: Si la fila distingue ambos signos de presión
                interna. El alero es una superficie abierta y no lo hace.

        Returns:
            La fila de resultado.
        """
        return FilaEdificio(
            zona=self.zona,
            sistema=self.sistema,
            q=q,
            cp=self.valor,
            factor_rafaga=factor_rafaga,
            gcpi=gcpi,
            pos=pos,
            neg=neg,
            referencia=self.referencia,
            con_presion_interna=con_presion_interna,
            direccion=self.direccion,
            pared=self.pared,
            posicion=self.posicion,
            caso=self.caso,
            componente=self.componente,
            zona_componente=self.zona_componente,
            rango=self.rango,
            distancia_a=self.distancia_a,
        )


@dataclass(frozen=True, slots=True)
class EntradaCpn:
    """Un coeficiente de presión neta de cubierta aislada, con sus claves."""

    tipo: TipoPresionCubiertaAislada
    extremo: ExtremoPresion
    valor: float
    referencia: str
    zona: ZonaPresionCubiertaAislada | None = None


@dataclass(frozen=True, slots=True)
class FilaCartel:
    """Una línea de resultado de cartel: una altura del cartel."""

    q: PresionVelocidad
    cf: float
    factor_rafaga: float
    presion: float
    referencia: str
    area_parcial: float | None = None
    fuerza: float | None = None

    @property
    def presiones(self) -> tuple[float, ...]:
        return (self.presion,)


@dataclass(frozen=True, slots=True)
class FilaCubiertaAislada:
    """Una línea de resultado de cubierta aislada."""

    tipo: TipoPresionCubiertaAislada
    extremo: ExtremoPresion
    q: PresionVelocidad
    cpn: float
    factor_rafaga: float
    presion: float
    presion_friccion: float
    referencia: str
    zona: ZonaPresionCubiertaAislada | None = None

    @property
    def presiones(self) -> tuple[float, ...]:
        return (self.presion,)


class Tabla[F]:
    """Una colección inmutable de filas de resultado.

    Es la única forma en que el núcleo publica sus valores. En vez de navegar
    un árbol, los consumidores filtran por las claves que les interesan y
    agrupan por las que encabezan cada tabla o cada actor.
    """

    __slots__ = ("_filas",)

    def __init__(self, filas: Iterable[F] = ()) -> None:
        self._filas: tuple[F, ...] = tuple(filas)

    @property
    def filas(self) -> tuple[F, ...]:
        return self._filas

    def __iter__(self) -> Iterator[F]:
        return iter(self._filas)

    def __len__(self) -> int:
        return len(self._filas)

    def __bool__(self) -> bool:
        return bool(self._filas)

    def __getitem__(self, indice: int) -> F:
        return self._filas[indice]

    def __add__(self, otra: Tabla[F]) -> Tabla[F]:
        return Tabla((*self._filas, *otra))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({len(self._filas)} filas)"

    def filtrar(self, **criterios: Any) -> Tabla[F]:
        """Las filas que cumplen todos los criterios.

        Cada criterio es ``campo=valor``. Si el valor es un ``set`` o una
        ``list``, la fila pasa cuando su campo es alguno de los elementos.

        Args:
            **criterios: Los campos a comparar y sus valores esperados.

        Returns:
            Una tabla nueva con las filas que coinciden.
        """

        def coincide(fila: F) -> bool:
            for campo, esperado in criterios.items():
                valor = getattr(fila, campo)
                if isinstance(esperado, (set, frozenset, list)):
                    if valor not in esperado:
                        return False
                elif valor != esperado:
                    return False
            return True

        return Tabla(fila for fila in self._filas if coincide(fila))

    def agrupar(self, *campos: str) -> tuple[tuple[Any, Tabla[F]], ...]:
        """Agrupa las filas por los campos indicados, en orden de aparición.

        Args:
            *campos: Los campos que forman la clave de cada grupo.

        Returns:
            Pares de clave y tabla. Con un solo campo la clave es su valor; con
            varios, la tupla de valores.
        """
        grupos: dict[tuple, list[F]] = {}
        for fila in self._filas:
            clave = tuple(getattr(fila, campo) for campo in campos)
            grupos.setdefault(clave, []).append(fila)
        if len(campos) == 1:
            return tuple((clave[0], Tabla(filas)) for clave, filas in grupos.items())
        return tuple((clave, Tabla(filas)) for clave, filas in grupos.items())

    def indexar(self, *campos: str) -> dict[Any, Tabla[F]]:
        """Un diccionario de clave a filas, para búsquedas directas.

        Es la forma en que la vista 3D encuentra la presión de un actor sin
        recorrer nada.

        Args:
            *campos: Los campos que forman la clave.

        Returns:
            La clave de cada grupo apuntando a sus filas.
        """
        return dict(self.agrupar(*campos))

    def valores(self, campo: str) -> tuple[Any, ...]:
        """Los valores distintos de un campo, en orden de aparición.

        Args:
            campo: El nombre del campo.

        Returns:
            Los valores sin repetir.
        """
        return tuple(dict.fromkeys(getattr(fila, campo) for fila in self._filas))

    def min_max(self) -> tuple[float, float]:
        """El mínimo y el máximo de todas las presiones de la tabla.

        Returns:
            El valor mínimo y el máximo.

        Raises:
            ValueError: Cuando la tabla está vacía.
        """
        valores = [p for fila in self._filas for p in fila.presiones]  # type: ignore[attr-defined]
        if not valores:
            raise ValueError("La tabla no tiene filas.")
        return min(valores), max(valores)

    def unica(self) -> F:
        """La única fila de la tabla.

        Returns:
            La fila.

        Raises:
            ValueError: Cuando la tabla no tiene exactamente una fila.
        """
        if len(self._filas) != 1:
            raise ValueError(f"Se esperaba una sola fila, hay {len(self._filas)}.")
        return self._filas[0]
