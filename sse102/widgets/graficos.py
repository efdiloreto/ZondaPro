"""Contiene clases que representan los widgets gráficos para las visualizaciones y resultados de presiones de viento
sobre las estructuras.
"""

from PyQt5 import QtCore, QtWidgets, QtGui
from vtkmodules import all as vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from sse102.cirsoc import Edificio, CubiertaAislada, Cartel
from sse102.enums import Estructura
from sse102.enums import PosicionCamara, SistemaResistente, Unidad
from sse102.graficos.actores import color_3d
from sse102.graficos.escenas import (
    geometrias,
    edificio as escena_edificio,
    aisladas as escena_aisladas,
    cartel as escena_cartel,
)


class WidgetGraficoBase(QtWidgets.QWidget):
    """WidgetGraficoBase.

    Representa la vista gráfica base 3D de resultados. Esta compuesto por una barra de comandos que contiene distintas acciones
    para interactuar con el gráfico (Por ejemplo, zoom-in, zoom-out, etc).
    """

    def __init__(self) -> None:
        super().__init__()

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setOrientation(QtCore.Qt.Vertical)
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self._toolbar.setIconSize(QtCore.QSize(24, 24))
        self._toolbar.setProperty("class", "graficos")
        # self._toolbar.setStyleSheet("QToolBar {background}")
        # self._toolbar.setFrameShape(QtWidgets.QFrame.Panel)
        # self._toolbar.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self._toolbar.setStyleSheet("QToolBar{border:1px solid;}")

        accion_vista_perspectiva = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/restablecer-vista.png"), "Restablecer Vista", self
        )
        accion_vista_perspectiva.triggered.connect(self._vista_perspectiva)
        self._toolbar.addAction(accion_vista_perspectiva)

        accion_vista_frente = QtWidgets.QAction(QtGui.QIcon(":/iconos/vista-frente.png"), "Vista Frente", self)
        accion_vista_frente.triggered.connect(self._vista_frente)
        self._toolbar.addAction(accion_vista_frente)

        accion_vista_contrafrente = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/vista-contrafrente.png"), "Vista Contrafrente", self
        )
        accion_vista_contrafrente.triggered.connect(self._vista_contrafrente)
        self._toolbar.addAction(accion_vista_contrafrente)

        accion_vista_lateral_derecha = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/vista-derecha.png"), "Vista Lateral Derecha", self
        )
        accion_vista_lateral_derecha.triggered.connect(self._vista_lateral_derecha)
        self._toolbar.addAction(accion_vista_lateral_derecha)

        accion_vista_lateral_izquierda = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/vista-izquierda.png"), "Vista Lateral Izquierda", self
        )
        accion_vista_lateral_izquierda.triggered.connect(self._vista_lateral_izquierda)
        self._toolbar.addAction(accion_vista_lateral_izquierda)

        accion_vista_superior = QtWidgets.QAction(QtGui.QIcon(":/iconos/vista-superior.png"), "Vista Superior", self)
        accion_vista_superior.triggered.connect(self._vista_superior)
        self._toolbar.addAction(accion_vista_superior)

        accion_camara_ortogonal = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/perspectiva-conica.png"), "Perspectiva Cónica", self
        )
        accion_camara_ortogonal.setCheckable(True)
        accion_camara_ortogonal.triggered.connect(self._setear_vista_ortogonal)
        accion_camara_ortogonal.setChecked(True)
        self._toolbar.addAction(accion_camara_ortogonal)

        accion_acercar = QtWidgets.QAction(QtGui.QIcon(":/iconos/acercar.png"), "Acercar", self)
        accion_acercar.triggered.connect(self._zoom_acercar)
        self._toolbar.addAction(accion_acercar)

        accion_alejar = QtWidgets.QAction(QtGui.QIcon(":/iconos/alejar.png"), "Alejar", self)
        accion_alejar.triggered.connect(self._zoom_alejar)
        self._toolbar.addAction(accion_alejar)

        self._qvtk_window_interactor = QVTKRenderWindowInteractor()

        frame = QtWidgets.QFrame()
        frame.setProperty("class", "recuadro")

        layout_frame = QtWidgets.QVBoxLayout()
        layout_frame.addWidget(self._qvtk_window_interactor)
        layout_frame.setContentsMargins(0, 0, 0, 0)

        frame.setLayout(layout_frame)

        self._renderer = vtk.vtkRenderer()

        rgb = 237 / 255

        self._renderer.SetBackground(rgb, rgb, rgb)

        self._camara = self._renderer.GetActiveCamera()

        self._interactor = self._qvtk_window_interactor.GetRenderWindow().GetInteractor()

        estilo_interactor = vtk.vtkInteractorStyleTrackballCamera()
        self._interactor.SetInteractorStyle(estilo_interactor)

        self._qvtk_window_interactor.GetRenderWindow().AddRenderer(self._renderer)

        accion_captura_imagen = QtWidgets.QAction(QtGui.QIcon(":/iconos/screenshot.png"), "Capturar Imagen", self)
        accion_captura_imagen.triggered.connect(self._capturar_imagen)
        self._toolbar.addAction(accion_captura_imagen)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(frame, 1)
        layout_principal.addWidget(self._toolbar)
        layout_principal.setContentsMargins(5, 0, 0, 0)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setLayout(layout_principal)

    def _capturar_imagen(self):
        filtro_ventana_imagen = vtk.vtkWindowToImageFilter()
        filtro_ventana_imagen.SetInput(self._qvtk_window_interactor.GetRenderWindow())
        filtro_ventana_imagen.SetScale(1)
        filtro_ventana_imagen.SetInputBufferTypeToRGB()
        filtro_ventana_imagen.Update()

        nombre, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar Imagen", "Captura.png", filter="PNG (*.png)")
        if nombre:
            writer = vtk.vtkPNGWriter()
            writer.SetFileName(nombre)
            writer.SetInputConnection(filtro_ventana_imagen.GetOutputPort())
            writer.Write()

    def _medir_distancia(self, estado):
        self._widget_distancia.SetEnabled(estado)

    def _setear_vista_ortogonal(self, estado):
        self._camara.SetParallelProjection(not estado)
        self._interactor.ReInitialize()

    def _zoom_acercar(self) -> None:
        self._camara.Zoom(1.25)
        self._interactor.ReInitialize()

    def _zoom_alejar(self) -> None:
        self._camara.Zoom(0.8)
        self._interactor.ReInitialize()

    def _vista_perspectiva(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.PERSPECTIVA)
        self._interactor.ReInitialize()

    def _vista_lateral_izquierda(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.IZQUIERDA)
        self._interactor.ReInitialize()

    def _vista_lateral_derecha(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.DERECHA)
        self._interactor.ReInitialize()

    def _vista_frente(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.FRENTE)
        self._interactor.ReInitialize()

    def _vista_contrafrente(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.CONTRAFRENTE)
        self._interactor.ReInitialize()

    def _vista_superior(self) -> None:
        self.escena.director.setear_posicion_camara(self._camara, posicion=PosicionCamara.SUPERIOR)
        self._interactor.ReInitialize()

    def finalizar(self) -> None:
        self._renderer.RemoveAllViewProps()
        self._renderer.GetRenderWindow().Finalize()
        self._qvtk_window_interactor.Finalize()
        del self._renderer
        self._qvtk_window_interactor.TerminateApp()
        del self._qvtk_window_interactor


