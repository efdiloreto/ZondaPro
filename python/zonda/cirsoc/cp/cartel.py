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

"""Coeficientes de fuerza de paredes libres llenas y carteles libres llenos.

La Figura 4.4-1 del CIRSOC 102-2025 tabula el coeficiente de fuerza ``Cf`` en
función de la relación de espacio libre ``s/h`` y de la relación de aspecto
``B/s``, y pide considerar tres casos: el Caso A aplica la fuerza resultante en
el centro geométrico del cartel, el Caso B la aplica con una excentricidad hacia
el borde de barlovento y el Caso C -sólo para B/s ≥ 2- la reparte en regiones
horizontales medidas desde el borde de barlovento.

Las Notas de la figura permiten reducir los coeficientes por las aberturas del
cartel (ε), por la esquina de retorno ``Lr`` de una pared libre y, para carteles
de doble cara con todos los lados cerrados, por el espesor ``t`` (Rmin y Rmax).
"""

from __future__ import annotations

from functools import cached_property
from typing import ClassVar

import numpy as np

from zonda.cirsoc import geometria
from zonda.enums import RegionCartel

_REGIONES_AGRUPADAS = (
    RegionCartel.REGION_0_S,
    RegionCartel.REGION_S_2S,
    RegionCartel.REGION_2S_3S,
    RegionCartel.REGION_3S_10S,
)

_REGIONES_SEPARADAS = (
    RegionCartel.REGION_0_S,
    RegionCartel.REGION_S_2S,
    RegionCartel.REGION_2S_3S,
    RegionCartel.REGION_3S_4S,
    RegionCartel.REGION_4S_5S,
    RegionCartel.REGION_5S_10S,
    RegionCartel.REGION_10S,
)


