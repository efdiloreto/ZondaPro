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

import math
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


class CasoCartel(Enum):
    """Los casos de fuerza de la Figura 4.4-1.

    Los Casos A y B comparten la tabla de coeficientes y aplican la fuerza
    resultante en el centro geométrico (A) o con una excentricidad hacia el
    borde de barlovento (B). El Caso C, sólo para B/s ≥ 2, reparte la fuerza
    en regiones horizontales medidas desde el borde de barlovento.
    """

    CASO_A = "Caso A"
    CASO_B = "Caso B"
    CASO_C = "Caso C"


class RegionCartel(Enum):
    """Las regiones del Caso C de la Figura 4.4-1.

    El valor es ``(inicio, fin, numero)``, con los límites medidos desde el
    borde de barlovento en unidades de la altura s del cartel y el número de
    región contado desde el borde de barlovento en el orden en que la tabla de
    la figura muestra las bandas. Para B/s ≤ 10 la tabla agrupa desde 3s en
    ``REGION_3S_10S``, que queda como región 4; para B/s mayores esa banda se
    separa en ``REGION_3S_4S``, ``REGION_4S_5S``, ``REGION_5S_10S`` y
    ``REGION_10S``, que heredan los números 4 a 7.
    """

    REGION_0_S = (0.0, 1.0, 1)
    REGION_S_2S = (1.0, 2.0, 2)
    REGION_2S_3S = (2.0, 3.0, 3)
    REGION_3S_4S = (3.0, 4.0, 4)
    REGION_4S_5S = (4.0, 5.0, 5)
    REGION_5S_10S = (5.0, 10.0, 6)
    REGION_10S = (10.0, math.inf, 7)
    REGION_3S_10S = (3.0, 10.0, 4)

    @property
    def inicio(self) -> float:
        return self.value[0]

    @property
    def fin(self) -> float:
        return self.value[1]

    @property
    def numero(self) -> int:
        return self.value[2]


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


class TipoSuperficieFriccion(Enum):
    """Los tipos de superficie de la Tabla 2.4-1.

    El valor es el coeficiente de empuje por fricción. Las ondulaciones y las
    nervaduras cuentan como transversales cuando lo son a la dirección del
    viento considerado.
    """

    LISA = 0.01
    ONDULACIONES_TRANSVERSALES = 0.02
    NERVADURAS_TRANSVERSALES = 0.04


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


class DireccionVientoCubiertaAislada(Enum):
    """La dirección del viento de las Figuras 2.4-4 a 2.4-7.

    Las direcciones γ = 0º y 180º son perpendiculares a la cumbrera (para
    cubiertas a un agua, a la vertiente), y γ = 90º y 270º paralelas a ella.
    """

    GAMMA_0 = "γ = 0º"
    GAMMA_90 = "γ = 90º"
    GAMMA_180 = "γ = 180º"
    GAMMA_270 = "γ = 270º"


class CasoCargaCubiertaAislada(Enum):
    """Los casos de carga de las Figuras 2.4-4 a 2.4-7.

    El reglamento exige investigar todos los casos de carga para cada ángulo
    de cubierta.
    """

    CASO_A = "Caso A"
    CASO_B = "Caso B"


class ZonaPresionCubiertaAislada(Enum):
    """Las zonas de las Figuras 2.4-4 a 2.4-7.

    Para viento perpendicular a la cumbrera (γ = 0º y 180º) las zonas son las
    mitades de barlovento y de sotavento de la superficie (C_NW y C_NL). Para
    viento paralelo (γ = 90º y 270º) son bandas horizontales medidas desde el
    borde de barlovento, con límites a la altura media del techo h y a 2h.
    """

    BARLOVENTO = "barlovento"
    SOTAVENTO = "sotavento"
    HASTA_H = "x ≤ h"
    ENTRE_H_Y_2H = "h < x ≤ 2h"
    MAYOR_2H = "x > 2h"


class NivelPatrocinio(Enum):
    """Los niveles con los que se puede apoyar el proyecto.

    El orden de declaración es el de importancia: es el que usa la pantalla de
    apoyo para ordenar la lista y decidir a quién le toca la franja de la
    bienvenida.
    """

    ORO = "oro"
    PLATA = "plata"
    BRONCE = "bronce"
