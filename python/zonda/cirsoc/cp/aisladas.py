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

"""Coeficientes de presión neta de cubiertas aisladas, artículo 2.4.3.

Las Figuras 2.4-4 a 2.4-7 dan valores de C_N firmados para dos casos de carga
(A y B) según la dirección del viento: perpendicular a la cumbrera (γ = 0º y
180º), con las mitades de barlovento y de sotavento de la superficie, o
paralelo a ella (γ = 90º y 270º), con bandas medidas desde el borde de
barlovento. Cada tabla distingue el flujo de viento libre (bloqueo ≤ 50 %) del
obstruido (bloqueo > 50 %).

Para cubiertas a dos aguas con ángulo menor que 7,5º se usan los coeficientes
de vertiente única (notas 3 de las Figuras 2.4-5 y 2.4-6), que para ángulos
menores a 7,5º son los de 0º (nota 3 de la Figura 2.4-4).

Para componentes y revestimientos, las Figuras 5.5-1 a 5.5-3 dan coeficientes
de presión neta C_N por zona (1, 2 y 3), para tres rangos de área efectiva de
viento (≤ a²; > a², ≤ 4a²; > 4a²) y dos situaciones de bloqueo. Cada zona
tiene un coeficiente positivo y uno negativo, y para ángulos distintos de los
tabulados se permite interpolar linealmente (nota 3).
"""

from __future__ import annotations

from functools import cached_property

import numpy as np

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.cirsoc.cp.edificio import distancia_a
from zonda.cirsoc.resultados import EntradaCpn, EntradaCpnComponentes
from zonda.enums import (
    CasoCargaCubiertaAislada,
    DireccionVientoCubiertaAislada,
    TipoCubierta,
    TipoPresionComponentesParedesCubierta,
    ZonaComponenteCubiertaAislada,
    ZonaPresionCubiertaAislada,
)

ANGULOS_VERTIENTE_UNICA = (0.0, 7.5, 15.0, 22.5, 30.0, 37.5, 45.0)
ANGULOS_DOS_AGUAS = (7.5, 15.0, 22.5, 30.0, 37.5, 45.0)

# Cada fila reúne los cuatro valores del ángulo: (A: CNW, CNL), (B: CNW, CNL).
# Figura 2.4-4. Vertiente única, una tabla por dirección y bloqueo.
_FIGURA_2_4_4 = {
    (DireccionVientoCubiertaAislada.GAMMA_0, False): (
        (1.2, 0.3, -1.1, -0.1),
        (-0.6, -1.0, -1.4, 0.0),
        (-0.9, -1.3, -1.9, 0.0),
        (-1.5, -1.6, -2.4, -0.3),
        (-1.8, -1.8, -2.5, -0.5),
        (-1.8, -1.8, -2.4, -0.6),
        (-1.6, -1.8, -2.3, -0.7),
    ),
    (DireccionVientoCubiertaAislada.GAMMA_0, True): (
        (-0.5, -1.2, -1.1, -0.6),
        (-1.0, -1.5, -1.7, -0.8),
        (-1.1, -1.5, -2.1, -0.6),
        (-1.5, -1.7, -2.3, -0.9),
        (-1.5, -1.8, -2.3, -1.1),
        (-1.5, -1.8, -2.2, -1.1),
        (-1.3, -1.8, -1.9, -1.2),
    ),
    (DireccionVientoCubiertaAislada.GAMMA_180, False): (
        (1.2, 0.3, -1.1, -0.1),
        (0.9, 1.5, 1.6, 0.3),
        (1.3, 1.6, 1.8, 0.6),
        (1.7, 1.8, 2.2, 0.7),
        (2.1, 2.1, 2.6, 1.0),
        (2.1, 2.2, 2.7, 1.1),
        (2.2, 2.5, 2.6, 1.4),
    ),
    (DireccionVientoCubiertaAislada.GAMMA_180, True): (
        (-0.5, -1.2, -1.1, -0.6),
        (-0.2, -1.2, 0.8, -0.3),
        (0.4, -1.1, 1.2, -0.3),
        (0.5, -1.0, 1.3, 0.0),
        (0.6, -1.0, 1.6, 0.1),
        (0.7, -0.9, 1.9, 0.3),
        (0.8, -0.9, 2.1, 0.4),
    ),
}

