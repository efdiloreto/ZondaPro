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

import itertools
from dataclasses import replace
from functools import cached_property
from math import log10

import numpy as np

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.cirsoc.resultados import EntradaCp
from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    MetodoSprfv,
    ParedEdificioSprfv,
    PosicionCubiertaAleroSprfv,
    SistemaResistente,
    TipoCubierta,
    TipoPresionComponentesParedesCubierta,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaComponenteCubiertaEdificio,
    ZonaComponenteParedEdificio,
    ZonaEdificio,
)
from zonda.tipos import ParNumerico


# TODO - El type hint deberia aceptar lista o array
def seleccionar_cp_area(
    cps: ParNumerico | tuple[ParNumerico, ...],
    areas: ParNumerico | tuple[ParNumerico, ...],
    area_componente: float,
) -> ParNumerico | tuple[ParNumerico, ...]:
    """Selecciona las areas y cps para luego interpolar el valor de area tributaria del componente.

    Es util, por ejemplo cuando hay mas de dos valores de area para interpolar, como el alero con
    voladizo de la Tabla C 5.3-2 del CIRSOC 102-2025, donde las Zonas 1 y 1' tienen dos tramos.
    En este caso se detecta entre que valores de area se encuentra el
    area del componente y se retorna esos valores de area con sus respectivos cps para luego usarse
    en la interpolación.

    Args:
        cps: Valores de cp.
        areas: Valores de area.
        area_componente: Area tributaria del componente.

    Returns:
        Dos valores de cp y dos valores de area que se utilizarán para interpolar.
    """
    # TODO - Se puede hacer mas "Pythonico"
    cp_areas = tuple(zip(cps, areas))
    numero_de_zonas = len(cp_areas)
    for i, (cp, area) in enumerate(cp_areas):
        if isinstance(cp, tuple) and isinstance(area, tuple):
            _primer_area, ultima_area = area
            if area_componente > ultima_area:
                if i == numero_de_zonas - 1:
                    return cp, area
                continue
            return cp, area
        return cps, areas


# TODO - El type hint deberia aceptar lista o array
def calcular_cp_componente(
    cps: ParNumerico, areas: ParNumerico, area_componente: float
) -> float:
    """Calcula el valor de cp para un componente en base a su area tributaria.

    Referencia: Libro "DESIGN OF BUILDINGS FOR WIND - Second Edition" - Emil Simiu Pag. 96.

    Args:
        cps: Valores de cp.
        areas: Valores de area.
        area_componente: Area tributaria del componente.

    Returns:
        El valor interpolado de cp para el componente el area tributaria ingresada.
    """
    primer_cp, ultimo_cp = cps
    primer_area, ultima_area = areas
    if area_componente <= primer_area:
        return primer_cp
    if area_componente >= ultima_area:
        return ultimo_cp
    g = (ultimo_cp - primer_cp) / log10(ultima_area / primer_area)
    return primer_cp + g * log10(area_componente / primer_area)


# CIRSOC 102-2025 - Tabla C 5.3-1: el GCp positivo de las paredes de C&R, que
# la Tabla no distingue por zona -es el mismo para las Zonas 4 y 5-, con su
# rango de áreas.
CP_POSITIVO_PAREDES = (1.0, 0.7)
AREAS_COMPONENTES_PAREDES = (1.0, 50.0)

# CIRSOC 102-2025 - Figura 5.4-1 (h > 20 m): el GCp positivo de las paredes de
# C&R de edificios de gran altura, con su rango de áreas. Con los valores
# positivos se debe usar qz y con los negativos qh (Nota 4), así que la
# presión resuelve el positivo altura por altura.
CP_POSITIVO_PAREDES_GRAN_ALTURA = (0.9, 0.6)
AREAS_COMPONENTES_PAREDES_GRAN_ALTURA = (2.0, 50.0)


def cp_positivo_paredes(area_componente: float, angulo_cubierta: float) -> float:
    """El GCp positivo de las Zonas de pared 4 y 5 de la Tabla C 5.3-1.

    La Nota 5 de la Figura 5.3-2A se lo presta a las Zonas 2 y 3 de la cubierta
    cuando hay un parapeto de 1 m o más alrededor del perímetro. Se presta el
    valor tal como queda para el edificio, o sea con el descuento por cubierta
    de pendiente baja, que con esa Figura siempre aplica.

    Args:
        area_componente: Area tributaria del componente.
        angulo_cubierta: El ángulo de cubierta del edificio.

    Returns:
        El valor de GCp positivo.
    """
    factor_reduccion = 0.9 if angulo_cubierta <= 10 else 1
    return (
        calcular_cp_componente(
            CP_POSITIVO_PAREDES, AREAS_COMPONENTES_PAREDES, area_componente
        )
        * factor_reduccion
    )


def distancia_a(ancho: float, longitud: float, altura_media: float) -> float:
    """Calcula la distancia "a" provista en las figuras para componentes y revestimientos.

    Args:
        ancho: El ancho del edificio.
        longitud: La longitud del edificio.
        altura_media: La altura media de cubierta del edificio.

    Returns:
        El valor de distancia "a".
    """
    menor_dimension_horizontal = min(ancho, longitud)
    valor_propuesto = min(0.1 * menor_dimension_horizontal, 0.4 * altura_media)
    limite_minimo = max(0.04 * menor_dimension_horizontal, 1)
    return max(valor_propuesto, limite_minimo)


