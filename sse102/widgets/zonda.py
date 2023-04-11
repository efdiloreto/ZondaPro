import json
import webbrowser
from datetime import datetime
from typing import Dict, Union

from PyQt5 import QtWidgets, QtGui, QtCore, QtNetwork
from pkg_resources import parse_version

from sse102 import __acercade__
from sse102.widgets.custom import (
    WidgetSinBorde,
    WidgetPanel,
    WidgetLogo,
    WidgetBotonModulo,
    EfectoPulsacion,
    WidgetLinksInfo,
)
from sse102.widgets.dialogos import DialogoConfiguracion
from sse102.widgets.modulos import WidgetModuloEdificio, WidgetModuloCubiertaAislada, WidgetModuloCartel


class WidgetAcercaDe(QtWidgets.QWidget):
    def __init__(self, parent, info_licencia: Dict[str, Union[Dict[str, str], str]]):
        super().__init__(parent)

        widget_logo = WidgetLogo()

        label_version = QtWidgets.QLabel(__acercade__.__version__)
        fuente_label_version = QtGui.QFont()
        fuente_label_version.setPixelSize(18)
        label_version.setFont(fuente_label_version)
        label_copyright = QtWidgets.QLabel("Copyright © 2020 ZondaCS. Todos los derechos reservados.")

        label_descripcion = QtWidgets.QLabel(
            "Cálculo de cargas de viento de acuerdo al Reglamento Argentino de Acción del Viento sobre las Construcciones CIRSOC 102-2005."
        )

        widget_links_info = WidgetLinksInfo(pagina_web=True, contacto=True, eula=True, licencias_terceros=True)

        layout_logo = QtWidgets.QGridLayout()
        layout_logo.addWidget(widget_logo, 0, 0)
        layout_logo.addWidget(label_version, 0, 1, QtCore.Qt.AlignBottom)
        layout_logo.setColumnStretch(2, 1)

        usuario = info_licencia.pop("user")
        dispositivo = info_licencia.pop("dispositivo")
        licencia = info_licencia.pop("licencia")

        formato_fecha_salida = "%d-%m-%Y"

        fecha_inicio_licencia = datetime.strptime(licencia["licencia_start"], "%Y-%m-%d %H:%M:%S")
        fecha_expiracion_licencia = datetime.strptime(licencia["licencia_expire"], "%Y-%m-%d")

        layout_info_licencia = QtWidgets.QGridLayout()

        layout_info_licencia.addWidget(QtWidgets.QLabel("Usuario:"), 0, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(
            QtWidgets.QLabel(f"{usuario['user_firstname']} {usuario['user_lastname']}"), 0, 1
        )

        layout_info_licencia.addWidget(QtWidgets.QLabel("Tipo de licencia:"), 1, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(licencia["licencia_type"]), 1, 1)

        layout_info_licencia.addWidget(QtWidgets.QLabel("Fecha de inicio:"), 2, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(fecha_inicio_licencia.strftime(formato_fecha_salida)), 2, 1)

        layout_info_licencia.addWidget(QtWidgets.QLabel("Fecha de expiración:"), 3, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(fecha_expiracion_licencia.strftime(formato_fecha_salida)), 3, 1)

        layout_info_licencia.addWidget(QtWidgets.QLabel("Dispositivos permitidos:"), 4, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(licencia["dispositivos_registrado"]), 4, 1)

        layout_info_licencia.addWidget(QtWidgets.QLabel("Dispositivos registrados:"), 5, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(licencia["licencia_cant_dispositivos"]), 5, 1)

        layout_info_licencia.addWidget(QtWidgets.QLabel("ID dispositivo:"), 6, 0, QtCore.Qt.AlignRight)
        layout_info_licencia.addWidget(QtWidgets.QLabel(dispositivo["dispositivo_id"]), 6, 1)

        layout_info_licencia.setRowMinimumHeight(1, 5)
        layout_info_licencia.setColumnStretch(2, 1)

        group_box_licencia = QtWidgets.QGroupBox("Información de Licencia:")
        group_box_licencia.setLayout(layout_info_licencia)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_logo)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(label_copyright)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(label_descripcion)
        layout_principal.addSpacing(15)
        layout_principal.addWidget(group_box_licencia)
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
    def __init__(self, datos_licencia: Dict):
        """

        Args:
            datos_licencia: Los datos de la licencia del usuario
        """

        super().__init__()

        self.datos_licencia = datos_licencia

        widget_logo = WidgetLogo()

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self._toolbar.setIconSize(QtCore.QSize(16, 16))

        accion_ayuda = QtWidgets.QAction(QtGui.QIcon(":/iconos/ayuda.png"), "Ayuda", self)
        accion_ayuda.triggered.connect(lambda: webbrowser.open(__acercade__.__ayuda__))
        self._toolbar.addAction(accion_ayuda)

        accion_configuracion = QtWidgets.QAction(QtGui.QIcon(":/iconos/configuracion.png"), "Configuración", self)
        accion_configuracion.triggered.connect(self._dialogo_configuracion)
        self._toolbar.addAction(accion_configuracion)

        accion_informacion = QtWidgets.QAction(QtGui.QIcon(":/iconos/informacion.png"), "Acerca de", self)
        accion_informacion.triggered.connect(self._acerca_de)
        self._toolbar.addAction(accion_informacion)

        accion_cerrar_sesion = QtWidgets.QAction(
            QtGui.QIcon(":/iconos/cerrar-sesion.png"), "Cerrar Sesión y Salir", self
        )
        accion_cerrar_sesion.triggered.connect(self._cerrar_sesion_salir)
        self._toolbar.addAction(accion_cerrar_sesion)

        boton_edificio = WidgetBotonModulo("Edificio", ":/iconos/edificio.png", self._modulo_edificio)

        boton_cubierta_aislada = WidgetBotonModulo(
            "Cubierta Aislada", ":/iconos/cubierta-aislada.png", self._modulo_cubierta_aislada
        )

        boton_cartel = WidgetBotonModulo("Cartel", ":/iconos/cartel.png", self._modulo_cartel)

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
        self._request_nueva_version()

    def _acerca_de(self):
        WidgetAcercaDe(self, self.datos_licencia)

    def _cerrar_sesion_salir(self):
        settings = QtCore.QSettings()
        settings.setValue("creds", "")
        self._salir()

    def _dialogo_configuracion(self):
        DialogoConfiguracion(self)

    def _modulo_edificio(self):
        self._modulo = WidgetModuloEdificio(self)

    def _modulo_cubierta_aislada(self):
        self._modulo = WidgetModuloCubiertaAislada(self)

    def _modulo_cartel(self):
        self._modulo = WidgetModuloCartel(self)

    def _request_nueva_version(self):
        url = "https://api.github.com/repos/efdiloreto/ZondaV/releases/latest"
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))

        self._manager = QtNetwork.QNetworkAccessManager()
        self._manager.finished.connect(self._procesar_respuesta)
        self._manager.get(request)

    def _procesar_respuesta(self, respuesta: QtNetwork.QNetworkReply):
        error = respuesta.error()
        if error == QtNetwork.QNetworkReply.NoError:
            respuesta_str = respuesta.readAll().data().decode()
            datos = json.loads(respuesta_str)
            nueva_version = datos["tag_name"]
            version_actual = __acercade__.__version__
            existe_nueva_version = parse_version(nueva_version) > parse_version(version_actual)
            if existe_nueva_version:
                boton_actualizar = QtWidgets.QToolButton()
                boton_actualizar.setIcon(QtGui.QIcon(":/iconos/actualizar.png"))
                boton_actualizar.setIconSize(QtCore.QSize(16, 16))
                boton_actualizar.setToolTip("Existe una nueva versión")
                boton_actualizar.clicked.connect(lambda: webbrowser.open(__acercade__.__descarga__))
                self._efecto_boton_actualizar = EfectoPulsacion()
                boton_actualizar.setGraphicsEffect(self._efecto_boton_actualizar)
                self._efecto_boton_actualizar.iniciar()

                self._toolbar.addWidget(boton_actualizar)

    @staticmethod
    def _salir():
        QtWidgets.qApp.quit()
