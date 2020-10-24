"""Contiene clases que representan los dialogos de la interfaz.
"""
import base64
import json
import os
from json.decoder import JSONDecodeError
from typing import Union, Dict, Tuple

import wmi
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtNetwork import QNetworkReply, QNetworkRequest, QNetworkAccessManager
from cryptography.fernet import Fernet

from zondapro.enums import CategoriaExposicion, Flexibilidad, TipoTerrenoTopografia, DireccionTopografia
from zondapro.excepciones import ErrorViento, ErrorComponentes
from zondapro.widgets.custom import WidgetLogo, EfectoPulsacion, WidgetLinksInfo
from zondapro.widgets.entrada import WidgetComponentes


class DialogoBase(QtWidgets.QDialog):
    """DialogoBase.

    Clase de la que heredan todos los demás diálogos.
    """

    def __init__(self) -> None:
        super().__init__()

        self._botones = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self._botones.accepted.connect(self.accept)
        self._botones.rejected.connect(self.reject)


class DialogoViento(DialogoBase):
    """DialogoViento.

    Permite configurar las opciones relacionadas con los parámetros de viento.
    """

    def __init__(
        self,
        categoria_exp: CategoriaExposicion,
        velocidad: float,
        frecuencia: float,
        beta: float,
        flexibilidad: Flexibilidad,
        ciudad: str,
        factor_g_simplificado: bool,
        editar_velocidad: bool,
    ) -> None:
        """

        Args:
            categoria_exp: La categoría de exposición al viento de la estructura.
            velocidad: La velocidad del viento en m/s.
            frecuencia: La frecuencia natural de la estructura en hz.
            beta: La relación de amortiguamiento crítico.
            flexibilidad: La flexibilidad de la estructura.
            ciudad: La ciudad donde se está calculando el viento.
            factor_g_simplificado: Indica si se debe usar 0.85 como valor del factor de ráfaga.
            editar_velocidad: Indica si el widget velocidad es editable.
        """
        super().__init__()

        self._parametros = None

        self._combobox_exposicion = QtWidgets.QComboBox()
        for enum in CategoriaExposicion:
            self._combobox_exposicion.addItem(enum.value, enum)
        self._combobox_exposicion.setMinimumWidth(50)
        self._combobox_exposicion.setCurrentText(categoria_exp.value)

        datos_spinboxs = (
            ("velocidad", 20, 100, " m/s", 2, "Velocidad básica del viento."),
            ("frecuencia", 0.1, 100, " Hz", 2, "Frecuencia natural de la estructura."),
            ("beta", 0.01, 0.05, None, 3, "Relación de amortiguamiento β, expresada como porcentaje del crítico."),
        )
        self._spinboxs = {}
        for (nombre, minimo, maximo, sufijo, precision, status_tip) in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setSuffix(sufijo)
            spinbox.setDecimals(precision)
            spinbox.setStatusTip(status_tip)
            self._spinboxs[nombre] = spinbox

        self._spinboxs["velocidad"].setValue(velocidad)
        self._spinboxs["frecuencia"].setValue(frecuencia)
        self._spinboxs["beta"].setValue(beta)

        self._editar_velocidad = QtWidgets.QCheckBox("Velocidad")
        self._editar_velocidad.setChecked(editar_velocidad)
        self._editar_velocidad.stateChanged.connect(self._habilitar_deshabilitar_velocidad)

        ciudades_velocidad = (
            ("Bahía Blanca", 55),
            ("Bariloche", 46),
            ("Buenos Aires", 45),
            ("Catamarca", 43),
            ("Comodoro Rivadavia", 67.5),
            ("Córdoba", 45),
            ("Corrientes", 46),
            ("Formosa", 45),
            ("La Plata", 46),
            ("La Rioja", 44),
            ("Mar del Plata", 51),
            ("Mendoza", 39),
            ("Neuquén", 48),
            ("Paraná", 52),
            ("Posada", 45),
            ("Rawson", 60),
            ("Resistencia", 45),
            ("Río Gallegos", 60),
            ("Rosario", 50),
            ("Salta", 35),
            ("Santa Fé", 51),
            ("San Juan", 40),
            ("San Luis", 45),
            ("San Miguel de Tucumán", 40),
            ("San Salvador de Jujuy", 34),
            ("Santa Rosa", 50),
            ("Santiago del Estero", 43),
            ("Ushuaia", 60),
            ("Viedma", 60),
        )

        self._combobox_ciudades = QtWidgets.QComboBox()
        for opcion, valor in ciudades_velocidad:
            self._combobox_ciudades.addItem(opcion, valor)
        self._combobox_ciudades.setCurrentText(ciudad)
        self._combobox_ciudades.currentIndexChanged.connect(
            lambda: self._spinboxs["velocidad"].setValue(self._combobox_ciudades.currentData())
        )

        self._factor_g_simplificado = QtWidgets.QCheckBox("Considerar Factor de Ráfaga igual a 0.85")
        self._factor_g_simplificado.stateChanged.connect(
            lambda: self._habilitar_deshabilitar_widgets_rafaga(self._factor_g_simplificado.isChecked())
        )

        self._combobox_flex = QtWidgets.QComboBox()
        for enum in Flexibilidad:
            self._combobox_flex.addItem(enum.value.capitalize(), enum)
        self._combobox_flex.setCurrentIndex(self._combobox_flex.findData(flexibilidad))

        imagen = QtWidgets.QLabel()
        imagen.setToolTip("Figura 1A - CIRSOC 102 2005")
        imagen.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        pixmap = QtGui.QPixmap(":/imagenes/mapa-viento.png")
        imagen.setPixmap(pixmap)

        textos_rafaga = (
            "Flexibilidad",
            "Frecuencia Natural",
            "Relación de amortiguamiento",
        )

        self._grid_layout_viento = QtWidgets.QGridLayout()
        self._grid_layout_viento.addWidget(QtWidgets.QLabel("Ciudad"), 0, 0, QtCore.Qt.AlignRight)
        self._grid_layout_viento.addWidget(self._combobox_ciudades, 0, 1)
        self._grid_layout_viento.addWidget(self._editar_velocidad, 1, 0, QtCore.Qt.AlignRight)
        self._grid_layout_viento.addWidget(self._spinboxs["velocidad"], 1, 1)
        self._grid_layout_viento.setColumnStretch(2, 1)

        grid_layout_exposicion = QtWidgets.QGridLayout()

        grid_layout_exposicion.addWidget(QtWidgets.QLabel("Categoría de Exposición"), 0, 0, QtCore.Qt.AlignRight)
        grid_layout_exposicion.addWidget(self._combobox_exposicion, 0, 1)
        grid_layout_exposicion.setColumnStretch(2, 1)

        self._grid_layout_rafaga = QtWidgets.QGridLayout()
        self._grid_layout_rafaga.addWidget(self._factor_g_simplificado, 0, 0, 1, 3)
        for i, texto in enumerate(textos_rafaga):
            self._grid_layout_rafaga.addWidget(QtWidgets.QLabel(texto), i + 1, 0, QtCore.Qt.AlignRight)
        self._grid_layout_rafaga.addWidget(self._combobox_flex, 1, 1)
        self._grid_layout_rafaga.addWidget(self._spinboxs["frecuencia"], 2, 1)
        self._grid_layout_rafaga.addWidget(self._spinboxs["beta"], 3, 1)

        self._grid_layout_rafaga.setColumnStretch(2, 1)

        # Tiene que instanciarse el atributo del layout de ragafa
        self._factor_g_simplificado.setChecked(factor_g_simplificado)

        box_viento = QtWidgets.QGroupBox("Velocidad básica del viento")
        box_viento.setLayout(self._grid_layout_viento)

        box_exposicion = QtWidgets.QGroupBox("Exposición")
        box_exposicion.setLayout(grid_layout_exposicion)

        box_rafaga = QtWidgets.QGroupBox("Factor de Ráfaga")
        box_rafaga.setLayout(self._grid_layout_rafaga)

        layout_viento = QtWidgets.QGridLayout()
        layout_viento.addWidget(box_viento, 0, 0)
        layout_viento.addWidget(box_exposicion, 1, 0)
        layout_viento.addWidget(box_rafaga, 2, 0)
        layout_viento.addWidget(imagen, 0, 1, 4, 1)
        layout_viento.setRowStretch(3, 1)
        layout_viento.setRowStretch(4, 2)
        layout_viento.setColumnStretch(1, 1)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_viento)
        layout_principal.addWidget(self._botones)

        self.setLayout(layout_principal)

        self._habilitar_deshabilitar_velocidad()

        self.setWindowTitle("Parámetros de Viento")

        self.setFixedSize(self.sizeHint())

    def _habilitar_deshabilitar_widgets_rafaga(self, estado: bool) -> None:
        """Habilita o deshabilita los widgets de frecuencia, beta y flexibilidad en base al estado del widget de
        factor_g_simplificado.

        Args:
            estado: El estado del widget de factor_g_simplificado.
        """
        for fila in range(1, 4):
            for columna in range(2):
                widget = self._grid_layout_rafaga.itemAtPosition(fila, columna).widget()
                widget.setEnabled(not estado)

    def _habilitar_deshabilitar_velocidad(self) -> None:
        """Habilita o deshabilita el widget encargado de setear la velocidad del viendo y su label."""
        estado = self._editar_velocidad.isChecked()
        self._spinboxs["velocidad"].setEnabled(estado)
        for fila in range(0, 1):
            for columna in range(2):
                widget = self._grid_layout_viento.itemAtPosition(fila, columna).widget()
                widget.setEnabled(not estado)

    def _validar(self) -> None:
        """Valida los datos ingresados."""
        if not self._factor_g_simplificado.isChecked():
            flexibilidad = self._combobox_flex.currentData()
            frecuencia = self._spinboxs["frecuencia"].value()
            if flexibilidad == Flexibilidad.RIGIDA and frecuencia < 1:
                raise ErrorViento(
                    "Para que la estructura sea considerada rígida, la"
                    " frecuencia debe debe ser mayor o igual a 1 Hz."
                )
            elif flexibilidad == Flexibilidad.FLEXIBLE and frecuencia >= 1:
                raise ErrorViento(
                    "Para que la estructura sea considerada flexible, la" " frecuencia debe ser menor a 1 Hz."
                )

    def parametros(self) -> Union[None, Dict[str, Union[float, Flexibilidad, CategoriaExposicion, str]]]:
        """Determina los parámetros de viento.

        Returns:
            Los parámetros de viento.
        """
        return self._parametros

    def accept(self):
        try:
            self._validar()
            resultados_spinboxs = {key: spinbox.value() for key, spinbox in self._spinboxs.items()}
            self._parametros = {
                "factor_g_simplificado": self._factor_g_simplificado.isChecked(),
                "categoria_exp": self._combobox_exposicion.currentData(),
                "flexibilidad": self._combobox_flex.currentData(),
                "ciudad": self._combobox_ciudades.currentText(),
                "editar_velocidad": self._editar_velocidad.isChecked(),
                **resultados_spinboxs,
            }
            super().accept()
        except ErrorViento as error:
            QtWidgets.QMessageBox.warning(self, "Error de Datos de Entrada", str(error))


