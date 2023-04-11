from __future__ import annotations

from typing import TYPE_CHECKING

from vtkmodules import all as vtk

from sse102.graficos.actores import ActorBarraEscala, ActorTexto2D
from sse102.graficos.directores.utils_iter import min_max_valores, aplicar_func_recursivamente
from sse102.graficos.escenas.base import PresionesMixin
from sse102.graficos.escenas.edificio import obtener_actores_presion_en_renderer
from sse102.unidades import convertir_unidad
from sse102.graficos.directores import aisladas as director_aisladas
from sse102.enums import ExtremoPresion, TipoPresionCubiertaAislada

if TYPE_CHECKING:
    from sse102.enums import Unidad
    from sse102.cirsoc import CubiertaAislada


class Presiones(PresionesMixin):
    """Presiones.

    Representa la escena de la visualización de presiones del viento sobre una cubierta aislada.
    """

    def __init__(
        self,
        interactor: vtk.vtkRenderWindowInteractor,
        renderer: vtk.vtkRenderer,
        cubierta_aislada: CubiertaAislada,
        unidad: Unidad,
    ) -> None:
        """

        Args:
            interactor: El interactor de la ventana de visualización.
            renderer: El renderer utilizado para renderizar los actores en la escena.
            cubierta_aislada: Una instancia de CubiertaAislada.
            unidad: La unidad en las que se muestran las presiones.
        """
        self.interactor = interactor
        self.renderer = renderer
        self.unidad = unidad

        self._presiones = cubierta_aislada.presiones()

        min_max_presiones = (convertir_unidad(p, self.unidad) for p in min_max_valores(presiones=self._presiones))

        tabla_colores = vtk.vtkLookupTable()
        tabla_colores.SetTableRange(*min_max_presiones)
        tabla_colores.SetHueRange(0.66, 0)
        tabla_colores.Build()

        self._barra_escala = ActorBarraEscala(self.renderer, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.renderer)

        self.director = director_aisladas.Presiones(self.renderer, tabla_colores, cubierta_aislada)

        self._extremo_presion_actual = ExtremoPresion.MAX

        self._actores_actuales = None
        self._presiones_actuales = None

        self._actores_presion = obtener_actores_presion_en_renderer(self.renderer)

    def actualizar_extremo_presion(self, extremo_presion: ExtremoPresion) -> None:
        """Actualiza el extremo de presión, a máximo o mínimo.

        Args:
            extremo_presion: El extremo de presión a actualizar.
        """
        self._extremo_presion_actual = extremo_presion
        self._actualizar_cubierta(regenerar_actores=False)
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_tipo_presion(self, tipo_presion: TipoPresionCubiertaAislada) -> None:
        """Actualiza el tipo de presión.

        Args:
            tipo_presion: El tipo de presión a actualizar.
        """
        self._presiones_actuales = self._presiones[tipo_presion]
        self.director.tipo_presion = tipo_presion
        self._actualizar_cubierta(regenerar_actores=True)
        self._actualizar_titulo()
        self.interactor.ReInitialize()

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
                self._actores_actuales.asignar_presion(presion=presion, unidad=self.unidad)

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""

        texto = (
            f"Presión {self.director.tipo_presion.value.capitalize()} {self._extremo_presion_actual.value.capitalize()}"
        )

        self._titulo.setear_texto(texto)
