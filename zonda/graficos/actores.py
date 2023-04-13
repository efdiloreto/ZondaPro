"""Contiene clases que representan los actores comunes que pueden ser presentados en los diferentes tipos de escenas.
"""

from __future__ import annotations

from functools import cached_property, partial, wraps
from typing import Optional, Union, Tuple, Sequence, TYPE_CHECKING, Callable, Any

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util import numpy_support

from zonda.enums import Unidad
from zonda.graficos.directores.utils_iter import aplicar_func_recursivamente
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.tipos import Punto

colores = vtk.vtkNamedColors()


def color_3d(color: Optional[str] = None) -> vtk.vtkColor3d:
    """Obtiene un color 3D desde un string.

    Args:
        color: El color a obtener. Si es None se adopta "Gainsboro".

    Returns:
        El color 3D.
    """
    color = color or "Gainsboro"
    return colores.GetColor3d(color)


def crear_poly_data(puntos: Sequence[Punto]) -> vtk.vtkPolyData:
    vtk_puntos = vtk.vtkPoints()
    polygon = vtk.vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(len(puntos))
    for i, p in enumerate(puntos):
        vtk_puntos.InsertNextPoint(*p)
        polygon.GetPointIds().SetId(i, i)
    polygons = vtk.vtkCellArray()
    polygons.InsertNextCell(polygon)

    poly_data = vtk.vtkPolyData()
    poly_data.SetPoints(vtk_puntos)
    poly_data.SetPolys(polygons)

    return poly_data


def crear_mapper(
    data: Union[vtk.vtkPolyData, vtk.vtkPolyDataAlgorithm],
    scalar_visibility: bool = False,
) -> vtk.vtkPolyDataMapper:
    """

    Args:
        data: Polydata o un Source (Cono, flecha, etc)
        scalar_visibility: Define si se se usan los escalares para definir los colores.

    Returns:
        Un mapper.
    """
    mapper = vtk.vtkPolyDataMapper()
    try:
        mapper.SetInputConnection(data.GetOutputPort())
    except (TypeError, AttributeError):
        mapper.SetInputData(data)
    if not scalar_visibility:
        mapper.ScalarVisibilityOff()
    return mapper


def clip_poly_data(
    poly_data: vtk.vtkPolyData, origen: Punto, normal: Punto
) -> Union[None, vtk.vtkPolyData]:
    plano = vtk.vtkPlane()
    plano.SetOrigin(*origen)
    plano.SetNormal(*normal)

    clip = vtk.vtkClipPolyData()
    clip.SetClipFunction(plano)
    clip.SetInputData(poly_data)
    clip.Update()

    poly_data_clip = clip.GetOutput()

    if poly_data_clip.GetNumberOfPolys() == 0:
        return

    return poly_data_clip


def crear_actor(
    data: Union[vtk.vtkPolyData, vtk.vtkPolyDataAlgorithm],
    color: Optional[str] = None,
    scalar_visibility: bool = False,
) -> vtk.vtkActor:
    """Crea un actor VTK.

    Args:
        data: Polydata o un Source (Cono, flecha, etc)
        color: El color del actor.
        scalar_visibility: Define si se se usan los escalares para definir los colores.

    Returns:
        Un actor.
    """
    mapper = crear_mapper(data, scalar_visibility)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    if color is not None:
        actor.GetProperty().SetColor(color_3d(color))

    return actor


class ActorMixin:
    """ActorMixin.

    Agrega funcionalidad para añadir u ocultar actores en el renderer.
    """

    def __init__(self, renderer: vtk.vtkRenderer) -> None:
        self.renderer = renderer

    def _añadir(self) -> None:
        """Añade un actor al renderer."""
        self.renderer.AddActor(self)

    def mostrar(self) -> None:
        """Muestra un actor."""
        self.VisibilityOn()

    def ocultar(self) -> None:
        """Oculta un actor."""
        self.VisibilityOff()


class ActorTexto2D(vtk.vtkTextActor, ActorMixin):
    """ActorTexto2D.

    Genera un texto 2D usado para titulo o anotaciones del grafico en VTK.
    """

    def __init__(self, renderer: vtk.vtkRenderer) -> None:
        super().__init__(renderer)

        propiedad_texto = vtk.vtkTextProperty()
        propiedad_texto.SetColor(color_3d("Black"))
        propiedad_texto.SetFontSize(15)
        propiedad_texto.SetVerticalJustificationToTop()
        propiedad_texto.SetFontFamilyAsString("Arial")

        self.SetTextProperty(propiedad_texto)
        self.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.SetPosition(0.025, 0.975)

        self._añadir()

    def setear_texto(self, texto: str) -> None:
        """Setea el texto en el actor.

        Args:
            texto: El texto a setear..

        """
        self.SetInput(texto)


