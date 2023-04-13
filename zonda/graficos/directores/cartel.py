from __future__ import annotations

from typing import TYPE_CHECKING

from vtkmodules import all as vtk

from zonda.enums import PosicionCamara
from zonda.graficos.actores import actores_poligonos, color_3d
from zonda.graficos.directores.utils_geometria import (
    coords_zona_cubierta,
    coords_pared_rectangular,
)

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel


class Geometria:
    """Geometria.
    Representa la geometria de un cartel. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        ancho: float,
        profundidad: float,
        altura_inferior: float,
        altura_superior: float,
    ) -> None:
        """
        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
            profundidad: La profundidad del cartel.
            ancho: El ancho del cartel.
            altura_inferior: La altura desde el suelo desde donde se consideran las presiones del viento sobre el cartel.
            altura_superior: La altura superior del cartel.
        """
        self.actores_cubierta = None

        self.renderer = renderer
        self.ancho = ancho
        # Se pasa a Negativo para que en VTK crezca hacia atras.
        self.profundidad = -profundidad
        self.altura_inferior = altura_inferior
        self.altura_superior = altura_superior

    @actores_poligonos(color="LightCoral", mostrar=True)
    def caras(self):
        """Genera los actores para todas las caras del cartel, excepto la cara que recibe la presión del viento.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        superior = coords_zona_cubierta(
            (0, self.altura_superior),
            (self.ancho, self.altura_superior),
            0,
            self.profundidad,
            dist_eucl=True,
        )
        inferior = coords_zona_cubierta(
            (0, self.altura_inferior),
            (self.ancho, self.altura_inferior),
            0,
            self.profundidad,
            dist_eucl=True,
        )
        lateral_izq = coords_pared_rectangular(
            self.profundidad,
            self.altura_superior,
            self.altura_superior,
            z0=0,
            elevacion=self.altura_inferior,
            sobre_eje_z=True,
        )
        lateral_der = coords_pared_rectangular(
            self.profundidad,
            self.altura_superior,
            self.altura_superior,
            z0=self.ancho,
            elevacion=self.altura_inferior,
            sobre_eje_z=True,
        )
        sotavento = coords_pared_rectangular(
            self.ancho,
            self.altura_superior,
            self.altura_superior,
            z0=self.profundidad,
            elevacion=self.altura_inferior,
            invertir_sentido=False,
        )

        return lateral_der, lateral_izq, superior, inferior, sotavento

    @actores_poligonos(color="LightCoral", mostrar=True)
    def cara_barlovento(self):
        """Genera el actor para la cara que recibe presion de viento.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_pared_rectangular(
            self.ancho,
            self.altura_superior,
            self.altura_superior,
            z0=0,
            elevacion=self.altura_inferior,
            invertir_sentido=True,
        )

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.renderer.RemoveAllViewProps()
        self.caras()
        self.cara_barlovento()
        self._crear_soportes()

    def setear_posicion_camara(
        self, camara: vtk.vtkCamera, posicion: PosicionCamara
    ) -> None:
        """Setea la posición de la camara.
        Args:
            camara: La camara a la que se le setea la vista.
            posicion: La posición a setear.
        """
        camara.SetFocalPoint(self.ancho / 2, 0, self.profundidad / 2)
        posiciones = {
            PosicionCamara.SUPERIOR: (
                self.ancho / 2,
                self.altura_superior,
                self.profundidad / 2,
            ),
            PosicionCamara.PERSPECTIVA: (self.ancho, self.altura_superior, 0),
            PosicionCamara.IZQUIERDA: (0, 0, self.profundidad / 2),
            PosicionCamara.DERECHA: (self.ancho, 0, self.profundidad / 2),
            PosicionCamara.FRENTE: (self.ancho / 2, 0, 0),
            PosicionCamara.CONTRAFRENTE: (self.ancho / 2, 0, self.profundidad),
        }
        camara.SetPosition(*posiciones[posicion])

        if posicion == PosicionCamara.SUPERIOR:
            vector_altura = (1, 0, 0)
        else:
            vector_altura = (0, 1, 0)
        camara.SetViewUp(*vector_altura)
        self.renderer.ResetCamera()

    def _crear_soportes(self):
        if self.altura_inferior > 0:
            radio = min(self.ancho, abs(self.profundidad)) / 4

            cylinder_source = vtk.vtkCylinderSource()
            cylinder_source.SetCenter(
                self.ancho / 2, self.altura_inferior / 2, self.profundidad / 2
            )
            cylinder_source.SetRadius(radio)
            cylinder_source.SetHeight(self.altura_inferior)
            cylinder_source.SetResolution(50)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(cylinder_source.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.renderer.AddActor(actor)


class Presiones(Geometria):
    """Presiones.

    Representa las presiones para un cartel. Inicializa los actores, setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        tabla_colores: vtk.vtkLookupTable,
        cartel: Cartel,
    ) -> None:
        """

        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
            tabla_colores: La tabla de escalas de colores de la escena general.
            cartel: Una instancia de Cartel.
        """
        super().__init__(
            renderer,
            cartel.ancho,
            cartel.profundidad,
            cartel.altura_inferior,
            cartel.altura_superior,
        )
        self.tabla_colores = tabla_colores

        self.inicializar_actores()

    def obtener_actores(self):
        # Se genera al inicializar la función cara_barlovento
        return self.actores_cara_barlovento

    @actores_poligonos(crear_atributo=False, presion=False, mostrar=True)
    def caras(self):
        return super().caras.__wrapped__(self)

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=True)
    def cara_barlovento(self):
        return super().cara_barlovento.__wrapped__(self)

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.caras()
        self.cara_barlovento()
        self._crear_soportes()
