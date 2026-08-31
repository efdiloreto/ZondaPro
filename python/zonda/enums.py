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

"""Enums que se utiliza ZONDA.

Es preferible utilizar estas clases antes que strings ya que las opciones requeridas
en las distintas funciones son especificas. De esta manera, utilizando Enums se disminuye la posibilidad de errores.
"""

from enum import Enum


class Estructura(Enum):
    EDIFICIO = "edificio"
    CARTEL = "cartel"
    CUBIERTA_AISLADA = "cubierta aislada"


class PosicionCamara(Enum):
    SUPERIOR = "superior"
    PERSPECTIVA = "perspectiva"
    IZQUIERDA = "izquierda"
    DERECHA = "derecha"
    FRENTE = "frente"
    CONTRAFRENTE = "contrafrente"


class Unidad(Enum):
    N = "N"
    KN = "kN"
    KG = "kG"


class Cerramiento(Enum):
    CERRADO = "cerrado"
    PARCIALMENTE_CERRADO = "parcialmente cerrado"
    ABIERTO = "abierto"


class CategoriaEstructura(Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class DireccionTopografia(Enum):
    BARLOVENTO = "barlovento"
    SOTAVENTO = "sotavento"


class TipoTerrenoTopografia(Enum):
    LOMA_BIDIMENSIONAL = "loma bidimensional"
    ESCARPA_BIDIMENSIONAL = "escarpa bidimensional"
    COLINA_TRIDIMENSIONAL = "colina tridimensional"


class Flexibilidad(Enum):
    RIGIDA = "rigida"
    FLEXIBLE = "flexible"


class CategoriaExposicion(Enum):
    B = "B"
    C = "C"
    D = "D"


class ExtremoPresion(Enum):
    MAX = "máx"
    MIN = "min"


class SistemaResistente(Enum):
    SPRFV = "sprfv"
    COMPONENTES = "componentes"


class DireccionVientoMetodoDireccionalSprfv(Enum):
    PARALELO = "paralelo"
    NORMAL = "normal"


class MetodoSprfv(Enum):
    DIRECCIONAL = "direccional"
    ENVOLVENTE = "envolvente"


class TipoCubierta(Enum):
    PLANA = "plana"
    UN_AGUA = "un agua"
    DOS_AGUAS = "dos aguas"


class PosicionBloqueoCubierta(Enum):
    ALERO_BAJO = "alero bajo"
    ALERO_ALTO = "alero alto"


class ZonaEdificio(Enum):
    PAREDES = "paredes"
    CUBIERTA = "cubierta"
    ALERO = "alero"


class ParedEdificioSprfv(Enum):
    BARLOVENTO = "barlovento"
    SOTAVENTO = "sotavento"
    LATERAL = "lateral"


class PosicionCubiertaAleroSprfv(Enum):
    SOTAVENTO = "sotavento"
    BARLOVENTO = "barlovento"


class TipoPresionCubiertaBarloventoSprfv(Enum):
    NEGATIVA = "presión negativa"
    POSITIVA = "presión positiva"


class TipoPresionComponentesParedesCubierta(Enum):
    NEGATIVA = "negativa"
    POSITIVA = "positiva"


class ZonaComponenteParedEdificio(Enum):
    CUATRO = "4"
    CINCO = "5"
    TODAS = "todas"


class ZonaComponenteCubiertaEdificio(Enum):
    UNO = "1"
    DOS = "2"
    TRES = "3"
    UNO_PRIMA = "1'"
    DOS_PRIMA = "2'"
    TRES_PRIMA = "3'"
    TODAS = "todas"


class TipoPresionCubiertaAislada(Enum):
    GLOBAL = "global"
    LOCAL = "local"


class ZonaPresionCubiertaAislada(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    BC = "bc"
    BD = "bd"