class DialogoTopografia(DialogoBase):
    """DialogoTopografia.

    Permite configurar las opciones relacionadas con los parámetros de topografía.
    """

    def __init__(
        self,
        considerar_topografia: bool,
        tipo_terreno: TipoTerrenoTopografia,
        direccion: DireccionTopografia,
        distancia_cresta: float,
        distancia_barlovento_sotavento: float,
        altura_terreno: float,
    ) -> None:
        """

        Args:
            considerar_topografia: indica si se tiene que calcular la topografia.
            tipo_terreno: El tipo de terreno.
            direccion: La direccion para la el parámetro `distancia_barlovento_sotavento`.
            distancia_cresta: La distancia en la dirección de barlovento, medida desde la cresta de la colina o escarpa.
            distancia_barlovento_sotavento: Distancia tomada desde la cima, en la dirección de barlovento o de sotavento.
            altura_terreno: La altura de la colina o escarpa.
        """
        super().__init__()

        self._parametros = None

        self._combobox_tipo_terreno = QtWidgets.QComboBox()
        for enum in TipoTerrenoTopografia:
            self._combobox_tipo_terreno.addItem(enum.value.title(), enum)
        self._combobox_tipo_terreno.setCurrentText(tipo_terreno.value.title())
        self._combobox_tipo_terreno.currentIndexChanged.connect(self._cambio_tipo_terreno)

        self._combobox_direccion = QtWidgets.QComboBox()
        for enum in DireccionTopografia:
            self._combobox_direccion.addItem(f"{enum.value.capitalize()} de la cresta", enum)
        self._combobox_direccion.setCurrentIndex(self._combobox_direccion.findData(direccion))

        textos_spinboxs = (
            "Distancia, L<sub>h</sub>",
            "Distancia, X",
            "Altura de Colina, H",
        )
        datos_spinboxs = (
            ("distancia_cresta", 1, 200, 50, " m", True),
            ("distancia_barlovento_sotavento", 1, 200, 50, " m", True),
            ("altura_terreno", 5, 200, 40, " m", True),
        )

        self._spinboxs = {}
        for (nombre, minimo, maximo, default, sufijo, activado) in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setValue(default)
            spinbox.setSuffix(sufijo)
            spinbox.setEnabled(activado)
            self._spinboxs[nombre] = spinbox

        self._spinboxs["distancia_cresta"].setValue(distancia_cresta)
        self._spinboxs["distancia_barlovento_sotavento"].setValue(distancia_barlovento_sotavento)
        self._spinboxs["altura_terreno"].setValue(altura_terreno)

        self._imagen = QtWidgets.QLabel()
        self._imagen.setFrameStyle(QtWidgets.QFrame.StyledPanel)

        self._layout_principal = QtWidgets.QGridLayout()

        self._layout_principal.addWidget(QtWidgets.QLabel("Tipo de Terreno"), 0, 0, QtCore.Qt.AlignRight)
        self._layout_principal.addWidget(self._combobox_tipo_terreno, 0, 1)
        self._layout_principal.addWidget(QtWidgets.QLabel("Dirección"), 1, 0, QtCore.Qt.AlignRight)
        self._layout_principal.addWidget(self._combobox_tipo_terreno, 0, 1)
        self._layout_principal.addWidget(self._combobox_direccion, 1, 1)
        for i, (nombre, widget) in enumerate(self._spinboxs.items()):
            self._layout_principal.addWidget(QtWidgets.QLabel(textos_spinboxs[i]), i + 2, 0, QtCore.Qt.AlignRight)
            self._layout_principal.addWidget(widget, i + 2, 1)
        self._layout_principal.addWidget(
            QtWidgets.QLabel("* Se condisera que se satisfacen los puntos 1, 2 y 3 " "del artículo 5.7.1."),
            7,
            0,
            1,
            3,
        )
        self._layout_principal.setRowStretch(5, 1)
        self._layout_principal.setRowMinimumHeight(6, 20)

        self._layout_principal.addWidget(self._imagen, 0, 2, 6, 1)

        self._considerar_topografia = QtWidgets.QGroupBox("Considerar Topografía*")
        self._considerar_topografia.setCheckable(True)
        self._considerar_topografia.setChecked(considerar_topografia)
        self._considerar_topografia.setLayout(self._layout_principal)

        layout_topografia = QtWidgets.QVBoxLayout()
        layout_topografia.addWidget(self._considerar_topografia)
        layout_topografia.addStretch()

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_topografia)
        layout_principal.addWidget(self._botones)

        self._cambio_tipo_terreno()

        self.setLayout(layout_principal)

        self.setWindowTitle("Parámetros de Topografía")

        self.setFixedSize(self.sizeHint())

    def parametros(self) -> Union[None, Dict[str, Union[TipoTerrenoTopografia, DireccionTopografia, float, bool]]]:
        """Determina los parámetros de topografía.

        Returns:
            Los parámetros de topografía.
        """
        return self._parametros

    def accept(self):
        resultados_spinboxs = {key: spinbox.value() for key, spinbox in self._spinboxs.items()}
        self._parametros = {
            "considerar_topografia": self._considerar_topografia.isChecked(),
            "tipo_terreno": self._combobox_tipo_terreno.currentData(),
            "direccion": self._combobox_direccion.currentData(),
            **resultados_spinboxs,
        }
        super().accept()

    def _cambio_tipo_terreno(self):
        if self._combobox_tipo_terreno.currentData() == TipoTerrenoTopografia.ESCARPA_BIDIMENSIONAL:
            imagen = "escarpa.jpg"
        else:
            imagen = "loma.jpg"
        self._imagen.setPixmap(QtGui.QPixmap(f":/imagenes/{imagen}"))


