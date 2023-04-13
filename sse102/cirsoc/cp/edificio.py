from collections import defaultdict
from functools import cached_property
from math import log10
from typing import Tuple, Union, Dict, Optional

import numpy as np

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.enums import (
    TipoCubierta,
    MetodoSprfv,
    DireccionVientoMetodoDireccionalSprfv,
    ParedEdificioSprfv,
    PosicionCubiertaAleroSprfv,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaComponenteParedEdificio,
    ZonaComponenteCubiertaEdificio,
    SistemaResistente,
    ZonaEdificio,
)
from zonda.tipos import (
    ParNumerico,
    ValoresCpParedesEdificioSprfvMetodoDireccional,
    ValoresCpParedesEdificioComponentes,
    ValoresCpCubiertaEdificioSprfvMetodoDireccional,
    ValoresCpCubiertaEdificioComponentes,
    ValoresCpAleroEdificioSprfvMetodoDireccional,
    ValoresCpAleroEdificioMetodoDireccional,
    ValoresCpParedesEdificioMetodoDireccional,
    ValoresCpCubiertaEdificioMetodoDireccional,
    ValoresCpEdificioMetodoDireccional,
)


# TODO - El type hint deberia aceptar lista o array
def seleccionar_cp_area(
    cps: Union[ParNumerico, Tuple[ParNumerico, ...]],
    areas: Union[ParNumerico, Tuple[ParNumerico, ...]],
    area_componente: float,
) -> Union[ParNumerico, Tuple[ParNumerico, ...]]:
    """Selecciona las areas y cps para luego interpolar el valor de area tributaria del componente.

    Es util, por ejemplo cuando hay mas de dos valores de area para interpolar, como el en Reglamento CIRSOC 102-2005
    Figura 5B - Cubierta a dos Aguas <= 10° - Aleros. En este caso se detecta entre que valores de area se encuentra el
    area del componente y se retorna esos valores de area con sus respectivos cps para luego usarse en la interpolación.

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
            primer_area, ultima_area = area
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
    def valores(self) -> ValoresCpParedesEdificioSprfvMetodoDireccional:
        """Calcula los valores de coeficiente de presión.

        Returns:
            Los valores de cp para dirección del viento normal y paralelo a la cumbrero para paredes barlovento, sotavento y lateral.
        """
        pared_sotavento_cp_paralelo = self._cp_pared_sotavento(
            self.longitud, self.ancho
        )
        pared_sotavento_cp_normal = self._cp_pared_sotavento(self.ancho, self.longitud)
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: {
                ParedEdificioSprfv.BARLOVENTO: 0.8,
                ParedEdificioSprfv.LATERAL: -0.7,
                ParedEdificioSprfv.SOTAVENTO: pared_sotavento_cp_paralelo,
            },
            DireccionVientoMetodoDireccionalSprfv.NORMAL: {
                ParedEdificioSprfv.BARLOVENTO: 0.8,
                ParedEdificioSprfv.LATERAL: -0.7,
                ParedEdificioSprfv.SOTAVENTO: pared_sotavento_cp_normal,
            },
        }

    @cached_property
    def referencia(self) -> str:
        """
        Returns:
            La referencia de la figura en el código.
        """
        return "Figura 3 (cont.)"

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

    def __call__(self) -> ValoresCpParedesEdificioSprfvMetodoDireccional:
        return self.valores


class ParedesMetodoEnvolvente:
    pass


class ParedesComponentes:
    """ParedesComponentes.

    Determina los coeficientes de presión de paredes de edificio para Componentes y Revestimientos.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_media: float,
        angulo_cubierta: float,
        componentes: Optional[Dict[str, float]] = None,
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
            self.referencia = "Figura 5A"
        else:
            self.referencia = "Figura 8"

    @cached_property
    def valores(self) -> Union[None, ValoresCpParedesEdificioComponentes]:
        """Calcula los valores de coeficiente de presión para Componentes y Revestimientos de paredes.

        Returns:
            Los valores de coeficiente de presión para cada pared y componente de la misma.
        """
        if self.componentes is None:
            return
        valores_zonas_cp = {
            "Figura 5A": {
                ZonaComponenteParedEdificio.CUATRO: (-1.1, -0.8),
                ZonaComponenteParedEdificio.CINCO: (-1.4, -0.8),
                ZonaComponenteParedEdificio.TODAS: (1, 0.7),
            },
            "Figura 8": {
                ZonaComponenteParedEdificio.CUATRO: (-0.9, -0.7),
                ZonaComponenteParedEdificio.CINCO: (-1.8, -1),
                ZonaComponenteParedEdificio.TODAS: (0.9, 0.6),
            },
        }
        factor_reduccion = 1
        if self.referencia == "Figura 8":
            area = (2, 50)
        else:
            area = (1, 50)
            if self.angulo_cubierta <= 10:
                factor_reduccion = 0.9
        caso_cp = valores_zonas_cp[self.referencia]
        valor_cp = defaultdict(dict)
        for nombre, area_componente in self.componentes.items():
            for zona, cp in caso_cp.items():
                valor_cp[nombre][zona] = (
                    calcular_cp_componente(cp, area, area_componente) * factor_reduccion
                )
        return valor_cp

    @cached_property
    def distancia_a(self) -> float:
        """
        Returns:
            El valor de distancia "a" del edificio.
        """
        return distancia_a(self.ancho, self.longitud, self.altura_media)

    def __call__(self) -> ValoresCpParedesEdificioComponentes:
        return self.valores


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
        if self.angulo < 10:
            return True
        return False

    @cached_property
    def zonas(
        self,
    ) -> Dict[
        DireccionVientoMetodoDireccionalSprfv, Union[Tuple[ParNumerico, ...], None]
    ]:
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
    def valores(self) -> ValoresCpCubiertaEdificioSprfvMetodoDireccional:
        """Calcula los valores de coeficiente de presión para cubierta para SPRFV.

        Returns:
            Los valores de cp para direccion de viento normal y paralelo a la cumbrera para cada zona de la cubierta
            según corresponda.
        """
        cp_paralelo = self._cp_cubierta_angulo_menor_diez(
            self.longitud,
            self.ancho,
            len(self.zonas[DireccionVientoMetodoDireccionalSprfv.PARALELO]),
        )
        if self.normal_como_paralelo:
            zonas = self.zonas[DireccionVientoMetodoDireccionalSprfv.NORMAL]
            numero_zonas = len(self.zonas[DireccionVientoMetodoDireccionalSprfv.NORMAL])
            mitad_ancho = self.ancho / 2
            mitad_ancho_en_distancias_codigo = mitad_ancho in self.distancias_codigo
            restar_zona_y_sumar_cp = (
                self.tipo_cubierta == TipoCubierta.DOS_AGUAS
                and not mitad_ancho_en_distancias_codigo
            )
            # Al agregar una zona porque las distancias de zonas de viento no coinciden
            # con la mitad del ancho o el ancho, se debe agregar el cp correspondiente a esa
            # distancia que se suma
            if restar_zona_y_sumar_cp:
                numero_zonas -= 1
            cp_normal = self._cp_cubierta_angulo_menor_diez(
                self.ancho, self.longitud, numero_zonas
            )
            if restar_zona_y_sumar_cp:
                indice = tuple(
                    i for i, (inicio, fin) in enumerate(zonas) if fin == mitad_ancho
                )[0]
                cp_normal = np.insert(cp_normal, indice + 1, cp_normal[indice])
        else:
            cp_barlovento = self._cp_cubierta_barlovento()
            cp_sotavento = self._cp_cubierta_sotavento()
            cp_normal = {
                PosicionCubiertaAleroSprfv.BARLOVENTO: cp_barlovento,
                PosicionCubiertaAleroSprfv.SOTAVENTO: cp_sotavento,
            }
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: cp_paralelo,
            DireccionVientoMetodoDireccionalSprfv.NORMAL: cp_normal,
        }

    @cached_property
    def referencia(self) -> str:
        """
        Returns:
            La referencia de la figura en el código.
        """
        return "Figura 3 (cont.)"

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
    ) -> Dict[TipoPresionCubiertaBarloventoSprfv, float]:
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
            (0, 0, 0),
            (0, 0, 0),
            (0.2, 0, 0),
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
    ) -> Tuple[ParNumerico, ...]:
        """
        Args:
            dimension_paralela: La longitud de la dimension paralela a la dirección del viento.
            *distancias_extras: Alturas a ser consideradas en el cálculo de las zonas de cubierta.

        Returns:
            Las zonas de la cubierta.
        """
        distancia_codigo = (
            self.distancias_codigo + (dimension_paralela,) + tuple(distancias_extras)
        )
        distancias_unicas = sorted(set(distancia_codigo))
        distancias_filtradas = tuple(
            dist for dist in distancias_unicas if dist <= dimension_paralela
        )
        return tuple(
            zona for zona in zip(distancias_filtradas, distancias_filtradas[1:])
        )

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

    def __call__(self) -> ValoresCpCubiertaEdificioSprfvMetodoDireccional:
        return self.valores


