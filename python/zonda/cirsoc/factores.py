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

import math
from collections import namedtuple
from collections.abc import Sequence
from functools import cached_property

import numpy as np

from zonda.cirsoc import geometria
from zonda.enums import (
    CategoriaExposicion,
    DireccionTopografia,
    DireccionVientoMetodoDireccionalSprfv,
    Flexibilidad,
    TipoTerrenoTopografia,
)

_Constantes = namedtuple(
    "_Constantes", "alfa zg a_hat b_hat alpha_bar b_bar c le ep_bar zmin"
)


_ParametrosTopograficos = namedtuple(
    "_ParametrosTopograficos", "factor_k gamma mu lh k1 k2 k3"
)


_constantes_exposicion = {
    CategoriaExposicion.B: _Constantes(
        7.5, 1000, 1 / 7.5, 0.84, 1 / 4.5, 0.47, 0.30, 98, 1 / 3.0, 9.2
    ),
    CategoriaExposicion.C: _Constantes(
        9.8, 750, 1 / 9.8, 1.00, 1 / 6.4, 0.66, 0.20, 152, 1 / 5.0, 4.6
    ),
    CategoriaExposicion.D: _Constantes(
        11.5, 590, 1 / 11.5, 1.09, 1 / 8.0, 0.78, 0.15, 198, 1 / 8.0, 2.1
    ),
}