class DialogoComponentes(DialogoBase):
    """DialogoComponentes.

    Permite configurar los componentes y revestimientos para paredes y cubierta.
    """

    def __init__(self, componentes: Dict[str, Union[None, Dict[str, float]]]) -> None:
        """

        Args:
            componentes: Los componentes de paredes y cubierta.
        """
        super().__init__()

        self._componentes = componentes

        self._componentes_paredes = WidgetComponentes(componentes["componentes_paredes"])
        self._componentes_cubierta = WidgetComponentes(componentes["componentes_cubierta"])

        label_aviso_geometria = QtWidgets.QLabel(
            "* Dependiendo de la geometria de la estructura es posible que existan solapamientos en la visualizazión"
            " gráfica, ya que el reglamento especifica dimensiones mínimas para las áreas de presión."
        )
        label_aviso_geometria.setWordWrap(True)

        layout_componentes = QtWidgets.QGridLayout()
        layout_componentes.addWidget(QtWidgets.QLabel("PAREDES"), 0, 0, QtCore.Qt.AlignCenter)
        layout_componentes.addWidget(QtWidgets.QLabel("CUBIERTA"), 0, 2, QtCore.Qt.AlignCenter)
        layout_componentes.addWidget(self._componentes_paredes, 2, 0)
        layout_componentes.addWidget(self._componentes_cubierta, 2, 2)
        layout_componentes.setVerticalSpacing(2)
        layout_componentes.setColumnMinimumWidth(1, 20)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_componentes)
        layout_principal.addWidget(label_aviso_geometria)

        layout_principal.addWidget(self._botones)

        self.setLayout(layout_principal)

        self.setWindowTitle("Componentes y Revestimientos")

        self.setMinimumSize(QtCore.QSize(650, 400))

    def componentes(self) -> Dict[str, Union[None, Dict[str, float]]]:
        return self._componentes

    def accept(self):
        try:
            self._componentes = {
                "componentes_paredes": self._componentes_paredes(),
                "componentes_cubierta": self._componentes_cubierta(),
            }
            super().accept()
        except ErrorComponentes as error:
            QtWidgets.QMessageBox.warning(self, "Error de Datos de Entrada", str(error))


