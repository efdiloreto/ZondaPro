"""Tipos utilizados por ZondaPro para utilizar type hints.
"""
from typing import Dict, Union, DefaultDict, Tuple, TypeVar

import numpy as np

from zondapro.cirsoc.presiones.edificio import PresionesEdificio
from zondapro.enums import (
    ExtremoPresion,
    ZonaPresionCubiertaAislada,
    TipoPresionCubiertaAislada,
    DireccionVientoMetodoDireccionalSprfv,
    ParedEdificioSprfv,
    ZonaComponenteParedEdificio,
    PosicionCubiertaAleroSprfv,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaComponenteCubiertaEdificio,
    SistemaResistente,
    ZonaEdificio,
)

ParNumerico = Tuple[float, float]

Punto = Tuple[float, float, float]

Punto2D = ParNumerico

EscalarOArray = TypeVar("EscalarOArray", float, np.ndarray)

ValoresCpCubiertaAislada = Dict[
    TipoPresionCubiertaAislada,
    Union[Dict[ExtremoPresion, float], Dict[ZonaPresionCubiertaAislada, Dict[ExtremoPresion, float]]],
]

ValoresCpParedesEdificioSprfvMetodoDireccional = Dict[
    DireccionVientoMetodoDireccionalSprfv, Dict[ParedEdificioSprfv, float]
]

ValoresCpParedesEdificioComponentes = DefaultDict[str, Dict[ZonaComponenteParedEdificio, float]]

ValoresCpCubiertaEdificioSprfvMetodoDireccional = Dict[
    DireccionVientoMetodoDireccionalSprfv,
    Union[np.ndarray, Dict[PosicionCubiertaAleroSprfv, Union[Dict[TipoPresionCubiertaBarloventoSprfv, float], float]]],
]

ValoresCpAleroEdificioSprfvMetodoDireccional = ValoresCpCubiertaEdificioSprfvMetodoDireccional

ValoresCpCubiertaEdificioComponentes = DefaultDict[str, Dict[ZonaComponenteCubiertaEdificio, float]]

ValoresCpParedesEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[
        ValoresCpParedesEdificioSprfvMetodoDireccional,
        ValoresCpParedesEdificioComponentes,
    ],
]

ValoresCpCubiertaEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[ValoresCpCubiertaEdificioSprfvMetodoDireccional, ValoresCpCubiertaEdificioComponentes],
]

ValoresCpAleroEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[ValoresCpAleroEdificioSprfvMetodoDireccional, ValoresCpCubiertaEdificioComponentes],
]

ValoresCpEdificioMetodoDireccional = Dict[
    ZonaEdificio,
    Union[
        ValoresCpParedesEdificioMetodoDireccional,
        ValoresCpCubiertaEdificioMetodoDireccional,
        ValoresCpCubiertaEdificioSprfvMetodoDireccional,
    ],
]

ValoresPresionesCubiertaAislada = ValoresCpCubiertaAislada

ValoresPresionesCubiertaEdificioSprfvMetodoDireccional = Dict[
    DireccionVientoMetodoDireccionalSprfv,
    Union[
        np.ndarray,
        Dict[
            PosicionCubiertaAleroSprfv,
            Union[Dict[TipoPresionCubiertaBarloventoSprfv, PresionesEdificio], PresionesEdificio],
        ],
    ],
]

ValoresPresionesAleroEdificioSprfvMetodoDireccional = ValoresCpAleroEdificioSprfvMetodoDireccional

ValoresPresionesParedesEdificioSprfvMetodoDireccional = DefaultDict[
    DireccionVientoMetodoDireccionalSprfv,
    Union[Dict[ParedEdificioSprfv, Union[np.ndarray, PresionesEdificio]]],
]

ValoresPresionesParedesEdificioComponentesA = DefaultDict[str, Dict[ZonaComponenteParedEdificio, PresionesEdificio]]
ValoresPresionesParedesEdificioComponentesB = DefaultDict[
    str,
    DefaultDict[ParedEdificioSprfv, Dict[ZonaComponenteParedEdificio, Union[np.ndarray, PresionesEdificio]]],
]

ValoresPresionesParedesEdificioComponentes = Union[
    ValoresPresionesParedesEdificioComponentesA, ValoresPresionesParedesEdificioComponentesB
]

ValoresPresionesCubiertaEdificioComponentes = DefaultDict[str, Dict[ZonaComponenteCubiertaEdificio, PresionesEdificio]]
ValoresPresionesAleroEdificioComponentes = DefaultDict[str, Dict[ZonaComponenteCubiertaEdificio, float]]

ValoresPresionesCubiertaEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[ValoresPresionesCubiertaEdificioSprfvMetodoDireccional, ValoresPresionesCubiertaEdificioComponentes],
]

ValoresPresionesParedesEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[ValoresPresionesParedesEdificioSprfvMetodoDireccional, ValoresPresionesParedesEdificioComponentes],
]

ValoresPresionesAleroEdificioMetodoDireccional = Dict[
    SistemaResistente,
    Union[ValoresPresionesAleroEdificioSprfvMetodoDireccional, ValoresPresionesAleroEdificioComponentes],
]

ValoresPresionesEdificioMetodoDireccional = Dict[
    ZonaEdificio,
    Union[
        ValoresPresionesParedesEdificioMetodoDireccional,
        ValoresPresionesCubiertaEdificioMetodoDireccional,
        ValoresPresionesAleroEdificioMetodoDireccional,
    ],
]