class ActorBarraEscala(vtk.vtkScalarBarActor, ActorMixin):
    """ActorBarraEscala.

    Genera una barra de escalas de colores.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        tabla_colores: vtk.vtkLookupTable,
        unidad: Unidad,
    ) -> None:
        """
        Args:
            renderer: El renderer que añade el actor.
            tabla_colores: Tabla utilizada para genera la barra.
            unidad: La unidad en la que se muestran los valores.
        """
        super().__init__(renderer)

        propiedad_texto = vtk.vtkTextProperty()
        propiedad_texto.SetColor(color_3d("Black"))
        propiedad_texto.SetFontSize(12)
        propiedad_texto.SetVerticalJustificationToCentered()

        self.SetLabelTextProperty(propiedad_texto)
        self.SetLookupTable(tabla_colores)
        self.SetNumberOfLabels(4)
        self.SetMaximumWidthInPixels(75)
        self.SetMaximumHeightInPixels(200)
        self.SetLabelFormat(f"%.2f {unidad.value}/m\u00B2")
        self.SetPosition(0.025, 0.025)
        self.SetAnnotationTextScaling(False)
        self.SetUnconstrainedFontSize(True)
        self.SetTextPad(2)

        self._añadir()


class ActorLabel(vtk.vtkBillboardTextActor3D, ActorMixin):
    """ActorLabel.

    Representa un recuadro con texto que siempre mira a la cámara.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        tamaño_texto: int = 12,
        borde: bool = True,
        centrado: bool = False,
    ) -> None:
        """
        Args:
            renderer: El renderer que añade u oculta al actor.
            tamaño_texto: El tamaño de texto.
            borde: Indica si el borde es visible.
            centrado: Indica si se debe centrar el texto vertical y horizontalmente.
        """

        super().__init__(renderer)

        self.tamaño_texto = tamaño_texto

        rgb = 237 / 255

        self._propiedad_texto = vtk.vtkTextProperty()
        self._propiedad_texto.SetColor(color_3d("Black"))
        self._propiedad_texto.SetFrameColor(color_3d("Black"))
        self._propiedad_texto.SetFontSize(tamaño_texto)
        self._propiedad_texto.SetVerticalJustificationToBottom()
        self._propiedad_texto.SetFrame(borde)
        self._propiedad_texto.SetBackgroundColor(rgb, rgb, rgb)
        self._propiedad_texto.SetBackgroundOpacity(1)
        self._propiedad_texto.UseTightBoundingBoxOff()
        if centrado:
            self._propiedad_texto.SetJustificationToCentered()
            self._propiedad_texto.SetVerticalJustificationToCentered()

        self.SetTextProperty(self._propiedad_texto)

        self._añadir()

    def setear_texto(self, texto: str) -> None:
        """Setea texto en el actor.

        Args:
            texto: El texto a setear.
        """
        self.SetInput(texto)

    def setear_posicion(self, posicion: Tuple[float, float, float]) -> None:
        """Setar la posición para el actor.

        Args:
            posicion: En el hint indica tuple, pero puede ser cualquier secuencia de tres floats.
        """
        self.SetPosition(*posicion)

    def aumentar_tamaño(self) -> None:
        """Aumenta el tamaño del texto."""
        self._cambiar_tamaño(1.1111)

    def disminuir_tamaño(self) -> None:
        """Disminuye el tamaño del texto."""
        self._cambiar_tamaño(0.9)

    def _cambiar_tamaño(self, factor: float) -> None:
        """Cambia el tamaño del texto de acuerdo al factor ingresado.

        Args:
            factor: El factor que modifica el tamaño.
        """
        tamaño = self._propiedad_texto.GetFontSize() * factor
        tamaño = max(tamaño, self.tamaño_texto)
        self._propiedad_texto.SetFontSize(int(tamaño))