class DialogoConfiguracion(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        settings = QtCore.QSettings()
        settings.beginGroup("unidades")
        fuerza = settings.value("fuerza", "N")
        presion = settings.value("presion", "N")
        settings.endGroup()

        fuerzas = (
            ("N", "N"),
            ("kN", "kN"),
            ("kG", "kG"),
        )
        self._combobox_fuerzas = QtWidgets.QComboBox()
        for opcion, valor in fuerzas:
            self._combobox_fuerzas.addItem(opcion, userData=QtCore.QVariant(valor))
        self._combobox_fuerzas.setCurrentIndex(self._combobox_fuerzas.findData(fuerza))

        presiones = (
            ("N/m\u00B2", "N"),
            ("kN/m\u00B2", "kN"),
            ("kG/m\u00B2", "kG"),
        )
        self._combobox_presiones = QtWidgets.QComboBox()
        for opcion, valor in presiones:
            self._combobox_presiones.addItem(opcion, userData=QtCore.QVariant(valor))
        self._combobox_presiones.setCurrentIndex(self._combobox_presiones.findData(presion))

        layout_unidades = QtWidgets.QGridLayout()
        layout_unidades.addWidget(QtWidgets.QLabel("Presión"), 0, 0, QtCore.Qt.AlignRight)
        layout_unidades.addWidget(QtWidgets.QLabel("Fuerza"), 1, 0, QtCore.Qt.AlignRight)
        layout_unidades.addWidget(self._combobox_presiones, 0, 1)
        layout_unidades.addWidget(self._combobox_fuerzas, 1, 1)

        groupbox_unidades = QtWidgets.QGroupBox("Unidades")
        groupbox_unidades.setLayout(layout_unidades)

        botones = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(groupbox_unidades)
        layout_principal.addWidget(botones)

        self.setLayout(layout_principal)
        self.setWindowTitle("Configuración")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setFixedSize(self.sizeHint())
        self.show()

    def accept(self):

        settings = QtCore.QSettings()
        settings.beginGroup("unidades")
        settings.setValue("fuerza", self._combobox_fuerzas.currentData())
        settings.setValue("presion", self._combobox_presiones.currentData())
        settings.endGroup()
        settings.sync()

        super().accept()


class DialogoAutenticacion(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        self._fernet = Fernet(b"U3L0hEBpVunU-jS7BDx0VjOKSzO7Hx7OwgGFCa7rAn8=")

        self._settings = QtCore.QSettings()

        self._credenciales = self._settings.value("creds", "")

        widget_logo = WidgetLogo(nombre_archivo="logo-login.png")
        widget_logo.setAlignment(QtCore.Qt.AlignCenter)

        self._line_edit_email = QtWidgets.QLineEdit()
        self._line_edit_email.setPlaceholderText("usuario@email.com")
        self._line_edit_email.setProperty("class", "login")

        self._line_edit_contrasenia = QtWidgets.QLineEdit()
        self._line_edit_contrasenia.setEchoMode(QtWidgets.QLineEdit.Password)
        self._line_edit_contrasenia.setPlaceholderText("contraseña")
        self._line_edit_contrasenia.setProperty("class", "login")

        boton_login = QtWidgets.QPushButton("Iniciar Sesión")
        boton_login.setProperty("class", "login")
        boton_login.clicked.connect(self._request_login)

        layout_login = QtWidgets.QVBoxLayout()
        layout_login.setContentsMargins(0, 20, 0, 0)
        layout_login.setSpacing(10)
        layout_login.addWidget(self._line_edit_email)
        layout_login.addWidget(self._line_edit_contrasenia)
        layout_login.addSpacing(10)
        layout_login.addWidget(boton_login)

        self._widget_login = QtWidgets.QWidget()
        self._widget_login.setLayout(layout_login)

        self._label_verificando_licencia = QtWidgets.QLabel("Verificando Licencia...")
        self._label_verificando_licencia.hide()
        self._label_verificando_licencia.setObjectName("verificando-licencia")
        self._label_verificando_licencia.setAlignment(QtCore.Qt.AlignCenter)
        self._efecto_label_autenticando = EfectoPulsacion()
        self._label_verificando_licencia.setGraphicsEffect(self._efecto_label_autenticando)

        self._label_info = QtWidgets.QLabel()
        self._label_info.setObjectName("error-auth")
        self._label_info.setWordWrap(True)

        self._label_info.hide()

        self._boton_cerrar_sesion = QtWidgets.QPushButton("Cerrar Sesión")
        self._boton_cerrar_sesion.setProperty("class", "salir")
        self._boton_cerrar_sesion.clicked.connect(self._cerrar_sesion)
        self._boton_cerrar_sesion.hide()

        self._boton_obtener_licencia = QtWidgets.QPushButton("Adquirir Licencia")
        self._boton_obtener_licencia.setProperty("class", "login")
        self._boton_obtener_licencia.setObjectName("adquirir-licencia")
        self._boton_obtener_licencia.hide()

        self._boton_volver_intentar = QtWidgets.QPushButton("Volver a intentar")
        self._boton_volver_intentar.setProperty("class", "salir")
        self._boton_volver_intentar.clicked.connect(self._request_login)
        self._boton_volver_intentar.hide()

        widget_links_info = WidgetLinksInfo(pagina_web=True, contacto=True, ayuda=True)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(25, 25, 25, 15)
        layout_principal.addWidget(widget_logo)
        layout_principal.addWidget(self._widget_login)
        layout_principal.addWidget(self._label_verificando_licencia)
        layout_principal.addWidget(self._label_info)
        layout_principal.addWidget(self._boton_obtener_licencia)
        layout_principal.addWidget(self._boton_volver_intentar)
        layout_principal.addWidget(self._boton_cerrar_sesion)
        layout_principal.addWidget(widget_links_info)

        self.setLayout(layout_principal)

        self._widget_login.setHidden(bool(self._credenciales))

        if self._credenciales:
            self._request_login()

        self.setFixedSize(self.sizeHint())
        self._label_info.setMaximumWidth(self.width() - 50)

    def accept(self) -> None:
        self._aceptado()
        super().accept()

    def reject(self) -> None:
        self._rechazado()
        super().reject()

    def _request_login(self):

        self._efecto_label_autenticando.iniciar()
        self._label_info.hide()
        self._boton_volver_intentar.hide()
        self._boton_cerrar_sesion.hide()
        self._label_verificando_licencia.show()
        self.setFixedSize(self.sizeHint())

        status_identificador, identificador_o_msj = self._obtener_identificador()

        if not status_identificador:
            self._label_verificando_licencia.hide()
            self._efecto_label_autenticando.detener()
            self._label_info.setText(identificador_o_msj)
            self._label_info.show()
            self.setFixedSize(self.sizeHint())
        else:
            url = "https://zondacs.com.ar/key"
            request = QNetworkRequest(QtCore.QUrl(url))
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

            if self._credenciales:
                auth_bytes = self._fernet.decrypt(self._credenciales.encode())
            else:
                email = (
                    self._line_edit_email.text() or "x"
                )  # El servidor no devuelve JSON si se envian ambas strings vacias.
                contrasenia = self._line_edit_contrasenia.text()
                auth_bytes = (email + ":" + contrasenia).encode()
                self._auth_bytes = auth_bytes

            auth = base64.b64encode(auth_bytes)

            data = json.dumps({"dispositivo": identificador_o_msj}).encode()

            request.setRawHeader("Authorization".encode(), "Basic ".encode() + auth)

            self._manager = QNetworkAccessManager()
            self._manager.finished.connect(self._procesar_respuesta)

            self._manager.put(request, data)

    def _procesar_respuesta(self, respuesta: QNetworkReply):
        error = respuesta.error()
        if respuesta.url().host() != "zondacs.com.ar":
            self.reject()
        status_code = respuesta.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        try:
            self._respuesta_json = json.loads(str(respuesta.readAll(), "utf-8"))
            status_respuesta = self._respuesta_json.get("status", False)
            error_respuesta = self._respuesta_json.get("error", "")
        except JSONDecodeError:
            status_respuesta = False
            error_respuesta = (
                "No se pudo conectar al servidor. Revise su conexión a internet o contactese con soporte técnico."
            )

        # Opciones para poder eliminar dispositivo, se debe permitir 3 (o dos) veces en el año por dispositivo para las cuentas
        # anuales de forma automatica y una vez de forma manual para las mensuales.

        # El error de autenticacion deberia ser "usuario o contraseña incorrectos".

        self._label_verificando_licencia.hide()
        self._efecto_label_autenticando.detener()

        if error == QNetworkReply.NoError and status_code == 201 and status_respuesta:
            auth_bytes = getattr(self, "_auth_bytes", None)
            if auth_bytes is not None:
                creds_encrypt = self._fernet.encrypt(auth_bytes)
                self._settings.setValue("creds", creds_encrypt.decode())

            self.accept()
        elif status_code == 401 or not status_respuesta:
            self._label_info.setText(f"Error al iniciar sesión.\n\n{error_respuesta}")
        elif error in (
            QNetworkReply.TimeoutError,
            QNetworkReply.NetworkSessionFailedError,
            QNetworkReply.UnknownNetworkError,
        ):
            self._label_info.setText(f"Error al iniciar sesión.\n\n{error_respuesta}")
        self._label_info.show()
        if self._widget_login.isHidden():
            self._boton_cerrar_sesion.show()
            if "Revise su conexión a internet" in error_respuesta:
                self._boton_volver_intentar.show()
            else:
                self._boton_obtener_licencia.show()
        self.setFixedSize(self.sizeHint())

    def _aceptado(self):
        self.codigo_validacion = ("w", "e", (("4", None),))
        self.datos_licencia = self._respuesta_json

    def _cerrar_sesion(self):
        self._settings.setValue("creds", "")
        self._credenciales = ""
        self._boton_obtener_licencia.hide()
        self._boton_cerrar_sesion.hide()
        self._boton_volver_intentar.hide()
        self._label_info.hide()
        self._widget_login.show()
        self.setFixedSize(self.sizeHint())

    @staticmethod
    def _obtener_identificador() -> Tuple[bool, str]:
        """Obtiene el identificador del equipo.

        Detecta si se esta corriendo desde una máquina virtual, de forma un poco light por cierto. Si no es asi intenta
        obtener los identificadores.

        Primero intenta obtener el uuid. Si existe se devuelve True y el uuid. Si no existe va a devolver un string con
        muchas "F". Ver https://www.nextofwindows.com/the-best-way-to-uniquely-identify-a-windows-machine. En ese caso
        se descarta y se continua viendo otros identificadores.

        Si el uuid no existe, de intenta obtener los numeros de serie de los discos. Si se logra se devuelve True con
        los numeros de serie concatenados en un string. Si no se logra se continua viendo otros identificadores.

        Si no se pueden identificar los numeros de serie de los discos, se verifica los numeros de serie de las memorias
        ram instaladas. Si se logra se devuelve True con los numeros de serie concatenados en un string. Si no se logra
        se continua viendo otros identificadores.

        Si no se pueden identificar las memorias ram, se busca identificar la mac address. Si se encuentra se devuelve
        True con la mac address. Sino se devuelve False y se informa que no se pudo identificar el equipo.

        """
        c = wmi.WMI()

        maquinas_virtuales = ("virtualbox", "vmware", "virtual machine")
        nombre_sistema = c.Win32_ComputerSystemProduct()[0].Name.lower()

        if any(maquina in nombre_sistema for maquina in maquinas_virtuales):
            return False, "No se puede identificar el equipo en una máquina virtual"

        uuid = c.Win32_ComputerSystemProduct()[0].uuid

        if "FFFFFFFFFFFF" not in uuid:
            return True, uuid

        numeros_serie_discos = []
        for disk in c.Win32_DiskDrive():
            if disk.MediaType == "Fixed hard disk media":
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        if logical.DriveType == 3:
                            numero_serie = disk.SerialNumber
                            if numero_serie is not None and numero_serie != "":
                                numero_serie_str = str(numero_serie).replace(" ", "")
                                if numero_serie_str not in numeros_serie_discos:
                                    numeros_serie_discos.append(numero_serie_str)

        if numeros_serie_discos:
            numeros_serie_discos.sort()
            return True, "".join(numeros_serie_discos)

        numeros_serie_ram = [
            m.SerialNumber for m in c.Win32_PhysicalMemory() if m.SerialNumber is not None and m.SerialNumber != ""
        ]

        if numeros_serie_ram:
            numeros_serie_ram = [str(n).replace(" ", "") for n in numeros_serie_ram]
            numeros_serie_ram.sort()
            return True, "".join(numeros_serie_ram)

        for line in os.popen("ipconfig /all"):
            if line.lstrip().startswith("Physical Address"):
                mac = line.split(":")[1].strip().replace("-", ":")
                return True, mac

        return False, "No se pudo obtener el identificador del equipo"

    @staticmethod
    def _rechazado():
        QTimer.singleShot(0, QtWidgets.qApp.quit)
