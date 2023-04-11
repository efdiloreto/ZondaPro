from __future__ import annotations

from collections import defaultdict
from functools import cached_property, partial
from typing import Dict, TYPE_CHECKING, Optional, Union, Hashable, Sequence, NamedTuple

import numpy as np

from sse102.cirsoc.presiones.base import PresionesBase
from sse102.enums import (
    Cerramiento,
    DireccionVientoMetodoDireccionalSprfv,
    TipoCubierta,
    ParedEdificioSprfv,
    MetodoSprfv,
    SistemaResistente,
    ZonaEdificio,
)

if TYPE_CHECKING:
    from sse102.cirsoc import geometria
    from sse102.cirsoc.cp import edificio as clases_cp_edificio
    from sse102.cirsoc.factores import Rafaga
    from sse102.enums import (
        CategoriaEstructura,
        CategoriaExposicion,
    )
    from sse102.tipos import (
        ValoresPresionesCubiertaEdificioSprfvMetodoDireccional,
        ValoresPresionesAleroEdificioSprfvMetodoDireccional,
        ValoresPresionesParedesEdificioSprfvMetodoDireccional,
        ValoresPresionesParedesEdificioComponentesA,
        ValoresPresionesCubiertaEdificioComponentes,
        ValoresPresionesAleroEdificioComponentes,
        ValoresPresionesParedesEdificioComponentesB,
        ValoresPresionesParedesEdificioComponentes,
        ValoresPresionesCubiertaEdificioMetodoDireccional,
        ValoresPresionesParedesEdificioMetodoDireccional,
        ValoresPresionesAleroEdificioMetodoDireccional,
        ValoresPresionesEdificioMetodoDireccional,
    )


def presion_minima(presion: float):
    """Asigna el valor de presion mínima según CIRSOC 102-05 Art. 1.4.

    Args:
        presion: El valor de presión a comparar.

    Returns: Maximo entre valor de presión minima y el valor de presión.

    """
    return np.sign(presion) * max(500, abs(presion))


class PresionesEdificio(NamedTuple):
    pos: float
    neg: float