class CubiertaMetodoEnvolvente:
    pass


class AleroSprfvMetodoDireccional(CubiertaSprfvMetodoDireccional):
    """AleroSprfvMetodoDireccional.

    Determina los coeficientes de presión de alero de cubierta de edificio para SPRFV usando el método direccional.
    """

    @cached_property
    def valores(self) -> ValoresCpAleroEdificioSprfvMetodoDireccional:
        """
        Returns:
            Los valores de cp para direccion de viento normal y paralelo a la cumbrera para cada zona del alero según
            corresponda.
        """
        valores = super().valores
        if self.normal_como_paralelo:
            cps = tuple(
                cp for cp in valores[DireccionVientoMetodoDireccionalSprfv.NORMAL]
            )
            cp_barlovento = cps[0] - 0.8
            cp_sotavento = cps[-1]
        else:
            cp_barlovento = {
                key: valor - 0.8
                for key, valor in valores[DireccionVientoMetodoDireccionalSprfv.NORMAL][
                    PosicionCubiertaAleroSprfv.BARLOVENTO
                ].items()
            }
            cp_sotavento = valores[DireccionVientoMetodoDireccionalSprfv.NORMAL][
                PosicionCubiertaAleroSprfv.SOTAVENTO
            ]
        valores[DireccionVientoMetodoDireccionalSprfv.NORMAL] = {
            PosicionCubiertaAleroSprfv.BARLOVENTO: cp_barlovento,
            PosicionCubiertaAleroSprfv.SOTAVENTO: cp_sotavento,
        }
        return valores

    def __call__(self) -> ValoresCpAleroEdificioSprfvMetodoDireccional:
        return self.valores


