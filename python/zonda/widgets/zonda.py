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

"""La pantalla de bienvenida: elegir el módulo con el que se va a trabajar.

Las opciones generales del programa —configuración, ayuda y acerca de— viven en
la barra de menús de cada módulo (``zonda.widgets.modulos``), no acá.

**La pantalla no se muestra sola.** Quien la crea decide si mostrarla: cuando el
programa arranca abriendo un archivo (`zonda.main`), el módulo que corresponde se
abre directo y la bienvenida queda escondida hasta que se cierre ese módulo.
"""

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, patrocinadores
from zonda.actualizaciones import Actualizacion, BuscadorActualizaciones
from zonda.enums import Estructura
from zonda.widgets.apoyo import DialogoApoyo, WidgetSeccionPatrocinadores
from zonda.widgets.custom import WidgetBotonModulo, WidgetLogo, WidgetPanel
from zonda.widgets.dialogos import DialogoActualizacion
from zonda.widgets.modulos import (
    WidgetModuloCartel,
    WidgetModuloCubiertaAislada,
    WidgetModuloEdificio,
)

MODULOS = {
    Estructura.EDIFICIO: WidgetModuloEdificio,
    Estructura.CUBIERTA_AISLADA: WidgetModuloCubiertaAislada,
    Estructura.CARTEL: WidgetModuloCartel,
}


