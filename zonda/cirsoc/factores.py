import math
from collections import namedtuple
from functools import cached_property
from typing import NamedTuple, Union, Dict

import numpy as np

from zonda.cirsoc import geometria
from zonda.enums import (
    Flexibilidad,
    CategoriaExposicion,
    DireccionVientoMetodoDireccionalSprfv,
    TipoTerrenoTopografia,
    DireccionTopografia,
)
from zonda.tipos import EscalarOArray

_Constantes = namedtuple(
    "Constantes", "alfa zg a_hat b_hat alpha_bar b_bar c le ep_bar zmin"
)


_ParametrosTopograficos = namedtuple(
    "ParametrosTopograficos", "factor_k gamma mu lh k1 k2 k3"
)


_constantes_exposicion = {
    CategoriaExposicion.A: _Constantes(
        5, 457, 1 / 5, 0.64, 1 / 3, 0.3, 0.45, 55, 1 / 2, 18.3
    ),
    CategoriaExposicion.B: _Constantes(
        7, 366, 1 / 7, 0.84, 1 / 4, 0.45, 0.3, 98, 1 / 3, 9.2
    ),
    CategoriaExposicion.C: _Constantes(
        9.5, 274, 1 / 9.5, 1, 1 / 6.5, 0.65, 0.2, 152, 1 / 5, 4.6
    ),
    CategoriaExposicion.D: _Constantes(
        11.5, 213, 1 / 11.5, 1.07, 1 / 9, 0.8, 0.15, 198, 1 / 8, 2.1
    ),
}