class Rafaga:
    """Ráfaga (CIRSOC 102-2025 Art. 1.9).

    Determina el factor de efecto de ráfaga y todos sus parámetros.
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
            ancho: Dimensión horizontal de la estructura medida normal (perpendicular) a la dirección del viento (B).
            longitud: Dimensión horizontal de la estructura medida paralela a la dirección del viento (L).
            altura: La altura de la estructura (h). Para edificios se toma la altura media de cubierta.
            altura_rafaga: La altura útil (z_bar) para calcular el factor de ráfaga (0.6 * h).
            velocidad: La velocidad básica del viento en m/s (V).
            frecuencia: La frecuencia natural fundamental de la estructura en Hz (n_1).
            beta: La relación de amortiguamiento crítico (β).
            flexibilidad: La flexibilidad de la estructura (rígida o flexible).
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
        """Calcula los parámetros de factor de ráfaga (CIRSOC 102-2025 Tabla 1.9-1 y Ecs. 1.9-7 a 1.9-16).

        Returns:
            Los parámetros de factor de ráfaga (z, iz, lz, gr, r).
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
                1 / j - ((1 - np.e ** (-2 * j)) / (2 * j**2)) if j > 0 else 1 for j in n
            )
            rh, rb, rl = ri
            r = (rn * rh * rb * (0.53 + 0.47 * rl) / self.beta) ** 0.5
            return parametros_rafaga(z, iz, lz, gr, r)
        return parametros_rafaga(z, iz, lz, None, None)

    @cached_property
    def factor_q(self) -> float:
        """Calcula el factor de respuesta de fondo Q (CIRSOC 102-2025 Ec. 1.9-8).

        Returns:
            El factor Q.
        """
        return (
            1 / (1 + 0.63 * ((self.ancho + self.altura) / self.parametros.lz) ** 0.63)
        ) ** 0.5

    def _rigida(self) -> float:
        """Calcula el factor de efecto de ráfaga para una estructura rígida (CIRSOC 102-2025 Ec. 1.9-6).

        Returns:
            El factor de ráfaga G.
        """
        return (
            (1 + 1.7 * 3.4 * self.parametros.iz * self.factor_q)
            / (1 + 1.7 * 3.4 * self.parametros.iz)
        ) * 0.925

    def _flexible(self) -> float:
        """Calcula el factor de efecto de ráfaga para una estructura flexible (CIRSOC 102-2025 Ec. 1.9-10).

        Returns:
            El factor de ráfaga Gf.
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
    """Topografía (CIRSOC 102-2025 Art. 1.8).

    Determina el factor topográfico Kzt para las alturas consideradas y todos sus parámetros (K1, K2, K3).
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
        alturas: float | Sequence[float] | np.ndarray,
    ) -> None:
        """
        Args:
            categoria_exp: La categoría de exposición al viento de la estructura.
            considerar_topografia: Indica si se tiene que calcular la topografía.
            tipo_terreno: El tipo de terreno (loma 2D, escarpa 2D o colina 3D).
            altura_terreno: La altura de la colina o escarpa (H).
            distancia_cresta: La distancia en la dirección de barlovento desde la cresta hasta la mitad de la altura (L_h).
            distancia_barlovento_sotavento: Distancia tomada desde la cima a barlovento o sotavento (x).
            direccion: La dirección para el parámetro `distancia_barlovento_sotavento` (barlovento o sotavento).
            alturas: La altura o las alturas sobre el terreno donde calcular la topografía (z).
        """
        self.categoria_exp = categoria_exp
        self.considerar_topografia = considerar_topografia
        self.tipo_terreno = tipo_terreno
        self.altura_terreno = altura_terreno
        self.distancia_cresta = distancia_cresta
        self.distancia_barlovento_sotavento = distancia_barlovento_sotavento
        self.direccion = direccion
        self.alturas = tuple(float(altura) for altura in np.atleast_1d(alturas))

    def topografia_considerada(self) -> bool:
        """Chequea si es necesario considerar la topografía (CIRSOC 102-2025 Art. 1.8.1).

        Returns:
            True si es necesario calcular la topografía.
        """
        if not self.considerar_topografia:
            return False
        return bool(
            self.altura_terreno / self.distancia_cresta >= 0.2
            and (
                (
                    self.categoria_exp == CategoriaExposicion.B
                    and self.altura_terreno >= 20
                )
                or (
                    self.categoria_exp in (CategoriaExposicion.C, CategoriaExposicion.D)
                    and self.altura_terreno >= 5
                )
            )
        )

    @cached_property
    def parametros(self):
        """Calcula los parámetros de factor topográfico (CIRSOC 102-2025 Figura 1.8-1).

        Returns:
            Los parámetros del factor topográfico (factor_k, gamma, mu, lh, k1, k2, k3).
        """
        # CIRSOC 102-2025 Figura 1.8-1
        param_topo_vel = {
            TipoTerrenoTopografia.LOMA_BIDIMENSIONAL: {
                "factor_k": {
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
        # CIRSOC 102-2025 Art. 1.8.2 / Figura 1.8-1: Para H/Lh > 0.5, adoptar H/Lh = 0.5 y sustituir 2H por Lh en K2 y K3.
        lh = max(self.distancia_cresta, 2 * self.altura_terreno)
        k_factor = param_topo_vel[self.tipo_terreno]["factor_k"][self.categoria_exp]
        gamma = param_topo_vel[self.tipo_terreno]["gamma"]
        mu = param_topo_vel[self.tipo_terreno]["mu"][self.direccion]
        # CIRSOC 102-2025 Figura 1.8-1: Si H/Lh < 0.2, K1 = 0
        h_sobre_lh = self.altura_terreno / self.distancia_cresta
        k1 = (k_factor * self.altura_terreno / lh) if h_sobre_lh >= 0.2 else 0.0
        # CIRSOC 102-2025 Figura 1.8-1: K2 = 0 si x > mu * Lh (K1, K2, K3 >= 0)
        k2 = max(0.0, 1 - self.distancia_barlovento_sotavento / (mu * lh))
        k3 = tuple(np.e ** (-1 * gamma * altura / lh) for altura in self.alturas)
        return _ParametrosTopograficos(k_factor, gamma, mu, lh, k1, k2, k3)

    @cached_property
    def factor(self) -> tuple[float, ...]:
        """Calcula el factor topográfico Kzt (CIRSOC 102-2025 Expresión 1.8-1).

        Returns:
            El factor topográfico de cada altura.
        """
        if not self.topografia_considerada():
            return (1.0,) * len(self.alturas)
        parametros = self.parametros
        return tuple(
            (1 + parametros.k1 * parametros.k2 * k3) ** 2 for k3 in parametros.k3
        )

    def k3_en(self, altura: float) -> float:
        """Obtiene el factor K3 correspondiente a una de las alturas consideradas.

        Args:
            altura: La altura buscada.

        Returns:
            El factor K3 de esa altura.

        Raises:
            ValueError: Cuando la altura no es una de las consideradas.
        """
        for considerada, k3 in zip(self.alturas, self.parametros.k3, strict=True):
            if considerada == altura:
                return k3
        raise ValueError(f"No hay factor topográfico calculado para {altura} m.")
