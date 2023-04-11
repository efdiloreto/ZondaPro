from __future__ import annotations

from typing import TYPE_CHECKING

from sse102.enums import Estructura, PosicionCamara
from sse102.graficos.directores import edificio, aisladas, cartel

if TYPE_CHECKING:
    from vtkmodules import all as vtk


class Geometria:
    """Geometria.

    Representa las escenas para las geometrias de diferentes tipos de estructuras."""

    def __init__(
        self,
        interactor: vtk.vtkRenderWindowInteractor,
        renderer: vtk.vtkRenderer,
        camara: vtk.vtkCamera,
        estructura: Estructura,
    ) -> None:
        """

        Args:
            interactor: El interactor de la ventana de visualización.
            renderer: El renderer utilizado para renderizar los actores en la escena.
            camara: La camara virtual para el renderizado 3D.
            estructura: La estructura a representar.
        """
        self.interactor = interactor
        self.renderer = renderer
        self.camara = camara
        self.director = None
        self._parametros_camara = None
        dict_directores = {
            Estructura.EDIFICIO: edificio.Geometria,
            Estructura.CUBIERTA_AISLADA: aisladas.Geometria,
            Estructura.CARTEL: cartel.Geometria,
        }
        self._clase_director = dict_directores[estructura]

    def generar(self, *args, **kwargs) -> None:
        if self.director is not None:
            self._parametros_camara = {
                "punto_focal": self.camara.GetFocalPoint(),
                "posicion": self.camara.GetPosition(),
                "vector_altura": self.camara.GetViewUp(),
            }
        posicion_camara = kwargs.pop("posicion_camara", None) or PosicionCamara.PERSPECTIVA
        self.director = self._clase_director(self.renderer, *args, **kwargs)
        self.director.inicializar_actores()
        if self._parametros_camara is not None:
            self.camara.SetFocalPoint(self._parametros_camara["punto_focal"])
            self.camara.SetPosition(self._parametros_camara["posicion"])
            self.camara.SetViewUp(self._parametros_camara["vector_altura"])
            self.renderer.ResetCamera()
        else:
            self.director.setear_posicion_camara(self.camara, posicion_camara)
        self.interactor.ReInitialize()
