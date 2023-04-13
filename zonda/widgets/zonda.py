import json
import webbrowser
from datetime import datetime
from typing import Dict, Union

from PyQt5 import QtWidgets, QtGui, QtCore, QtNetwork
from pkg_resources import parse_version

from zonda import __acercade__
from zonda.widgets.custom import (
    WidgetSinBorde,
    WidgetPanel,
    WidgetLogo,
    WidgetBotonModulo,
    WidgetLinksInfo,
)
from zonda.widgets.dialogos import DialogoConfiguracion
from zonda.widgets.modulos import (
    WidgetModuloEdificio,
    WidgetModuloCubiertaAislada,
    WidgetModuloCartel,
)


class WidgetAcercaDe(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        widget_logo = WidgetLogo()

        label_version = QtWidgets.QLabel(__acercade__.__version__)
        fuente_label_version = QtGui.QFont()
        fuente_label_version.setPixelSize(18)
        label_version.setFont(fuente_label_version)
        label_copyright = QtWidgets.QLabel(
            "Copyright © 2023 Eduardo Di Loreto. Todos los derechos reservados."
        )

        label_descripcion = QtWidgets.QLabel(
            "Cálculo de cargas de viento de acuerdo al Reglamento Argentino de Acción del Viento sobre las Construcciones CIRSOC 102-2005."
        )

        widget_links_info = WidgetLinksInfo(
            pagina_web=True, contacto=True
        )

        layout_logo = QtWidgets.QGridLayout()
        layout_logo.addWidget(widget_logo, 0, 0)
        layout_logo.addWidget(label_version, 0, 1, QtCore.Qt.AlignBottom)
        layout_logo.setColumnStretch(2, 1)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_logo)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(label_copyright)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(label_descripcion)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(widget_links_info)

        self.setLayout(layout_principal)

        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setWindowTitle("Acerca de")
        self.setLayout(layout_principal)
        self.setFixedSize(self.sizeHint())
        self.show()


class WidgetBienvenida(WidgetSinBorde):
    def __init__(self):
        """ """

        super().__init__()

        widget_logo = WidgetLogo()

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self._toolbar.setIconSize(QtCore.QSize(16, 16))

        accion_ayuda = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/ayuda.png"), "Ayuda", self
        )
        accion_ayuda.triggered.connect(lambda: webbrowser.open(__acercade__.__ayuda__))
        self._toolbar.addAction(accion_ayuda)

        accion_configuracion = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/configuracion.png"), "Configuración", self
        )
        accion_configuracion.triggered.connect(self._dialogo_configuracion)
        self._toolbar.addAction(accion_configuracion)

        accion_informacion = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/informacion.png"), "Acerca de", self
        )
        accion_informacion.triggered.connect(self._acerca_de)
        self._toolbar.addAction(accion_informacion)

        boton_edificio = WidgetBotonModulo(
            "Edificio", ":/iconos/edificio.png", self._modulo_edificio
        )

        boton_cubierta_aislada = WidgetBotonModulo(
            "Cubierta Aislada",
            ":/iconos/cubierta-aislada.png",
            self._modulo_cubierta_aislada,
        )

        boton_cartel = WidgetBotonModulo(
            "Cartel", ":/iconos/cartel.png", self._modulo_cartel
        )

        # boton_abrir_archivo = QtWidgets.QPushButton(" Abrir Archivo")
        # boton_abrir_archivo.setCursor(QtCore.Qt.PointingHandCursor)
        # boton_abrir_archivo.setIcon(QtGui.QIcon(":/iconos/carpeta.png"))
        # boton_abrir_archivo.setIconSize(QtCore.QSize(16, 16))
        # boton_abrir_archivo.setFlat(True)

        boton_salir = QtWidgets.QPushButton("Salir")
        boton_salir.setFixedWidth(75)
        boton_salir.setProperty("class", "salir")
        boton_salir.clicked.connect(self._salir)

        layout_encabezado = QtWidgets.QHBoxLayout()

        layout_encabezado.addWidget(widget_logo)
        layout_encabezado.addStretch()
        layout_encabezado.addWidget(self._toolbar)

        widget_encabezado = WidgetPanel()
        widget_encabezado.setLayout(layout_encabezado)

        layout_modulos = QtWidgets.QHBoxLayout()
        layout_modulos.setContentsMargins(25, 25, 25, 11)
        layout_modulos.setSpacing(60)
        layout_modulos.addWidget(boton_edificio)
        layout_modulos.addWidget(boton_cubierta_aislada)
        layout_modulos.addWidget(boton_cartel)

        layout_inferior = QtWidgets.QHBoxLayout()
        layout_inferior.setContentsMargins(25, 11, 25, 11)
        # layout_inferior.addWidget(boton_abrir_archivo)
        layout_inferior.addStretch()
        layout_inferior.addWidget(boton_salir)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(widget_encabezado)
        layout_principal.addLayout(layout_modulos)
        layout_principal.addLayout(layout_inferior)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout_principal)
        self.setWindowFlag(QtCore.Qt.Window)
        self.show()

    def _acerca_de(self):
        WidgetAcercaDe(self)

    def _dialogo_configuracion(self):
        DialogoConfiguracion(self)

    def _modulo_edificio(self):
        self._modulo = WidgetModuloEdificio(self)

    def _modulo_cubierta_aislada(self):
        self._modulo = WidgetModuloCubiertaAislada(self)

    def _modulo_cartel(self):
        self._modulo = WidgetModuloCartel(self)

    @staticmethod
    def _salir():
        QtWidgets.qApp.quit()