class ParedesSprfvMetodoDireccional:
    """ParedesSprfvMetodoDireccional.

    Determina los coeficientes de presión de paredes de edificio para SPRFV usando el método
    direccional.
    """

    def __init__(self, ancho: float, longitud: float) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
        """
        self.ancho = ancho
        self.longitud = longitud

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión de las paredes.

        Returns:
            Un coeficiente por cada pared y dirección del viento.
        """
        cp_sotavento = {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: self._cp_pared_sotavento(
                self.longitud, self.ancho
            ),
            DireccionVientoMetodoDireccionalSprfv.NORMAL: self._cp_pared_sotavento(
                self.ancho, self.longitud
            ),
        }
        return tuple(
            EntradaCp(
                zona=ZonaEdificio.PAREDES,
                sistema=SistemaResistente.SPRFV,
                valor=float(valor),
                referencia=self.referencia,
                direccion=direccion,
                pared=pared,
            )
            for direccion, sotavento in cp_sotavento.items()
            for pared, valor in (
                (ParedEdificioSprfv.BARLOVENTO, 0.8),
                (ParedEdificioSprfv.LATERAL, -0.7),
                (ParedEdificioSprfv.SOTAVENTO, sotavento),
            )
        )

    @cached_property
    def referencia(self) -> str:
        """
        Returns:
            La referencia de la figura en el código.
        """
        return "Figura 2.4-1 (cont.)"

    @staticmethod
    def _cp_pared_sotavento(
        dimension_paralela: float, dimension_normal: float
    ) -> float:
        """Calcula el coeficiente de presión para pared sotavento.

        Args:
            dimension_paralela: La dimension del edificio medida de forma paralela a la dirección del viento.
            dimension_normal: La dimension del edificio medida de forma normal a la dirección del viento.

        Returns:
            El coeficiente de presión para pared sotavento.
        """
        relaciones_paralelo_normal = (0, 1, 2, 4)
        valores_cp = (-0.5, -0.5, -0.3, -0.2)
        return np.interp(
            dimension_paralela / dimension_normal,
            relaciones_paralelo_normal,
            valores_cp,
        )


def tipo_presion_componente(
    zona: ZonaComponenteParedEdificio | ZonaComponenteCubiertaEdificio,
) -> TipoPresionComponentesParedesCubierta:
    """El signo del coeficiente externo de una zona de componentes.

    Las tablas dan un único valor positivo para todas las zonas, que viaja en
    la zona "todas"; el resto de las zonas son las negativas.

    Args:
        zona: La zona del componente.

    Returns:
        El tipo de presión de la zona.
    """
    if zona in (
        ZonaComponenteParedEdificio.TODAS,
        ZonaComponenteCubiertaEdificio.TODAS,
    ):
        return TipoPresionComponentesParedesCubierta.POSITIVA
    return TipoPresionComponentesParedesCubierta.NEGATIVA


class ParedesComponentes:
    """ParedesComponentes.

    Determina los coeficientes de presión de paredes de edificio para Componentes y Revestimientos.

    La Tabla C 5.3-1 cubre hasta 20 m de altura media y la Figura 5.4-1 desde
    ahí en adelante: es la reemplazante de la Figura 8 del CIRSOC 102-2005,
    con los mismos valores y la misma distribución de Zonas 4 y 5.

    TODO (#9): falta la zona 4+ de la superficie inferior de los edificios
    separados del suelo (Figura 5.4-1A). El dato de entrada existe -la
    elevación del edificio-, y el valor es el positivo de la zona 4, que ya
    devuelve ``cp_positivo_paredes``.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo_cubierta: float,
        componentes: dict[str, float] | None = None,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_media: La altura media de cubierta del edificio.
            angulo_cubierta: El ángulo de cubierta del edificio.
            componentes: Los componentes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_media = altura_media
        self.angulo_cubierta = angulo_cubierta
        self.componentes = componentes
        if self.altura_media <= 20:
            self.referencia = "Tabla C 5.3-1"
        else:
            self.referencia = "Figura 5.4-1"

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión para componentes y revestimientos.

        La Figura 5.4-1 (h > 20 m) da un solo valor positivo para todas las
        paredes, que se evalúa con qz altura por altura (Nota 4); los negativos
        se evalúan con qh. La rama baja no cambia de tabla por pared.

        Returns:
            Un coeficiente por cada componente y zona. Ninguno si no se
            cargaron componentes.
        """
        if self.componentes is None:
            return ()
        if self.referencia == "Tabla C 5.3-1":
            caso_cp = {
                ZonaComponenteParedEdificio.CUATRO: (-1.1, -0.8),
                ZonaComponenteParedEdificio.CINCO: (-1.4, -0.8),
                ZonaComponenteParedEdificio.TODAS: CP_POSITIVO_PAREDES,
            }
            factor_reduccion = 0.9 if self.angulo_cubierta <= 10 else 1
            area = AREAS_COMPONENTES_PAREDES
        else:
            caso_cp = {
                ZonaComponenteParedEdificio.CUATRO: (-0.9, -0.7),
                ZonaComponenteParedEdificio.CINCO: (-1.8, -1.0),
                ZonaComponenteParedEdificio.TODAS: CP_POSITIVO_PAREDES_GRAN_ALTURA,
            }
            factor_reduccion = 1
            area = AREAS_COMPONENTES_PAREDES_GRAN_ALTURA
        return tuple(
            EntradaCp(
                zona=ZonaEdificio.PAREDES,
                sistema=SistemaResistente.COMPONENTES,
                valor=float(
                    calcular_cp_componente(cp, area, area_componente) * factor_reduccion
                ),
                referencia=self.referencia,
                componente=nombre,
                zona_componente=zona,
                distancia_a=self.distancia_a,
                tipo_presion=tipo_presion_componente(zona),
            )
            for nombre, area_componente in self.componentes.items()
            for zona, cp in caso_cp.items()
        )

    @cached_property
    def distancia_a(self) -> float:
        """La distancia "a", con la excepción para edificios bajos y planos.

        Excepción del Reglamento (Tabla C 5.3-1): para ángulo de cubierta de
        0° a 7° y dimensión horizontal mínima mayor que 90 m, la distancia "a"
        se limita a un máximo de 0,8 veces la altura media. La Figura 5.4-1 no
        tiene esa excepción.

        Returns:
            El valor de distancia "a" del edificio.
        """
        a = distancia_a(self.ancho, self.longitud, self.altura_media)
        if (
            self.referencia == "Tabla C 5.3-1"
            and 0 <= self.angulo_cubierta <= 7
            and min(self.ancho, self.longitud) > 90
        ):
            a = min(a, 0.8 * self.altura_media)
        return a


