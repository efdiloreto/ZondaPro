from __future__ import annotations

from functools import cached_property
from typing import Optional, Sequence, TYPE_CHECKING, Tuple, NamedTuple

from sse102.cirsoc.geometria.cubiertas import Cubierta
from sse102.cirsoc.geometria.utils_alturas import array_alturas
from sse102.enums import TipoCubierta

if TYPE_CHECKING:
    import numpy as np


class AreasEdificio(NamedTuple):
    frontal: float
    izquierda: float
    trasera: float
    derecha: float
    cubierta: float


class Edificio:
    """Edificio.

    Genera la geometria de un edificio.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        elevacion: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        parapeto: float = 0,
        alero: float = 0,
        alturas_personalizadas: Optional[Sequence[float]] = None,
        volumen_interno: Optional[float] = None,
        aberturas: Optional[Tuple[float, float, float, float, float]] = None,
    ) -> None:
        """
        Args:
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            elevacion: La altura desde el suelo desde donde se consideran las presiones del viento sobre el edificio.
            altura_alero: La altura de alero de la cubierta, medida desde el nivel de suelo.
            altura_cumbrera: La altura de cumbrera de la cubierta, medida desde el nivel de suelo.
            tipo_cubierta: El tipo de cubierta.
            parapeto: La dimensión del parapeto.
            alero: La dimensión del alero.
            alturas_personalizadas: Las alturas sobre las que se calcularán las presiones de viento sobre paredes a barlovento.
            volumen_interno: El volumen interno no dividido del edificio.
            aberturas: Las aberturas del edificio para cada pared y cubierta.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.elevacion = elevacion
        self.altura_alero = altura_alero
        self.tipo_cubierta = tipo_cubierta
        self.cubierta: Cubierta = Cubierta(
            ancho, longitud, altura_alero, altura_cumbrera, tipo_cubierta, parapeto, alero
        )
        self.altura_cumbrera = self.cubierta.altura_cumbrera  # Ya es procesada en la inicialización de la clase
        self.parapeto = parapeto
        self.alero = alero
        self.alturas_personalizadas = alturas_personalizadas
        self.volumen_interno = volumen_interno or self.volumen
        self._aberturas = aberturas or (0.0,) * 5

    def _area_frontal(self) -> float:
        """Calcula el area de la pared frontal.

        Returns:
            El area de pared frontal.
        """
        return self.ancho * self.cubierta.altura_alero + self.cubierta.area_mojinete

    def _area_trasera(self) -> float:
        """Calcula el area de la pared trasera.

        Returns:
            El area de pared trasera.
        """
        return self._area_frontal()

    def _area_izquierda(self) -> float:
        """Calcula el area de la pared derecha.

        Returns:
            El area de pared derecha.
        """
        return self.longitud * self.cubierta.altura_alero

    def _area_derecha(self) -> float:
        """Calcula el area de la pared izquierda.

        Se considera que para cubiertas a un agua la cumbrera esta del lado de
        la pared derecha.

        Returns:
            El area de pared derecha.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return self.longitud * self.cubierta.altura_cumbrera
        return self._area_izquierda()

    @cached_property
    def areas(self) -> AreasEdificio:
        """Las areas de las paredes y el techo.

        Returns:
            Las areas de las paredes y techo.
        """
        return AreasEdificio(
            self._area_frontal(),
            self._area_izquierda(),
            self._area_trasera(),
            self._area_derecha(),
            self.cubierta.area,
        )

    @cached_property
    def aberturas(self) -> AreasEdificio:
        """Retorna las aberturas del edificio. Se procesan para que no sean menores que cero y que no sean mayores que
        las paredes o cubierta que las contienen.

        Returns:
            Las aberturas procesadas.
        """
        aberturas = tuple(
            min(abertura, area) if abertura >= 0 else 0.0 for abertura, area in zip(self._aberturas, self.areas)
        )
        return AreasEdificio(*aberturas)

    @cached_property
    def area_total(self) -> float:
        """Calcula el area total del edificio.

        Returns:
            El area total.
        """
        return sum(self.areas)

    @cached_property
    def abertura_total(self) -> float:
        """Calcula el valor de abertura total del edificio.

        Returns:
            Las abertura total.
        """
        return sum(self.aberturas)

    @cached_property
    def volumen(self) -> float:
        """Calcula el volumen interno del edificio.

        Returns:
            El volumen interno del edificio.
        """
        return self._area_frontal() * self.longitud

    @cached_property
    def alturas(self) -> np.ndarray:
        """Crea un array de alturas desde la elevación del edificio hasta la altura de cumbrera.

        Returns:
            Un array de alturas.
        """
        return array_alturas(
            self.elevacion,
            self.altura_cumbrera,
            self.alturas_personalizadas,
            self.altura_alero,
            self.cubierta.altura_media,
        )

    @cached_property
    def alturas_alero(self) -> np.ndarray:
        """Crea un array de alturas desde la elevación del edificio hasta la altura de alero.

        Returns:
            Un array de alturas.
        """
        return self.alturas[self.alturas <= self.cubierta.altura_alero]

    @cached_property
    def a0i(self) -> Tuple[float, ...]:
        """Calcula la suma de las áreas totales de superficie de la envolvente del edificio (paredes y cubierta) no
        incluyendo Ag (el área total de aquella pared con la cual Ao está asociada) para cada pared.

        Returns:
            El calculo de A0i para cada pared.
        """
        return tuple(self.abertura_total - abertura for abertura in self.aberturas[:-1])

    @cached_property
    def agi(self) -> Tuple[float, ...]:
        """la suma de las áreas totales de superficie de la envolvente del edificio (paredes y cubierta) no incluyendo
        Ag (el área total de aquella pared con la cual Ao está asociada) para cada pared.

        Returns:
            El calculo de Agi para cada pared.
        """
        return tuple(self.area_total - area for area in self.areas[:-1])

    @cached_property
    def min_areas(self) -> Tuple[float, ...]:
        """Calcula el valor mínimo entre 0.4 m2 y 0.01 Ag para cada pared.

        Returns:
            El valor mínimo para cada pared.
        """
        return tuple(min(0.4, 0.01 * area) for area in self.areas[:-1])

    @cached_property
    def cerramiento_condicion_1(self) -> Tuple[bool, ...]:
        """Chequea para cada pared si su abertura supera el 80% del area.

        Returns:
            Chequeo de condición 1 para cada pared.
        """
        return tuple(abertura >= 0.8 * area for abertura, area in zip(self.aberturas[:-1], self.areas[:-1]))

    @cached_property
    def cerramiento_condicion_2(self) -> Tuple[bool, ...]:
        """Chequea si el área total de aberturas en una pared que recibe presión externa positiva excede la  suma  de
        las  áreas  de  aberturas en  el  resto  de  la  envolvente  del  edificio  (paredes y cubierta) en más del 10%.

        Returns:
            Chequeo de condición 2 para cada pared.
        """
        return tuple(abertura > 1.1 * area for abertura, area in zip(self.aberturas[:-1], self.a0i))

    @cached_property
    def cerramiento_condicion_3(self) -> Tuple[bool, ...]:
        """Chequea si el área total de aberturas en una pared que recibe presión externa positiva excede el  valor
        menor  entre  0,4  m2  ó  el  1%  del área  de  dicha  pared.

        Returns:
            Chequeo de condición 3 para cada pared.
        """
        return tuple(abertura > area for abertura, area in zip(self.aberturas[:-1], self.min_areas))

    @cached_property
    def cerramiento_condicion_4(self) -> Tuple[bool, ...]:
        """Chequea si el  porcentaje  de  aberturas en el resto de la envolvente del edificio no excede el 20%.

        Returns:
            Chequeo de condición 4 para cada pared.
        """
        return tuple(abertura / area <= 0.2 for abertura, area in zip(self.a0i, self.agi))