class WidgetGraficoGeometria(WidgetGraficoBase):
    def __init__(self, estructura: Estructura):
        self.estructura = estructura
        super().__init__()
        self.escena = geometrias.Geometria(self._interactor, self._renderer, self._camara, self.estructura)


class WidgetPresiones(WidgetGraficoBase):
    def __init__(self):
        super().__init__()
        self._crear_widget_distancia()

        accion_medir = QtWidgets.QAction(QtGui.QIcon(":/iconos/regla.png"), "Medir Distancia", self)
        accion_medir.setCheckable(True)
        accion_medir.triggered.connect(self._medir_distancia)
        self._toolbar.addAction(accion_medir)

        settings = QtCore.QSettings()
        settings.beginGroup("unidades")
        self._unidad_presion = settings.value("presion", "N")
        self._unidad_fuerza = settings.value("fuerza", "N")
        settings.endGroup()

    def _crear_comandos_presiones(self):

        accion_aumentar_escala_flecha = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/aumentar-flecha.png"), "Aumentar Escalas Flechas", self
        )
        accion_aumentar_escala_flecha.triggered.connect(self.escena.aumentar_escala_flechas)
        self._toolbar.addAction(accion_aumentar_escala_flecha)

        accion_disminuir_escala_flecha = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/disminuir-flecha.png"), "Disminuir Escalas Flechas", self
        )
        accion_disminuir_escala_flecha.triggered.connect(self.escena.disminuir_escala_flechas)
        self._toolbar.addAction(accion_disminuir_escala_flecha)

        accion_aumentar_tamanio_texto = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/aumentar-texto.png"), "Aumentar Tamaño Texto Presiones", self
        )
        accion_aumentar_tamanio_texto.triggered.connect(self.escena.aumentar_tamanio_label_presion)
        self._toolbar.addAction(accion_aumentar_tamanio_texto)

        accion_disminuir_tamanio_texto = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/disminuir-texto.png"), "Disminuir Tamaño Texto Presiones", self
        )
        accion_disminuir_tamanio_texto.triggered.connect(self.escena.disminuir_tamanio_label_presion)
        self._toolbar.addAction(accion_disminuir_tamanio_texto)

    def _crear_widget_distancia(self) -> None:
        self._widget_distancia = vtk.vtkDistanceWidget()
        self._widget_distancia.SetInteractor(self._interactor)
        self._handle = vtk.vtkPointHandleRepresentation3D()
        self._handle.GetProperty().SetColor(color_3d("magenta"))
        self._handle.GetProperty().SetLineWidth(2)
        self._representation = vtk.vtkDistanceRepresentation2D()
        self._representation.SetLabelFormat("%.2f m")
        self._representation.GetAxisProperty().SetLineWidth(2)
        self._representation.GetAxisProperty().SetColor(color_3d("magenta"))
        self._representation.GetAxis().UseFontSizeFromPropertyOn()
        propiedad_texto = vtk.vtkTextProperty()
        propiedad_texto.SetColor(color_3d("magenta"))
        propiedad_texto.SetFontSize(16)
        propiedad_texto.SetBold(True)
        self._representation.GetAxis().SetTitleTextProperty(propiedad_texto)
        self._representation.SetHandleRepresentation(self._handle)
        self._point_picker = vtk.vtkPointPicker()
        self._point_picker.SetUseCells(True)
        self._widget_distancia.AddObserver(vtk.vtkCommand.EndInteractionEvent, self._ubicar_puntos_distancia)
        self._widget_distancia.SetRepresentation(self._representation)
        self._interactor.SetPicker(self._point_picker)

    def _ubicar_puntos_distancia(self, widget, event):
        p1 = [0, 0, 0]
        p2 = [0, 0, 0]
        self._representation.GetPoint1DisplayPosition(p1)
        self._representation.GetPoint2DisplayPosition(p2)
        if self._point_picker.Pick(p1, self._renderer):
            pos1 = self._point_picker.GetPickPosition()
            self._representation.GetPoint1Representation().SetWorldPosition(pos1)
            self._representation.GetAxis().GetPoint1Coordinate().SetValue(pos1)
        if self._point_picker.Pick(p2, self._renderer):
            pos2 = self._point_picker.GetPickPosition()
            self._representation.GetPoint2Representation().SetWorldPosition(pos2)
            self._representation.GetAxis().GetPoint2Coordinate().SetValue(pos2)
        self._representation.BuildRepresentation()
        return


