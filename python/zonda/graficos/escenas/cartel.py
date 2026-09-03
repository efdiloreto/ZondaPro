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

from zonda.enums import CasoCartel
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

    Representa la escena de la visualización de presiones del viento sobre un
    cartel, según el caso de la Figura 4.4-1 que se esté considerando.
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
        self.unidad_fuerza = unidad_fuerza

        self._filas_por_caso = dict(cartel.resultados.indexar("caso"))

        tabla_colores = TablaColores(
            *(
                convertir_unidad(presion, self.unidad_presion)
                for presion in cartel.resultados.min_max()
            )
        )

        self._barra_escala = ActorBarraEscala(
            self.escena, tabla_colores, self.unidad_presion
        )

        self._titulo = ActorTexto2D(self.escena)

        self.director = director_cartel.Presiones(self.escena, tabla_colores, cartel)

        # La cara a barlovento muestra los Casos A y B.
        self._actor = self.director.obtener_actores()

        self._actores_presion = self.escena.actores_presion

        self.actualizar_caso(CasoCartel.CASO_A)

    def actualizar_caso(self, caso: CasoCartel) -> None:
        """Muestra las presiones del caso pedido.

        Para los Casos A y B asigna la presión a la cara a barlovento; para el
        Caso C la reparte entre las regiones, una por actor.

        Args:
            caso: El caso de la Figura 4.4-1 a mostrar.
        """
        filas = self._filas_por_caso[caso]
        if caso is CasoCartel.CASO_C:
            self._actor.asignar_visible(False)
            presion_por_region = {fila.region: fila for fila in filas}
            for region, actor in self.director.obtener_regiones().items():
                fila = presion_por_region[region]
                actor.asignar_presion(
                    fila.presion,
                    str_extra=f" - región {region.etiqueta}",
                    unidad=self.unidad_presion,
                )
        else:
            self._ocultar_regiones()
            fila = filas.unica()
            extra = f" - {caso.value}"
            if caso is CasoCartel.CASO_B:
                extra += f" (e = {fila.excentricidad:.2f} m)"
            self._actor.asignar_presion(
                fila.presion, str_extra=extra, unidad=self.unidad_presion
            )

        fuerza = convertir_unidad(
            self.director.cartel.presiones.fuerzas_totales[caso], self.unidad_fuerza
        )
        self._titulo.setear_texto(
            f"Fuerza Total = {fuerza:.2f} {self.unidad_fuerza.value} ({caso.value})"
        )

    def _ocultar_regiones(self) -> None:
        """Oculta los actores de las regiones del Caso C."""
        for actor in self.director.obtener_regiones().values():
            actor.asignar_visible(False)