class Cartel:
    """Cartel.

    Determina los coeficientes de fuerza de la Figura 4.4-1 para paredes libres
    llenas y carteles libres llenos.
    """

    referencia = "Figura 4.4-1"

    # Tabla de los Casos A y B. Las filas son la relación de espacio libre s/h,
    # en orden ascendente, y las columnas la relación de aspecto B/s. Los
    # extremos de ambas escalas son abiertos (≤ y ≥) y la interpolación los
    # cubre.
    _relaciones_espacio_libre = (0.16, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0)
    _relaciones_aspecto_ab = (
        0.05,
        0.1,
        0.2,
        0.5,
        1.0,
        2.0,
        4.0,
        5.0,
        10.0,
        20.0,
        30.0,
        45.0,
    )
    _tabla_ab = (
        (1.95, 1.90, 1.85, 1.85, 1.80, 1.80, 1.85, 1.85, 1.85, 1.90, 1.90, 1.95),
        (1.95, 1.90, 1.85, 1.80, 1.80, 1.80, 1.80, 1.80, 1.85, 1.90, 1.90, 1.95),
        (1.95, 1.90, 1.85, 1.80, 1.80, 1.80, 1.80, 1.80, 1.80, 1.85, 1.85, 1.85),
        (1.95, 1.85, 1.80, 1.75, 1.75, 1.70, 1.70, 1.70, 1.70, 1.70, 1.70, 1.75),
        (1.90, 1.85, 1.75, 1.70, 1.65, 1.60, 1.60, 1.55, 1.55, 1.55, 1.55, 1.55),
        (1.85, 1.75, 1.70, 1.60, 1.55, 1.50, 1.45, 1.45, 1.40, 1.40, 1.40, 1.40),
        (1.80, 1.70, 1.65, 1.55, 1.45, 1.40, 1.35, 1.35, 1.30, 1.30, 1.30, 1.30),
    )

    # Tabla del Caso C. La clave es la relación de aspecto B/s. Para B/s ≤ 10
    # la tabla agrupa desde 3s en REGION_3S_10S; para B/s mayores separa esa
    # banda. Los valores con asterisco en la figura -la primera región cuando
    # B/s ≥ 5- son los que reduce la esquina de retorno.
    _relaciones_aspecto_c = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 13.0, 45.0)
    _tabla_c: ClassVar[dict[float, dict[RegionCartel, float]]] = {
        2.0: {RegionCartel.REGION_0_S: 2.25, RegionCartel.REGION_S_2S: 1.50},
        3.0: {
            RegionCartel.REGION_0_S: 2.60,
            RegionCartel.REGION_S_2S: 1.70,
            RegionCartel.REGION_2S_3S: 1.15,
        },
        4.0: {
            RegionCartel.REGION_0_S: 2.90,
            RegionCartel.REGION_S_2S: 1.90,
            RegionCartel.REGION_2S_3S: 1.30,
            RegionCartel.REGION_3S_10S: 1.10,
        },
        5.0: {
            RegionCartel.REGION_0_S: 3.10,
            RegionCartel.REGION_S_2S: 2.00,
            RegionCartel.REGION_2S_3S: 1.45,
            RegionCartel.REGION_3S_10S: 1.05,
        },
        6.0: {
            RegionCartel.REGION_0_S: 3.30,
            RegionCartel.REGION_S_2S: 2.15,
            RegionCartel.REGION_2S_3S: 1.55,
            RegionCartel.REGION_3S_10S: 1.05,
        },
        7.0: {
            RegionCartel.REGION_0_S: 3.40,
            RegionCartel.REGION_S_2S: 2.25,
            RegionCartel.REGION_2S_3S: 1.65,
            RegionCartel.REGION_3S_10S: 1.05,
        },
        8.0: {
            RegionCartel.REGION_0_S: 3.55,
            RegionCartel.REGION_S_2S: 2.30,
            RegionCartel.REGION_2S_3S: 1.70,
            RegionCartel.REGION_3S_10S: 1.05,
        },
        9.0: {
            RegionCartel.REGION_0_S: 3.65,
            RegionCartel.REGION_S_2S: 2.35,
            RegionCartel.REGION_2S_3S: 1.75,
            RegionCartel.REGION_3S_10S: 1.00,
        },
        10.0: {
            RegionCartel.REGION_0_S: 3.75,
            RegionCartel.REGION_S_2S: 2.45,
            RegionCartel.REGION_2S_3S: 1.85,
            RegionCartel.REGION_3S_10S: 0.95,
        },
        13.0: {
            RegionCartel.REGION_0_S: 4.00,
            RegionCartel.REGION_S_2S: 2.60,
            RegionCartel.REGION_2S_3S: 2.00,
            RegionCartel.REGION_3S_4S: 1.50,
            RegionCartel.REGION_4S_5S: 1.35,
            RegionCartel.REGION_5S_10S: 0.90,
            RegionCartel.REGION_10S: 0.55,
        },
        45.0: {
            RegionCartel.REGION_0_S: 4.30,
            RegionCartel.REGION_S_2S: 2.55,
            RegionCartel.REGION_2S_3S: 1.95,
            RegionCartel.REGION_3S_4S: 1.85,
            RegionCartel.REGION_4S_5S: 1.85,
            RegionCartel.REGION_5S_10S: 1.10,
            RegionCartel.REGION_10S: 0.55,
        },
    }

    def __init__(
        self,
        altura_inferior: float,
        altura_neta: float,
        altura_superior: float,
        ancho: float,
        profundidad: float,
        epsilon: float = 1.0,
        doble_cara: bool = False,
        esquina_retorno: float = 0.0,
    ) -> None:
        """

        Args:
            altura_inferior: La altura del espacio libre bajo el cartel.
            altura_neta: s, la altura de la superficie del cartel donde pega el viento.
            altura_superior: h, la altura medida desde el suelo hasta la punta del cartel.
            ancho: B, el ancho del cartel.
            profundidad: t, el espesor del cartel.
            epsilon: La relación entre el área sólida y el área bruta (Nota 1). El
                valor 1.0 es un cartel sin aberturas.
            doble_cara: Si es True, el cartel es de doble cara con todos los lados
                cerrados y aplican las reducciones de Rmin y Rmax de la Nota 2.
            esquina_retorno: La dimensión horizontal Lr de la esquina de retorno, en
                metros. El valor 0 indica que no hay esquina de retorno.

        Raises:
            ValueError: Si epsilon no está entre 0.7 y 1.0, o si la esquina de
                retorno es negativa.
        """
        if not 0.7 <= epsilon <= 1.0:
            raise ValueError(
                "La relación de área sólida epsilon debe estar entre 0.7 y 1.0: la"
                " Figura 4.4-1 sólo cubre carteles llenos, con aberturas menores al"
                " 30 % del área bruta."
            )
        if esquina_retorno < 0:
            raise ValueError("La esquina de retorno no puede ser negativa.")
        self.altura_inferior = altura_inferior
        self.altura_neta = altura_neta
        self.altura_superior = altura_superior
        self.ancho = ancho
        self.profundidad = profundidad
        self.epsilon = epsilon
        self.doble_cara = doble_cara
        self.esquina_retorno = esquina_retorno

    @property
    def relacion_espacio_libre(self) -> float:
        """La relación de espacio libre s/h.

        Es el cociente entre la altura del cartel y la altura medida desde el
        suelo hasta su punta. El valor 1 corresponde a un cartel o pared apoyado
        en forma continua en el suelo.
        """
        return self.altura_neta / self.altura_superior

    @property
    def relacion_aspecto(self) -> float:
        """La relación de aspecto B/s."""
        return self.ancho / self.altura_neta

    @cached_property
    def r_min(self) -> float:
        """La relación entre el espesor y la menor dimensión del cartel."""
        return self.profundidad / min(self.ancho, self.altura_neta)

    @cached_property
    def r_max(self) -> float:
        """La relación entre el espesor y la mayor dimensión del cartel."""
        return self.profundidad / max(self.ancho, self.altura_neta)

    @property
    def factor_aberturas(self) -> float:
        """El factor de reducción por aberturas de la Nota 1."""
        return 1.0 - (1.0 - self.epsilon) ** 1.5

    @cached_property
    def aplica_caso_c(self) -> bool:
        """Indica si corresponde considerar el Caso C (Nota 2: B/s ≥ 2)."""
        return self.relacion_aspecto >= 2.0

    @cached_property
    def cf_casos_ab(self) -> float:
        """El coeficiente de fuerza de los Casos A y B.

        Interpola la tabla en s/h y B/s y aplica las reducciones de la Nota 1
        (aberturas) y, para carteles de doble cara con todos los lados cerrados,
        la de Rmin de la Nota 2.
        """
        cf = self._cf_tabla_ab()
        if self.doble_cara and self.r_min <= 0.75:
            cf *= 1.0 - 0.133 * self.r_min
        return float(cf) * self.factor_aberturas

    @cached_property
    def excentricidad(self) -> float:
        """La excentricidad e del Caso B, en metros.

        Es la distancia desde el centro geométrico hacia el borde de barlovento
        a la que actúa la fuerza resultante. Para carteles de doble cara con
        todos los lados cerrados y Rmax ≤ 0.4 la Nota 2 permite reducirla.
        """
        if self.doble_cara and self.r_max <= 0.4:
            return (0.2 - 0.25 * self.r_max) * self.ancho
        return 0.2 * self.ancho

    @cached_property
    def factor_esquina_retorno(self) -> float:
        """El factor de reducción por esquina de retorno.

        Reduce los valores con asterisco de la tabla del Caso C -la primera
        región cuando B/s ≥ 5- según Lr/s. Sin esquina de retorno, con Lr/s
        menor que 0.3 o con B/s menor que 5, no reduce.
        """
        if self.esquina_retorno <= 0 or self.relacion_aspecto < 5.0:
            return 1.0
        lr_s = self.esquina_retorno / self.altura_neta
        if lr_s < 0.3:
            return 1.0
        if lr_s >= 2.0:
            return 0.6
        if lr_s <= 1.0:
            return float(np.interp(lr_s, (0.3, 1.0), (0.9, 0.75)))
        return float(np.interp(lr_s, (1.0, 2.0), (0.75, 0.6)))

    @cached_property
    def limites_regiones(self) -> dict[RegionCartel, tuple[float, float]]:
        """Los límites de cada región del Caso C, en metros desde el borde de barlovento.

        Las regiones cubren todo el ancho del cartel, sin huecos ni solapes, y
        la última se recorta en el borde de sotavento. Cuando B/s ≤ 10 la banda
        desde 3s va agrupada; para B/s mayores va separada, como en la figura.

        Returns:
            Cada región con el par (inicio, fin) en metros. Vacío cuando el
            Caso C no aplica (B/s < 2).
        """
        if not self.aplica_caso_c:
            return {}
        b_s = self.relacion_aspecto
        regiones = _REGIONES_AGRUPADAS if b_s <= 10.0 else _REGIONES_SEPARADAS
        s = self.altura_neta
        return {
            region: (region.inicio * s, min(region.fin, b_s) * s)
            for region in regiones
            if region.inicio < b_s
        }

    @cached_property
    def cf_por_region(self) -> dict[RegionCartel, float]:
        """Los coeficientes de fuerza del Caso C por región.

        Interpola la tabla del Caso C en B/s y aplica las reducciones de la
        Nota 1 (aberturas), la de la Nota 3 para s/h > 0.8 y la de la esquina
        de retorno en la primera región.

        Returns:
            Cada región con su coeficiente. Vacío cuando el Caso C no aplica
            (B/s < 2).
        """
        return {region: self._cf_region(region) for region in self.limites_regiones}

    def _cf_region(self, region: RegionCartel) -> float:
        """El coeficiente de la región con las reducciones aplicables."""
        cf = self._cf_tabla_c(region)
        cf *= self.factor_aberturas
        if self.relacion_espacio_libre > 0.8:
            cf *= 1.8 - self.relacion_espacio_libre
        if region is RegionCartel.REGION_0_S:
            cf *= self.factor_esquina_retorno
        return cf

    def _cf_tabla_ab(self) -> float:
        """El coeficiente de la tabla de los Casos A y B, interpolando en s/h y B/s."""
        por_columna = [
            np.interp(self.relacion_aspecto, self._relaciones_aspecto_ab, fila)
            for fila in self._tabla_ab
        ]
        return np.interp(
            self.relacion_espacio_libre, self._relaciones_espacio_libre, por_columna
        )

    def _cf_tabla_c(self, region: RegionCartel) -> float:
        """El coeficiente de la tabla del Caso C para la región, interpolando en B/s.

        Cuando una región no figura en una de las columnas que rodean a B/s -
        porque esa columna la agrupa en una banda mayor o porque no existe- se
        usa el valor de la otra columna, o el de la región que la cubre.
        """
        b_s = self.relacion_aspecto
        columnas = self._relaciones_aspecto_c
        if b_s <= columnas[0]:
            valor = self._valor_tabla_c(columnas[0], region)
            assert valor is not None, "la región no existe en la tabla"
            return valor
        if b_s >= columnas[-1]:
            valor = self._valor_tabla_c(columnas[-1], region)
            assert valor is not None, "la región no existe en la tabla"
            return valor
        indice = int(np.searchsorted(columnas, b_s))
        menor, mayor = columnas[indice - 1], columnas[indice]
        valor_menor = self._valor_tabla_c(menor, region)
        valor_mayor = self._valor_tabla_c(mayor, region)
        if valor_menor is None:
            assert valor_mayor is not None, "la región no existe en la tabla"
            return valor_mayor
        if valor_mayor is None:
            return valor_menor
        peso = (b_s - menor) / (mayor - menor)
        return valor_menor + peso * (valor_mayor - valor_menor)

    def _valor_tabla_c(self, columna: float, region: RegionCartel) -> float | None:
        """El valor tabulado de la región en la columna, o el de la región que la cubre.

        Returns:
            El coeficiente tabulado, o None si la región no existe en la columna.
        """
        tabla = self._tabla_c[columna]
        if region in tabla:
            return tabla[region]
        for candidata, valor in tabla.items():
            if candidata.inicio <= region.inicio and region.fin <= candidata.fin:
                return valor
        return None

    @classmethod
    def desde_cartel(
        cls,
        cartel: geometria.Cartel,
        epsilon: float = 1.0,
        doble_cara: bool = False,
        esquina_retorno: float = 0.0,
    ) -> Cartel:
        """Crea una instancia desde la geometría de un cartel.

        Args:
            cartel: La geometría de un cartel.
            epsilon: La relación entre el área sólida y el área bruta (Nota 1).
            doble_cara: Si es True, el cartel es de doble cara con todos los lados
                cerrados.
            esquina_retorno: La dimensión horizontal Lr de la esquina de retorno, en
                metros. El valor 0 indica que no hay.

        Returns:
            Una instancia de Cartel.
        """
        return cls(
            cartel.altura_inferior,
            cartel.altura_neta,
            cartel.altura_superior,
            cartel.ancho,
            cartel.profundidad,
            epsilon=epsilon,
            doble_cara=doble_cara,
            esquina_retorno=esquina_retorno,
        )