class CubiertaSprfvMetodoDireccional(PresionesBase):
    """CubiertaSprfvMetodoDireccional.

    Determina las presiones de cubierta para SPRFV usando el método direccional.
    """

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.CubiertaSprfvMetodoDireccional,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de CubiertaMetodoDireccional.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
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
        self.cerramiento = cerramiento
        self.cp = cp
        self.reducir_gcpi = reducir_gcpi
        self.aberturas_totales = aberturas_totales
        self.volumen_interno = volumen_interno
        self.factores_rafaga = {key: value.factor for key, value in rafaga.items()}
        self._bool_indices_altura_media = alturas == altura_media
        self._presion_media_parcial = partial(
            self._presiones,
            presion_velocidad=self.presion_velocidad_media,
            gcpi=self.gcpi,
            presion_velocidad_media=self.presion_velocidad_media,
        )

    @property
    def coeficiente_exposicion_media(self) -> float:
        """Obtiene el coeficiente de exposición correspondiente a la altura media.

        Returns:
            El coeficiente de exposición correspondiente a la altura media.
        """
        return self.coeficientes_exposicion[self._bool_indices_altura_media][0]

    @cached_property
    def factor_topografico_media(self) -> float:
        """Obtiene el factor topográfico correspondiente a la altura media.

        Returns:
            El factor topográfico correspondiente a la altura media.
        """
        return self.factor_topografico[self._bool_indices_altura_media][0]

    @property
    def presion_velocidad_media(self) -> float:
        """Obtiene la presión de velocidad correspondiente a la altura media.

        Returns:
            La presión de velocidad correspondiente a la altura media.
        """
        return self.presiones_velocidad[self._bool_indices_altura_media][0]

    @cached_property
    def factor_reduccion_gcpi(self) -> float:
        """Calcula el factor de reduccion para el coeficiente de presion interna.

        Returns:
            El factor de reduccion de gcpi.
        """
        if self.reducir_gcpi:
            if self.cerramiento == Cerramiento.PARCIALMENTE_CERRADO:
                if (
                    self.volumen_interno is not None and self.aberturas_totales
                ):  # Las aberturas totales no pueden ser "cero"
                    reduccion = 0.5 * (1 + 1 / (1 + self.volumen_interno / 6954 / self.aberturas_totales) ** 0.5)
                    return min(reduccion, 1.0)
        return 1.0

    @cached_property
    def gcpi(self) -> float:
        """Calcula el coeficiente de presión interna de acuerdo al cerramiento del edificio.

        Returns:
            El coeficiente de presión interna.
        """
        cerramiento_gcpi = {Cerramiento.CERRADO: 0.18, Cerramiento.PARCIALMENTE_CERRADO: 0.55, Cerramiento.ABIERTO: 0.0}
        return cerramiento_gcpi[self.cerramiento] * self.factor_reduccion_gcpi

    @cached_property
    def valores(self) -> ValoresPresionesCubiertaEdificioSprfvMetodoDireccional:
        """Calcula los valores de presión para la cubierta.

        Returns:
            Los valores de presión correspondientes a cada cp para presión interna negativa y presión externa positiva.
        """
        valores_cp = self.cp()
        valores = {}
        for direccion, cp in valores_cp.items():
            valores[direccion] = self._calcular_presiones(
                cp, self.factores_rafaga[direccion], self._presion_media_parcial
            )
        return valores

    def _calcular_presiones(self, cp: [Dict[Hashable, float], Sequence[float]], factor_rafaga: float, func: partial):
        """

        Args:
            cp: Los valores de coeficiente de presión.
            factor_rafaga: El factor de ráfaga.
            func: La función que calcula las presiones. En este caso se utiliza una función parcial que solo hay que
            pasarle el valor de cp y de rafaga. Ver el método "valores".

        Returns:
            Las presiones para cada cp.
        """
        presiones = {}
        if not isinstance(cp, dict):
            return func(cp=cp, factor_rafaga=factor_rafaga)
        for key, valor in cp.items():
            if isinstance(valor, dict):
                presiones[key] = self._calcular_presiones(valor, factor_rafaga, func)
            else:
                presiones[key] = func(cp=valor, factor_rafaga=factor_rafaga)
        return presiones

    def __call__(self) -> ValoresPresionesCubiertaEdificioSprfvMetodoDireccional:
        return self.valores

    @staticmethod
    def _presiones(
        presion_velocidad: float,
        cp: float,
        factor_rafaga: float,
        presion_velocidad_media: float,
        gcpi: float = 0.0,
        considerar_presion_minima: bool = False,
    ) -> PresionesEdificio:
        """

        Args:
            presion_velocidad: La presión de velocidad.
            cp: El valor de cp.
            factor_rafaga: El valor de factor de ráfaga.
            presion_velocidad_media: La presión a la altura media de la estructura.
            gcpi: El coeficiente de presión interna.
            considerar_presion_minima: Determina si se debe considerar la presión mínima del reglamento.

        Returns:
            Los valores de presión para presión interna positiva y negativa.
        """
        q1 = presion_velocidad * factor_rafaga * cp
        q2 = presion_velocidad_media * gcpi
        q_pos = q1 - q2
        q_neg = q1 + q2
        if considerar_presion_minima:
            q_pos = presion_minima(q_pos)
            q_neg = presion_minima(q_neg)
        return PresionesEdificio(q_pos, q_neg)


class CubiertaSprfvMetodoEnvolvente(PresionesBase):
    pass


