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

import numpy as np

from zonda.cirsoc.presiones.edificio import PresionesEdificio
from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    ExtremoPresion,
    ParedEdificioSprfv,
    SistemaResistente,
    TipoCubierta,
    TipoPresionCubiertaAislada,
    ZonaEdificio,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from zonda.enums import (
        PosicionCubiertaAleroSprfv,
        TipoPresionCubiertaBarloventoSprfv,
        ZonaComponenteCubiertaEdificio,
        ZonaComponenteParedEdificio,
        ZonaPresionCubiertaAislada,
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


def _q_media(presiones: Any, altura_media: float) -> PresionVelocidad:
    """La presión de velocidad a la altura media de cubierta.

    Args:
        presiones: Una instancia de presiones de edificio.
        altura_media: La altura media de cubierta.

    Returns:
        La presión de velocidad con sus factores.
    """
    return PresionVelocidad(
        altura_media,
        float(presiones.coeficiente_exposicion_media),
        float(presiones.factor_topografico_media),
        float(presiones.presion_velocidad_media),
    )


def _q_por_altura(
    alturas: Sequence[float],
    kz: Sequence[float],
    kzt: Sequence[float],
    valores: Sequence[float],
) -> tuple[PresionVelocidad, ...]:
    """Arma una presión de velocidad por cada altura.

    Args:
        alturas: Las alturas.
        kz: Los coeficientes de exposición.
        kzt: Los factores topográficos.
        valores: Las presiones de velocidad.

    Returns:
        Una presión de velocidad por altura.
    """
    return tuple(
        PresionVelocidad(float(a), float(k), float(t), float(v))
        for a, k, t, v in zip(alturas, kz, kzt, valores, strict=True)
    )


def _q_barlovento(
    edificio: Any,
    presiones: Any,
    direccion: DireccionVientoMetodoDireccionalSprfv,
) -> tuple[PresionVelocidad, ...]:
    """Las presiones de velocidad de la pared a barlovento.

    Con el viento normal a la cumbrera la presión se toma hasta la altura de
    alero, salvo en cubiertas a un agua, donde se toma hasta la cumbrera.

    Args:
        edificio: La fachada de cálculo del edificio.
        presiones: Las presiones de paredes para el SPRFV.
        direccion: La dirección del viento.

    Returns:
        Una presión de velocidad por cada altura considerada.
    """
    geometria = edificio.geometria
    if (
        direccion is DireccionVientoMetodoDireccionalSprfv.NORMAL
        and geometria.tipo_cubierta is not TipoCubierta.UN_AGUA
    ):
        return _q_por_altura(
            geometria.alturas_alero,
            presiones.coeficientes_exposicion_alero,
            presiones.factor_topografico_alero,
            presiones.presion_velocidad_alero,
        )
    return _q_por_altura(
        presiones.alturas,
        presiones.coeficientes_exposicion,
        presiones.factor_topografico,
        presiones.presiones_velocidad,
    )


def _filas_paredes_sprfv(edificio: Any) -> list[FilaEdificio]:
    """Las filas de paredes para el SPRFV.

    Args:
        edificio: La fachada de cálculo del edificio.

    Returns:
        Una fila por altura en la pared a barlovento y una por cada otra pared.
    """
    presiones = edificio.presiones.paredes.sprfv
    cp_paredes = edificio.cp.paredes.sprfv
    valores_cp = cp_paredes()
    valores = presiones()
    q_media = _q_media(presiones, edificio.geometria.cubierta.altura_media)
    filas: list[FilaEdificio] = []
    for direccion, cps in valores_cp.items():
        factor_rafaga = float(presiones.factores_rafaga[direccion])
        for pared, cp in cps.items():
            presion = valores[direccion][pared]
            comunes = {
                "zona": ZonaEdificio.PAREDES,
                "sistema": SistemaResistente.SPRFV,
                "cp": float(cp),
                "factor_rafaga": factor_rafaga,
                "gcpi": float(presiones.gcpi),
                "referencia": cp_paredes.referencia,
                "direccion": direccion,
                "pared": pared,
            }
            if pared is ParedEdificioSprfv.BARLOVENTO:
                for i, q in enumerate(_q_barlovento(edificio, presiones, direccion)):
                    filas.append(
                        FilaEdificio(
                            q=q,
                            pos=float(presion.pos[i]),
                            neg=float(presion.neg[i]),
                            **comunes,
                        )
                    )
            else:
                filas.append(
                    FilaEdificio(
                        q=q_media,
                        pos=float(presion.pos),
                        neg=float(presion.neg),
                        **comunes,
                    )
                )
    return filas


def _filas_cubierta_sprfv(
    edificio: Any, zona: ZonaEdificio = ZonaEdificio.CUBIERTA
) -> list[FilaEdificio]:
    """Las filas de cubierta o de alero para el SPRFV.

    La cubierta se divide en zonas cuando el viento actúa paralelo a la
    cumbrera, o normal con un ángulo menor que 10°; en el resto de los casos se
    resuelve por posición respecto al viento, y a barlovento con dos casos de
    presión. Acá esas tres formas se emiten como filas con distintas claves.

    Args:
        edificio: La fachada de cálculo del edificio.
        zona: Si se procesa la cubierta o el alero.

    Returns:
        Las filas correspondientes.
    """
    es_alero = zona is ZonaEdificio.ALERO
    grupo = edificio.presiones.alero if es_alero else edificio.presiones.cubierta
    grupo_cp = edificio.cp.alero if es_alero else edificio.cp.cubierta
    presiones = grupo.sprfv
    cp_cubierta = grupo_cp.sprfv
    valores_cp = cp_cubierta()
    valores = presiones()
    q_media = _q_media(presiones, edificio.geometria.cubierta.altura_media)
    comunes = {
        "zona": zona,
        "sistema": SistemaResistente.SPRFV,
        "q": q_media,
        "gcpi": float(presiones.gcpi),
        "referencia": cp_cubierta.referencia,
        "con_presion_interna": not es_alero,
    }
    filas: list[FilaEdificio] = []
    for direccion, cps in valores_cp.items():
        factor_rafaga = float(presiones.factores_rafaga[direccion])
        presion_direccion = valores[direccion]
        if isinstance(cps, np.ndarray):
            # La superficie está dividida en zonas: una fila por zona.
            zonas = cp_cubierta.zonas[direccion]
            presiones_zonas = _desdoblar(presion_direccion)
            for rango, cp, (pos, neg) in zip(zonas, cps, presiones_zonas, strict=True):
                filas.append(
                    FilaEdificio(
                        cp=float(cp),
                        factor_rafaga=factor_rafaga,
                        pos=pos,
                        neg=neg,
                        direccion=direccion,
                        rango=(float(rango[0]), float(rango[1])),
                        **comunes,
                    )
                )
            continue
        for posicion, cp in cps.items():
            if isinstance(cp, dict):
                # Cubierta a barlovento con ángulo >= 10°: dos casos de presión.
                for caso, valor_cp in cp.items():
                    pos, neg = _par_presiones(presion_direccion[posicion][caso])
                    filas.append(
                        FilaEdificio(
                            cp=float(valor_cp),
                            factor_rafaga=factor_rafaga,
                            pos=pos,
                            neg=neg,
                            direccion=direccion,
                            posicion=posicion,
                            caso=caso,
                            **comunes,
                        )
                    )
                continue
            pos, neg = _par_presiones(presion_direccion[posicion])
            filas.append(
                FilaEdificio(
                    cp=float(cp),
                    factor_rafaga=factor_rafaga,
                    pos=pos,
                    neg=neg,
                    direccion=direccion,
                    posicion=posicion,
                    **comunes,
                )
            )
    return filas


def _par_presiones(presion: Any) -> tuple[float, float]:
    """Separa una presión en sus valores para presión interna positiva y negativa.

    El alero es una superficie abierta y su presión es un único valor; el resto
    de las superficies llegan como un par.

    Args:
        presion: Un par de presiones o un valor único.

    Returns:
        Las presiones positiva y negativa.
    """
    if isinstance(presion, PresionesEdificio):
        return float(presion.pos), float(presion.neg)
    return float(presion), float(presion)


def _desdoblar(presion: Any) -> tuple[tuple[float, float], ...]:
    """Convierte las presiones de una superficie zonificada en un par por zona.

    Args:
        presion: Un par de arrays, o un array cuando no hay presión interna.

    Returns:
        Un par de presiones por cada zona.
    """
    if isinstance(presion, PresionesEdificio):
        # ``PresionesEdificio`` está declarada con escalares, pero cuando la
        # superficie se divide en zonas sus campos son arrays.
        pos: Any = presion.pos
        neg: Any = presion.neg
        return tuple(
            (float(valor_pos), float(valor_neg))
            for valor_pos, valor_neg in zip(pos, neg, strict=True)
        )
    return tuple((float(valor), float(valor)) for valor in presion)


def _filas_paredes_componentes(edificio: Any) -> list[FilaEdificio]:
    """Las filas de componentes y revestimientos de paredes.

    Con la Figura 8 del Reglamento los valores dependen además de la pared, y
    los de la pared a barlovento varían con la altura.

    Args:
        edificio: La fachada de cálculo del edificio.

    Returns:
        Las filas de componentes de paredes, o ninguna si no se cargaron.
    """
    presiones = edificio.presiones.paredes.componentes
    cp_paredes = edificio.cp.paredes.componentes
    valores_cp = cp_paredes()
    if valores_cp is None:
        return []
    valores = presiones()
    comunes = {
        "zona": ZonaEdificio.PAREDES,
        "sistema": SistemaResistente.COMPONENTES,
        "factor_rafaga": 1.0,
        "gcpi": float(presiones.gcpi),
        "referencia": cp_paredes.referencia,
        "distancia_a": float(cp_paredes.distancia_a),
    }
    q_media = _q_media(presiones, edificio.geometria.cubierta.altura_media)
    filas: list[FilaEdificio] = []
    if cp_paredes.referencia != "Figura 8":
        for nombre, zonas in valores.items():
            for zona_componente, presion in zonas.items():
                filas.append(
                    FilaEdificio(
                        q=q_media,
                        cp=float(valores_cp[nombre][zona_componente]),
                        pos=float(presion.pos),
                        neg=float(presion.neg),
                        componente=nombre,
                        zona_componente=zona_componente,
                        **comunes,
                    )
                )
        return filas
    q_alturas = _q_por_altura(
        presiones.alturas,
        presiones.coeficientes_exposicion,
        presiones.factor_topografico,
        presiones.presiones_velocidad,
    )
    for pared, componentes in valores.items():
        for nombre, zonas in componentes.items():
            for zona_componente, presion in zonas.items():
                cp = float(valores_cp[nombre][zona_componente])
                if pared is ParedEdificioSprfv.BARLOVENTO:
                    for i, q in enumerate(q_alturas):
                        filas.append(
                            FilaEdificio(
                                q=q,
                                cp=cp,
                                pos=float(presion.pos[i]),
                                neg=float(presion.neg[i]),
                                pared=pared,
                                componente=nombre,
                                zona_componente=zona_componente,
                                **comunes,
                            )
                        )
                else:
                    filas.append(
                        FilaEdificio(
                            q=q_media,
                            cp=cp,
                            pos=float(presion.pos),
                            neg=float(presion.neg),
                            pared=pared,
                            componente=nombre,
                            zona_componente=zona_componente,
                            **comunes,
                        )
                    )
    return filas


def _filas_cubierta_componentes(
    edificio: Any, zona: ZonaEdificio = ZonaEdificio.CUBIERTA
) -> list[FilaEdificio]:
    """Las filas de componentes y revestimientos de cubierta o de alero.

    Args:
        edificio: La fachada de cálculo del edificio.
        zona: Si se procesa la cubierta o el alero.

    Returns:
        Las filas correspondientes, o ninguna si no se cargaron componentes.
    """
    es_alero = zona is ZonaEdificio.ALERO
    grupo = edificio.presiones.alero if es_alero else edificio.presiones.cubierta
    grupo_cp = edificio.cp.alero if es_alero else edificio.cp.cubierta
    presiones = grupo.componentes
    cp_cubierta = grupo_cp.componentes
    valores_cp = cp_cubierta()
    if valores_cp is None:
        return []
    valores = presiones()
    q_media = _q_media(presiones, edificio.geometria.cubierta.altura_media)
    comunes = {
        "zona": zona,
        "sistema": SistemaResistente.COMPONENTES,
        "q": q_media,
        "factor_rafaga": 1.0,
        "gcpi": float(presiones.gcpi),
        "referencia": cp_cubierta.referencia,
        "distancia_a": float(cp_cubierta.distancia_a),
        "con_presion_interna": not es_alero,
    }
    filas: list[FilaEdificio] = []
    for nombre, zonas in valores.items():
        for zona_componente, presion in zonas.items():
            pos, neg = _par_presiones(presion)
            filas.append(
                FilaEdificio(
                    cp=float(valores_cp[nombre][zona_componente]),
                    pos=pos,
                    neg=neg,
                    componente=nombre,
                    zona_componente=zona_componente,
                    **comunes,
                )
            )
    return filas


def tabla_edificio_sprfv(edificio: Any) -> Tabla[FilaEdificio]:
    """Arma la tabla de resultados del SPRFV de un edificio.

    Args:
        edificio: La fachada de cálculo del edificio.

    Returns:
        Las filas de paredes, cubierta y alero.
    """
    filas = _filas_paredes_sprfv(edificio) + _filas_cubierta_sprfv(edificio)
    if hasattr(edificio.presiones, "alero"):
        filas += _filas_cubierta_sprfv(edificio, ZonaEdificio.ALERO)
    return Tabla(filas)


def tabla_edificio_componentes(edificio: Any) -> Tabla[FilaEdificio]:
    """Arma la tabla de resultados de componentes y revestimientos de un edificio.

    Args:
        edificio: La fachada de cálculo del edificio.

    Returns:
        Las filas de paredes, cubierta y alero.

    Raises:
        ErrorLineamientos: Cuando la geometría excede el alcance del Reglamento
            para componentes y revestimientos.
    """
    filas = _filas_paredes_componentes(edificio) + _filas_cubierta_componentes(edificio)
    if hasattr(edificio.presiones, "alero"):
        filas += _filas_cubierta_componentes(edificio, ZonaEdificio.ALERO)
    return Tabla(filas)


def tabla_cartel(cartel: Any) -> Tabla[FilaCartel]:
    """Arma la tabla de resultados de un cartel.

    Args:
        cartel: La fachada de cálculo del cartel.

    Returns:
        Una fila por cada altura. El área parcial y la fuerza corresponden al
        tramo que va desde la altura anterior, así que la primera fila no las
        tiene.
    """
    presiones = cartel.presiones
    q_alturas = _q_por_altura(
        cartel.geometria.alturas,
        presiones.coeficientes_exposicion,
        presiones.factor_topografico,
        presiones.presiones_velocidad,
    )
    valores = presiones()
    areas = cartel.geometria.areas_parciales
    fuerzas = presiones.fuerzas_parciales
    cf = float(cartel.cf())
    factor_rafaga = float(presiones.factor_rafaga)
    filas = []
    for i, q in enumerate(q_alturas):
        filas.append(
            FilaCartel(
                q=q,
                cf=cf,
                factor_rafaga=factor_rafaga,
                presion=float(valores[i]),
                referencia="Tabla 11",
                area_parcial=None if i == 0 else float(areas[i - 1]),
                fuerza=None if i == 0 else float(fuerzas[i - 1]),
            )
        )
    return Tabla(filas)


def tabla_cubierta_aislada(cubierta: Any) -> Tabla[FilaCubiertaAislada]:
    """Arma la tabla de resultados de una cubierta aislada.

    Args:
        cubierta: La fachada de cálculo de la cubierta aislada.

    Returns:
        Una fila por cada combinación de tipo de presión, zona y extremo.
    """
    presiones = cubierta.presiones
    q = PresionVelocidad(
        float(cubierta.geometria.altura_media),
        float(presiones.coeficientes_exposicion),
        float(presiones.factor_topografico),
        float(presiones.presiones_velocidad),
    )
    factor_rafaga = float(presiones.rafaga.factor)
    friccion = cubierta.coeficiente_friccion
    valores_cpn = cubierta.cpn()
    valores = presiones()
    filas = []
    for tipo, contenido in valores_cpn.items():
        if tipo is TipoPresionCubiertaAislada.GLOBAL:
            grupos: Any = ((None, contenido),)
        else:
            grupos = tuple(contenido.items())
        for zona, extremos in grupos:
            for extremo, cpn in extremos.items():
                presion = (
                    valores[tipo][extremo]
                    if zona is None
                    else valores[tipo][zona][extremo]
                )
                filas.append(
                    FilaCubiertaAislada(
                        tipo=tipo,
                        extremo=extremo,
                        q=q,
                        cpn=float(cpn),
                        factor_rafaga=factor_rafaga,
                        presion=float(presion),
                        presion_friccion=float(presion) * friccion,
                        referencia=cubierta.cpn.referencia,
                        zona=zona,
                    )
                )
    return Tabla(filas)
