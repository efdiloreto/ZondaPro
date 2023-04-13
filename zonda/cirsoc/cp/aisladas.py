from functools import cached_property
from typing import Tuple

import numpy as np

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.enums import (
    TipoPresionCubiertaAislada,
    ExtremoPresion,
    ZonaPresionCubiertaAislada,
    PosicionBloqueoCubierta,
    TipoCubierta,
)
from zonda.tipos import ValoresCpCubiertaAislada


class CubiertaAislada:
    """CubiertaAislada.

    Determinar los coeficientes de presión neta de cubiertas aisladas.
    """

    def __init__(
        self,
        tipo_cubierta: TipoCubierta,
        angulo: float,
        relacion_bloqueo: float,
        posicion_bloqueo: PosicionBloqueoCubierta,
    ) -> None:
        """

        Args:
            tipo_cubierta: El tipo de cubierta.
            angulo: El ángulo de la cubierta.
            relacion_bloqueo: La relación de bloqueo de la cubierta.
            posicion_bloqueo: Las posicion de bloqueo de la cubierta. Solo es usada cuando la cubierta es a un agua.

        Raises:
            ErrorLineamientos si el -5° < angulo < 5°.
            ValueError si la relación de bloque no está entre 0 y 1.
        """
        if not 0 <= relacion_bloqueo <= 1:
            raise ValueError("La relación de bloqueo debe ser un valor entre 0 y 1")
        if tipo_cubierta not in (TipoCubierta.DOS_AGUAS, TipoCubierta.UN_AGUA):
            raise excepciones.ErrorLineamientos(
                "El Reglamento solo provee lineamientos para calcular los coeficientes de presión neta para cubiertas"
                " a dos aguas y a un agua."
            )
        if -5 < angulo < 5 and tipo_cubierta == TipoCubierta.DOS_AGUAS:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas aisladas"
                f" a dos aguas con ángulo igual a {angulo:.2f}°."
            )
        if not 0 <= angulo <= 30 and tipo_cubierta == TipoCubierta.UN_AGUA:
            raise excepciones.ErrorLineamientos(
                "El Reglamento no provee lineamientos para calcular los coeficientes de presión neta para cubiertas aisladas"
                f" a un agua con ángulo igual a {angulo}°."
            )

        self.tipo_cubierta = tipo_cubierta
        self.angulo = angulo
        self.relacion_bloqueo = relacion_bloqueo
        self.posicion_bloqueo = posicion_bloqueo

    @cached_property
    def referencia(self) -> str:
        """Obtiene la referencia de la tabla del reglamento.

        Returns:
            La referencia de la tabla del reglamento desde donde se calculan los valores.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return "Tabla I.1"
        return "Tabla I.2"

    @cached_property
    def valores(
        self,
    ) -> ValoresCpCubiertaAislada:
        """Calcula los factores cpn para la cubierta.

        Returns:
            Los factores cpn.
        """
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return self._cpn_un_agua()
        return self._cpn_dos_aguas()

    def _cpn_dos_aguas(
        self,
    ) -> ValoresCpCubiertaAislada:
        """Calcula los factores cpn para una cubierta a dos aguas.

        Returns:
            Los valores de cpn de la cubierta.
        """
        angulos = (-20, -15, -10, -5, 5, 10, 15, 20, 25, 30)
        maximos_valores_globales = (0.7, 0.5, 0.4, 0.3, 0.3, 0.4, 0.4, 0.6, 0.7, 0.9)
        maximos_valores_zona_a = (0.8, 0.6, 0.6, 0.5, 0.6, 0.7, 0.9, 1.1, 1.2, 1.3)
        maximos_valores_zona_b = (1.6, 1.5, 1.4, 1.5, 1.8, 1.8, 1.9, 1.9, 1.9, 1.9)
        maximos_valores_zona_c = (0.6, 0.7, 0.8, 0.8, 1.3, 1.4, 1.4, 1.5, 1.6, 1.6)
        maximos_valores_zona_d = (1.7, 1.4, 1.1, 0.8, 0.4, 0.4, 0.4, 0.4, 0.5, 0.7)
        minimos_valores_globales = (
            (-0.7, -1.5),
            (-0.6, -1.5),
            (-0.6, -1.4),
            (-0.5, -1.4),
            (-0.6, -1.2),
            (-0.7, -1.2),
            (-0.8, -1.2),
            (-0.9, -1.2),
            (-1.0, -1.2),
            (-1.0, -1.2),
        )
        minimos_valores_zona_a = (
            (-0.9, -1.5),
            (-0.8, -1.5),
            (-0.8, -1.4),
            (-0.5, -1.4),
            (-0.6, -1.2),
            (-0.7, -1.2),
            (-0.9, -1.2),
            (-1.2, -1.2),
            (-1.4, -1.2),
            (-1.4, -1.2),
        )
        minimos_valores_zona_b = (
            (-1.3, -2.4),
            (-1.3, -2.7),
            (-1.3, -2.5),
            (-1.3, -2.3),
            (-1.4, -2.0),
            (-1.5, -1.8),
            (-1.7, -1.6),
            (-1.8, -1.5),
            (-1.9, -1.4),
            (-1.9, -1.3),
        )
        minimos_valores_zona_c = (
            (-1.6, -2.4),
            (-1.6, -2.6),
            (-1.5, -2.5),
            (-1.6, -2.4),
            (-1.4, -1.8),
            (-1.4, -1.6),
            (-1.4, -1.3),
            (-1.4, -1.2),
            (-1.4, -1.1),
            (-1.4, -1.1),
        )
        minimos_valores_zona_d = (
            (-0.6, -1.2),
            (-0.6, -1.2),
            (-0.6, -1.2),
            (-0.6, -1.2),
            (-1.1, -1.5),
            (-1.4, -1.6),
            (-1.8, -1.7),
            (-2.0, -1.7),
            (-2.0, -1.6),
            (-2.0, -1.6),
        )
        valor_maximo_global: float = np.interp(
            self.angulo, angulos, maximos_valores_globales
        )
        valor_maximo_zona_a: float = np.interp(
            self.angulo, angulos, maximos_valores_zona_a
        )
        valor_maximo_zona_b: float = np.interp(
            self.angulo, angulos, maximos_valores_zona_b
        )
        valor_maximo_zona_c: float = np.interp(
            self.angulo, angulos, maximos_valores_zona_c
        )
        valor_maximo_zona_d: float = np.interp(
            self.angulo, angulos, maximos_valores_zona_d
        )

        bloqueos = [0, 1]

        minimos_valores_globales_relacion: Tuple = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_globales
        )
        minimos_valores_caso_a_relacion: Tuple = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_a
        )
        minimos_valores_caso_b_relacion: Tuple = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_b
        )
        minimos_valores_caso_c_relacion: Tuple = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_c
        )
        minimos_valores_caso_d_relacion: Tuple = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_d
        )
        # TODO Corregir esto, es repetitivo
        valor_minimo_global: float = np.interp(
            self.angulo, angulos, minimos_valores_globales_relacion
        )
        valor_minimo_zona_a: float = np.interp(
            self.angulo, angulos, minimos_valores_caso_a_relacion
        )
        valor_minimo_zona_b: float = np.interp(
            self.angulo, angulos, minimos_valores_caso_b_relacion
        )
        valor_minimo_zona_c: float = np.interp(
            self.angulo, angulos, minimos_valores_caso_c_relacion
        )
        valor_minimo_zona_d: float = np.interp(
            self.angulo, angulos, minimos_valores_caso_d_relacion
        )

        return {
            TipoPresionCubiertaAislada.GLOBAL: {
                ExtremoPresion.MAX: valor_maximo_global,
                ExtremoPresion.MIN: valor_minimo_global,
            },
            TipoPresionCubiertaAislada.LOCAL: {
                ZonaPresionCubiertaAislada.A: {
                    ExtremoPresion.MAX: valor_maximo_zona_a,
                    ExtremoPresion.MIN: valor_minimo_zona_a,
                },
                ZonaPresionCubiertaAislada.B: {
                    ExtremoPresion.MAX: valor_maximo_zona_b,
                    ExtremoPresion.MIN: valor_minimo_zona_b,
                },
                ZonaPresionCubiertaAislada.C: {
                    ExtremoPresion.MAX: valor_maximo_zona_c,
                    ExtremoPresion.MIN: valor_minimo_zona_c,
                },
                ZonaPresionCubiertaAislada.D: {
                    ExtremoPresion.MAX: valor_maximo_zona_d,
                    ExtremoPresion.MIN: valor_minimo_zona_d,
                },
                ZonaPresionCubiertaAislada.BC: {
                    ExtremoPresion.MAX: max(valor_maximo_zona_b, valor_maximo_zona_c),
                    ExtremoPresion.MIN: min(valor_minimo_zona_b, valor_minimo_zona_c),
                },
                ZonaPresionCubiertaAislada.BD: {
                    ExtremoPresion.MAX: max(valor_maximo_zona_b, valor_maximo_zona_d),
                    ExtremoPresion.MIN: min(valor_minimo_zona_b, valor_minimo_zona_d),
                },
            },
        }

    def _cpn_un_agua(
        self,
    ) -> ValoresCpCubiertaAislada:
        """Calcula los factores cpn para una cubierta a un agua.

        Returns:
            Los valores de cpn de la cubierta.
        """
        angulos = (0, 5, 10, 15, 20, 25, 30)
        maximos_valores_globales = (0.2, 0.4, 0.5, 0.7, 0.8, 1, 1.2)
        maximos_valores_zona_a = (0.5, 0.8, 1.2, 1.4, 1.7, 2, 2.2)
        maximos_valores_zona_b = (1.8, 2.1, 2.4, 2.7, 2.9, 3.1, 3.2)
        maximos_valores_zona_c = (1.1, 1.3, 1.6, 1.8, 2.1, 2.3, 2.4)
        minimos_valores_globales = {
            PosicionBloqueoCubierta.ALERO_BAJO: (
                (-0.5, -1.2),
                (-0.7, -1.4),
                (-0.9, -1.4),
                (-1.1, -1.5),
                (-1.3, -1.5),
                (-1.6, -1.4),
                (-1.8, -1.4),
            ),
            PosicionBloqueoCubierta.ALERO_ALTO: (
                (-0.5, -1.2),
                (-0.7, -1.2),
                (-0.9, -1.1),
                (-1.1, -1),
                (-1.3, -0.9),
                (-1.6, -0.8),
                (-1.8, -0.8),
            ),
        }
        minimos_valores_zona_a = {
            PosicionBloqueoCubierta.ALERO_BAJO: (
                (-0.6, -1.3),
                (-1.1, -1.4),
                (-1.5, -1.4),
                (-1.8, -1.5),
                (-2.2, -1.5),
                (-2.6, -1.4),
                (-3.0, -1.4),
            ),
            PosicionBloqueoCubierta.ALERO_ALTO: (
                (-0.6, -1.3),
                (-1.1, -1.2),
                (-1.5, -1.1),
                (-1.8, -1),
                (-2.2, -0.9),
                (-2.6, -0.8),
                (-3.0, -0.8),
            ),
        }
        minimos_valores_zona_b = (
            (-1.3, -1.8),
            (-1.7, -2.6),
            (-2.0, -2.6),
            (-2.4, -2.9),
            (-2.8, -2.9),
            (-3.2, -2.5),
            (-3.8, -2.0),
        )
        minimos_valores_zona_c = {
            PosicionBloqueoCubierta.ALERO_BAJO: (
                (-1.4, -2.2),
                (-1.8, -2.6),
                (-2.1, -2.7),
                (-2.5, -2.8),
                (-2.9, -2.7),
                (-3.2, -2.5),
                (-3.6, -2.3),
            ),
            PosicionBloqueoCubierta.ALERO_ALTO: (
                (-1.4, -2.2),
                (-1.8, -2.1),
                (-2.1, -1.8),
                (-2.5, -1.6),
                (-2.9, -1.5),
                (-3.2, -1.4),
                (-3.6, -1.2),
            ),
        }
        # TODO corregir, es repetitivo
        valor_maximo_global = np.interp(self.angulo, angulos, maximos_valores_globales)
        valor_maximo_zona_a = np.interp(self.angulo, angulos, maximos_valores_zona_a)
        valor_maximo_zona_b = np.interp(self.angulo, angulos, maximos_valores_zona_b)
        valor_maximo_zona_c = np.interp(self.angulo, angulos, maximos_valores_zona_c)

        bloqueos = [0, 1]

        minimos_valores_globales_relacion = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_globales[self.posicion_bloqueo]
        )
        minimos_valores_caso_a_relacion = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_a[self.posicion_bloqueo]
        )
        minimos_valores_caso_b_relacion = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_b
        )
        minimos_valores_caso_c_relacion = tuple(
            np.interp(self.relacion_bloqueo, bloqueos, valores)
            for valores in minimos_valores_zona_c[self.posicion_bloqueo]
        )
        # TODO Corregir, es repetitivo
        valor_minimo_global = np.interp(
            self.angulo, angulos, minimos_valores_globales_relacion
        )
        valor_minimo_zona_a = np.interp(
            self.angulo, angulos, minimos_valores_caso_a_relacion
        )
        valor_minimo_zona_b = np.interp(
            self.angulo, angulos, minimos_valores_caso_b_relacion
        )
        valor_minimo_zona_c = np.interp(
            self.angulo, angulos, minimos_valores_caso_c_relacion
        )
        return {
            TipoPresionCubiertaAislada.GLOBAL: {
                ExtremoPresion.MAX: valor_maximo_global,
                ExtremoPresion.MIN: valor_minimo_global,
            },
            TipoPresionCubiertaAislada.LOCAL: {
                ZonaPresionCubiertaAislada.A: {
                    ExtremoPresion.MAX: valor_maximo_zona_a,
                    ExtremoPresion.MIN: valor_minimo_zona_a,
                },
                ZonaPresionCubiertaAislada.B: {
                    ExtremoPresion.MAX: valor_maximo_zona_b,
                    ExtremoPresion.MIN: valor_minimo_zona_b,
                },
                ZonaPresionCubiertaAislada.C: {
                    ExtremoPresion.MAX: valor_maximo_zona_c,
                    ExtremoPresion.MIN: valor_minimo_zona_c,
                },
                ZonaPresionCubiertaAislada.BC: {
                    ExtremoPresion.MAX: max(valor_maximo_zona_b, valor_maximo_zona_c),
                    ExtremoPresion.MIN: min(valor_minimo_zona_b, valor_minimo_zona_c),
                },
            },
        }

    @classmethod
    def desde_cubierta(cls, cubierta: geometria.Cubierta):
        """Crea una instancia desde la geometria de una cubierta.

        Args:
            cubierta: La geometria de una cubierta.
        """
        return cls(
            cubierta.tipo_cubierta,
            cubierta.angulo,
            cubierta.relacion_bloqueo,
            cubierta.posicion_bloqueo,
        )

    def __call__(
        self,
    ) -> ValoresCpCubiertaAislada:
        return self.valores