class ActorFlechaPresion(vtk.vtkActor, ActorMixin):
    """ActorFlechaPresion.

    Actor representado por una flecha que se usa para indicar las presiones sobre las superficies.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        normal_centro: vtk.vtkCellCenters,
        max_valor_presion: float,
    ) -> None:
        """

        Args:
            renderer: El renderer utilizado para añadir u ocultar el actor.
            normal_centro: La norma en el centro de un poligono.
            max_valor_presion: El mayor valor de presión. Se utiliza para escalar el actor en base a este valor.
        """
        super().__init__(renderer)
        self.normals_centro = normal_centro
        self.max_valor_presion = max_valor_presion

        self._arrow_source = vtk.vtkArrowSource()
        self._arrow_source.SetTipResolution(30)
        self._arrow_source.SetShaftResolution(30)
        self._arrow_source.InvertOn()
        self._arrow_source.SetShaftRadius(0.03)
        self._arrow_source.SetTipRadius(0.1)
        self._arrow_source.SetTipLength(0.3)

        self._escala_base = 7

        self._mapper = crear_mapper(self._glyph3d)
        self.SetMapper(self._mapper)

        self.label = ActorLabel(renderer)
        self.SetPickable(False)

        self._añadir()

    def aumentar_escala(self) -> None:
        """Aumenta la escala de la flecha."""
        self._cambiar_escala_general(1.1111)

    def disminuir_escala(self) -> None:
        """Disminuye la escala de la flecha."""
        self._cambiar_escala_general(0.9)

    def _cambiar_escala_general(self, factor: float) -> None:
        """Cambia la escala base de acuerdo al factor ingresado. Además, modifica la escala actual de la flecha tambien
        con el factor ingresado.

        Args:
            factor: El factor que modifica la escala.
        """
        self._escala_base *= factor
        escala_actual = self._glyph3d.GetScaleFactor() * factor
        self._escalar_reubicar_label(escala_actual)

    @cached_property
    def _glyph3d(self) -> vtk.vtkGlyph3D:
        """Crea un glyph 3D que sirve para orientar el actor (la flecha) según la normal al polígono.

        Returns:
            Glyph3d
        """
        glyph3d = vtk.vtkGlyph3D()
        glyph3d.SetSourceConnection(self._arrow_source.GetOutputPort())
        glyph3d.SetVectorModeToUseNormal()
        glyph3d.SetInputConnection(self.normals_centro.GetOutputPort())
        glyph3d.OrientOn()
        glyph3d.Update()

        return glyph3d

    def asignar_presion(self, valor: float) -> None:
        """Asigna una presión al actor. Con este valor de presión se escala el actor (la flecha) y se orienta la dependiendo
        del signo de la presión (Positivo entra al poligono y negativo sale del poligono)

        Args:
            valor: El valor de presión.
        """
        self._escalar_reubicar_label(
            abs(valor) / self.max_valor_presion * self._escala_base
        )
        bool_invertir_flecha = valor >= 0
        self._arrow_source.SetInvert(bool_invertir_flecha)

    def mostrar(self) -> None:
        """Añade el actor (la flecha) y el label."""
        self.VisibilityOn()
        self.label.mostrar()

    def ocultar(self) -> None:
        """Ocualta el actor (la flecha) y el label."""
        self.VisibilityOff()
        self.label.ocultar()

    def reubicar_label(self) -> None:
        """Cambia la posición del label. Se detecta la escala de la flecha y en base a esta y su posición se obtiene
        el punto extremos de la misma que es donde se ubica el label.
        """
        escala = self._glyph3d.GetScaleFactor()
        np_normal = numpy_support.vtk_to_numpy(
            self.normals_centro.GetOutput().GetCellData().GetNormals()
        )
        posicion = np.array(self.GetCenter()) + escala / 2 * 1.05 * np_normal
        self.label.setear_posicion(posicion)

    def _escalar_reubicar_label(self, escala: float) -> None:
        """Escala el actor (la flecha) en base al valor ingresado y reubica el label.

        Args:
            escala: El valor de escala.
        """
        self._glyph3d.SetScaleFactor(escala)
        self._glyph3d.Update()
        self.reubicar_label()


class ActorPresion(vtk.vtkActor, ActorMixin):
    """ActorPresion.

    Visualizar las presiones. Se representada por un poligono que representa el area sobre la que actua el viento, por
    una flecha normal a este que representa su sentido, orientación y por un label que indica el valor de presión.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        puntos_poligono: Optional[Sequence[Punto]] = None,
        poly_data: Optional[vtk.vtkPolyData] = None,
        color: Optional[str] = None,
        tabla_colores: Optional[vtk.vtkLookupTable] = None,
        presion: bool = False,
        mostrar: bool = True,
    ) -> None:
        """

        Args:
            renderer: El renderer utilizado para añadir u ocultar el actor.
            puntos_poligono: Los puntos X, Y, Z que forman el poligono.
            poly_data: La polydata a usar si esta presente en lugar de los puntos.
            color: El color del poligono.
            tabla_colores: La tabla de escalas de colores de la escena general.
            presion: Indica si se debe mostrar la flecha y el label.
            mostrar: Indica si debe ser mostrado cuando se instancia.
        """
        super().__init__(renderer)
        self.puntos_poligono = puntos_poligono
        self._poly_data = poly_data
        self.color = color
        if tabla_colores is not None:
            self.tabla_colores = tabla_colores
            valor_min_presion, valor_max_presion = tabla_colores.GetTableRange()
            self._max_valor_presion = max(
                abs(valor_min_presion), abs(valor_max_presion)
            )

        self._mapper = crear_mapper(self.poly_data)
        self.SetMapper(self._mapper)
        self.GetProperty().EdgeVisibilityOn()
        self.GetProperty().SetLineWidth(2)
        self.GetProperty().SetColor(color_3d(self.color))

        if presion and tabla_colores is not None:
            self.flecha = ActorFlechaPresion(
                self.renderer,
                self._normals_centro,
                self._max_valor_presion,
            )

        self._añadir()

        if mostrar:
            self.mostrar()
        else:
            self.ocultar()

    def asignar_presion(
        self, presion: float, unidad: Unidad, str_extra: str = ""
    ) -> None:
        """Asigna un valor de presión al actor.

        Al hacerlo obtiene un color de la tabla en base al valor de presión y se lo asigna al poligono. Además escala
        la flecha, modifica su orientación en base al signo de la presión y asigna el texto correspondiente al label.

        Args:
            presion: El valor de presión.
            unidad: La unidad en que se encuentra la presión.
            str_extra: Un string a añadir al texto del label.
        """
        presion = convertir_unidad(presion, unidad)
        color_poligono = self._obtener_color(presion)
        self.GetProperty().SetColor(color_poligono)
        self.flecha.asignar_presion(presion)
        self.flecha.label.setear_texto(
            f"{presion:.2f} {unidad.value}/m\u00B2 {str_extra}"
        )
        self.mostrar()

    def mostrar(self) -> None:
        """Añade el actor y la flecha (si existe)."""
        if not self.GetVisibility():
            self.VisibilityOn()
            if hasattr(self, "flecha"):
                self.flecha.mostrar()

    def ocultar(self) -> None:
        """Oculta el actor y la flecha (si existe)."""
        if self.GetVisibility():
            self.VisibilityOff()
            if hasattr(self, "flecha"):
                self.flecha.ocultar()

    @cached_property
    def poly_data(self) -> vtk.vtkPolyData:
        """Crea la polydata del poligono.

        Returns:
            Polydata del poligono.
        """
        if self._poly_data is not None:
            return self._poly_data
        return crear_poly_data(self.puntos_poligono)

    @cached_property
    def _normals(self) -> vtk.vtkPolyDataNormals:
        """Obtiene las normales de la polydata.

        Returns:
            Normales de la polydata.
        """
        normals = vtk.vtkPolyDataNormals()

        normals.SetInputData(self._mapper.GetInput())
        normals.ComputePointNormalsOn()
        normals.ComputeCellNormalsOn()
        normals.SplittingOff()
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOff()
        normals.Update()

        return normals

    @cached_property
    def _normals_centro(self) -> vtk.vtkCellCenters:
        """Obtiene el centro de las normales.

        Returns:
            Centro de las normales.
        """
        centro = vtk.vtkCellCenters()
        centro.SetInputConnection(self._normals.GetOutputPort())
        centro.VertexCellsOn()
        centro.Update()
        return centro

    def _obtener_color(self, presion: float) -> list:
        """Obtiene un color de la tabla de colores en base al valor de presión ingresado.

        Args:
            presion: El valor de presión.

        Returns:
            El color obtenido.
        """
        dcolor = 3 * [0.0]
        self.tabla_colores.GetColor(presion, dcolor)
        return dcolor


