# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

"""Tipos utilizados por ZONDA para utilizar type hints."""

from collections import defaultdict
from typing import TypeVar

import numpy as np

from zonda.cirsoc.presiones.edificio import PresionesEdificio
from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    ExtremoPresion,
    ParedEdificioSprfv,
    PosicionCubiertaAleroSprfv,
    SistemaResistente,
    TipoPresionCubiertaAislada,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaComponenteCubiertaEdificio,
    ZonaComponenteParedEdificio,
    ZonaEdificio,
    ZonaPresionCubiertaAislada,
)

ParNumerico = tuple[float, float]

Punto = tuple[float, float, float]

Punto2D = ParNumerico

EscalarOArray = TypeVar("EscalarOArray", float, np.ndarray)

ValoresCpCubiertaAislada = dict[
    TipoPresionCubiertaAislada,
    dict[ExtremoPresion, float]
    | dict[ZonaPresionCubiertaAislada, dict[ExtremoPresion, float]],
]

ValoresCpParedesEdificioSprfvMetodoDireccional = dict[
    DireccionVientoMetodoDireccionalSprfv, dict[ParedEdificioSprfv, float]
]

ValoresCpParedesEdificioComponentes = defaultdict[
    str, dict[ZonaComponenteParedEdificio, float]
]

ValoresCpCubiertaEdificioSprfvMetodoDireccional = dict[
    DireccionVientoMetodoDireccionalSprfv,
    np.ndarray
    | dict[
        PosicionCubiertaAleroSprfv,
        dict[TipoPresionCubiertaBarloventoSprfv, float] | float,
    ],
]

ValoresCpAleroEdificioSprfvMetodoDireccional = (
    ValoresCpCubiertaEdificioSprfvMetodoDireccional
)

ValoresCpCubiertaEdificioComponentes = defaultdict[
    str, dict[ZonaComponenteCubiertaEdificio, float]
]

ValoresCpParedesEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresCpParedesEdificioSprfvMetodoDireccional
    | ValoresCpParedesEdificioComponentes,
]

ValoresCpCubiertaEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresCpCubiertaEdificioSprfvMetodoDireccional
    | ValoresCpCubiertaEdificioComponentes,
]

ValoresCpAleroEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresCpAleroEdificioSprfvMetodoDireccional | ValoresCpCubiertaEdificioComponentes,
]

ValoresCpEdificioMetodoDireccional = dict[
    ZonaEdificio,
    ValoresCpParedesEdificioMetodoDireccional
    | ValoresCpCubiertaEdificioMetodoDireccional
    | ValoresCpCubiertaEdificioSprfvMetodoDireccional,
]

ValoresPresionesCubiertaAislada = ValoresCpCubiertaAislada

ValoresPresionesCubiertaEdificioSprfvMetodoDireccional = dict[
    DireccionVientoMetodoDireccionalSprfv,
    np.ndarray
    | dict[
        PosicionCubiertaAleroSprfv,
        dict[TipoPresionCubiertaBarloventoSprfv, PresionesEdificio] | PresionesEdificio,
    ],
]

ValoresPresionesAleroEdificioSprfvMetodoDireccional = (
    ValoresCpAleroEdificioSprfvMetodoDireccional
)

ValoresPresionesParedesEdificioSprfvMetodoDireccional = defaultdict[
    DireccionVientoMetodoDireccionalSprfv,
    dict[ParedEdificioSprfv, np.ndarray | PresionesEdificio],
]

ValoresPresionesParedesEdificioComponentesA = defaultdict[
    str, dict[ZonaComponenteParedEdificio, PresionesEdificio]
]
ValoresPresionesParedesEdificioComponentesB = defaultdict[
    str,
    defaultdict[
        ParedEdificioSprfv,
        dict[ZonaComponenteParedEdificio, np.ndarray | PresionesEdificio],
    ],
]

ValoresPresionesParedesEdificioComponentes = (
    ValoresPresionesParedesEdificioComponentesA
    | ValoresPresionesParedesEdificioComponentesB
)

ValoresPresionesCubiertaEdificioComponentes = defaultdict[
    str, dict[ZonaComponenteCubiertaEdificio, PresionesEdificio]
]
ValoresPresionesAleroEdificioComponentes = defaultdict[
    str, dict[ZonaComponenteCubiertaEdificio, float]
]

ValoresPresionesCubiertaEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresPresionesCubiertaEdificioSprfvMetodoDireccional
    | ValoresPresionesCubiertaEdificioComponentes,
]

ValoresPresionesParedesEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresPresionesParedesEdificioSprfvMetodoDireccional
    | ValoresPresionesParedesEdificioComponentes,
]

ValoresPresionesAleroEdificioMetodoDireccional = dict[
    SistemaResistente,
    ValoresPresionesAleroEdificioSprfvMetodoDireccional
    | ValoresPresionesAleroEdificioComponentes,
]

ValoresPresionesEdificioMetodoDireccional = dict[
    ZonaEdificio,
    ValoresPresionesParedesEdificioMetodoDireccional
    | ValoresPresionesCubiertaEdificioMetodoDireccional
    | ValoresPresionesAleroEdificioMetodoDireccional,
]
