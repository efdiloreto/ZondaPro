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

import numpy as np

from zonda.enums import Estructura, PosicionCamara
from zonda.graficos.directores import aisladas, cartel, edificio

if TYPE_CHECKING:
    from zonda.graficos.escena import Escena3D


class Geometria:
    """Geometria.

    Representa las escenas para las geometrias de diferentes tipos de estructuras."""

    def __init__(self, escena: Escena3D, estructura: Estructura) -> None:
        """

        Args:
            escena: La escena que junta los actores y los publica a la vista.
            estructura: La estructura a representar.
        """
        self.escena = escena
        self.camara = escena.camara
        # Los llena `generar()`; hasta la primera llamada no hay escena.
        self.director: (
            aisladas.Geometria | cartel.Geometria | edificio.Geometria | None
        ) = None
        self._parametros_camara: dict[str, np.ndarray] | None = None
        dict_directores = {
            Estructura.EDIFICIO: edificio.Geometria,
            Estructura.CUBIERTA_AISLADA: aisladas.Geometria,
            Estructura.CARTEL: cartel.Geometria,
        }
        self._clase_director = dict_directores[estructura]

    def generar(self, *args, **kwargs) -> None:
        if self.director is not None:
            self._parametros_camara = {
                "punto_focal": self.camara.punto_focal,
                "posicion": self.camara.posicion,
                "vector_altura": self.camara.vector_altura,
            }
        posicion_camara = (
            kwargs.pop("posicion_camara", None) or PosicionCamara.PERSPECTIVA
        )
        director = self._clase_director(self.escena, *args, **kwargs)
        director.inicializar_actores()
        self.director = director
        if self._parametros_camara is not None:
            self.camara.setear_punto_focal(*self._parametros_camara["punto_focal"])
            self.camara.setear_posicion(*self._parametros_camara["posicion"])
            self.camara.setear_vector_altura(*self._parametros_camara["vector_altura"])
            self.escena.encuadrar()
        else:
            director.setear_posicion_camara(self.camara, posicion_camara)
