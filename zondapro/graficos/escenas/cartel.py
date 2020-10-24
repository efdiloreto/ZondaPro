from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from vtkmodules import all as vtk

from zondapro.graficos.actores import ActorBarraEscala, ActorTexto2D
from zondapro.graficos.directores import cartel as director_cartel
from zondapro.graficos.escenas.base import PresionesMixin
from zondapro.graficos.escenas.edificio import obtener_actores_presion_en_renderer
from zondapro.unidades import convertir_unidad

if TYPE_CHECKING:
    from zondapro.enums import Unidad
    from zondapro.cirsoc import Cartel


class Presiones(PresionesMixin):
    """Presiones.

    Representa la escena de la visualización de presiones del viento sobre un cartel.
    """

    def __init__(
        self,
        interactor: vtk.vtkRenderWindowInteractor,
        renderer: vtk.vtkRenderer,
        cartel: Cartel,
        unidad_presion: Unidad,
        unidad_fuerza: Unidad,
    ) -> None:
        """

        Args:
            interactor: El interactor de la ventana de visualización.
            renderer: El renderer utilizado para renderizar los actores en la escena.
            cartel: Una instancia de Cartel.
            unidad_presion: La unidad en las que se muestran las presiones.
            unidad_fuerza: La unidad en las que se muestran las fuerzas.
        """
        self.interactor = interactor
        self.renderer = renderer
        self.unidad_presion = unidad_presion

        self._presiones = cartel.presiones()
        self._alturas = cartel.geometria.alturas

        tabla_colores = vtk.vtkLookupTable()
        tabla_colores.SetTableRange(
            (
                convertir_unidad(min(self._presiones), self.unidad_presion),
                convertir_unidad(max(self._presiones), self.unidad_presion),
            )
        )
        tabla_colores.SetHueRange(0.66, 0)
        tabla_colores.Build()

        self._barra_escala = ActorBarraEscala(self.renderer, tabla_colores, self.unidad_presion)

        titulo = ActorTexto2D(self.renderer)
        titulo.setear_texto(
            f"Fuerza Total = {convertir_unidad(cartel.presiones.fuerza_total, unidad_fuerza):.2f} {unidad_fuerza.value}"
        )

        self.director = director_cartel.Presiones(self.renderer, tabla_colores, cartel)

        self._actor = self.director.obtener_actores()

        self._actores_presion = obtener_actores_presion_en_renderer(self.renderer)

    def actualizar_altura(self, altura) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la cara a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
        """

        presion = self._presiones[np.where(self._alturas == altura)][0]
        self._actor.asignar_presion(presion, str_extra=f"({altura} m)", unidad=self.unidad_presion)
        self.interactor.ReInitialize()