class Rafaga:
    """Ráfaga.

    Determina el factor de ráfaga y todos sus parámetros.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura: float,
        altura_rafaga: float,
        velocidad: float,
        frecuencia: float,
        beta: float,
        flexibilidad: Flexibilidad,
        factor_g_simplificado: bool,
        categoria_exp: CategoriaExposicion,
    ) -> None:
        """

        Args:
            ancho: El ancho de la estructura medido de forma normal a la dirección del viento.
            longitud: El ancho de la estructura medido de forma paralelo a la dirección del viento.
            altura: La altura de la estructura. Para edificios se toma la altura media.
            altura_rafaga: La altura útil para calcular el factor de ráfaga. Por ejemplo, para edificios es 0.6 * altura media.
            velocidad: La velocidad del viento en m/s.
            frecuencia: La frecuencia natural de la estructura en hz.
            beta: La relación de amortiguamiento crítico.
            flexibilidad: La flexibilidad de la estructura.
            factor_g_simplificado: Indica si se debe usar 0.85 como valor del factor de ráfaga.
            categoria_exp: La categoría de exposición al viento de la estructura.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura = altura
        self.altura_rafaga = altura_rafaga
        self.velocidad = velocidad
        self.frecuencia = frecuencia
        self.beta = beta
        self.flexibilidad = flexibilidad
        self.factor_g_simplificado = factor_g_simplificado
        self.categoria_exp = categoria_exp
        self.constantes_exp_terreno = _constantes_exposicion[self.categoria_exp]

    @cached_property
    def parametros(self):
        """Calcula los parámetros de factor de ráfaga.

        Returns:
            Los parámetros de factor de ráfaga.
        """
        parametros_rafaga = namedtuple("ParametrosRafaga", "z iz lz gr r")
        z = max(self.altura_rafaga, self.constantes_exp_terreno.zmin)
        iz = self.constantes_exp_terreno.c * ((10 / z) ** (1 / 6))
        lz = self.constantes_exp_terreno.le * (
            (z / 10) ** self.constantes_exp_terreno.ep_bar
        )
        if self.flexibilidad == Flexibilidad.FLEXIBLE:
            gr = (2 * math.log(3600 * self.frecuencia)) ** 0.5 + 0.577 / (
                (2 * math.log(3600 * self.frecuencia)) ** 0.5
            )
            vz = (
                self.constantes_exp_terreno.b_bar
                * ((z / 10) ** self.constantes_exp_terreno.alpha_bar)
                * self.velocidad
            )
            n1 = self.frecuencia * lz / vz
            rn = 7.47 * n1 / ((1 + 10.3 * n1) ** (5 / 3))
            nh = 4.6 * self.frecuencia * self.altura / vz
            nb = 4.6 * self.frecuencia * self.ancho / vz
            nl = 15.4 * self.frecuencia * self.longitud / vz
            n = (nh, nb, nl)
            ri = tuple(
                1 / j - ((1 - np.e ** (-2 * j)) / (2 * j**2)) if j > 0 else 1
                for j in n
            )
            rh, rb, rl = ri
            r = (rn * rh * rb * (0.53 + 0.47 * rl) / self.beta) ** 0.5
            return parametros_rafaga(z, iz, lz, gr, r)
        return parametros_rafaga(z, iz, lz, None, None)

    @cached_property
    def factor_q(self) -> float:
        """Calcula el factor Q.

        Returns:
            El factor Q.
        """
        return (
            1
            / (1 + 0.63 * ((self.longitud + self.altura) / self.parametros.lz) ** 0.63)
        ) ** 0.5

    def _rigida(self) -> float:
        """Calcula el factor de ráfaga para una estructura rígida.

        Returns:
            El factor de ráfaga.
        """
        return (
            (1 + 1.7 * 3.4 * self.parametros.iz * self.factor_q)
            / (1 + 1.7 * 3.4 * self.parametros.iz)
        ) * 0.925

    def _flexible(self) -> float:
        """Calcula el factor de ráfaga para una estructura flexible.

        Returns:
            El factor de ráfaga.
        """
        return (
            (
                1
                + 1.7
                * self.parametros.iz
                * (
                    (
                        (3.4 * self.factor_q) ** 2
                        + (self.parametros.gr * self.parametros.r) ** 2
                    )
                    ** 0.5
                )
            )
            / (1 + 1.7 * 3.4 * self.parametros.iz)
        ) * 0.925

    @cached_property
    def factor(self) -> float:
        """Calcula el factor de ráfaga de acuerdo a la flexibilidad de la estructura o si es considerado simplificado o no.

        Returns:
            El factor de ráfaga.
        """
        if self.factor_g_simplificado:
            return 0.85
        if self.flexibilidad == Flexibilidad.FLEXIBLE:
            return self._flexible()
        return self._rigida()

    @classmethod
    def desde_edificio_metodo_direccional(
        cls,
        edificio: geometria.Edificio,
        velocidad: float,
        frecuencia: float,
        beta: float,
        flexibilidad: Flexibilidad,
        factor_g_simplificado: bool,
        categoria_exp: CategoriaExposicion,
    ):
        """Crea dos un diccionario con dos instancias de donde cada una corresponde a una dirección para un edificio cuando se
        utiliza el método direccional para calcular las presiones sobre el SPRFV.

        Args:
            edificio: La geometria de un edificio.
            velocidad: La velocidad del viento en m/s.
            frecuencia: La frecuencia natural de la estructura en hz.
            beta: La relación de amortiguamiento crítico.
            flexibilidad: La flexibilidad de la estructura.
            factor_g_simplificado: Indica si se debe usar 0.85 como valor del factor de ráfaga.
            categoria_exp: La categoría de exposición al viento de la estructura.

        Returns:
            Diccionario con dos instancias para direcciones paralelo y normal a la cumbrera.
        """
        ancho = edificio.ancho
        longitud = edificio.longitud
        altura = edificio.cubierta.altura_media
        altura_rafaga = 0.6 * altura
        paralelo = cls(
            ancho,
            longitud,
            altura,
            altura_rafaga,
            velocidad,
            frecuencia,
            beta,
            flexibilidad,
            factor_g_simplificado,
            categoria_exp,
        )
        normal = cls(
            longitud,
            ancho,
            altura,
            altura_rafaga,
            velocidad,
            frecuencia,
            beta,
            flexibilidad,
            factor_g_simplificado,
            categoria_exp,
        )
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: paralelo,
            DireccionVientoMetodoDireccionalSprfv.NORMAL: normal,
        }


