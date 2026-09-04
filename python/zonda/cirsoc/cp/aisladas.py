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
"""

from functools import cached_property

import numpy as np

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.cirsoc.resultados import EntradaCpn
from zonda.enums import (
    CasoCargaCubiertaAislada,
    DireccionVientoCubiertaAislada,
    TipoCubierta,
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