def actores_poligonos(
    func: Optional[Callable] = None,
    *,
    crear_atributo: bool = False,
    color: Optional[str] = None,
    presion: bool = False,
    mostrar: bool = False,
) -> Any:
    """Crea un actor poligono VTK a partir de un método que retorna una secuencia de puntos que forman el poligono.

    Se debe usar como decorador de un método de clase.

    Args:
        func: La función o método decorado.
        crear_atributo: Indica si se debe crear un atributo en la clase que referencie a los actores generados. El nombre
            del atributo esta dado por "actores_" + el nombre del método.
        color: El color del actor poligono generado.
        presion: Indica si el poligono actua como poligono de presión, es decir si se le debe agregar una flecha y label.
        mostrar: Indica si debe ser mostrado al ser instanciado por el renderer.

    Notes:
        La clase que contiene al metodo debe tener creados los atributos "self._renderer" y "self._tabla_colores". Este
        último es necesario si el actor es de tipo presión.

    Returns:
        Actores generado en base los puntos retornado por el método decorado.
    """
    if func is None:
        return partial(
            actores_poligonos,
            crear_atributo=crear_atributo,
            color=color,
            presion=presion,
            mostrar=mostrar,
        )

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        puntos = func(self, *args, **kwargs)
        tabla_colores = getattr(self, "tabla_colores", None)
        actores = aplicar_func_recursivamente(
            puntos,
            lambda x: ActorPresion(
                self.renderer,
                x,
                color=color,
                tabla_colores=tabla_colores,
                presion=presion,
                mostrar=mostrar,
            ),
        )
        if crear_atributo:
            setattr(self, f"actores_{func.__name__}", actores)

    return wrapped