class CubiertaSprfvMetodoDireccional:
    """CubiertaSprfvMetodoDireccional.

    Determina los coeficientes de presión de cubierta de edificio para SPRFV usando el método direccional.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo: float,
        tipo_cubierta: TipoCubierta,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio (que es igual al de cubierta).
            longitud: La longitud del edificio (que es igual a la de cubierta).
            altura_media: La altura media de cubierta.
            angulo: El ángulo de cubierta.
            tipo_cubierta: El tipo de cubierta.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_media = altura_media
        self.angulo = angulo
        self.tipo_cubierta = tipo_cubierta
        self.zona = ZonaEdificio.CUBIERTA
        self.distancias_codigo = (
            0.0,
            self.altura_media / 2,
            self.altura_media,
            2 * self.altura_media,
        )

    @cached_property
    def normal_como_paralelo(self) -> bool:
        """Determina si los coeficientes de presion sobre cubierta con el viento actuando normal a la cumbrera se deben
        determinar de la misma forma que con el viento actuando paralelo a la cumbrera.

        Returns:
            True si el angulo es menor que 10°, sino retorna False.
        """
        return self.angulo < 10

    @cached_property
    def zonas(
        self,
    ) -> dict[DireccionVientoMetodoDireccionalSprfv, tuple[ParNumerico, ...] | None]:
        """Calcula las distancias en la cubierta sobre las que actua el viento, cuando la dirección del mismo es paralelo
        a la cumbrera o cuando el ángulo de la cubierta es menor que 10° y la dirección del viento es normal a la cumbrera.

        Returns:
            Las zonas para las direcciones normal y paralelo.
        """
        paralelo = self._zonas_cubierta(self.longitud)
        if self.normal_como_paralelo:
            args = (self.ancho, self.longitud)
            if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
                args += (self.ancho / 2,)
            normal = self._zonas_cubierta(*args)
        else:
            normal = None
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: paralelo,
            DireccionVientoMetodoDireccionalSprfv.NORMAL: normal,
        }

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión de la cubierta para el SPRFV.

        Returns:
            Un coeficiente por cada zona o posición y dirección del viento.
        """
        return self._entradas_cubierta()

    def _entradas_cubierta(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión de la superficie de cubierta.

        Con el viento paralelo a la cumbrera -y con el viento normal cuando el
        ángulo no llega a 10°- la superficie se divide en zonas y cada una tiene
        su coeficiente. Si no, se resuelve por posición respecto al viento, con
        dos casos de presión a barlovento.

        Returns:
            Un coeficiente por cada zona o posición y dirección del viento.
        """
        entradas = self._entradas_zonificadas(
            DireccionVientoMetodoDireccionalSprfv.PARALELO, self.longitud, self.ancho
        )
        if self.normal_como_paralelo:
            entradas += self._entradas_zonificadas(
                DireccionVientoMetodoDireccionalSprfv.NORMAL, self.ancho, self.longitud
            )
        else:
            entradas += self._entradas_por_posicion()
        return tuple(entradas)

    def _entrada(self, valor: float, **claves) -> EntradaCp:
        """Arma una entrada con las claves comunes de la superficie.

        Args:
            valor: El coeficiente de presión.
            **claves: Las claves que identifican a la entrada.

        Returns:
            La entrada.
        """
        return EntradaCp(
            zona=self.zona,
            sistema=SistemaResistente.SPRFV,
            valor=float(valor),
            referencia=self.referencia,
            **claves,
        )

    def _entradas_zonificadas(
        self,
        direccion: DireccionVientoMetodoDireccionalSprfv,
        dimension_paralela: float,
        dimension_normal: float,
    ) -> list[EntradaCp]:
        """Calcula los coeficientes de una dirección en la que hay zonas.

        Args:
            direccion: La dirección del viento.
            dimension_paralela: La longitud de la dimension paralela a la dirección del viento.
            dimension_normal: La longitud de la dimension normal a la dirección del viento.

        Returns:
            Una entrada por cada zona.
        """
        zonas = self.zonas[direccion]
        numero_de_zonas = len(zonas)
        indice_repetido = None
        if direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            mitad_ancho = self.ancho / 2
            if (
                self.tipo_cubierta == TipoCubierta.DOS_AGUAS
                and mitad_ancho not in self.distancias_codigo
            ):
                # Se agrega una zona porque las distancias de zonas de viento no
                # coinciden con la mitad del ancho: esa zona repite el cp de la
                # anterior.
                numero_de_zonas -= 1
                indice_repetido = next(
                    i for i, (_inicio, fin) in enumerate(zonas) if fin == mitad_ancho
                )
        cps = list(
            self._cp_cubierta_angulo_menor_diez(
                dimension_paralela, dimension_normal, numero_de_zonas
            )
        )
        if indice_repetido is not None:
            cps.insert(indice_repetido + 1, cps[indice_repetido])
        entradas = [
            self._entrada(cp, direccion=direccion, rango=(float(inicio), float(fin)))
            for (inicio, fin), cp in zip(zonas, cps, strict=True)
        ]
        if direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            # El nuevo Reglamento especifica además un caso de presión positiva
            # de -0.18 en todas las zonas, con viento normal a la cumbrera y
            # ángulo menor que 10°.
            entradas += [
                replace(
                    entrada,
                    valor=-0.18,
                    caso=TipoPresionCubiertaBarloventoSprfv.POSITIVA,
                )
                for entrada in entradas
            ]
        return entradas

    def _entradas_por_posicion(self) -> list[EntradaCp]:
        """Calcula los coeficientes con viento normal a la cumbrera y ángulo ≥ 10°.

        Returns:
            Una entrada por cada caso de presión a barlovento, más la de sotavento.
        """
        direccion = DireccionVientoMetodoDireccionalSprfv.NORMAL
        entradas = [
            self._entrada(
                valor,
                direccion=direccion,
                posicion=PosicionCubiertaAleroSprfv.BARLOVENTO,
                caso=caso,
            )
            for caso, valor in self._cp_cubierta_barlovento().items()
        ]
        entradas.append(
            self._entrada(
                self._cp_cubierta_sotavento(),
                direccion=direccion,
                posicion=PosicionCubiertaAleroSprfv.SOTAVENTO,
            )
        )
        return entradas

    @cached_property
    def referencia(self) -> str:
        """
        Returns:
            La referencia de la figura en el código.
        """
        return "Figura 2.4-1 (cont.)"

    def _cp_cubierta_angulo_menor_diez(
        self, dimension_paralela: float, dimension_normal: float, numero_de_zonas: int
    ) -> np.ndarray:
        """Calcula los coeficientes de presion cuando el viento actua normal a
        la cumbrera o cuando el viento actua normal a la cumbrera y la cubierta
        tiene un angulo < 10°.

        Args:
            dimension_paralela: La longitud de la dimension paralela a la dirección del viento.
            dimension_normal: La longitud de la dimension normal a la dirección del viento.
            numero_de_zonas: El numero de zonas de aplicación del viento.

        Returns:
            Los valores de cp para cubierta con viento paralelo a la cumbrera o con viento normal a la cumbrera y
            cubierta con angulo menor que 10° .

        Raises:
            ValueError cuando el numero de zonas no se encuentra entre 1 y 4.
        """
        if not 1 <= numero_de_zonas <= 4:
            raise ValueError("El número de zonas debe ser un entero entre 1 y 4.")
        area = self._area_cp_cubierta(
            self.altura_media,
            dimension_paralela,
            dimension_normal,
        )
        reduccion = np.interp(area, (10, 25, 100), (1.0, 0.9, 0.8))
        relaciones_altura_longitud = (0.5, 1.0)
        cp = ((-0.9, -1.3 * reduccion), (-0.9, -0.7), (-0.5, -0.7), (-0.3, -0.7))
        cp_iter = (
            np.interp(
                self.altura_media / dimension_paralela,
                relaciones_altura_longitud,
                cp_val,
            )
            for cp_val in cp
        )
        valores_cp = np.fromiter(cp_iter, float)[:numero_de_zonas]
        return valores_cp

    def _cp_cubierta_barlovento(
        self,
    ) -> dict[TipoPresionCubiertaBarloventoSprfv, float]:
        """Calcula por interpolación los coeficientes de presión para la cubierta a barlovento.

        Returns:
            Los coeficientes de presión para cubierta a barlovento.

        Raises:
            ValueError: Cuando el ángulo de cubierta es < 10°.
        """
        if self.angulo < 10:
            raise ValueError(
                "No se pueden calcular los valores, el ángulo de cubierta debe ser ≥ 10° para usar este método."
            )
        area = self._area_cp_cubierta(self.altura_media, self.longitud, self.ancho)
        reduccion = np.interp(area, (10, 25, 100), (1, 0.9, 0.8))
        relaciones_altura_longitud = (0.25, 0.5, 1)
        angulos = (10, 15, 20, 25, 30, 35, 45, 60, 80)
        valores_cp_presion_negativa = (
            (-0.7, -0.9, -1.3 * reduccion),
            (-0.5, -0.7, -1),
            (-0.3, -0.4, -0.7),
            (-0.2, -0.3, -0.5),
            (-0.2, -0.2, -0.3),
            (0, -0.2, -0.2),
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
        )
        valores_cp_presion_positiva = (
            (-0.18, -0.18, -0.18),
            (0, -0.18, -0.18),
            (0.2, 0, -0.18),
            (0.3, 0.2, 0),
            (0.3, 0.2, 0.2),
            (0.4, 0.3, 0.2),
            (0.4, 0.4, 0.3),
            (0.6, 0.6, 0.6),
            (0.8, 0.8, 0.8),
        )
        iter_interp_relacion_presion_negativa = (
            np.interp(
                self.altura_media / self.ancho, relaciones_altura_longitud, cp_tuple
            )
            for cp_tuple in valores_cp_presion_negativa
        )
        iter_interp_relacion_presion_positiva = (
            np.interp(
                self.altura_media / self.ancho, relaciones_altura_longitud, cp_tuple
            )
            for cp_tuple in valores_cp_presion_positiva
        )
        interp_relacion_presion_negativa = np.fromiter(
            iter_interp_relacion_presion_negativa, float
        )
        interp_relacion_presion_positiva = np.fromiter(
            iter_interp_relacion_presion_positiva, float
        )
        cp_presion_negativa: float = np.interp(
            self.angulo, angulos, interp_relacion_presion_negativa
        )
        cp_presion_positiva: float = np.interp(
            self.angulo, angulos, interp_relacion_presion_positiva
        )

        return {
            TipoPresionCubiertaBarloventoSprfv.NEGATIVA: cp_presion_negativa,
            TipoPresionCubiertaBarloventoSprfv.POSITIVA: cp_presion_positiva,
        }

    def _cp_cubierta_sotavento(self) -> float:
        """Calcula por interpolación el coeficiente de presión para la cubierta a sotavento.

        Returns:
            Los coeficientes de presión para cubierta a barlovento.

        Raises:
            ValueError: Cuando el ángulo de cubierta es < 10°.
        """
        if self.angulo < 10:
            raise ValueError(
                "No se pueden calcular los valores, el ángulo de "
                "cubierta debe ser ≥ 10° para usar este método."
            )
        relaciones_altura_longitud = (0.25, 0.5, 1)
        angulos = (10, 15, 20)
        valores_cp = ((-0.3, -0.5, -0.7), (-0.5, -0.5, -0.6), (-0.6, -0.6, -0.6))
        iter_interp_relacion = (
            np.interp(
                self.altura_media / self.ancho, relaciones_altura_longitud, cp_tuple
            )
            for cp_tuple in valores_cp
        )
        relation_interp_cp = np.fromiter(iter_interp_relacion, float)
        cp: float = np.interp(self.angulo, angulos, relation_interp_cp)
        return cp

    def _zonas_cubierta(
        self, dimension_paralela: float, *distancias_extras: float
    ) -> tuple[ParNumerico, ...]:
        """
        Args:
            dimension_paralela: La longitud de la dimension paralela a la dirección del viento.
            *distancias_extras: Alturas a ser consideradas en el cálculo de las zonas de cubierta.

        Returns:
            Las zonas de la cubierta.
        """
        distancia_codigo = (
            *self.distancias_codigo,
            dimension_paralela,
            *tuple(distancias_extras),
        )
        distancias_unicas = sorted(set(distancia_codigo))
        distancias_filtradas = tuple(
            dist for dist in distancias_unicas if dist <= dimension_paralela
        )
        return tuple(zona for zona in itertools.pairwise(distancias_filtradas))

    @staticmethod
    def _area_cp_cubierta(
        altura_media_cubierta: float, dimension_paralela: float, dimension_normal: float
    ) -> float:
        """Calcula el area correspondiente al producto entre el menor valor entre la mitad de la altura media de cubierta
        y la dimensión paralela, y la dimensión normal.

        Args:
            altura_media_cubierta: La altura media de cubierta.
            dimension_paralela: La longitud de la dimension paralela a la dirección del viento.
            dimension_normal: La longitud de la dimension normal a la dirección del viento.

        Returns:
            El area calculada.
        """
        min_dimension = min(altura_media_cubierta / 2, dimension_paralela)
        return min_dimension * dimension_normal


class AleroSprfvMetodoDireccional(CubiertaSprfvMetodoDireccional):
    """AleroSprfvMetodoDireccional.

    Determina los coeficientes de presión de alero de cubierta de edificio para SPRFV usando el método direccional.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.zona = ZonaEdificio.ALERO

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión del alero para el SPRFV.

        Con el viento paralelo a la cumbrera el alero toma los coeficientes de
        la cubierta. Con el viento normal no se divide en zonas: a barlovento el
        coeficiente se reduce en 0.8 y a sotavento se mantiene. Con el viento
        normal y ángulo menor que 10° se repite el caso de presión positiva de
        la cubierta.

        Returns:
            Un coeficiente por cada zona o posición y dirección del viento.
        """
        entradas = self._entradas_cubierta()
        paralelo = [
            entrada
            for entrada in entradas
            if entrada.direccion == DireccionVientoMetodoDireccionalSprfv.PARALELO
        ]
        normal = [
            entrada
            for entrada in entradas
            if entrada.direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
        ]
        if self.normal_como_paralelo:
            negativa = [entrada for entrada in normal if entrada.caso is None]
            positiva = [entrada for entrada in normal if entrada.caso is not None]
            normal = [
                self._entrada(
                    negativa[0].valor - 0.8,
                    direccion=DireccionVientoMetodoDireccionalSprfv.NORMAL,
                    posicion=PosicionCubiertaAleroSprfv.BARLOVENTO,
                ),
                self._entrada(
                    negativa[-1].valor,
                    direccion=DireccionVientoMetodoDireccionalSprfv.NORMAL,
                    posicion=PosicionCubiertaAleroSprfv.SOTAVENTO,
                ),
                self._entrada(
                    positiva[0].valor - 0.8,
                    direccion=DireccionVientoMetodoDireccionalSprfv.NORMAL,
                    posicion=PosicionCubiertaAleroSprfv.BARLOVENTO,
                    caso=TipoPresionCubiertaBarloventoSprfv.POSITIVA,
                ),
                self._entrada(
                    positiva[-1].valor,
                    direccion=DireccionVientoMetodoDireccionalSprfv.NORMAL,
                    posicion=PosicionCubiertaAleroSprfv.SOTAVENTO,
                    caso=TipoPresionCubiertaBarloventoSprfv.POSITIVA,
                ),
            ]
        else:
            normal = [
                replace(entrada, valor=entrada.valor - 0.8)
                if entrada.posicion == PosicionCubiertaAleroSprfv.BARLOVENTO
                else entrada
                for entrada in normal
            ]
        return (*paralelo, *normal)


class CubiertaComponentes:
    """CubiertaComponentes.

    Determina los coeficientes de presión de cubierta de edificio para Componentes y Revestimientos.

    Sólo se proveen las tablas del CIRSOC 102-2025: la Tabla C 5.3-2 (Fig. 5.3-2A,
    cubierta a dos aguas con ángulo <= 7° y altura media <= 20 m), la Tabla C
    5.3-3 (Fig. 5.3-2B, 7° < ángulo <= 20° y altura media <= 20 m), la Tabla C
    5.3-4 (Fig. 5.3-2C, 20° < ángulo <= 27° y altura media <= 20 m), la Tabla C
    5.3-5 (Fig. 5.3-2D, 27° < ángulo <= 45° y altura media <= 20 m), para
    cubiertas a un agua, las Figuras 5.3-5A y 5.3-5B (3° < ángulo <= 10° y
    10° < ángulo <= 30°, ambas con altura media <= 20 m) y, para edificios con
    altura media mayor que 20 m y ángulo <= 7°, la Figura 5.4-1 (paredes y
    cubierta, Nota 6 del Art. 5.4.2). El resto de la geometría (cubiertas a un
    agua con ángulo > 30°, otros ángulos o alturas) todavía no tiene
    lineamientos 2025 migrados y lanza ErrorLineamientos.

    TODO: el alero de las Tablas C 5.3-3, C 5.3-4, C 5.3-5 y de las Figuras
    5.3-5A y 5.3-5B debería resolverse por el Art. 5.7 del reglamento
    (superficie superior + inferior de pared); hoy usa sólo la superficie
    superior (ver issue). El alero de gran altura (Art. 5.7) sigue pendiente.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo: float,
        tipo_cubierta: TipoCubierta,
        parapeto: float = 0,
        es_alero: bool = False,
        componentes: dict[str, float] | None = None,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio (que es igual al de cubierta).
            longitud: La longitud del edificio (que es igual a la de cubierta).
            altura_media: La altura media de cubierta.
            angulo: El ángulo de cubierta.
            tipo_cubierta: El tipo de cubierta.
            parapeto: La dimensión del parapeto.
            es_alero: Indica si los valores de cp se deben calcular para un alero.
            componentes: Los componentes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_media = altura_media
        self.angulo = angulo
        self.tipo_cubierta = tipo_cubierta
        self.parapeto = parapeto
        self.es_alero = es_alero
        self.componentes = componentes
        self.zona = ZonaEdificio.ALERO if es_alero else ZonaEdificio.CUBIERTA

    @cached_property
    def distancia_a(self) -> float:
        """Calcula la distancia "a".
        Returns:
            El valor de distancia "a" del edificio.
        """
        return distancia_a(self.ancho, self.longitud, self.altura_media)

    @cached_property
    def distancias_zonas(self) -> tuple[float, float, float] | None:
        """Las distancias al borde que delimitan las zonas de la Figura 5.3-2A.

        Se miden desde el borde de la cubierta -desde el borde exterior del
        voladizo si existe, Nota 7- y no dependen de la distancia "a": la
        Figura las define en función de la altura del alero "h", que para
        ángulo <= 10° es la altura media de cubierta.

        Returns:
            El espesor de la "L" de la Zona 3 (0,2h), el ancho de la franja
            perimetral que comparten la Zona 3 -es el largo de sus brazos- y la
            Zona 2 (0,6h), y la distancia al borde donde termina la Zona 1
            (1,2h). Ninguno si la referencia no es la Tabla C 5.3-2.
        """
        if self.referencia != "Tabla C 5.3-2":
            return None
        return 0.2 * self.altura_media, 0.6 * self.altura_media, 1.2 * self.altura_media

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Determina los coeficientes de presión para componentes y revestimientos.

        Returns:
            Un coeficiente por cada componente y zona. Ninguno si no se cargaron
            componentes.
        """
        if self.componentes is None:
            return ()
        casos = {
            # CIRSOC 102-2025 - Tabla C 5.3-2 (Figura 5.3-2A), cubierta sin
            # voladizo. Cada zona trae el rango de áreas de su tramo log.
            "Tabla C 5.3-2": {
                ZonaComponenteCubiertaEdificio.UNO_PRIMA: {
                    "cp": (-0.9, -0.4),
                    "area": (10, 100),
                },
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.7, -1),
                    "area": (1, 50),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-2.3, -1.4),
                    "area": (1, 50),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-3.2, -1.4),
                    "area": (1, 50),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.3, 0.2),
                    "area": (1, 10),
                },
            },
            # CIRSOC 102-2025 - Tabla C 5.3-3 (Figura 5.3-2B). Cada zona
            # declara su rango de áreas.
            "Tabla C 5.3-3": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-2.0, -0.5),
                    "area": (2, 30),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-2.7, -1.0),
                    "area": (1, 20),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-3.6, -1.8),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.6, 0.3),
                    "area": (1, 20),
                },
            },
            # CIRSOC 102-2025 - Tabla C 5.3-4 (Figura 5.3-2C). Cada zona
            # declara su rango de áreas.
            "Tabla C 5.3-4": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.5, -0.8),
                    "area": (1, 20),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-2.5, -1.2),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-3.0, -1.4),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.6, 0.3),
                    "area": (1, 20),
                },
            },
            # CIRSOC 102-2025 - Tabla C 5.3-5 (Figura 5.3-2D). Cada zona
            # declara su rango de áreas.
            "Tabla C 5.3-5": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.8, -0.8),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-2.0, -1.0),
                    "area": (1, 20),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-2.5, -1.0),
                    "area": (1, 20),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.9, 0.5),
                    "area": (1, 20),
                },
            },
            # CIRSOC 102-2025 - Figura 5.3-5A (cubierta a un agua, 3° < ángulo
            # <= 10° y altura media <= 20 m). Cada zona declara su rango de
            # áreas.
            "Figura 5.3-5A": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.1, -1.1),
                    "area": (0.1, 100),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-1.3, -1.2),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.DOS_PRIMA: {
                    "cp": (-1.6, -1.5),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-1.8, -1.2),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TRES_PRIMA: {
                    "cp": (-2.6, -1.6),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.3, 0.2),
                    "area": (1, 10),
                },
            },
            # CIRSOC 102-2025 - Figura 5.3-5B (cubierta a un agua, 10° < ángulo
            # <= 30° y altura media <= 20 m). Cada zona declara su rango de
            # áreas.
            "Figura 5.3-5B": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.3, -1.1),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-1.6, -1.2),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-2.9, -2.0),
                    "area": (1, 10),
                },
                ZonaComponenteCubiertaEdificio.TODAS: {
                    "cp": (0.4, 0.3),
                    "area": (1, 10),
                },
            },
            # CIRSOC 102-2025 - Figura 5.4-1 (h > 20 m y ángulo <= 7°): los GCp
            # de cubierta de C&R de edificios de gran altura, la reemplazante
            # de la Figura 8 del 2005. La cubierta no lleva positivo. El
            # rango de áreas es el de la Figura, (1, 50).
            "Figura 5.4-1": {
                ZonaComponenteCubiertaEdificio.UNO: {
                    "cp": (-1.4, -0.9),
                    "area": (1, 50),
                },
                ZonaComponenteCubiertaEdificio.DOS: {
                    "cp": (-2.3, -1.6),
                    "area": (1, 50),
                },
                ZonaComponenteCubiertaEdificio.TRES: {
                    "cp": (-3.2, -2.3),
                    "area": (1, 50),
                },
            },
        }
        if self.es_alero:
            # Tabla C 5.3-2, bloque "Negativo con voladizo". Las Zonas 1 y
            # 1' comparten curva y los valores ya incluyen las presiones de
            # las superficies superior e inferior del voladizo (Nota 6).
            # Las Tablas C 5.3-3, 5.3-4, 5.3-5 y la Figura 5.3-5A resuelven
            # el voladizo por el Art. 5.7 (aún pendiente, ver issue): por
            # ahora el alero usa la superficie superior, o sea el bloque de
            # la cubierta.
            casos["Tabla C 5.3-2"].update(
                {
                    ZonaComponenteCubiertaEdificio.UNO_PRIMA: {
                        "cp": ((-1.7, -1.6), (-1.6, -1)),
                        "area": ((1, 10), (10, 50)),
                    },
                    ZonaComponenteCubiertaEdificio.UNO: {
                        "cp": ((-1.7, -1.6), (-1.6, -1)),
                        "area": ((1, 10), (10, 50)),
                    },
                    ZonaComponenteCubiertaEdificio.DOS: {
                        "cp": (-2.3, -1.1),
                        "area": (1, 50),
                    },
                    ZonaComponenteCubiertaEdificio.TRES: {
                        "cp": (-3.2, -1.1),
                        "area": (1, 50),
                    },
                }
            )

        caso_cp = casos[self.referencia]
        if self.es_alero:
            caso_cp.pop(ZonaComponenteCubiertaEdificio.TODAS, None)

        # CIRSOC 102-2025 - Nota de parapeto: la Fig. 5.3-2A (Nota 5) y la
        # Fig. 5.4-1 (Nota 7) igualan la Zona 3 negativa a la Zona 2; la
        # primera pide parapeto de 1 m o más y la segunda, además, ángulo
        # <= 10°. El positivo propio de las Zonas 2 y 3 lo agrega
        # _entradas_positivas_nota_parapeto y es de la Fig. 5.3-2A
        # solamente: la 5.4-1 no lleva positivo de cubierta. La Tabla C 5.3-3
        # no trae nota de parapeto.
        if self.referencia == "Tabla C 5.3-2":
            aplica_nota_parapeto = self.parapeto >= 1
        else:
            aplica_nota_parapeto = (
                self.referencia == "Figura 5.4-1"
                and self.parapeto >= 1
                and self.angulo <= 10
            )
        if aplica_nota_parapeto:
            caso_cp[ZonaComponenteCubiertaEdificio.TRES] = caso_cp[
                ZonaComponenteCubiertaEdificio.DOS
            ]
        entradas = []
        for nombre, area_componente in self.componentes.items():
            for zona, cps in caso_cp.items():
                cp_filtrado, area_filtrada = seleccionar_cp_area(
                    cps["cp"], cps["area"], area_componente
                )
                entradas.append(
                    self._entrada(
                        nombre,
                        zona,
                        float(
                            calcular_cp_componente(
                                cp_filtrado, area_filtrada, area_componente
                            )
                        ),
                        tipo_presion_componente(zona),
                    )
                )
            entradas += self._entradas_positivas_nota_parapeto(
                nombre, area_componente, aplica_nota_parapeto
            )
        return tuple(entradas)

    def _entrada(
        self,
        componente: str,
        zona: ZonaComponenteCubiertaEdificio,
        valor: float,
        tipo_presion: TipoPresionComponentesParedesCubierta,
    ) -> EntradaCp:
        """Arma la entrada de una zona.

        Args:
            componente: El nombre del componente.
            zona: La zona del Reglamento.
            valor: El valor de cp.
            tipo_presion: El signo del coeficiente externo.

        Returns:
            La entrada de cp.
        """
        return EntradaCp(
            zona=self.zona,
            sistema=SistemaResistente.COMPONENTES,
            valor=valor,
            referencia=self.referencia,
            componente=componente,
            zona_componente=zona,
            distancia_a=self.distancia_a,
            tipo_presion=tipo_presion,
        )

    def _entradas_positivas_nota_parapeto(
        self, componente: str, area_componente: float, aplica_nota_parapeto: bool
    ) -> list[EntradaCp]:
        """Los positivos propios de las Zonas 2 y 3 cuando hay parapeto.

        La Nota 5 de la Figura 5.3-2A los iguala a los de las Zonas de pared 4
        y 5, con lo que el positivo deja de ser único: las Zonas 1' y 1 siguen
        con el de la zona "todas". La Nota es de la Figura de cubierta y no
        aplica al alero, que no lleva positivo.

        Args:
            componente: El nombre del componente.
            area_componente: Area tributaria del componente.
            aplica_nota_parapeto: Indica si el parapeto llega a la dimensión
                que pide la Nota.

        Returns:
            Una entrada por zona, o ninguna si la Nota no aplica.
        """
        if (
            not aplica_nota_parapeto
            or self.referencia != "Tabla C 5.3-2"
            or self.es_alero
        ):
            return []
        valor = cp_positivo_paredes(area_componente, self.angulo)
        return [
            self._entrada(
                componente,
                zona,
                valor,
                TipoPresionComponentesParedesCubierta.POSITIVA,
            )
            for zona in (
                ZonaComponenteCubiertaEdificio.DOS,
                ZonaComponenteCubiertaEdificio.TRES,
            )
        ]

    @cached_property
    def referencia(self) -> str:
        """Determina la tabla de C&R del CIRSOC 102-2025 que corresponde.

        Returns:
            La referencia de la figura o tabla en el código.

        Raises:
            ErrorLineamientos: Cuando la geometría excede el alcance del
                reglamento 2025 para componentes y revestimientos de cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return self._referencia_un_agua()
        if self.altura_media > 20:
            return self._referencia_gran_altura()
        if self.angulo <= 7:
            return "Tabla C 5.3-2"
        if self.angulo <= 20:
            return "Tabla C 5.3-3"
        if self.angulo <= 27:
            return "Tabla C 5.3-4"
        if self.angulo <= 45:
            return "Tabla C 5.3-5"
        raise excepciones.ErrorLineamientos(
            "El CIRSOC 102-2025 aún no provee lineamientos para calcular "
            "los coeficientes de presión para Componentes y Revestimientos "
            "de cubiertas a dos aguas con ángulo > 45° (Figuras 5.3-2 E a G "
            "pendientes de migrar)."
        )

    def _referencia_gran_altura(self) -> str:
        """Determina la referencia de la figura para edificios de gran altura.

        Con h > 20 m la Nota 6 de la Figura 5.4-1 y el Art. 5.4.2 resuelven
        las cubiertas con ángulo <= 7° con esa misma Figura; el resto (ángulos
        mayores y los aleros) sigue pendiente de migrar en el 2025.

        Returns:
            La referencia de la figura o tabla en el código.

        Raises:
            ErrorLineamientos: Cuando la geometría excede el alcance del
                reglamento 2025 para componentes y revestimientos de cubierta.
        """
        if not self.es_alero and self.angulo <= 7:
            return "Figura 5.4-1"
        raise excepciones.ErrorLineamientos(
            "El CIRSOC 102-2025 aún no provee lineamientos para calcular "
            "los coeficientes de presión para Componentes y Revestimientos "
            "de cubiertas de edificios con altura media mayor que 20 m y "
            "ángulo mayor que 7° (Figuras 5.3-2 E a G pendientes de migrar "
            "y el alero de gran altura por el Art. 5.7)."
        )

    def _referencia_un_agua(self) -> str:
        """Determina la referencia de la figura para cubiertas a un agua.

        La Nota 5 de la Figura 5.3-5A envía los ángulos <= 3° a la Figura
        5.3-2A (Tabla C 5.3-2). La altura media de cubierta coincide con la
        altura de alero para ángulo <= 10° (ver geometría), así que la "a" de
        las Figuras 5.3-5A y 5.3-5B, que miden con la altura de alero, se
        calcula bien con la altura media.

        Returns:
            La referencia de la figura o tabla en el código.

        Raises:
            ErrorLineamientos: Cuando la geometría excede el alcance del
                reglamento 2025 para componentes y revestimientos de cubierta.
        """
        if self.altura_media > 20:
            return self._referencia_gran_altura()
        if self.angulo <= 3:
            return "Tabla C 5.3-2"
        if self.angulo <= 10:
            return "Figura 5.3-5A"
        if self.angulo <= 30:
            return "Figura 5.3-5B"
        raise excepciones.ErrorLineamientos(
            "El CIRSOC 102-2025 aún no provee lineamientos para calcular "
            "los coeficientes de presión para Componentes y Revestimientos "
            "de cubiertas a un agua con ángulo > 30° (figuras siguientes a la "
            "5.3-5B pendientes de migrar)."
        )


class Paredes:
    """Paredes.

    Determina los coeficientes de presión de paredes de edificio para SPRFV - Componentes y Revestimientos.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo_cubierta: float,
        componentes: dict[str, float] | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_media: La altura media de cubierta del edificio.
            angulo_cubierta: El ángulo de cubierta del edificio.
            componentes: Los componentes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
            metodo_sprfv: El metodo a utilizar para calcular los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = ParedesSprfvMetodoDireccional(ancho, longitud)
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = ParedesComponentes(
            ancho, longitud, altura_media, angulo_cubierta, componentes
        )

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Los coeficientes de presión para el SPRFV y para componentes.

        Returns:
            Las entradas de ambos sistemas resistentes.
        """
        return (*self.sprfv.entradas, *self.componentes.entradas)


class Cubierta:
    """Cubierta.

    Determina los coeficientes de presión de cubierta de edificio para SPRFV - Componentes y Revestimientos.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo: float,
        tipo_cubierta: TipoCubierta,
        parapeto: float = 0,
        componentes: dict[str, float] | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_media: La altura media de cubierta del edificio.
            angulo: El ángulo de cubierta.
            tipo_cubierta: El tipo de cubierta.
            parapeto: La dimensión del parapeto.
            componentes: Los componentes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
            metodo_sprfv: El metodo a utilizar para calcular los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = CubiertaSprfvMetodoDireccional(
                ancho, longitud, altura_media, angulo, tipo_cubierta
            )
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = CubiertaComponentes(
            ancho,
            longitud,
            altura_media,
            angulo,
            tipo_cubierta,
            parapeto,
            False,
            componentes,
        )

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Los coeficientes de presión para el SPRFV y para componentes.

        Returns:
            Las entradas de ambos sistemas resistentes.
        """
        return (*self.sprfv.entradas, *self.componentes.entradas)


class Alero:
    """Alero.

    Determina los coeficientes de presión de alero de cubierta de edificio para SPRFV - Componentes y Revestimientos.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo: float,
        tipo_cubierta: TipoCubierta,
        componentes: dict[str, float] | None = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_media: La altura media de cubierta del edificio.
            angulo: El ángulo de cubierta del edificio.
            tipo_cubierta: El tipo de cubierta.
            componentes: Los componentes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
            metodo_sprfv: El metodo a utilizar para calcular los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = AleroSprfvMetodoDireccional(
                ancho, longitud, altura_media, angulo, tipo_cubierta
            )
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = CubiertaComponentes(
            ancho, longitud, altura_media, angulo, tipo_cubierta, 0, True, componentes
        )

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Los coeficientes de presión para el SPRFV y para componentes.

        Returns:
            Las entradas de ambos sistemas resistentes.
        """
        return (*self.sprfv.entradas, *self.componentes.entradas)


class Edificio:
    """Edificio.

    Determina los coeficientes de presión de edificio para SPRFV - Componentes y Revestimientos.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo_cubierta: float,
        tipo_cubierta: TipoCubierta,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
        alero: float = 0,
        parapeto: float = 0,
        componentes_paredes: dict[str, float] | None = None,
        componentes_cubierta: dict[str, float] | None = None,
    ):
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_media: La altura media de cubierta del edificio.
            angulo_cubierta: El ángulo de cubierta del edificio.
            tipo_cubierta: El tipo de cubierta.
            metodo_sprfv: El metodo a utilizar para calcular los coeficientes de presión para el SPRFV.
            parapeto: La dimensión del parapeto.
            componentes_paredes: Los componentes de paredes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
            componentes_cubierta: Los componentes de cubierta para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
        """
        self.paredes = Paredes(
            ancho,
            longitud,
            altura_media,
            angulo_cubierta,
            componentes_paredes,
            metodo_sprfv,
        )
        self.cubierta = Cubierta(
            ancho,
            longitud,
            altura_media,
            angulo_cubierta,
            tipo_cubierta,
            parapeto,
            componentes_cubierta,
            metodo_sprfv,
        )
        if alero:
            self.alero = Alero(
                ancho,
                longitud,
                altura_media,
                angulo_cubierta,
                tipo_cubierta,
                componentes_cubierta,
                metodo_sprfv,
            )

    @cached_property
    def entradas(self) -> tuple[EntradaCp, ...]:
        """Los coeficientes de presión de todo el edificio.

        Returns:
            Las entradas de paredes, cubierta y alero.
        """
        entradas = (*self.paredes.entradas, *self.cubierta.entradas)
        alero: Alero | None = getattr(self, "alero", None)
        if alero is not None:
            entradas += alero.entradas
        return entradas

    @classmethod
    def desde_geometria_edifico(
        cls,
        edificio: geometria.Edificio,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
        componentes_paredes: dict[str, float] | None = None,
        componentes_cubierta: dict[str, float] | None = None,
    ):
        """Crea una instancia desde la geometria de una cubierta.

        Args:
            edificio: La geometria de un edificio.
            metodo_sprfv: El metodo a utilizar para calcular los coeficientes de presión para el SPRFV.
            componentes_paredes: Los componentes de paredes para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
            componentes_cubierta: Los componentes de cubierta para calcular los valores de cp, donde "key" es el nombre del componente
                y "value" es el area del mismo. Requerido para calcular las presiones sobre los componentes y
                revestimientos.
        """
        return cls(
            edificio.ancho,
            edificio.longitud,
            edificio.cubierta.altura_media,
            edificio.cubierta.angulo,
            edificio.tipo_cubierta,
            metodo_sprfv,
            edificio.alero,
            edificio.parapeto,
            componentes_paredes,
            componentes_cubierta,
        )