class Topografia:
    """Topografia.

    Determina el factor topógrafico para las alturas consideradas y todos sus parámetros.
    """

    def __init__(
        self,
        categoria_exp: CategoriaExposicion,
        considerar_topografia: bool,
        tipo_terreno: TipoTerrenoTopografia,
        altura_terreno: float,
        distancia_cresta: float,
        distancia_barlovento_sotavento: float,
        direccion: DireccionTopografia,
        alturas: EscalarOArray,
    ) -> None:
        """

        Args:
            categoria_exp: La categoría de exposición al viento de la estructura.
            considerar_topografia: indica si se tiene que calcular la topografia.
            tipo_terreno: El tipo de terreno.
            altura_terreno: La altura de la colina o escarpa.
            distancia_cresta: La distancia en la dirección de barlovento, medida desde la cresta de la colina o escarpa.
            distancia_barlovento_sotavento: Distancia tomada desde la cima, en la dirección de barlovento o de sotavento.
            direccion: La direccion para la el parámetro `distancia_barlovento_sotavento`.
            alturas: Las alturas donde calcular la topografía.
        """
        self.categoria_exp = categoria_exp
        self.considerar_topografia = considerar_topografia
        self.tipo_terreno = tipo_terreno
        self.altura_terreno = altura_terreno
        self.distancia_cresta = distancia_cresta
        self.distancia_barlovento_sotavento = distancia_barlovento_sotavento
        self.direccion = direccion
        self.alturas = alturas

    def topografia_considerada(self) -> bool:
        """Chequea si es necesario considerar la topografia.

        Returns:
            True si es necesario calcular la topografía.
        """
        if not self.considerar_topografia:
            return False
        if self.altura_terreno / self.distancia_cresta >= 0.2 and (
            (
                self.categoria_exp in (CategoriaExposicion.A, CategoriaExposicion.B)
                and self.altura_terreno > 20
            )
            or (
                self.categoria_exp in (CategoriaExposicion.C, CategoriaExposicion.D)
                and self.altura_terreno > 5
            )
        ):
            return True
        return False

    @cached_property
    def parametros(self):
        """Calcula los parámetros de factor topográfico.

        Returns:
            Los parámetros del factor topográfico.
        """
        # Referencia = CIRSOC 102-2005 Fig. 2
        param_topo_vel = {
            TipoTerrenoTopografia.LOMA_BIDIMENSIONAL: {
                "factor_k": {
                    CategoriaExposicion.A: 1.3,
                    CategoriaExposicion.B: 1.3,
                    CategoriaExposicion.C: 1.45,
                    CategoriaExposicion.D: 1.55,
                },
                "gamma": 3.0,
                "mu": {
                    DireccionTopografia.BARLOVENTO: 1.5,
                    DireccionTopografia.SOTAVENTO: 1.5,
                },
            },
            TipoTerrenoTopografia.ESCARPA_BIDIMENSIONAL: {
                "factor_k": {
                    CategoriaExposicion.A: 0.75,
                    CategoriaExposicion.B: 0.75,
                    CategoriaExposicion.C: 0.85,
                    CategoriaExposicion.D: 0.95,
                },
                "gamma": 2.5,
                "mu": {
                    DireccionTopografia.BARLOVENTO: 1.5,
                    DireccionTopografia.SOTAVENTO: 4.0,
                },
            },
            TipoTerrenoTopografia.COLINA_TRIDIMENSIONAL: {
                "factor_k": {
                    CategoriaExposicion.A: 0.95,
                    CategoriaExposicion.B: 0.95,
                    CategoriaExposicion.C: 1.05,
                    CategoriaExposicion.D: 1.15,
                },
                "gamma": 4.0,
                "mu": {
                    DireccionTopografia.BARLOVENTO: 1.5,
                    DireccionTopografia.SOTAVENTO: 1.5,
                },
            },
        }
        # Lh Referencia: CiIRSOC 102 2005 Fig. 2 Nota 2
        lh = max(self.distancia_cresta, 2 * self.altura_terreno)
        k_factor = param_topo_vel[self.tipo_terreno]["factor_k"][self.categoria_exp]
        gamma = param_topo_vel[self.tipo_terreno]["gamma"]
        mu = param_topo_vel[self.tipo_terreno]["mu"][self.direccion]
        k1 = k_factor * self.altura_terreno / lh
        k2 = 1 - self.distancia_barlovento_sotavento / mu / lh
        k3 = np.e ** (-1 * gamma * self.alturas / lh)
        return _ParametrosTopograficos(k_factor, gamma, mu, lh, k1, k2, k3)

    @cached_property
    def factor(self) -> EscalarOArray:
        """Calcula el factor topográfico.

        Returns:
            El factor topografico para cada altura.
        """
        if not self.topografia_considerada():
            try:
                kzt = np.fromiter((1 for i in range(len(self.alturas))), float)
            except TypeError:
                kzt = 1.00
            return kzt
        return (1 + self.parametros.k1 * self.parametros.k2 * self.parametros.k3) ** 2