class WidgetGraficoEdificioPresiones(WidgetPresiones):
    """WidgetGraficoEdificioPresiones.

    Representa la vista gráfica base 3D de resultados para las presiones de viento sobre el SPRFV de un edificio utilizando
    el método direccional. Esta compuesto por una barra de comandos que contiene distintas acciones para interactuar con
    el gráfico (Por ejemplo, zoom-in, zoom-out, etc).
    """

    def __init__(self, edificio: Edificio, sistema_resistente: SistemaResistente) -> None:
        """

        Args:
            edificio: Una instancia de Edificio.
            sistema_resistente: El sistema resistente utilizado para calcular las presiones.
        """
        super().__init__()

        self.sistema_resistente = sistema_resistente
        escenas = {
            SistemaResistente.SPRFV: escena_edificio.PresionesSprfvMetodoDireccional,
            sistema_resistente.COMPONENTES: escena_edificio.PresionesComponentes,
        }

        self.escena = escenas[sistema_resistente](
            self._interactor, self._renderer, edificio, Unidad(self._unidad_presion)
        )
        self._crear_comandos_presiones()
        self._vista_perspectiva()


class WidgetGraficoCubiertaAisladaPresiones(WidgetPresiones):
    """WidgetGraficoCubiertaAisladaPresiones.

    Representa la vista gráfica base 3D de resultados para las presiones de viento sobre el SPRFV de un edificio utilizando
    el método direccional. Esta compuesto por una barra de comandos que contiene distintas acciones para interactuar con
    el gráfico (Por ejemplo, zoom-in, zoom-out, etc).
    """

    def __init__(self, cubierta_aislada: CubiertaAislada) -> None:
        """

        Args:
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__()

        self.escena = escena_aisladas.Presiones(
            self._interactor, self._renderer, cubierta_aislada, Unidad(self._unidad_presion)
        )

        self._crear_comandos_presiones()
        self._vista_perspectiva()


class WidgetGraficoCartelPresiones(WidgetPresiones):
    """WidgetGraficoCubiertaAisladaPresiones.

    Representa la vista gráfica base 3D de resultados para las presiones de viento sobre el SPRFV de un edificio utilizando
    el método direccional. Esta compuesto por una barra de comandos que contiene distintas acciones para interactuar con
    el gráfico (Por ejemplo, zoom-in, zoom-out, etc).
    """

    def __init__(self, cartel: Cartel) -> None:
        """

        Args:
            cartel: Una instancia de Cartel.
        """
        super().__init__()

        self.escena = escena_cartel.Presiones(
            self._interactor, self._renderer, cartel, Unidad(self._unidad_presion), Unidad(self._unidad_fuerza)
        )

        self._crear_comandos_presiones()
        self._vista_frente()
