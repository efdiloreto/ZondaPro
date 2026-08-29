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

"""Contiene clases que representan los dialogos de la interfaz."""

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, actualizaciones, recursos
from zonda.actualizaciones import Actualizacion
from zonda.cirsoc import factores
from zonda.enums import (
    CategoriaEstructura,
    CategoriaExposicion,
    DireccionTopografia,
    Flexibilidad,
    TipoTerrenoTopografia,
)
from zonda.excepciones import ErrorComponentes, ErrorViento
from zonda.widgets import utils_qt
from zonda.widgets.entrada import WidgetComponentes


class DialogoBase(QtWidgets.QDialog):
    """DialogoBase.

    Clase de la que heredan todos los demás diálogos.
    """

    def __init__(self) -> None:
        super().__init__()

        self._botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self.accept)
        self._botones.rejected.connect(self.reject)


CIUDADES_VELOCIDAD: dict[str, dict[CategoriaEstructura, float]] = {
    "Bahía Blanca": {
        CategoriaEstructura.I: 62.8,
        CategoriaEstructura.II: 67.4,
        CategoriaEstructura.III: 72.2,
        CategoriaEstructura.IV: 72.2,
    },
    "Bariloche": {
        CategoriaEstructura.I: 52.5,
        CategoriaEstructura.II: 56.3,
        CategoriaEstructura.III: 60.4,
        CategoriaEstructura.IV: 60.4,
    },
    "Buenos Aires": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "Catamarca": {
        CategoriaEstructura.I: 49.1,
        CategoriaEstructura.II: 52.7,
        CategoriaEstructura.III: 56.5,
        CategoriaEstructura.IV: 56.5,
    },
    "Comodoro Rivadavia": {
        CategoriaEstructura.I: 77.1,
        CategoriaEstructura.II: 82.7,
        CategoriaEstructura.III: 88.7,
        CategoriaEstructura.IV: 88.7,
    },
    "Córdoba": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "Corrientes": {
        CategoriaEstructura.I: 52.5,
        CategoriaEstructura.II: 56.3,
        CategoriaEstructura.III: 60.4,
        CategoriaEstructura.IV: 60.4,
    },
    "Formosa": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "La Plata": {
        CategoriaEstructura.I: 52.5,
        CategoriaEstructura.II: 56.3,
        CategoriaEstructura.III: 60.4,
        CategoriaEstructura.IV: 60.4,
    },
    "La Rioja": {
        CategoriaEstructura.I: 50.3,
        CategoriaEstructura.II: 53.9,
        CategoriaEstructura.III: 57.8,
        CategoriaEstructura.IV: 57.8,
    },
    "Mar del Plata": {
        CategoriaEstructura.I: 58.3,
        CategoriaEstructura.II: 62.5,
        CategoriaEstructura.III: 67.0,
        CategoriaEstructura.IV: 67.0,
    },
    "Mendoza": {
        CategoriaEstructura.I: 44.6,
        CategoriaEstructura.II: 47.8,
        CategoriaEstructura.III: 51.2,
        CategoriaEstructura.IV: 51.2,
    },
    "Neuquén": {
        CategoriaEstructura.I: 54.8,
        CategoriaEstructura.II: 58.8,
        CategoriaEstructura.III: 63.0,
        CategoriaEstructura.IV: 63.0,
    },
    "Paraná": {
        CategoriaEstructura.I: 59.4,
        CategoriaEstructura.II: 63.7,
        CategoriaEstructura.III: 68.3,
        CategoriaEstructura.IV: 68.3,
    },
    "Posadas": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "Rawson": {
        CategoriaEstructura.I: 68.5,
        CategoriaEstructura.II: 73.5,
        CategoriaEstructura.III: 78.8,
        CategoriaEstructura.IV: 78.8,
    },
    "Resistencia": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "Río Gallegos": {
        CategoriaEstructura.I: 68.5,
        CategoriaEstructura.II: 73.5,
        CategoriaEstructura.III: 78.8,
        CategoriaEstructura.IV: 78.8,
    },
    "Rosario": {
        CategoriaEstructura.I: 57.1,
        CategoriaEstructura.II: 61.2,
        CategoriaEstructura.III: 65.7,
        CategoriaEstructura.IV: 65.7,
    },
    "Salta": {
        CategoriaEstructura.I: 40.0,
        CategoriaEstructura.II: 42.9,
        CategoriaEstructura.III: 46.0,
        CategoriaEstructura.IV: 46.0,
    },
    "San Juan": {
        CategoriaEstructura.I: 45.7,
        CategoriaEstructura.II: 49.0,
        CategoriaEstructura.III: 52.5,
        CategoriaEstructura.IV: 52.5,
    },
    "San Luis": {
        CategoriaEstructura.I: 51.4,
        CategoriaEstructura.II: 55.1,
        CategoriaEstructura.III: 59.1,
        CategoriaEstructura.IV: 59.1,
    },
    "San Miguel de Tucumán": {
        CategoriaEstructura.I: 45.7,
        CategoriaEstructura.II: 49.0,
        CategoriaEstructura.III: 52.5,
        CategoriaEstructura.IV: 52.5,
    },
    "San Salvador de Jujuy": {
        CategoriaEstructura.I: 38.8,
        CategoriaEstructura.II: 41.6,
        CategoriaEstructura.III: 44.7,
        CategoriaEstructura.IV: 44.7,
    },
    "Santa Fe": {
        CategoriaEstructura.I: 58.3,
        CategoriaEstructura.II: 62.5,
        CategoriaEstructura.III: 67.0,
        CategoriaEstructura.IV: 67.0,
    },
    "Santa Rosa": {
        CategoriaEstructura.I: 57.1,
        CategoriaEstructura.II: 61.2,
        CategoriaEstructura.III: 65.7,
        CategoriaEstructura.IV: 65.7,
    },
    "Santiago del Estero": {
        CategoriaEstructura.I: 49.1,
        CategoriaEstructura.II: 52.7,
        CategoriaEstructura.III: 56.5,
        CategoriaEstructura.IV: 56.5,
    },
    "Ushuaia": {
        CategoriaEstructura.I: 68.5,
        CategoriaEstructura.II: 73.5,
        CategoriaEstructura.III: 78.8,
        CategoriaEstructura.IV: 78.8,
    },
    "Viedma": {
        CategoriaEstructura.I: 68.5,
        CategoriaEstructura.II: 73.5,
        CategoriaEstructura.III: 78.8,
        CategoriaEstructura.IV: 78.8,
    },
}


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
        altitud: float = 0.0,
        categoria_riesgo_viento: CategoriaEstructura = CategoriaEstructura.II,
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
            altitud: Altitud del terreno sobre el nivel del mar en metros.
            categoria_riesgo_viento: La categoría de riesgo para la selección del mapa.
        """
        super().__init__()

        self._parametros = None

        self._combobox_mapa = QtWidgets.QComboBox()
        self._combobox_mapa.addItem("Cat. II (Figura 1.5-1A)", CategoriaEstructura.II)
        self._combobox_mapa.addItem(
            "Cat. III y IV (Figura 1.5-1B)", CategoriaEstructura.III
        )
        self._combobox_mapa.addItem("Cat. I (Figura 1.5-1C)", CategoriaEstructura.I)
        _idx = self._combobox_mapa.findData(categoria_riesgo_viento)
        if _idx >= 0:
            self._combobox_mapa.setCurrentIndex(_idx)

        self._combobox_exposicion = QtWidgets.QComboBox()
        for exp in CategoriaExposicion:
            self._combobox_exposicion.addItem(exp.value, exp)
        self._combobox_exposicion.setMinimumWidth(50)
        self._combobox_exposicion.setCurrentText(categoria_exp.value)

        datos_spinboxs = (
            ("velocidad", 20, 100, " m/s", 2, "Velocidad básica del viento."),
            (
                "altitud",
                0,
                5000,
                " m",
                0,
                "Altitud del terreno sobre el nivel del mar.",
            ),
            ("frecuencia", 0.1, 100, " Hz", 2, "Frecuencia natural de la estructura."),
            (
                "beta",
                0.01,
                0.05,
                None,
                3,
                "Relación de amortiguamiento β, expresada como porcentaje del crítico.",
            ),
        )
        self._spinboxs = {}
        for nombre, minimo, maximo, sufijo, precision, status_tip in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setSuffix(sufijo)
            spinbox.setDecimals(precision)
            spinbox.setStatusTip(status_tip)
            self._spinboxs[nombre] = spinbox

        self._spinboxs["velocidad"].setValue(velocidad)
        self._spinboxs["altitud"].setValue(altitud)
        self._spinboxs["frecuencia"].setValue(frecuencia)
        self._spinboxs["beta"].setValue(beta)

        self._editar_velocidad = QtWidgets.QCheckBox("Editar velocidad")
        self._editar_velocidad.setChecked(editar_velocidad)
        self._editar_velocidad.stateChanged.connect(
            self._habilitar_deshabilitar_velocidad
        )

        self._combobox_ciudades = QtWidgets.QComboBox()
        for opcion in CIUDADES_VELOCIDAD:
            self._combobox_ciudades.addItem(opcion)
        if ciudad in CIUDADES_VELOCIDAD:
            self._combobox_ciudades.setCurrentText(ciudad)
        else:
            self._combobox_ciudades.setCurrentText("Buenos Aires")

        self._combobox_ciudades.currentIndexChanged.connect(
            self._actualizar_velocidad_ciudad
        )
        self._combobox_mapa.currentIndexChanged.connect(self._actualizar_mapa)

        self._factor_g_simplificado = QtWidgets.QCheckBox(
            "Considerar Factor de Ráfaga igual a 0.85"
        )
        self._factor_g_simplificado.stateChanged.connect(
            lambda: self._habilitar_deshabilitar_widgets_rafaga(
                self._factor_g_simplificado.isChecked()
            )
        )

        self._combobox_flex = QtWidgets.QComboBox()
        for flex in Flexibilidad:
            self._combobox_flex.addItem(flex.value.capitalize(), flex)
        self._combobox_flex.setCurrentIndex(self._combobox_flex.findData(flexibilidad))

        self._imagen = QtWidgets.QLabel()
        self._imagen.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)

        self._label_ke = QtWidgets.QLabel()
        self._spinboxs["altitud"].valueChanged.connect(self._actualizar_ke)
        self._actualizar_ke()

        textos_rafaga = (
            "Flexibilidad",
            "Frecuencia Natural",
            "Relación de amortiguamiento",
        )

        self._grid_layout_viento = QtWidgets.QGridLayout()
        self._grid_layout_viento.addWidget(
            QtWidgets.QLabel("Mapa de Viento"), 0, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._grid_layout_viento.addWidget(self._combobox_mapa, 0, 1)
        self._grid_layout_viento.addWidget(
            QtWidgets.QLabel("Ciudad"), 1, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._grid_layout_viento.addWidget(self._combobox_ciudades, 1, 1)
        self._grid_layout_viento.addWidget(
            self._editar_velocidad, 2, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._grid_layout_viento.addWidget(self._spinboxs["velocidad"], 2, 1)
        self._grid_layout_viento.setColumnStretch(2, 1)

        grid_layout_altitud = QtWidgets.QGridLayout()
        grid_layout_altitud.addWidget(
            QtWidgets.QLabel("Altitud (zg)"), 0, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        grid_layout_altitud.addWidget(self._spinboxs["altitud"], 0, 1)
        grid_layout_altitud.addWidget(self._label_ke, 0, 2)
        grid_layout_altitud.setColumnStretch(3, 1)

        grid_layout_exposicion = QtWidgets.QGridLayout()
        grid_layout_exposicion.addWidget(
            QtWidgets.QLabel("Categoría de Exposición"),
            0,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        grid_layout_exposicion.addWidget(self._combobox_exposicion, 0, 1)
        grid_layout_exposicion.setColumnStretch(2, 1)

        self._grid_layout_rafaga = QtWidgets.QGridLayout()
        self._grid_layout_rafaga.addWidget(self._factor_g_simplificado, 0, 0, 1, 3)
        for i, texto in enumerate(textos_rafaga):
            self._grid_layout_rafaga.addWidget(
                QtWidgets.QLabel(texto), i + 1, 0, QtCore.Qt.AlignmentFlag.AlignRight
            )
        self._grid_layout_rafaga.addWidget(self._combobox_flex, 1, 1)
        self._grid_layout_rafaga.addWidget(self._spinboxs["frecuencia"], 2, 1)
        self._grid_layout_rafaga.addWidget(self._spinboxs["beta"], 3, 1)
        self._grid_layout_rafaga.setColumnStretch(2, 1)

        # Tiene que instanciarse el atributo del layout de ragafa
        self._factor_g_simplificado.setChecked(factor_g_simplificado)

        box_viento = QtWidgets.QGroupBox("Velocidad básica del viento (Art. 1.5)")
        box_viento.setLayout(self._grid_layout_viento)

        box_altitud = QtWidgets.QGroupBox("Factor de altitud Ke (Art. 1.12)")
        box_altitud.setLayout(grid_layout_altitud)

        box_exposicion = QtWidgets.QGroupBox("Exposición (Art. 1.7)")
        box_exposicion.setLayout(grid_layout_exposicion)

        box_rafaga = QtWidgets.QGroupBox("Factor de Ráfaga (Art. 1.9)")
        box_rafaga.setLayout(self._grid_layout_rafaga)

        layout_izquierda = QtWidgets.QVBoxLayout()
        layout_izquierda.addWidget(box_viento)
        layout_izquierda.addWidget(box_altitud)
        layout_izquierda.addWidget(box_exposicion)
        layout_izquierda.addWidget(box_rafaga)
        layout_izquierda.addStretch()

        layout_viento = QtWidgets.QHBoxLayout()
        layout_viento.addLayout(layout_izquierda)
        layout_viento.addWidget(self._imagen)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addLayout(layout_viento)
        layout_principal.addWidget(self._botones)

        self.setLayout(layout_principal)

        self._actualizar_mapa()
        self._habilitar_deshabilitar_velocidad()

        self.setWindowTitle("Parámetros de Viento")
        self.setFixedSize(self.sizeHint())

    def _actualizar_ke(self) -> None:
        """Actualiza la etiqueta con el valor de Ke correspondiente a la altitud."""
        altitud = self._spinboxs["altitud"].value()
        ke = factores.factor_altitud(altitud)
        self._label_ke.setText(f"<i>K<sub>e</sub></i> = {ke:.3f}")

    def _actualizar_mapa(self) -> None:
        """Actualiza la imagen del mapa según la categoría de riesgo seleccionada."""
        cat = self._combobox_mapa.currentData()
        if cat == CategoriaEstructura.I:
            clave = "imagenes/figura-1-5-1c.png"
            tooltip = "Figura 1.5-1C — CIRSOC 102 (Cat. de Riesgo I)"
        elif cat in (CategoriaEstructura.III, CategoriaEstructura.IV):
            clave = "imagenes/figura-1-5-1b.png"
            tooltip = "Figura 1.5-1B — CIRSOC 102 (Cat. de Riesgo III y IV)"
        else:
            clave = "imagenes/figura-1-5-1a.png"
            tooltip = "Figura 1.5-1A — CIRSOC 102 (Cat. de Riesgo II)"
        pixmap = recursos.pixmap(clave).scaledToHeight(
            540, QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self._imagen.setPixmap(pixmap)
        self._imagen.setToolTip(tooltip)
        self._actualizar_velocidad_ciudad()

    def _actualizar_velocidad_ciudad(self) -> None:
        """Actualiza la velocidad con el valor de la ciudad seleccionada si no está en modo edición."""
        if not self._editar_velocidad.isChecked():
            ciudad = self._combobox_ciudades.currentText()
            cat = self._combobox_mapa.currentData()
            if ciudad in CIUDADES_VELOCIDAD:
                velocidad = CIUDADES_VELOCIDAD[ciudad].get(cat, 55.1)
                self._spinboxs["velocidad"].setValue(velocidad)

    def _habilitar_deshabilitar_widgets_rafaga(self, estado: bool) -> None:
        """Habilita o deshabilita los widgets de frecuencia, beta y flexibilidad en base al estado del widget de
        factor_g_simplificado.

        Args:
            estado: El estado del widget de factor_g_simplificado.
        """
        for fila in range(1, 4):
            for columna in range(2):
                widget = utils_qt.widget_de_celda(
                    self._grid_layout_rafaga, fila, columna
                )
                widget.setEnabled(not estado)

    def _habilitar_deshabilitar_velocidad(self) -> None:
        """Habilita o deshabilita el widget encargado de setear la velocidad del viendo y su label."""
        estado = self._editar_velocidad.isChecked()
        self._spinboxs["velocidad"].setEnabled(estado)
        for fila in range(1, 2):
            for columna in range(2):
                widget = utils_qt.widget_de_celda(
                    self._grid_layout_viento, fila, columna
                )
                widget.setEnabled(not estado)
        if not estado:
            self._actualizar_velocidad_ciudad()

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
                    "Para que la estructura sea considerada flexible, la"
                    " frecuencia debe ser menor a 1 Hz."
                )

    def parametros(
        self,
    ) -> (
        dict[
            str,
            float
            | Flexibilidad
            | CategoriaExposicion
            | CategoriaEstructura
            | str
            | bool,
        ]
        | None
    ):
        """Determina los parámetros de viento.

        Returns:
            Los parámetros de viento.
        """
        return self._parametros

    def accept(self):
        try:
            self._validar()
            resultados_spinboxs = {
                key: spinbox.value() for key, spinbox in self._spinboxs.items()
            }
            self._parametros = {
                "factor_g_simplificado": self._factor_g_simplificado.isChecked(),
                "categoria_exp": self._combobox_exposicion.currentData(),
                "flexibilidad": self._combobox_flex.currentData(),
                "ciudad": self._combobox_ciudades.currentText(),
                "editar_velocidad": self._editar_velocidad.isChecked(),
                "categoria_riesgo_viento": self._combobox_mapa.currentData(),
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
        self._combobox_tipo_terreno.currentIndexChanged.connect(
            self._cambio_tipo_terreno
        )

        self._combobox_direccion = QtWidgets.QComboBox()
        for enum in DireccionTopografia:
            self._combobox_direccion.addItem(
                f"{enum.value.capitalize()} de la cresta", enum
            )
        self._combobox_direccion.setCurrentIndex(
            self._combobox_direccion.findData(direccion)
        )

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
        for nombre, minimo, maximo, default, sufijo, activado in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setValue(default)
            spinbox.setSuffix(sufijo)
            spinbox.setEnabled(activado)
            self._spinboxs[nombre] = spinbox

        self._spinboxs["distancia_cresta"].setValue(distancia_cresta)
        self._spinboxs["distancia_barlovento_sotavento"].setValue(
            distancia_barlovento_sotavento
        )
        self._spinboxs["altura_terreno"].setValue(altura_terreno)

        self._imagen = QtWidgets.QLabel()
        self._imagen.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)

        self._layout_principal = QtWidgets.QGridLayout()

        self._layout_principal.addWidget(
            QtWidgets.QLabel("Tipo de Terreno"),
            0,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self._layout_principal.addWidget(self._combobox_tipo_terreno, 0, 1)
        self._layout_principal.addWidget(
            QtWidgets.QLabel("Dirección"), 1, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._layout_principal.addWidget(self._combobox_tipo_terreno, 0, 1)
        self._layout_principal.addWidget(self._combobox_direccion, 1, 1)
        for i, (_nombre, widget) in enumerate(self._spinboxs.items()):
            self._layout_principal.addWidget(
                QtWidgets.QLabel(textos_spinboxs[i]),
                i + 2,
                0,
                QtCore.Qt.AlignmentFlag.AlignRight,
            )
            self._layout_principal.addWidget(widget, i + 2, 1)
        self._layout_principal.addWidget(
            QtWidgets.QLabel(
                "* Se condisera que se satisfacen los puntos 1, 2 y 3 "
                "del artículo 5.7.1."
            ),
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

    def parametros(
        self,
    ) -> dict[str, TipoTerrenoTopografia | DireccionTopografia | float | bool] | None:
        """Determina los parámetros de topografía.

        Returns:
            Los parámetros de topografía.
        """
        return self._parametros

    def accept(self):
        resultados_spinboxs = {
            key: spinbox.value() for key, spinbox in self._spinboxs.items()
        }
        self._parametros = {
            "considerar_topografia": self._considerar_topografia.isChecked(),
            "tipo_terreno": self._combobox_tipo_terreno.currentData(),
            "direccion": self._combobox_direccion.currentData(),
            **resultados_spinboxs,
        }
        super().accept()

    def _cambio_tipo_terreno(self):
        if (
            self._combobox_tipo_terreno.currentData()
            == TipoTerrenoTopografia.ESCARPA_BIDIMENSIONAL
        ):
            imagen = "escarpa.jpg"
        else:
            imagen = "loma.jpg"
        self._imagen.setPixmap(recursos.pixmap(f"imagenes/{imagen}"))


class DialogoComponentes(DialogoBase):
    """DialogoComponentes.

    Permite configurar los componentes y revestimientos para paredes y cubierta.
    """

    def __init__(self, componentes: dict[str, dict[str, float] | None]) -> None:
        """

        Args:
            componentes: Los componentes de paredes y cubierta.
        """
        super().__init__()

        self._componentes = componentes

        self._componentes_paredes = WidgetComponentes(
            componentes["componentes_paredes"]
        )
        self._componentes_cubierta = WidgetComponentes(
            componentes["componentes_cubierta"]
        )

        label_aviso_geometria = QtWidgets.QLabel(
            "* Dependiendo de la geometria de la estructura es posible que existan solapamientos en la visualizazión"
            " gráfica, ya que el reglamento especifica dimensiones mínimas para las áreas de presión."
        )
        label_aviso_geometria.setWordWrap(True)

        layout_componentes = QtWidgets.QGridLayout()
        layout_componentes.addWidget(
            QtWidgets.QLabel("PAREDES"), 0, 0, QtCore.Qt.AlignmentFlag.AlignCenter
        )
        layout_componentes.addWidget(
            QtWidgets.QLabel("CUBIERTA"), 0, 2, QtCore.Qt.AlignmentFlag.AlignCenter
        )
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

    def componentes(self) -> dict[str, dict[str, float] | None]:
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
            ("N/m\u00b2", "N"),
            ("kN/m\u00b2", "kN"),
            ("kG/m\u00b2", "kG"),
        )
        self._combobox_presiones = QtWidgets.QComboBox()
        for opcion, valor in presiones:
            self._combobox_presiones.addItem(opcion, userData=QtCore.QVariant(valor))
        self._combobox_presiones.setCurrentIndex(
            self._combobox_presiones.findData(presion)
        )

        layout_unidades = QtWidgets.QGridLayout()
        layout_unidades.addWidget(
            QtWidgets.QLabel("Presión"), 0, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout_unidades.addWidget(
            QtWidgets.QLabel("Fuerza"), 1, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout_unidades.addWidget(self._combobox_presiones, 0, 1)
        layout_unidades.addWidget(self._combobox_fuerzas, 1, 1)

        groupbox_unidades = QtWidgets.QGroupBox("Unidades")
        groupbox_unidades.setLayout(layout_unidades)

        botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(groupbox_unidades)
        layout_principal.addWidget(botones)

        self.setLayout(layout_principal)
        self.setWindowTitle("Configuración")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

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


class DialogoActualizacion(QtWidgets.QMessageBox):
    """Avisa que hay una versión nueva de Zonda y ofrece ir a descargarla.

    Es un ``QMessageBox`` y no un diálogo propio para que el aviso conserve el
    aspecto, los atajos y el manejo de foco nativos de cada sistema.

    El check de "no volver a avisarme" se anota por número de versión, no como
    un "nunca más": si el usuario decide saltear una versión, la siguiente
    vuelve a avisar.
    """

    def __init__(self, parent: QtWidgets.QWidget, actualizacion: Actualizacion):
        super().__init__(parent)

        self._actualizacion = actualizacion

        self.setIcon(QtWidgets.QMessageBox.Icon.Information)
        self.setWindowTitle("Hay una versión nueva de Zonda")
        self.setText(f"Ya está disponible Zonda {actualizacion.version}.")
        self.setInformativeText(
            f"Tenés instalada la versión {__acercade__.__version__}."
        )

        self._no_avisar = QtWidgets.QCheckBox(
            f"No volver a avisarme de la versión {actualizacion.version}"
        )
        self.setCheckBox(self._no_avisar)

        self._boton_descargar = self.addButton(
            "Ir a la descarga", QtWidgets.QMessageBox.ButtonRole.AcceptRole
        )
        self.addButton("Ahora no", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        self.setDefaultButton(self._boton_descargar)

        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self.finished.connect(self._resolver)
        self.show()

    def _resolver(self) -> None:
        if self._no_avisar.isChecked():
            actualizaciones.ignorar_version(self._actualizacion.version)

        if self.clickedButton() is self._boton_descargar:
            # Igual que en ``errores``: se lo pide al sistema operativo, que es
            # lo único que funciona en las tres plataformas.
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._actualizacion.url))