# Figuras 2.4-5 (diedro positivo) y 2.4-6 (diedro negativo). La dirección del
# viento γ = 0º y 180º comparte valores: sólo se intercambian barlovento y
# sotavento. Una tabla por bloqueo.
_FIGURA_2_4_5 = {
    False: (
        (1.1, -0.3, 0.2, -1.2),
        (1.1, -0.4, 0.1, -1.1),
        (1.1, 0.1, -0.1, -0.8),
        (1.3, 0.3, -0.1, -0.9),
        (1.3, 0.6, -0.2, -0.6),
        (1.1, 0.9, -0.3, -0.5),
    ),
    True: (
        (-1.6, -1.0, -0.9, -1.7),
        (-1.2, -1.0, -0.6, -1.6),
        (-1.2, -1.2, -0.8, -1.7),
        (-0.7, -0.7, -0.2, -1.1),
        (-0.6, -0.6, -0.3, -0.9),
        (-0.5, -0.5, -0.3, -0.7),
    ),
}

_FIGURA_2_4_6 = {
    False: (
        (-1.1, 0.3, -0.2, 1.2),
        (-1.1, 0.4, 0.1, 1.1),
        (-1.1, -0.1, -0.1, 0.8),
        (-1.3, -0.3, -0.1, 0.9),
        (-1.3, -0.6, 0.2, 0.6),
        (-1.1, -0.9, 0.3, 0.5),
    ),
    True: (
        (-1.6, -0.5, -0.9, -0.8),
        (-1.2, -0.5, -0.6, -0.8),
        (-1.2, -0.6, -0.8, -0.8),
        (-1.4, -0.4, -0.2, -0.5),
        (-1.4, -0.3, -0.3, -0.4),
        (-1.2, -0.3, -0.3, -0.4),
    ),
}

# Figura 2.4-7. Viento paralelo a la cumbrera, γ = 90º y 270º. El valor de cada
# banda depende sólo del bloqueo, y dentro de ella del caso de carga.
_FIGURA_2_4_7 = {
    False: {
        ZonaPresionCubiertaAislada.HASTA_H: (-0.8, 0.8),
        ZonaPresionCubiertaAislada.ENTRE_H_Y_2H: (-0.6, 0.5),
        ZonaPresionCubiertaAislada.MAYOR_2H: (-0.3, 0.3),
    },
    True: {
        ZonaPresionCubiertaAislada.HASTA_H: (-1.2, 0.5),
        ZonaPresionCubiertaAislada.ENTRE_H_Y_2H: (-0.9, 0.5),
        ZonaPresionCubiertaAislada.MAYOR_2H: (-0.6, 0.3),
    },
}

# Los límites de las bandas de la Figura 2.4-7, en distancias horizontales
# medidas desde el borde de barlovento y en unidades de la altura media h.
_LIMITES_BANDAS = {
    ZonaPresionCubiertaAislada.HASTA_H: (0.0, 1.0),
    ZonaPresionCubiertaAislada.ENTRE_H_Y_2H: (1.0, 2.0),
    ZonaPresionCubiertaAislada.MAYOR_2H: (2.0, float("inf")),
}

DIRECCIONES_PERPENDICULARES = (
    DireccionVientoCubiertaAislada.GAMMA_0,
    DireccionVientoCubiertaAislada.GAMMA_180,
)
DIRECCIONES_PARALELAS = (
    DireccionVientoCubiertaAislada.GAMMA_90,
    DireccionVientoCubiertaAislada.GAMMA_270,
)


