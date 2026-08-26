# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

from __future__ import annotations

from typing import TYPE_CHECKING

from zonda.enums import ExtremoPresion, TipoPresionCubiertaAislada
from zonda.graficos.actores import ActorBarraEscala, ActorTexto2D
from zonda.graficos.colores import TablaColores
from zonda.graficos.directores import aisladas as director_aisladas
from zonda.graficos.directores.utils_iter import (
    min_max_valores,
)
from zonda.graficos.escenas.base import PresionesMixin
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.cirsoc import CubiertaAislada
    from zonda.enums import Unidad
    from zonda.graficos.escena import Escena3D


class Presiones(PresionesMixin):
    """Presiones.

    Representa la escena de la visualización de presiones del viento sobre una cubierta aislada.
    """

    def __init__(
        self,
        escena: Escena3D,
        cubierta_aislada: CubiertaAislada,
        unidad: Unidad,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores y los publica a la vista.
            cubierta_aislada: Una instancia de CubiertaAislada.
            unidad: La unidad en las que se muestran las presiones.
        """
        self.escena = escena
        self.unidad = unidad

        self._presiones = cubierta_aislada.presiones()

        min_max_presiones = (
            convertir_unidad(p, self.unidad)
            for p in min_max_valores(presiones=self._presiones)
        )

        tabla_colores = TablaColores(*min_max_presiones)

        self._barra_escala = ActorBarraEscala(self.escena, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.escena)

        self.director = director_aisladas.Presiones(
            self.escena, tabla_colores, cubierta_aislada
        )

        self._extremo_presion_actual = ExtremoPresion.MAX

        self._actores_actuales = None
        self._presiones_actuales = None

        self._actores_presion = self.escena.actores_presion

    def actualizar_extremo_presion(self, extremo_presion: ExtremoPresion) -> None:
        """Actualiza el extremo de presión, a máximo o mínimo.

        Args:
            extremo_presion: El extremo de presión a actualizar.
        """
        self._extremo_presion_actual = extremo_presion
        self._actualizar_cubierta(regenerar_actores=False)
        self._actualizar_titulo()

    def actualizar_tipo_presion(self, tipo_presion: TipoPresionCubiertaAislada) -> None:
        """Actualiza el tipo de presión.

        Args:
            tipo_presion: El tipo de presión a actualizar.
        """
        self._presiones_actuales = self._presiones[tipo_presion]
        self.director.tipo_presion = tipo_presion
        self._actualizar_cubierta(regenerar_actores=True)
        self._actualizar_titulo()

    def _actualizar_cubierta(self, regenerar_actores: bool) -> None:
        """Actualiza los actores y presiones para la cubierta.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if self._actores_actuales is None:
            self._actores_actuales = self.director.obtener_actores()
        if regenerar_actores:
            self.ocultar_actores_presion()
            self._actores_actuales = self.director.obtener_actores()

        if self.director.tipo_presion == TipoPresionCubiertaAislada.LOCAL:
            for zona, actores in self._actores_actuales.items():
                presion = self._presiones_actuales[zona][self._extremo_presion_actual]
                try:
                    for actor in actores:
                        actor.asignar_presion(presion=presion, unidad=self.unidad)
                except TypeError:
                    actores.asignar_presion(presion=presion, unidad=self.unidad)
        else:
            presion = self._presiones_actuales[self._extremo_presion_actual]
            try:
                for actor in self._actores_actuales:
                    actor.asignar_presion(presion=presion, unidad=self.unidad)
            except TypeError:
                self._actores_actuales.asignar_presion(
                    presion=presion, unidad=self.unidad
                )

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""

        texto = f"Presión {self.director.tipo_presion.value.capitalize()} {self._extremo_presion_actual.value.capitalize()}"

        self._titulo.setear_texto(texto)