class AleroSprfvMetodoDireccional(CubiertaSprfvMetodoDireccional):
    """AleroSprfvMetodoDireccional.

    Determina las presiones del alero para SPRFV usando el método direccional.
    """

    def __init__(
        self,
        alturas: np.ndarray,  # TODO - Ver si es necesario
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cp: clases_cp_edificio.AleroSprfvMetodoDireccional,
        categoria_exp: CategoriaExposicion,
    ) -> None:
        """
        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cp: Un instancia de AleroSprfvMetodoDireccional.
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
        self._presion_media_parcial = partial(self._presiones, presion_velocidad=self.presion_velocidad_media)

    @cached_property
    def valores(self) -> ValoresPresionesAleroEdificioSprfvMetodoDireccional:
        """Calcula los valores de presión para el alero.

        Returns:
            Los valores de presión correspondientes a cada cp.
        """
        valores_cp = self.cp()
        valores = {}
        for direccion, cp in valores_cp.items():
            valores[direccion] = self._calcular_presiones(
                cp, self.factores_rafaga[direccion], self._presion_media_parcial
            )
        return valores

    @staticmethod
    def _presiones(
        presion_velocidad: float, cp: float, factor_rafaga: float, considerar_presion_minima: bool = False
    ) -> float:
        """
        Args:
            presion_velocidad: La presión de velocidad determinada a la altura requerida.
            cp: El coeficiente de presión cp.
            factor_rafaga: El factor de ráfaga.
            considerar_presion_minima: Determina si se debe considerar la presión mínima del reglamento.

        Returns:
            La presión correspondiente.
        """

        presion = presion_velocidad * factor_rafaga * cp
        if considerar_presion_minima:
            return presion_minima(presion)
        return presion

    def __call__(self) -> ValoresPresionesAleroEdificioSprfvMetodoDireccional:
        return self.valores


class AleroSprfvMetodoEnvolvente:
    pass


class ParedesSprfvMetodoDireccional(CubiertaSprfvMetodoDireccional):
    """ParedesSprfvMetodoDireccional.

    Determina las presiones de paredes para SPRFV usando el método direccional.
    """

    # https://www.python.org/dev/peps/pep-0526/#class-and-instance-variable-annotations
    cp: clases_cp_edificio.ParedesSprfvMetodoDireccional

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        altura_alero: float,
        tipo_cubierta: TipoCubierta,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de ParedesSprfvMetodoDireccional.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
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
        self.tipo_cubierta = tipo_cubierta
        self._bool_indices_alero = alturas <= altura_alero

    @property
    def coeficientes_exposicion_alero(self) -> np.ndarray:  # TODO - Averiguar si se puede hacer -> np.ndarray[float]
        """Obtiene el coeficiente de exposición correspondiente a la altura de alero.

        Returns:
            El coeficiente de exposición correspondiente a la altura de alero.
        """
        return self.coeficientes_exposicion[self._bool_indices_alero]

    @cached_property
    def factor_topografico_alero(self) -> np.ndarray:
        """Factor topográfico calculado hasta la altura de alero.

        Returns:
            El factor topográfico correspondiente a la altura de alero.
        """
        return self.factor_topografico[self._bool_indices_alero]

    @property
    def presion_velocidad_alero(self) -> np.ndarray:
        """Obtiene la presión de velocidad correspondiente a la altura de alero.

        Returns:
            La presión de velocidad correspondiente a la altura de alero.
        """
        return self.presiones_velocidad[self._bool_indices_alero]

    @cached_property
    def valores(self) -> ValoresPresionesParedesEdificioSprfvMetodoDireccional:
        """Calcula los valores de presión para las paredes.

        Returns:
            Los valores de presión correspondientes a cada cp para presión interna negativa y presión externa positiva.
        """
        valores_cp = self.cp()
        presiones_paredes = defaultdict(dict)
        for direccion, diccionario in valores_cp.items():
            for pared, cp in diccionario.items():
                if pared == ParedEdificioSprfv.BARLOVENTO:
                    if (
                        direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
                        and self.tipo_cubierta != TipoCubierta.UN_AGUA
                    ):
                        qi = self.presion_velocidad_alero
                    else:
                        qi = self.presiones_velocidad
                else:
                    qi = self.presion_velocidad_media
                presiones_paredes[direccion][pared] = self._presiones(
                    qi,
                    cp,
                    self.factores_rafaga[direccion],
                    self.gcpi,
                    self.presion_velocidad_media,
                )
        return presiones_paredes

    def __call__(self) -> ValoresPresionesParedesEdificioSprfvMetodoDireccional:
        return self.valores


class ParedesSprfvMetodoEnvolvente:
    pass


class MixinCr:
    """MixinCr.

    Extendiende la funcionalidad para componentes. No debe ser usada por si sola.
    """

    def _presiones_componentes(
        self,
    ) -> Union[
        None,
        ValoresPresionesParedesEdificioComponentesA,
        ValoresPresionesCubiertaEdificioComponentes,
        ValoresPresionesAleroEdificioComponentes,
    ]:
        """Calcula las presiones para componentes y revestimientos.

        Returns:
            Las presiones correspondientes a cada cp.
        """
        valores_cp = self.cp()
        if valores_cp is None:
            return
        presiones = defaultdict(dict)
        for nombre, zonas in valores_cp.items():
            for zona, valor_cp in zonas.items():
                presiones[nombre][zona] = self._presion_media_parcial(
                    cp=valor_cp, factor_rafaga=1, considerar_presion_minima=True
                )
        return presiones


class CubiertaComponentes(CubiertaSprfvMetodoDireccional, MixinCr):
    """CubiertaComponentes.

    Determina las presiones para componentes y revestimiento para cubierta.
    """

    cp: clases_cp_edificio.CubiertaComponentes

    def __init__(
        self,
        alturas: np.ndarray,
        altura_media: float,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de CubiertaMetodoDireccional.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
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
            reducir_gcpi=reducir_gcpi,
            aberturas_totales=aberturas_totales,
            volumen_interno=volumen_interno,
        )

    @cached_property
    def valores(self) -> ValoresPresionesCubiertaEdificioComponentes:
        """Calcula los valores de presión para los componentes.

        Returns:
            Los valores de presión correspondientes a cada cp para presión interna negativa y presión externa positiva.
        """
        return self._presiones_componentes()

    @cached_property
    def _altura_limite(self):
        return self._calcular_altura_limite(1)

    def __call__(self) -> ValoresPresionesCubiertaEdificioComponentes:
        return self.valores


class AleroComponentes(AleroSprfvMetodoDireccional, MixinCr):
    @cached_property
    def valores(self) -> ValoresPresionesAleroEdificioComponentes:
        """Calcula los valores de presión para los componentes.

        Returns:
            Los valores de presión correspondientes a cada cp para presión interna negativa y presión externa positiva.
        """
        return self._presiones_componentes()

    @cached_property
    def _altura_limite(self):
        return self._calcular_altura_limite(1)

    def __call__(self) -> ValoresPresionesAleroEdificioComponentes:
        return self.valores


class ParedesComponentes(ParedesSprfvMetodoDireccional, MixinCr):
    # """ParedesComponentes.
    #
    # Determina las presiones para componentes y revestimiento para paredes.
    # """
    #
    # cp: clases_cp_edificio.ParedesComponentes
    #
    # def __init__(
    #     self,
    #     alturas: np.ndarray,
    #     altura_media: float,
    #     altura_alero: float,
    #     tipo_cubierta: TipoCubierta,
    #     categoria: CategoriaEstructura,
    #     velocidad: float,
    #     rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
    #     factor_topografico: np.ndarray,
    #     cerramiento: Cerramiento,
    #     cp,
    #     categoria_exp: CategoriaExposicion,
    #     reducir_gcpi: bool = False,
    #     aberturas_totales: Optional[float] = None,
    #     volumen_interno: Optional[float] = None,
    # ) -> None:
    #     """
    #
    #     Args:
    #         alturas: Las alturas o altura de la estructura donde calcular las presiones.
    #         altura_media: La altura media de la cubierta.
    #         altura_alero: La altura de alero del edificio.
    #         tipo_cubierta: El tipo de cubierta.
    #         categoria: La categoría de la estructura.
    #         velocidad: La velocidad del viento en m/s.
    #         rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
    #         factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
    #         cerramiento: El tipo de cerramiento del edificio.
    #         cp: Un instancia de ParedesComponentes.
    #         categoria_exp: La categoría de exposición al viento de la estructura.
    #         reducir_gcpi: Indica si hay que reducir el valor de gcpi.
    #         aberturas_totales: Las valor total de aberturas totales del edificio.
    #         volumen_interno: El volumen interno no dividido del edificio.
    #     """
    #     super().__init__(
    #         alturas,
    #         altura_media,
    #         altura_alero,
    #         tipo_cubierta,
    #         categoria,
    #         velocidad,
    #         rafaga,
    #         factor_topografico,
    #         cerramiento,
    #         cp,
    #         categoria_exp,
    #         reducir_gcpi,
    #         aberturas_totales,
    #         volumen_interno,
    #     )
    #     self._altura_limite = self._calcular_altura_limite(1)

    @cached_property
    def _altura_limite(self):
        return self._calcular_altura_limite(1)

    def _presiones_cr_caso_b(self) -> Union[None, ValoresPresionesParedesEdificioComponentesB]:
        """Calcula las presiones sobre los componentes de pared cuando hay que
        utilizar la Figura 8 del Reglamento CIRSOC 102-05.

        :returns: ``dict`` con las presiones para cada componente.
        :rtype: dict
        """
        valores_cp = self.cp()
        if valores_cp is None:
            return
        presiones = defaultdict(lambda: defaultdict(dict))
        for pared in ParedEdificioSprfv:
            if pared == ParedEdificioSprfv.BARLOVENTO:
                qi = self.presiones_velocidad
            else:
                qi = self.presion_velocidad_media
            for nombre, zonas in valores_cp.items():
                for zona, valor_gcp in zonas.items():
                    presiones[pared][nombre][zona] = self._presiones(
                        qi, valor_gcp, 1, self.gcpi, self.presion_velocidad_media
                    )
        return presiones

    @cached_property
    def valores(
        self,
    ) -> Union[ValoresPresionesParedesEdificioComponentesB, ValoresPresionesParedesEdificioComponentesA,]:
        """Calcula los valores de presión dependiendo la referencia del Reglamento.

        Returns:
            Los valores de presión.
        """
        if self.cp.referencia == "Figura 8":
            return self._presiones_cr_caso_b()
        return self._presiones_componentes()

    def __call__(self) -> ValoresPresionesParedesEdificioComponentes:
        return self.valores


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
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Cubierta,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Cubierta.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = CubiertaSprfvMetodoDireccional(
                alturas,
                altura_media,
                categoria,
                velocidad,
                rafaga,
                factor_topografico,
                cerramiento,
                cp.sprfv,
                categoria_exp,
                reducir_gcpi,
                aberturas_totales,
                volumen_interno,
            )
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = CubiertaComponentes(
            alturas,
            altura_media,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp.componentes,
            categoria_exp,
            reducir_gcpi,
            aberturas_totales,
            volumen_interno,
        )

    @cached_property
    def valores(self) -> ValoresPresionesCubiertaEdificioMetodoDireccional:
        return {SistemaResistente.SPRFV: self.sprfv(), SistemaResistente.COMPONENTES: self.componentes()}

    def __call__(self) -> ValoresPresionesCubiertaEdificioMetodoDireccional:
        return self.valores


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
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cp: clases_cp_edificio.Alero,
        categoria_exp: CategoriaExposicion,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cp: Un instancia de AleroSprfvMetodoDireccional.
            categoria_exp: La categoría de exposición al viento de la estructura.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = AleroSprfvMetodoDireccional(
                alturas, altura_media, categoria, velocidad, rafaga, factor_topografico, cp.sprfv, categoria_exp
            )
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = AleroComponentes(
            alturas, altura_media, categoria, velocidad, rafaga, factor_topografico, cp.componentes, categoria_exp
        )

    @cached_property
    def valores(self) -> ValoresPresionesAleroEdificioMetodoDireccional:
        return {SistemaResistente.SPRFV: self.sprfv(), SistemaResistente.COMPONENTES: self.componentes()}

    def __call__(self) -> ValoresPresionesAleroEdificioMetodoDireccional:
        return self.valores


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
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Paredes,
        categoria_exp: CategoriaExposicion,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ) -> None:
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Paredes.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            metodo_sprfv: El metodo a utilizar para determinar que clase se usa para seleccionar los coeficientes de presión para el SPRFV.
        """
        if metodo_sprfv == MetodoSprfv.DIRECCIONAL:
            self.sprfv = ParedesSprfvMetodoDireccional(
                alturas,
                altura_media,
                altura_alero,
                tipo_cubierta,
                categoria,
                velocidad,
                rafaga,
                factor_topografico,
                cerramiento,
                cp.sprfv,
                categoria_exp,
                reducir_gcpi,
                aberturas_totales,
                volumen_interno,
            )
        else:
            raise NotImplementedError("El método envolvente no esta implementado aún.")
        self.componentes = ParedesComponentes(
            alturas,
            altura_media,
            altura_alero,
            tipo_cubierta,
            categoria,
            velocidad,
            rafaga,
            factor_topografico,
            cerramiento,
            cp.componentes,
            categoria_exp,
            reducir_gcpi,
            aberturas_totales,
            volumen_interno,
        )

    @cached_property
    def valores(self) -> ValoresPresionesParedesEdificioMetodoDireccional:
        return {SistemaResistente.SPRFV: self.sprfv(), SistemaResistente.COMPONENTES: self.componentes()}

    def __call__(self) -> ValoresPresionesParedesEdificioMetodoDireccional:
        return self.valores


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
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
        cerramiento: Cerramiento,
        cp: clases_cp_edificio.Edificio,
        categoria_exp: CategoriaExposicion,
        alero: float = 0,
        reducir_gcpi: bool = False,
        aberturas_totales: Optional[float] = None,
        volumen_interno: Optional[float] = None,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
    ):
        """

        Args:
            alturas: Las alturas o altura de la estructura donde calcular las presiones.
            altura_media: La altura media de la cubierta.
            altura_alero: La altura de alero del edificio.
            tipo_cubierta: El tipo de cubierta.
            categoria: La categoría de la estructura.
            velocidad: La velocidad del viento en m/s.
            rafaga: Diccionario con instancia de Rafaga para direcciones de viento paralelo y normal a la cumbrera.
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
            cerramiento: El tipo de cerramiento del edificio.
            cp: Un instancia de Edificio.
            categoria_exp: La categoría de exposición al viento de la estructura.
            reducir_gcpi: Indica si hay que reducir el valor de gcpi.
            aberturas_totales: Las valor total de aberturas totales del edificio.
            volumen_interno: El volumen interno no dividido del edificio.
            alero: La dimensión del alero.
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
    def valores(self) -> ValoresPresionesEdificioMetodoDireccional:
        valores = {ZonaEdificio.PAREDES: self.paredes(), ZonaEdificio.CUBIERTA: self.cubierta()}
        alero = getattr(self, "alero", None)
        if alero is not None:
            valores[ZonaEdificio.ALERO] = alero()
        return valores

    @classmethod
    def desde_edificio(
        cls,
        edificio: geometria.Edificio,
        cp: clases_cp_edificio.Edificio,
        categoria: CategoriaEstructura,
        velocidad: float,
        rafaga: Dict[DireccionVientoMetodoDireccionalSprfv, Rafaga],
        factor_topografico: np.ndarray,
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
            factor_topografico: El factor o factores topográficos correspondientes a la altura o alturas de la estructura.
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

    def __call__(self) -> ValoresPresionesEdificioMetodoDireccional:
        return self.valores