class CubiertaAislada:
    """CubiertaAislada.

    Determinar los coeficientes de presión neta de cubiertas aisladas,
    artículo 2.4.3 del Reglamento CIRSOC 102-2025.
    """

    def __init__(
        self,
        tipo_cubierta: TipoCubierta,
        angulo: float,
        con_bloqueo: bool,
        altura_media: float,
        ancho: float,
        longitud: float,
    ) -> None:
        """

        Args:
            tipo_cubierta: El tipo de cubierta.
            angulo: El ángulo de la cubierta. Para cubiertas a dos aguas con
                diedro negativo es negativo.
            con_bloqueo: Indica si el flujo de viento bajo la cubierta está
                obstruido (bloqueo mayor al 50 %).
            altura_media: La altura media del techo, h.
            ancho: El ancho de la cubierta. Es la dimensión horizontal en la
                dirección del viento de las Figuras 2.4-4 a 2.4-6.
            longitud: La longitud de la cubierta. Es la dimensión horizontal
                en la dirección del viento de la Figura 2.4-7.

        Raises:
            ErrorLineamientos si el Reglamento no provee lineamientos para la
            geometría, o si h/L queda fuera del rango de 0,25 a 1,0.
        """
        if tipo_cubierta not in (TipoCubierta.DOS_AGUAS, TipoCubierta.UN_AGUA):
            raise excepciones.ErrorLineamientos(
                "El Reglamento solo provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                " a dos aguas y a un agua."
            )
        if tipo_cubierta == TipoCubierta.UN_AGUA and not 0 <= angulo <= 45:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                f" aisladas a un agua con ángulo igual a {angulo:.2f}°."
            )
        if tipo_cubierta == TipoCubierta.DOS_AGUAS and not -45 <= angulo <= 45:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                f" aisladas a dos aguas con ángulo igual a {angulo:.2f}°."
            )

        self.tipo_cubierta = tipo_cubierta
        self.angulo = angulo
        self.con_bloqueo = con_bloqueo
        self.altura_media = altura_media
        self.ancho = ancho
        self.longitud = longitud

        self._validar_relacion_h_l()

    def _validar_relacion_h_l(self) -> None:
        """Valida que h/L esté entre 0,25 y 1,0 para cada dirección del viento.

        L es la dimensión horizontal del techo medida en la dirección del
        viento: el ancho para viento perpendicular a la cumbrera y la longitud
        para viento paralelo.

        Raises:
            ErrorLineamientos si alguna dirección queda fuera del rango.
        """
        for direccion, relacion in (
            *(
                (direccion, self.altura_media / self.ancho)
                for direccion in DIRECCIONES_PERPENDICULARES
            ),
            *(
                (direccion, self.altura_media / self.longitud)
                for direccion in DIRECCIONES_PARALELAS
            ),
        ):
            if 0.25 <= relacion <= 1.0:
                continue
            mensaje = (
                f"La relación h/L = {relacion:.2f} para la dirección del viento {direccion.value} está fuera del rango de 0,25 a 1,0"
                " de las Figuras 2.4-4 a 2.4-7."
            )
            if (
                self.tipo_cubierta == TipoCubierta.UN_AGUA
                and self.angulo < 5
                and direccion in DIRECCIONES_PERPENDICULARES
            ):
                mensaje += (
                    " La nota 5 de la Figura 2.4-7 extiende el rango hasta 0,05 solo para γ = 0º; las demás"
                    " direcciones quedan sin lineamientos."
                )
            raise excepciones.ErrorLineamientos(mensaje)

    @cached_property
    def entradas(self) -> tuple[EntradaCpn, ...]:
        """Calcula los factores cpn para la cubierta.

        Returns:
            Una entrada por cada combinación de dirección, caso de carga y
            zona de las Figuras 2.4-4 a 2.4-7.
        """
        return tuple(
            EntradaCpn(
                direccion=direccion,
                caso=caso,
                valor=float(valor),
                referencia=self._referencia(direccion),
                zona=zona,
            )
            for direccion in DireccionVientoCubiertaAislada
            for caso in CasoCargaCubiertaAislada
            for zona, valor in self._valores(direccion, caso)
        )

    def _referencia(self, direccion: DireccionVientoCubiertaAislada) -> str:
        """La referencia reglamentaria de los coeficientes de una dirección.

        Args:
            direccion: La dirección del viento.

        Returns:
            La figura o tabla de donde salen los valores.
        """
        if direccion in DIRECCIONES_PARALELAS:
            return "Figura 2.4-7"
        if self.tipo_cubierta == TipoCubierta.UN_AGUA or abs(self.angulo) < 7.5:
            return "Figura 2.4-4"
        if self.angulo < 0:
            return "Figura 2.4-6"
        return "Figura 2.4-5"

    def _valores(
        self, direccion: DireccionVientoCubiertaAislada, caso: CasoCargaCubiertaAislada
    ):
        """Los coeficientes de cada zona para una dirección y un caso.

        Args:
            direccion: La dirección del viento.
            caso: El caso de carga.

        Returns:
            Una tupla de pares zona-valor. Para viento paralelo a la cumbrera
            sólo incluye las bandas que caben en la longitud de la cubierta.
        """
        if direccion in DIRECCIONES_PERPENDICULARES:
            caso_a, caso_b = self._fila_perpendicular(direccion)
            valores = caso_a if caso is CasoCargaCubiertaAislada.CASO_A else caso_b
            return (
                (ZonaPresionCubiertaAislada.BARLOVENTO, valores[0]),
                (ZonaPresionCubiertaAislada.SOTAVENTO, valores[1]),
            )
        indice_caso = 0 if caso is CasoCargaCubiertaAislada.CASO_A else 1
        return tuple(
            (zona, self._figura_2_4_7[zona][indice_caso])
            for zona in _LIMITES_BANDAS
            if _LIMITES_BANDAS[zona][0] * self.altura_media < self.longitud
        )

    @property
    def _figura_2_4_7(self):
        """La tabla de la Figura 2.4-7 según el bloqueo."""
        return _FIGURA_2_4_7[self.con_bloqueo]

    def _fila_perpendicular(
        self, direccion: DireccionVientoCubiertaAislada
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Los coeficientes de barlovento y sotavento de los dos casos de carga.

        Args:
            direccion: La dirección del viento, perpendicular a la cumbrera.

        Returns:
            Los valores (CNW, CNL) del Caso A y del Caso B, interpolados al
            ángulo de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            tabla = _FIGURA_2_4_4[(direccion, self.con_bloqueo)]
            return self._interpolar(tabla, ANGULOS_VERTIENTE_UNICA, self.angulo)
        if abs(self.angulo) < 7.5:
            # Notas 3 de las Figuras 2.4-5 y 2.4-6: se usan los coeficientes
            # de vertiente única, que para ángulos menores a 7,5º son los de
            # 0º. Los de 0º no dependen de la dirección.
            clave = (DireccionVientoCubiertaAislada.GAMMA_0, self.con_bloqueo)
            return self._interpolar(_FIGURA_2_4_4[clave], ANGULOS_VERTIENTE_UNICA, 0.0)
        figura = _FIGURA_2_4_5 if self.angulo > 0 else _FIGURA_2_4_6
        return self._interpolar(
            figura[self.con_bloqueo], ANGULOS_DOS_AGUAS, abs(self.angulo)
        )

    @staticmethod
    def _interpolar(
        tabla: tuple[tuple[float, float, float, float], ...],
        angulos: tuple[float, ...],
        angulo: float,
    ):
        """Interpola los cuatro valores de la tabla al ángulo dado.

        Args:
            tabla: Una fila por ángulo, con (A: CNW, CNL), (B: CNW, CNL).
            angulos: Los ángulos de las filas de la tabla.
            angulo: El ángulo al que interpolar.

        Returns:
            Los valores (CNW, CNL) del Caso A y del Caso B.
        """
        if angulo < angulos[1]:
            # Nota 3 de la Figura 2.4-4: para ángulos menores al primero del
            # rango de interpolación se usan los coeficientes de 0º.
            fila = tabla[0]
            return (fila[0], fila[1]), (fila[2], fila[3])
        columnas = tuple(
            float(np.interp(angulo, angulos, valores))
            for valores in zip(*tabla, strict=True)
        )
        return (columnas[0], columnas[1]), (columnas[2], columnas[3])

    @classmethod
    def desde_cubierta(cls, cubierta: geometria.Cubierta):
        """Crea una instancia desde la geometria de una cubierta.

        Args:
            cubierta: La geometria de una cubierta.
        """
        return cls(
            cubierta.tipo_cubierta,
            cubierta.angulo,
            cubierta.con_bloqueo,
            cubierta.altura_media,
            cubierta.ancho,
            cubierta.longitud,
        )


# Cada valor de las Figuras 5.5-1 a 5.5-3 es la tupla
# (Zona 3 positiva, Zona 3 negativa, Zona 2 positiva, Zona 2 negativa,
# Zona 1 positiva, Zona 1 negativa) de un rango de área efectiva de viento
# (≤ a²; > a², ≤ 4a²; > 4a²), en ese orden. Hay una fila por ángulo
# (0°, 7.5°, 15°, 30°, 45°) y un bloque por situación de bloqueo
# (False: sin bloqueo; True: con bloqueo).
ANGULOS_COMPONENTES = (0.0, 7.5, 15.0, 30.0, 45.0)

# Los seis valores de una fila de las figuras: Zonas 3, 2 y 1, cada una con
# su coeficiente positivo y su negativo.
_ValorCN = tuple[float, float, float, float, float, float]

# Figura 5.5-1. Vertiente única.
_FIGURA_5_5_1: dict[bool, tuple[tuple[_ValorCN, _ValorCN, _ValorCN], ...]] = {
    False: (
        (
            (2.4, -3.3, 1.8, -1.7, 1.2, -1.1),
            (1.8, -1.7, 1.8, -1.7, 1.2, -1.1),
            (1.2, -1.1, 1.2, -1.1, 1.2, -1.1),
        ),
        (
            (3.2, -4.2, 2.4, -2.1, 1.6, -1.4),
            (2.4, -2.1, 2.4, -2.1, 1.6, -1.4),
            (1.6, -1.4, 1.6, -1.4, 1.6, -1.4),
        ),
        (
            (3.6, -3.8, 2.7, -2.9, 1.8, -1.9),
            (2.7, -2.9, 2.7, -2.9, 1.8, -1.9),
            (1.8, -1.9, 1.8, -1.9, 1.8, -1.9),
        ),
        (
            (5.2, -5.0, 3.9, -3.8, 2.6, -2.5),
            (3.9, -3.8, 3.9, -3.8, 2.6, -2.5),
            (2.6, -2.5, 2.6, -2.5, 2.6, -2.5),
        ),
        (
            (5.2, -4.6, 3.9, -3.5, 2.6, -2.3),
            (3.9, -3.5, 3.9, -3.5, 2.6, -2.3),
            (2.6, -2.3, 2.6, -2.3, 2.6, -2.3),
        ),
    ),
    True: (
        (
            (1.0, -3.6, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
        (
            (1.6, -5.1, 1.2, -2.6, 0.8, -1.7),
            (1.2, -2.6, 1.2, -2.6, 0.8, -1.7),
            (0.8, -1.7, 0.8, -1.7, 0.8, -1.7),
        ),
        (
            (2.4, -4.2, 1.8, -3.2, 1.2, -2.1),
            (1.8, -3.2, 1.8, -3.2, 1.2, -2.1),
            (1.2, -2.1, 1.2, -2.1, 1.2, -2.1),
        ),
        (
            (3.2, -4.6, 2.4, -3.5, 1.6, -2.3),
            (2.4, -3.5, 2.4, -3.5, 1.6, -2.3),
            (1.6, -2.3, 1.6, -2.3, 1.6, -2.3),
        ),
        (
            (4.2, -3.8, 3.2, -2.9, 2.1, -1.9),
            (3.2, -2.9, 3.2, -2.9, 2.1, -1.9),
            (2.1, -1.9, 2.1, -1.9, 2.1, -1.9),
        ),
    ),
}

# Figura 5.5-2. Dos aguas (diedro positivo).
_FIGURA_5_5_2: dict[bool, tuple[tuple[_ValorCN, _ValorCN, _ValorCN], ...]] = {
    False: (
        (
            (2.4, -3.3, 1.8, -1.7, 1.2, -1.1),
            (1.8, -1.7, 1.8, -1.7, 1.2, -1.1),
            (1.2, -1.1, 1.2, -1.1, 1.2, -1.1),
        ),
        (
            (2.2, -3.6, 1.7, -1.8, 1.1, -1.2),
            (1.7, -1.8, 1.7, -1.8, 1.1, -1.2),
            (1.1, -1.2, 1.1, -1.2, 1.1, -1.2),
        ),
        (
            (2.2, -2.2, 1.7, -1.7, 1.1, -1.1),
            (1.7, -1.7, 1.7, -1.7, 1.1, -1.1),
            (1.1, -1.1, 1.1, -1.1, 1.1, -1.1),
        ),
        (
            (2.6, -1.8, 2.0, -1.4, 1.3, -0.9),
            (2.0, -1.4, 2.0, -1.4, 1.3, -0.9),
            (1.3, -0.9, 1.3, -0.9, 1.3, -0.9),
        ),
        (
            (2.2, -1.6, 1.7, -1.2, 1.1, -0.8),
            (1.7, -1.2, 1.7, -1.2, 1.1, -0.8),
            (1.1, -0.8, 1.1, -0.8, 1.1, -0.8),
        ),
    ),
    True: (
        (
            (1.0, -3.6, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
        (
            (1.0, -5.1, 0.8, -2.6, 0.5, -1.7),
            (0.8, -2.6, 0.8, -2.6, 0.5, -1.7),
            (0.5, -1.7, 0.5, -1.7, 0.5, -1.7),
        ),
        (
            (1.0, -3.2, 0.8, -2.4, 0.5, -1.6),
            (0.8, -2.4, 0.8, -2.4, 0.5, -1.6),
            (0.5, -1.6, 0.5, -1.6, 0.5, -1.6),
        ),
        (
            (1.0, -2.4, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
        (
            (1.0, -2.4, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
    ),
}

# Figura 5.5-3. Dos aguas con diedro negativo. El ángulo de la tabla es el
# módulo del diedro.
_FIGURA_5_5_3: dict[bool, tuple[tuple[_ValorCN, _ValorCN, _ValorCN], ...]] = {
    False: (
        (
            (2.4, -3.3, 1.8, -1.7, 1.2, -1.1),
            (1.8, -1.7, 1.8, -1.7, 1.2, -1.1),
            (1.2, -1.1, 1.2, -1.1, 1.2, -1.1),
        ),
        (
            (2.4, -3.3, 1.8, -1.7, 1.2, -1.1),
            (1.8, -1.7, 1.8, -1.7, 1.2, -1.1),
            (1.2, -1.1, 1.2, -1.1, 1.2, -1.1),
        ),
        (
            (2.2, -2.2, 1.7, -1.7, 1.1, -1.1),
            (1.7, -1.7, 1.7, -1.7, 1.1, -1.1),
            (1.1, -1.1, 1.1, -1.1, 1.1, -1.1),
        ),
        (
            (1.8, -2.6, 1.4, -2.0, 0.9, -1.3),
            (1.4, -2.0, 1.4, -2.0, 0.9, -1.3),
            (0.9, -1.3, 0.9, -1.3, 0.9, -1.3),
        ),
        (
            (1.6, -2.2, 1.2, -1.7, 0.8, -1.1),
            (1.2, -1.7, 1.2, -1.7, 0.8, -1.1),
            (0.8, -1.1, 0.8, -1.1, 0.8, -1.1),
        ),
    ),
    True: (
        (
            (1.0, -3.6, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
        (
            (1.0, -4.8, 0.8, -2.4, 0.5, -1.6),
            (0.8, -2.4, 0.8, -2.4, 0.5, -1.6),
            (0.5, -1.6, 0.5, -1.6, 0.5, -1.6),
        ),
        (
            (1.0, -2.4, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
        (
            (1.0, -2.8, 0.8, -2.1, 0.5, -1.4),
            (0.8, -2.1, 0.8, -2.1, 0.5, -1.4),
            (0.5, -1.4, 0.5, -1.4, 0.5, -1.4),
        ),
        (
            (1.0, -2.4, 0.8, -1.8, 0.5, -1.2),
            (0.8, -1.8, 0.8, -1.8, 0.5, -1.2),
            (0.5, -1.2, 0.5, -1.2, 0.5, -1.2),
        ),
    ),
}

_FIGURAS_COMPONENTES = {
    TipoCubierta.UN_AGUA: _FIGURA_5_5_1,
    TipoCubierta.DOS_AGUAS: _FIGURA_5_5_2,
}

# Las zonas en el orden en que vienen los valores de cada fila, con su signo.
_ZONAS_SIGNOS = (
    (
        ZonaComponenteCubiertaAislada.TRES,
        TipoPresionComponentesParedesCubierta.POSITIVA,
    ),
    (
        ZonaComponenteCubiertaAislada.TRES,
        TipoPresionComponentesParedesCubierta.NEGATIVA,
    ),
    (ZonaComponenteCubiertaAislada.DOS, TipoPresionComponentesParedesCubierta.POSITIVA),
    (ZonaComponenteCubiertaAislada.DOS, TipoPresionComponentesParedesCubierta.NEGATIVA),
    (ZonaComponenteCubiertaAislada.UNO, TipoPresionComponentesParedesCubierta.POSITIVA),
    (ZonaComponenteCubiertaAislada.UNO, TipoPresionComponentesParedesCubierta.NEGATIVA),
)

# Un par (zona, signo) de _ZONAS_SIGNOS junto con su valor.
_ZonaValor = tuple[
    ZonaComponenteCubiertaAislada,
    TipoPresionComponentesParedesCubierta,
    float,
]


class ComponentesCubiertaAislada:
    """ComponentesCubiertaAislada.

    Determina los coeficientes de presión neta para componentes y
    revestimientos de cubiertas aisladas de edificios abiertos, Figuras
    5.5-1 a 5.5-3 del Reglamento CIRSOC 102-2025.

    Las figuras consideran una sola dirección de viento, normal a la
    cumbrera o a lo largo de la vertiente, con L medido en esa dirección
    (el ancho de la cubierta).
    """

    def __init__(
        self,
        tipo_cubierta: TipoCubierta,
        angulo: float,
        con_bloqueo: bool,
        altura_media: float,
        ancho: float,
        longitud: float,
        componentes: dict[str, float] | None = None,
    ) -> None:
        """

        Args:
            tipo_cubierta: El tipo de cubierta.
            angulo: El ángulo de la cubierta. Para cubiertas a dos aguas con
                diedro negativo es negativo.
            con_bloqueo: Indica si el flujo de viento bajo la cubierta está
                obstruido (bloqueo mayor al 50 %).
            altura_media: La altura media del techo, h.
            ancho: El ancho de la cubierta. Es la dimensión horizontal en la
                dirección del viento de las figuras, L.
            longitud: La longitud de la cubierta.
            componentes: Los componentes para calcular los valores de C_N,
                donde la clave es el nombre del componente y el valor es su
                área efectiva de viento en m².

        Raises:
            ErrorLineamientos si el Reglamento no provee lineamientos para la
            geometría.
        """
        if tipo_cubierta not in (TipoCubierta.DOS_AGUAS, TipoCubierta.UN_AGUA):
            raise excepciones.ErrorLineamientos(
                "El Reglamento solo provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                " a dos aguas y a un agua."
            )
        if tipo_cubierta == TipoCubierta.UN_AGUA and not 0 <= angulo <= 45:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                f" aisladas a un agua con ángulo igual a {angulo:.2f}°."
            )
        if tipo_cubierta == TipoCubierta.DOS_AGUAS and not -45 <= angulo <= 45:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                f" aisladas a dos aguas con ángulo igual a {angulo:.2f}°."
            )

        self.tipo_cubierta = tipo_cubierta
        self.angulo = angulo
        self.con_bloqueo = con_bloqueo
        self.altura_media = altura_media
        self.ancho = ancho
        self.longitud = longitud
        self.componentes = componentes

    @classmethod
    def desde_cubierta(
        cls, cubierta: geometria.Cubierta, componentes: dict[str, float] | None = None
    ) -> ComponentesCubiertaAislada:
        """Crea una instancia desde la geometria de una cubierta.

        Args:
            cubierta: La geometria de una cubierta.
            componentes: Los componentes con sus áreas efectivas de viento.
        """
        return cls(
            cubierta.tipo_cubierta,
            cubierta.angulo,
            cubierta.con_bloqueo,
            cubierta.altura_media,
            cubierta.ancho,
            cubierta.longitud,
            componentes,
        )

    @cached_property
    def referencia(self) -> str:
        """La figura del Reglamento que corresponde a la cubierta.

        Returns:
            La referencia de la figura.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return "Figura 5.5-1"
        if self.angulo < 0:
            return "Figura 5.5-3"
        return "Figura 5.5-2"

    @property
    def _figura(self) -> dict[bool, tuple[tuple[_ValorCN, _ValorCN, _ValorCN], ...]]:
        """La tabla de la figura que corresponde, indexada por bloqueo."""
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return _FIGURA_5_5_1
        if self.angulo < 0:
            return _FIGURA_5_5_3
        return _FIGURA_5_5_2

    @cached_property
    def distancia_a(self) -> float:
        """La distancia "a" de la notación de las figuras.

        Es el 10 % de la menor dimensión horizontal o 0,4h, lo que sea menor,
        pero no menos del 4 % de la menor dimensión horizontal ni menos de
        1 m.

        Returns:
            El valor de la distancia "a".
        """
        return distancia_a(self.ancho, self.longitud, self.altura_media)

    @cached_property
    def entradas(self) -> tuple[EntradaCpnComponentes, ...]:
        """Los coeficientes de presión neta de cada componente y zona.

        Valida la relación h/L sólo cuando hay componentes cargados, para que
        el SPRFV siga siendo válido cuando la geometría queda fuera del
        alcance de las figuras.

        Returns:
            Una entrada por cada componente, zona y signo.

        Raises:
            ErrorLineamientos si h/L queda fuera del rango de 0,25 a 1,0.
        """
        if self.componentes is None:
            return ()
        self._validar_relacion_h_l()
        return tuple(
            EntradaCpnComponentes(
                componente=nombre,
                zona_componente=zona,
                tipo_presion=tipo_presion,
                valor=float(valor),
                referencia=self.referencia,
                distancia_a=self.distancia_a,
            )
            for nombre, area in self.componentes.items()
            for zona, tipo_presion, valor in self._valores(area)
        )

    def _validar_relacion_h_l(self) -> None:
        """Valida que h/L esté entre 0,25 y 1,0.

        L es la dimensión horizontal medida a lo largo de la dirección del
        viento de las figuras: el ancho de la cubierta.

        Raises:
            ErrorLineamientos si la relación queda fuera del rango.
        """
        relacion = self.altura_media / self.ancho
        if 0.25 <= relacion <= 1.0:
            return
        raise excepciones.ErrorLineamientos(
            f"La relación h/L = {relacion:.2f} está fuera del rango de 0,25 a 1,0"
            f" de la {self.referencia}."
        )

    def _valores(self, area: float) -> tuple[_ZonaValor, ...]:
        """Los coeficientes de cada zona y signo para un área efectiva.

        Args:
            area: El área efectiva de viento del componente, en m².

        Returns:
            Pares (zona, signo, valor), interpolados al ángulo de la cubierta.
        """
        fila = self._fila(self._indice_area(area))
        return tuple(
            (*clave, valor) for clave, valor in zip(_ZONAS_SIGNOS, fila, strict=True)
        )

    def _indice_area(self, area: float) -> int:
        """El índice de la columna del área efectiva de viento.

        Args:
            area: El área efectiva de viento del componente, en m².

        Returns:
            0 para áreas de hasta a², 1 hasta 4a² y 2 para áreas mayores.
        """
        a_cuadrado = self.distancia_a**2
        if area <= a_cuadrado:
            return 0
        if area <= 4.0 * a_cuadrado:
            return 1
        return 2

    def _fila(self, indice_area: int) -> tuple[float, ...]:
        """La fila de seis valores interpolada al ángulo de la cubierta.

        Args:
            indice_area: El índice de la columna del área efectiva.

        Returns:
            Los seis valores (Zona 3 positiva y negativa, Zona 2 positiva y
            negativa, Zona 1 positiva y negativa), interpolados al ángulo
            (nota 3 de las figuras).
        """
        filas = tuple(
            valores[indice_area] for valores in self._figura[self.con_bloqueo]
        )
        columnas = (
            float(np.interp(abs(self.angulo), ANGULOS_COMPONENTES, valores))
            for valores in zip(*filas, strict=True)
        )
        return tuple(columnas)

    @cached_property
    def distancias_zonas(
        self,
    ) -> dict[
        ZonaComponenteCubiertaAislada,
        tuple[tuple[float, float, float, float], ...],
    ]:
        """Los rectángulos de cada zona en planta, para la vista 3D.

        Para vertiente única, y para cubiertas a dos aguas con ángulo menor
        que 10º, la distribución es la de la Figura 5.5-1 sobre el rectángulo
        completo: Zona 3 anillo perimetral de ancho a, Zona 2 el anillo
        interior y Zona 1 el rectángulo central. Para dos aguas con ángulo
        de 10º o más la misma distribución se aplica a cada faldón, de modo
        que las Zonas 3 de ambos faldones se tocan en la cumbrera.

        Cada rectángulo es (x0, x1, z0, z1), con X a lo largo del ancho y Z
        a lo largo de la longitud, negativa (0 → -longitud), como los ejes
        de la vista 3D.

        En cubiertas muy chicas, donde los anillos no entran, "a" se limita
        para que las zonas no se solapen y los rectángulos degenerados se
        descartan.

        Returns:
            Un diccionario de zona a tupla de rectángulos.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA or abs(self.angulo) < 10:
            return self._anillos(
                min(self.distancia_a, min(self.ancho, self.longitud) / 4),
                0.0,
                self.ancho,
            )
        a = min(self.distancia_a, self.ancho / 8, self.longitud / 4)
        mitad = self.ancho / 2
        faldon_izquierdo = self._anillos(a, 0.0, mitad)
        faldon_derecho = self._anillos(a, mitad, self.ancho)
        return {
            zona: faldon_izquierdo[zona] + faldon_derecho[zona]
            for zona in faldon_izquierdo
        }

    def _anillos(
        self, a: float, x_inicial: float, x_final: float
    ) -> dict[
        ZonaComponenteCubiertaAislada, tuple[tuple[float, float, float, float], ...]
    ]:
        """Los rectángulos de las zonas como anillos concéntricos.

        La Figura 5.5-1 sobre un rectángulo: la Zona 3 es el anillo
        perimetral de ancho a, la Zona 2 el anillo interior de ancho a y
        la Zona 1 el rectángulo restante.

        Args:
            a: La distancia "a" ya limitada.
            x_inicial: La coordenada X del borde donde arranca el anillo.
            x_final: La coordenada X del borde opuesto.

        Returns:
            Un diccionario de zona a tupla de rectángulos (x0, x1, z0, z1).
        """
        x = (
            x_inicial,
            x_inicial + a,
            x_inicial + 2 * a,
            x_final - 2 * a,
            x_final - a,
            x_final,
        )
        z = (
            0.0,
            -a,
            -2 * a,
            -self.longitud + 2 * a,
            -self.longitud + a,
            -self.longitud,
        )
        return {
            ZonaComponenteCubiertaAislada.TRES: self._rectangulos(
                (x[0], x[1], z[0], z[5]),
                (x[4], x[5], z[0], z[5]),
                (x[1], x[4], z[0], z[1]),
                (x[1], x[4], z[4], z[5]),
            ),
            ZonaComponenteCubiertaAislada.DOS: self._rectangulos(
                (x[1], x[2], z[1], z[4]),
                (x[3], x[4], z[1], z[4]),
                (x[2], x[3], z[1], z[2]),
                (x[2], x[3], z[3], z[4]),
            ),
            ZonaComponenteCubiertaAislada.UNO: self._rectangulos(
                (x[2], x[3], z[2], z[3]),
            ),
        }

    @staticmethod
    def _rectangulos(
        *rectangulos: tuple[float, float, float, float],
    ) -> tuple[tuple[float, float, float, float], ...]:
        """Los rectángulos con área positiva, descartando los degenerados.

        Args:
            *rectangulos: Los rectángulos (x0, x1, z0, z1), con Z negativa.

        Returns:
            Los rectángulos válidos.
        """
        return tuple(
            rectangulo
            for rectangulo in rectangulos
            if rectangulo[1] - rectangulo[0] > 1e-9
            and rectangulo[2] - rectangulo[3] > 1e-9
        )
