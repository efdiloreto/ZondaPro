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

from typing import TYPE_CHECKING

from zonda.graficos.actores import ActorBarraEscala, ActorTexto2D
from zonda.graficos.colores import TablaColores
from zonda.graficos.directores import cartel as director_cartel
from zonda.graficos.escenas.base import PresionesMixin
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel
    from zonda.enums import Unidad
    from zonda.graficos.escena import Escena3D


class Presiones(PresionesMixin):
    """Presiones.

    Representa la escena de la visualización de presiones del viento sobre un cartel.
    """

    def __init__(
        self,
        escena: Escena3D,
        cartel: Cartel,
        unidad_presion: Unidad,
        unidad_fuerza: Unidad,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores y los publica a la vista.
            cartel: Una instancia de Cartel.
            unidad_presion: La unidad en las que se muestran las presiones.
            unidad_fuerza: La unidad en las que se muestran las fuerzas.
        """
        self.escena = escena
        self.unidad_presion = unidad_presion

        self._presion_por_altura = {
            fila.q.altura: fila.presion for fila in cartel.resultados
        }

        tabla_colores = TablaColores(
            *(
                convertir_unidad(presion, self.unidad_presion)
                for presion in cartel.resultados.min_max()
            )
        )

        self._barra_escala = ActorBarraEscala(
            self.escena, tabla_colores, self.unidad_presion
        )

        titulo = ActorTexto2D(self.escena)
        titulo.setear_texto(
            f"Fuerza Total = {convertir_unidad(cartel.presiones.fuerza_total, unidad_fuerza):.2f} {unidad_fuerza.value}"
        )

        self.director = director_cartel.Presiones(self.escena, tabla_colores, cartel)

        self._actor = self.director.obtener_actores()

        self._actores_presion = self.escena.actores_presion

    def actualizar_altura(self, altura) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la cara a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
        """

        presion = self._presion_por_altura[altura]
        self._actor.asignar_presion(
            presion, str_extra=f"({altura} m)", unidad=self.unidad_presion
        )
