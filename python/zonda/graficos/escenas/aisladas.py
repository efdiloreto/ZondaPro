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

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from zonda.enums import CasoCargaCubiertaAislada
from zonda.graficos.actores import ActorBarraEscala, ActorTexto2D
from zonda.graficos.colores import TablaColores
from zonda.graficos.directores import aisladas as director_aisladas
from zonda.graficos.escenas.base import PresionesMixin
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.cirsoc import CubiertaAislada
    from zonda.enums import (
        DireccionVientoCubiertaAislada,
        Unidad,
        ZonaPresionCubiertaAislada,
    )
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

        # La presión de cada actor se busca por su clave; no hay que recorrer
        # ninguna estructura para encontrarla.
        self._filas = cubierta_aislada.resultados.indexar("direccion", "zona", "caso")

        tabla_colores = TablaColores(
            *(
                convertir_unidad(presion, self.unidad)
                for presion in cubierta_aislada.resultados.min_max()
            )
        )

        self._barra_escala = ActorBarraEscala(self.escena, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.escena)

        self.director = director_aisladas.Presiones(
            self.escena, tabla_colores, cubierta_aislada
        )

        self._caso_actual = CasoCargaCubiertaAislada.CASO_A

        self._direccion_actual: DireccionVientoCubiertaAislada | None = None

        self._actores_actuales: dict[ZonaPresionCubiertaAislada, Any] | None = None

        self._actores_presion = self.escena.actores_presion

    def actualizar_caso(self, caso: CasoCargaCubiertaAislada) -> None:
        """Actualiza el caso de carga.

        Args:
            caso: El caso de carga a actualizar.
        """
        self._caso_actual = caso
        self._actualizar_presiones()
        self._actualizar_titulo()

    def actualizar_direccion(self, direccion: DireccionVientoCubiertaAislada) -> None:
        """Actualiza la dirección del viento.

        Cambiar de dirección no rearma geometría: la escena oculta el conjunto
        actual y le pide al director el subdiccionario de la dirección.

        Args:
            direccion: La dirección del viento a actualizar.
        """
        self._direccion_actual = direccion
        self.director.direccion = direccion
        self.ocultar_actores_presion()
        self._actores_actuales = self.director.obtener_actores()
        self._actualizar_presiones()
        self._actualizar_titulo()

    def _actualizar_presiones(self) -> None:
        """Asigna a cada actor la presión de su zona para el caso vigente."""
        direccion = self._direccion_actual
        if direccion is None or self._actores_actuales is None:
            return
        for zona, actores in self._actores_actuales.items():
            presion = self._presion(direccion, zona)
            try:
                for actor in actores:
                    actor.asignar_presion(presion=presion, unidad=self.unidad)
            except TypeError:
                actores.asignar_presion(presion=presion, unidad=self.unidad)

    def _presion(
        self,
        direccion: DireccionVientoCubiertaAislada,
        zona: ZonaPresionCubiertaAislada,
    ) -> float:
        """La presión de una zona para el caso actual.

        Args:
            direccion: La dirección del viento.
            zona: La zona de la cubierta para esa dirección.

        Returns:
            La presión correspondiente.
        """
        return self._filas[(direccion, zona, self._caso_actual)].unica().presion

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""
        if self._direccion_actual is None:
            return

        texto = f"Presión {self._direccion_actual.value} {self._caso_actual.value}"

        self._titulo.setear_texto(texto)