class WidgetBienvenida(QtWidgets.QWidget):
    """La ventana desde la que se elige el módulo y se ve quién apoya Zonda.

    Es una ventana común del sistema, con su barra de título, sus botones de
    minimizar y cerrar y su posición recordada entre sesiones. Antes era una
    ventana sin borde que se arrastraba desde cualquier lado: se veía distinta
    de todo lo demás del escritorio y no ofrecía nada a cambio.
    """

    GRUPO_SETTINGS = "bienvenida"
    """El grupo de ``QSettings`` donde se recuerda la geometría."""

    def __init__(self, buscador: BuscadorActualizaciones | None = None):
        """
        Args:
            buscador: Quien averigua si hay una versión nueva publicada. Si no
                se pasa ninguno, no se avisa de actualizaciones.
        """

        super().__init__()

        # Los tres modulos derivan de WidgetModuloEdificio.
        self._modulo: WidgetModuloEdificio | None = None
        self._buscador = buscador
        self._ya_aviso = False
        # Se lee una sola vez: es un JSON chico al lado de los logos, y volver
        # a leerlo cada vez que se abre el dialogo rebarajaria el orden.
        self._patrocinadores = patrocinadores.cargar()

        widget_logo = WidgetLogo()

        boton_edificio = WidgetBotonModulo(
            "Edificio", "iconos/edificio.png", self._modulo_edificio
        )

        boton_cubierta_aislada = WidgetBotonModulo(
            "Cubierta Aislada",
            "iconos/cubierta-aislada.png",
            self._modulo_cubierta_aislada,
        )

        boton_cartel = WidgetBotonModulo(
            "Cartel", "iconos/cartel.png", self._modulo_cartel
        )

        boton_apoyo = QtWidgets.QPushButton("Apoyá el proyecto")
        boton_apoyo.setProperty("class", "apoyo")
        boton_apoyo.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton_apoyo.clicked.connect(self._mostrar_apoyo)

        seccion_patrocinadores = WidgetSeccionPatrocinadores(self._patrocinadores)
        seccion_patrocinadores.apoyo_solicitado.connect(self._mostrar_apoyo)

        boton_salir = QtWidgets.QPushButton("Salir")
        boton_salir.setFixedWidth(75)
        boton_salir.setProperty("class", "salir")
        boton_salir.clicked.connect(self._salir)

        layout_encabezado = QtWidgets.QHBoxLayout()

        layout_encabezado.addWidget(widget_logo)
        layout_encabezado.addStretch()

        widget_encabezado = WidgetPanel()
        widget_encabezado.setLayout(layout_encabezado)

        layout_modulos = QtWidgets.QHBoxLayout()
        layout_modulos.setContentsMargins(25, 25, 25, 11)
        layout_modulos.setSpacing(60)
        layout_modulos.addWidget(boton_edificio)
        layout_modulos.addWidget(boton_cubierta_aislada)
        layout_modulos.addWidget(boton_cartel)

        # Los dos botones viven dentro de la sección de patrocinadores: son
        # del mismo asunto, y agruparlos evita sumarle otra fila a la ventana.
        layout_seccion = seccion_patrocinadores.layout()
        assert layout_seccion is not None
        layout_seccion.addWidget(boton_apoyo)
        layout_seccion.addWidget(boton_salir)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(widget_encabezado)
        layout_principal.addLayout(layout_modulos)
        layout_principal.addStretch()
        layout_principal.addWidget(seccion_patrocinadores)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        self.setLayout(layout_principal)

        self.setWindowTitle(f"Zonda {__acercade__.__version__}")
        # El mínimo sale del tamaño que pide el contenido: por debajo de eso los
        # tres módulos no entran en una fila y el pie se empieza a recortar.
        self.setMinimumSize(self.sizeHint())
        self._restaurar_geometria()

    @property
    def modulo(self):
        """El módulo abierto, o ``None`` si no hay ninguno."""
        return self._modulo

    def abrir_modulo(self, estructura: Estructura):
        """Abre el módulo que corresponde a un tipo de estructura.

        Args:
            estructura: El tipo de estructura del módulo a abrir.

        Returns:
            El módulo abierto.
        """
        modulo = MODULOS[estructura](self)
        # Los módulos se destruyen al cerrarse (``WA_DeleteOnClose``): sin esto
        # la referencia quedaría apuntando a un objeto de Qt ya borrado, y
        # tocarla levantaría ``RuntimeError``.
        modulo.destroyed.connect(self._olvidar_modulo)
        self._modulo = modulo
        self._avisar_de_actualizacion()
        return modulo

    def _avisar_de_actualizacion(self) -> None:
        """Avisa, sobre el módulo recién abierto, si hay una versión nueva.

        Se avisa una sola vez por sesión: abrir y cerrar módulos no tiene por
        qué repetir el aviso. Si la consulta a GitHub todavía no volvió, el
        aviso queda enganchado a la señal y aparece cuando llegue.
        """
        if self._buscador is None or self._ya_aviso:
            return
        self._ya_aviso = True

        if self._buscador.actualizacion is not None:
            self._mostrar_aviso(self._buscador.actualizacion)
            return

        # El stub de PyQt6 no declara el parametro de tipo de conexion, pero
        # existe: sin SingleShotConnection el aviso se repetiria si la senal
        # volviera a emitirse.
        self._buscador.encontrada.connect(  # type: ignore[call-arg]
            self._mostrar_aviso,
            QtCore.Qt.ConnectionType.SingleShotConnection,
        )

    def _mostrar_aviso(self, actualizacion: Actualizacion) -> None:
        # El módulo pudo cerrarse mientras GitHub contestaba, y los módulos se
        # destruyen al cerrarse. La bienvenida, en cambio, vive toda la sesión.
        DialogoActualizacion(self._modulo or self, actualizacion)

    def _restaurar_geometria(self) -> None:
        """Vuelve a poner la ventana donde estaba la última vez.

        Si no hay nada guardado —primera corrida— o lo guardado no se puede
        aplicar —cambió la cantidad de monitores, por ejemplo—, Qt deja que el
        sistema la ubique, que es el comportamiento correcto.
        """
        settings = QtCore.QSettings()
        settings.beginGroup(self.GRUPO_SETTINGS)
        geometria = settings.value("geometria")
        settings.endGroup()

        if isinstance(geometria, QtCore.QByteArray):
            self.restoreGeometry(geometria)

    def _guardar_geometria(self) -> None:
        """Anota dónde quedó la ventana, para la próxima sesión."""
        settings = QtCore.QSettings()
        settings.beginGroup(self.GRUPO_SETTINGS)
        settings.setValue("geometria", self.saveGeometry())
        settings.endGroup()
        settings.sync()

    def closeEvent(self, a0: QtGui.QCloseEvent | None) -> None:
        self._guardar_geometria()
        super().closeEvent(a0)

    def _mostrar_apoyo(self) -> None:
        """Abre la pantalla de apoyo al proyecto."""
        DialogoApoyo(self, self._patrocinadores).show()

    def _olvidar_modulo(self) -> None:
        self._modulo = None

    def _modulo_edificio(self):
        self.abrir_modulo(Estructura.EDIFICIO)

    def _modulo_cubierta_aislada(self):
        self.abrir_modulo(Estructura.CUBIERTA_AISLADA)

    def _modulo_cartel(self):
        self.abrir_modulo(Estructura.CARTEL)

    @staticmethod
    def _salir():
        QtWidgets.QApplication.quit()