class AleroMetodoEnvolvente:
    pass


class CubiertaComponentes:
    """CubiertaComponentes.

    Determina los coeficientes de presión de cubierta de edificio para Componentes y Revestimientos.
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
        componentes: Optional[Dict[str, float]] = None,
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

    @cached_property
    def distancia_a(self) -> float:
        """Calcula la distancia "a".
        Returns:
            El valor de distancia "a" del edificio.
        """
        return distancia_a(self.ancho, self.longitud, self.altura_media)

    @cached_property
    def valores(self) -> Union[None, ValoresCpCubiertaEdificioComponentes]:
        """Calcula los valores de coeficiente de presión para componentes y revestimientos de cubierta a dos aguas o plana.

        Returns:
            Los valores de coeficiente de presión para cada componente y zona.
        """
        if self.componentes is None:
            return
        casos = {
            "Figura 5B": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-1, -0.9)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-1.8, -1.1)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-2.8, -1.1)},
                ZonaComponenteCubiertaEdificio.TODAS: {"cp": (0.3, 0.2)},
            },
            "Figura 5B (cont.) 1": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-0.9, -0.8)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-2.1, -1.4)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-2.1, -1.4)},
                ZonaComponenteCubiertaEdificio.TODAS: {"cp": (0.5, 0.3)},
            },
            "Figura 5B (cont.) 2": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-1, -0.8)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-1.2, -1)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-1.2, -1)},
                ZonaComponenteCubiertaEdificio.TODAS: {"cp": (0.9, 0.8)},
            },
            "Figura 7A": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-1.1, -1.1)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-1.3, -1.2)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-1.8, -1.2)},
                ZonaComponenteCubiertaEdificio.DOS_PRIMA: {"cp": (-1.6, -1.5)},
                ZonaComponenteCubiertaEdificio.TRES_PRIMA: {"cp": (-2.6, -1.6)},
                ZonaComponenteCubiertaEdificio.TODAS: {"cp": (0.3, 0.2)},
            },
            "Figura 7A (cont.)": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-1.3, -1.1)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-1.6, -1.2)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-2.9, -2)},
                ZonaComponenteCubiertaEdificio.TODAS: {"cp": (0.4, 0.3)},
            },
            "Figura 8": {
                ZonaComponenteCubiertaEdificio.UNO: {"cp": (-1.4, -0.9)},
                ZonaComponenteCubiertaEdificio.DOS: {"cp": (-2.3, -1.6)},
                ZonaComponenteCubiertaEdificio.TRES: {"cp": (-3.2, -2.3)},
            },
        }
        if self.es_alero:
            casos_alero = {
                "Figura 5B": {
                    ZonaComponenteCubiertaEdificio.UNO: {
                        "cp": ((-1.7, -1.6), (-1.6, -1.1)),
                        "area": ((1, 10), (10, 50)),
                    },
                    ZonaComponenteCubiertaEdificio.DOS: {
                        "cp": ((-1.7, -1.6), (-1.6, -1.1)),
                        "area": ((1, 10), (10, 50)),
                    },
                    ZonaComponenteCubiertaEdificio.TRES: {"cp": (-2.8, -0.8)},
                },
                "Figura 5B (cont.) 1": {
                    ZonaComponenteCubiertaEdificio.DOS: {"cp": (-2.2, -2.2)},
                    ZonaComponenteCubiertaEdificio.TRES: {"cp": (-3.7, -2.5)},
                },
                "Figura 5B (cont.) 2": {
                    ZonaComponenteCubiertaEdificio.DOS: {"cp": (-2.0, -1.8)},
                    ZonaComponenteCubiertaEdificio.TRES: {"cp": (-2.0, -1.8)},
                },
            }
            for caso_alero, diccionario in casos_alero.items():
                casos[caso_alero].update(diccionario)

        caso_cp = casos[self.referencia]
        if self.es_alero:
            caso_cp.pop(ZonaComponenteCubiertaEdificio.TODAS, None)

        if self.referencia in ("Figura 5B", "Figura 8") and self.parapeto > 1:
            # CIRSOC 102 - 2005 (Fig. 5B -Nota de pie 5 y Fig. 8 Nota de pie 7)
            caso_cp[ZonaComponenteCubiertaEdificio.TRES] = caso_cp[
                ZonaComponenteCubiertaEdificio.DOS
            ]
        if self.referencia == "Figura 8":
            # Areas techo grandes alturas -CIRSOC 102 (2005) Fig. 8
            area = (1, 50)
        else:
            # Areas techo pequeñas alturas -CIRSOC 102 (2005) Fig. 5B)
            area = (1, 10)
        valor_cp = defaultdict(dict)
        for nombre, area_componente in self.componentes.items():
            for zona, cps in caso_cp.items():
                cp = cps["cp"]
                areas = cps.get("area", area)
                cp_filtrado, area_filtrada = seleccionar_cp_area(
                    cp, areas, area_componente
                )
                valor_cp[nombre][zona] = calcular_cp_componente(
                    cp_filtrado, area_filtrada, area_componente
                )
        return valor_cp

    @cached_property
    def referencia(self) -> str:
        """Determina referencia de la figura en el código.

        Returns:
            La referencia de la figura en el código.
        """
        if self.tipo_cubierta != TipoCubierta.UN_AGUA or self.es_alero:
            return self._referencia_dos_aguas()
        return self._referencia_un_agua()

    def _referencia_dos_aguas(self) -> str:
        """Determina referencia de la figura en el código para cubiertas a dos aguas o planas.

        Returns:
            La referencia de la figura en el código.

        Raises:
            ErrorLineamientos cuando la cubierta tiene un angulo > 45°.
        """
        if self.angulo <= 10 and self.altura_media > 20 and not self.es_alero:
            return "Figura 8"
        elif self.angulo <= 10:
            return "Figura 5B"
        elif 10 < self.angulo <= 30:
            return "Figura 5B (cont.) 1"
        elif 30 < self.angulo <= 45:
            return "Figura 5B (cont.) 2"
        raise excepciones.ErrorLineamientos(
            "El Reglamento CIRSOC 102-2005 no provee lineamientos para calcular los coeficientes de presión para"
            " Componentes y Revestimientos de cubiertas a dos aguas con ángulo > 45°."
        )

    def _referencia_un_agua(self) -> str:
        """
        Returns:
            La referencia de la figura en el código para cubiertas a un agua.

        Raises:
            ErrorLineamientos cuando la cubierta tiene un ángulo > 30° o cuando el edificio es de gran altura con y el
            ángulo de cubierta es > 10°.
        """
        if self.altura_media > 20:
            if self.angulo <= 10:
                return "Figura 8"
            elif 10 < self.angulo <= 30:
                return "Figura 5B (cont.) 1"
            elif 30 < self.angulo <= 45:
                return "Figura 5B (cont.) 2"
            else:
                raise excepciones.ErrorLineamientos(
                    "El Reglamento CIRSOC 102-2005 no provee lineamientos para calcular los coeficientes de presión para"
                    " Componentes y Revestimientos de cubiertas a un agua con ángulo > 45° y edificios de gran altura."
                )
        if self.angulo <= 3:
            return "Figura 5B"
        elif 3 < self.angulo <= 10:
            return "Figura 7A"
        elif 10 < self.angulo <= 30:
            return "Figura 7A (cont.)"
        raise excepciones.ErrorLineamientos(
            "El Reglamento CIRSOC 102-2005 no provee lineamientos para calcular los coeficientes de presión para"
            " Componentes y Revestimientos de cubiertas a un agua con ángulo > 30°."
        )

    def __call__(self) -> ValoresCpCubiertaEdificioComponentes:
        return self.valores


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
        componentes: Optional[Dict[str, float]] = None,
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
    def valores(self) -> ValoresCpParedesEdificioMetodoDireccional:
        return {
            SistemaResistente.SPRFV: self.sprfv(),
            SistemaResistente.COMPONENTES: self.componentes(),
        }

    def __call__(self) -> ValoresCpParedesEdificioMetodoDireccional:
        return self.valores


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
        componentes: Optional[Dict[str, float]] = None,
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
    def valores(self) -> ValoresCpCubiertaEdificioMetodoDireccional:
        return {
            SistemaResistente.SPRFV: self.sprfv(),
            SistemaResistente.COMPONENTES: self.componentes(),
        }

    def __call__(self) -> ValoresCpCubiertaEdificioMetodoDireccional:
        return self.valores


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
        componentes: Optional[Dict[str, float]] = None,
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
    def valores(self) -> ValoresCpAleroEdificioMetodoDireccional:
        return {
            SistemaResistente.SPRFV: self.sprfv(),
            SistemaResistente.COMPONENTES: self.componentes(),
        }

    def __call__(self) -> ValoresCpAleroEdificioMetodoDireccional:
        return self.valores


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
        componentes_paredes: Optional[Dict[str, float]] = None,
        componentes_cubierta: Optional[Dict[str, float]] = None,
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
    def valores(self) -> ValoresCpEdificioMetodoDireccional:
        valores = {
            ZonaEdificio.PAREDES: self.paredes(),
            ZonaEdificio.CUBIERTA: self.cubierta(),
        }
        alero: Alero = getattr(self, "alero", None)
        if alero is not None:
            valores[ZonaEdificio.ALERO] = alero()
        return valores

    @classmethod
    def desde_geometria_edifico(
        cls,
        edificio: geometria.Edificio,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
        componentes_paredes: Optional[Dict[str, float]] = None,
        componentes_cubierta: Optional[Dict[str, float]] = None,
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

    def __call__(self) -> ValoresCpEdificioMetodoDireccional:
        return self.valores
