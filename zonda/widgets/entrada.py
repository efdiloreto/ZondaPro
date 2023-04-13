from typing import Dict, Union, Optional, Tuple

from PyQt5 import QtWidgets, QtCore

from zonda import excepciones
from zonda.cirsoc import geometria
from zonda.enums import (
    CategoriaEstructura,
    TipoCubierta,
    Cerramiento,
    Estructura,
    MetodoSprfv,
    PosicionBloqueoCubierta,
    PosicionCamara,
)
from zonda.widgets.graficos import WidgetGraficoGeometria


class WidgetLineEditAlturasPersonalizadas(QtWidgets.QLineEdit):
    """LineEditAlturasPersonalizadas.

    Permite el ingreso de valores numericos separados por coma y devuelve una lista con estos valores.
    """

    def __init__(self):
        super().__init__()
        self.setToolTip('Ingrese los valores de altura separados por coma (",")')
        self.setStatusTip(
            "Las alturas personalizadas donde se calcularán las presiones."
        )

    def text(self):
        alturas_personalizadas = super().text()
        if alturas_personalizadas:
            try:
                alturas_personalizadas = [
                    float(altura) for altura in alturas_personalizadas.split(",")
                ]
            except (ValueError, TypeError) as error:
                raise excepciones.ErrorEstructura(
                    'Las alturas personalizadas deben ser valores numéricos separados por ","'
                ) from error
        return alturas_personalizadas


class WidgetCategoria(QtWidgets.QGroupBox):
    """WidgetCategoria.

    Permite la selección de la categoria de la estructura.
    """

    def __init__(self):
        super().__init__("Categoría")
        self._combobox = QtWidgets.QComboBox()
        for enum in CategoriaEstructura:
            self._combobox.addItem(enum.value, enum)
        self._combobox.setMinimumWidth(50)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Categoría de la Estructura"))
        layout.addWidget(self._combobox)
        layout.addStretch()

        self.setLayout(layout)

    def datos(self) -> CategoriaEstructura:
        return self._combobox.currentData()

    def __call__(self) -> CategoriaEstructura:
        return self.datos()


class WidgetComponentes(QtWidgets.QTableWidget):
    """WidgetComponentes

    Permite ingresar en una tabla los nombres de los componentes con su respectiva área.
    """

    def __init__(self, componentes: Optional[Dict[str, float]] = None):
        super().__init__()
        self.setColumnCount(2)
        self.setRowCount(30)
        self.verticalHeader().setDefaultSectionSize(22)
        self.verticalHeader().setVisible(False)
        self.setHorizontalHeaderLabels(("Descripción", "Área de influencia (m\u00B2)"))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for fila in range(self.rowCount()):
            for columna in range(self.columnCount()):
                self.setItem(fila, columna, QtWidgets.QTableWidgetItem())
        if componentes is not None:
            for i, (descripcion, area) in enumerate(componentes.items()):
                self.item(i, 0).setText(descripcion)
                self.item(i, 1).setText(str(area))

    def componentes(self) -> Union[None, Dict[str, float]]:
        """Obtiene los componentes con sus areas.

        Returns:
            Componente con su respectiva área.
        """
        componentes = {}
        for fila in range(self.rowCount()):
            nombre = self.item(fila, 0).text()
            area_str = self.item(fila, 1).text()
            if nombre:
                if nombre not in componentes:
                    try:
                        area = float(area_str)
                        if area <= 0:
                            raise ValueError(
                                "El valor de área debe ser un valor mayor o "
                                "igual que cero."
                            )
                        componentes[nombre] = float(self.item(fila, 1).text())
                    except ValueError as error:
                        raise excepciones.ErrorComponentes(
                            "El valor de área debe ser un valor numérico."
                        ) from error
                else:
                    raise excepciones.ErrorComponentes(
                        "Existen descripciones de componentes repetidas."
                    )
            elif not nombre and area_str:
                raise excepciones.ErrorComponentes(
                    "Existen componentes sin descripción."
                )
        return componentes or None

    def __call__(self) -> Union[None, Dict[str, float]]:
        return self.componentes()


class WidgetEstructuraBase(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

    def finalizar(self):
        self.grafico.finalizar()


class WidgetEstructuraEdificio(WidgetEstructuraBase):
    def __init__(self):
        super().__init__()

        self._volumen_usuario = None

        textos_geometria = (
            "Ancho",
            "Altura de Alero",
            "Altura de Cumbrera",
            "Longitud",
            "Elevación sobre el terreno",
        )

        self._combobox_tipo_cubierta = QtWidgets.QComboBox()
        for enum in TipoCubierta:
            self._combobox_tipo_cubierta.addItem(enum.value.title(), enum)
        self._combobox_tipo_cubierta.setCurrentText(
            TipoCubierta.DOS_AGUAS.value.title()
        )
        self._combobox_tipo_cubierta.currentTextChanged.connect(
            self._cambio_tipo_cubierta
        )

        datos_spinboxs = (
            ("ancho", 1, 300, 30, " m", True),
            ("altura_alero", 1, 300, 6, " m", True),
            ("altura_cumbrera", 1, 300, 16, " m", True),
            ("longitud", 1, 300, 60, " m", True),
            ("elevacion", 0, 200, 0, " m", True),
            ("alero", 0, 6, 0, " m", False),
            ("parapeto", 0, 6, 0, " m", False),
        )
        self._spinboxs = {}
        for nombre, minimo, maximo, default, sufijo, activado in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setValue(default)
            spinbox.setSuffix(sufijo)
            spinbox.setEnabled(activado)
            if nombre != "parapeto":
                spinbox.editingFinished.connect(self._generar_escena)
            self._spinboxs[nombre] = spinbox
        self._spinboxs["altura_alero"].editingFinished.connect(
            lambda: self._spinboxs["alero"].setMaximum(
                self._spinboxs["altura_alero"].value()
            )
        )

        self._checkbox_alero = QtWidgets.QCheckBox("Alero")
        self._checkbox_alero.setLayoutDirection(QtCore.Qt.RightToLeft)
        self._checkbox_alero.stateChanged.connect(self._spinboxs["alero"].setEnabled)
        self._checkbox_alero.stateChanged.connect(self._generar_escena)
        self._checkbox_parapeto = QtWidgets.QCheckBox("Parapeto")
        self._checkbox_parapeto.setLayoutDirection(QtCore.Qt.RightToLeft)
        self._checkbox_parapeto.stateChanged.connect(
            self._habilitar_deshabilitar_parapeto
        )

        self._mensaje_parapeto = QtWidgets.QErrorMessage()
        self._mensaje_parapeto.setWindowTitle("Aviso parapeto")
        self._mensaje_parapeto.setFixedWidth(350)
        self._mensaje_parapeto.setFixedHeight(250)

        self._alturas_personalizadas = WidgetLineEditAlturasPersonalizadas()

        self._categoria = WidgetCategoria()

        self._combobox_cerramiento = QtWidgets.QComboBox()
        for enum in (Cerramiento.CERRADO, Cerramiento.PARCIALMENTE_CERRADO):
            self._combobox_cerramiento.addItem(enum.value.title(), enum)

        boton_calcular_cerramiento = QtWidgets.QPushButton("Verificar")
        boton_calcular_cerramiento.clicked.connect(self._verificar_cerramiento)

        self._checkbox_unico_volumen = QtWidgets.QCheckBox(
            "El edificio es un único volumen sin particionar"
        )
        self._checkbox_unico_volumen.setStatusTip(
            "Si se activa, se adopta como volumen interno el volumen total del"
            " edificio."
        )
        self._checkbox_unico_volumen.stateChanged.connect(
            lambda: self._habilitar_deshabilitar_volumen(
                self._checkbox_unico_volumen.isChecked()
            )
        )

        texto_aberturas = ("Pared 1", "Pared 2", "Pared 3", "Pared 4", "Cubierta")

        self._spinboxs_aberturas = {
            key: QtWidgets.QDoubleSpinBox() for key in texto_aberturas
        }
        for spinbox in self._spinboxs_aberturas.values():
            spinbox.setMinimum(0)
            spinbox.setMaximum(100000000)
            spinbox.setValue(0)
            spinbox.setSuffix(" m2")
            spinbox.setMaximumWidth(100)

        self._spinbox_volumen = QtWidgets.QDoubleSpinBox()
        self._spinbox_volumen.setMinimum(1)
        self._spinbox_volumen.setMaximum(100000000)
        self._spinbox_volumen.setSuffix(" m3")
        self._spinbox_volumen.setFixedWidth(100)

        self._grid_layout_geometria = QtWidgets.QGridLayout()
        self._grid_layout_geometria.addWidget(
            QtWidgets.QLabel("Tipo de Cubierta"), 0, 0, QtCore.Qt.AlignRight
        )
        self._grid_layout_geometria.addWidget(self._combobox_tipo_cubierta, 0, 1)

        for i, texto in enumerate(textos_geometria):
            self._grid_layout_geometria.addWidget(
                QtWidgets.QLabel(texto), i + 1, 0, QtCore.Qt.AlignRight
            )

        for i, spinbox in enumerate(self._spinboxs.values()):
            self._grid_layout_geometria.addWidget(spinbox, i + 1, 1)

        self._grid_layout_geometria.addWidget(self._checkbox_alero, 6, 0)
        self._grid_layout_geometria.addWidget(self._checkbox_parapeto, 7, 0)
        self._grid_layout_geometria.addWidget(
            QtWidgets.QLabel("Personalizar Alturas"), 8, 0, QtCore.Qt.AlignRight
        )
        self._grid_layout_geometria.addWidget(self._alturas_personalizadas, 8, 1)

        layout_cerramiento = QtWidgets.QHBoxLayout()
        layout_cerramiento.addWidget(QtWidgets.QLabel("Clasificación"))
        layout_cerramiento.addWidget(self._combobox_cerramiento)
        layout_cerramiento.addWidget(boton_calcular_cerramiento)
        layout_cerramiento.addStretch()

        grid_layout_aberturas = QtWidgets.QGridLayout()
        coords_grid = ((0, 0), (0, 2), (1, 0), (1, 2), (2, 0))
        for (f, c), (key, spinbox) in zip(
            coords_grid, self._spinboxs_aberturas.items()
        ):
            grid_layout_aberturas.addWidget(
                QtWidgets.QLabel(key), f, c, QtCore.Qt.AlignRight
            )
            grid_layout_aberturas.addWidget(spinbox, f, c + 1)
        grid_layout_aberturas.setRowStretch(4, 1)
        grid_layout_aberturas.setColumnStretch(1, 1)

        box_aberturas = QtWidgets.QGroupBox("Aberturas")
        box_aberturas.setLayout(grid_layout_aberturas)

        self.grafico = WidgetGraficoGeometria(Estructura.EDIFICIO)
        self._generar_escena()

        self._grid_layout_reduccion_gcpi = QtWidgets.QGridLayout()
        self._grid_layout_reduccion_gcpi.addWidget(
            self._checkbox_unico_volumen, 0, 0, 1, 2
        )
        self._grid_layout_reduccion_gcpi.addWidget(
            QtWidgets.QLabel("Volumen interno no dividido, V<sub>i</sub>"), 1, 0
        )
        self._grid_layout_reduccion_gcpi.addWidget(
            self._spinbox_volumen, 1, 1, QtCore.Qt.AlignLeft
        )
        self._grid_layout_reduccion_gcpi.setColumnStretch(2, 1)
        self._grid_layout_reduccion_gcpi.setRowStretch(2, 1)

        box_estructura = QtWidgets.QGroupBox("Geometría")
        box_estructura.setLayout(self._grid_layout_geometria)

        self._box_reduccion_gcpi = QtWidgets.QGroupBox(
            "Considerar reducción de coeficiente de presión interna"
        )
        self._box_reduccion_gcpi.setLayout(self._grid_layout_reduccion_gcpi)
        self._box_reduccion_gcpi.setCheckable(True)
        self._box_reduccion_gcpi.setChecked(False)

        box_cerramiento = QtWidgets.QGroupBox("Cerramiento")
        box_cerramiento.setLayout(layout_cerramiento)

        layout_inputs = QtWidgets.QVBoxLayout()
        layout_inputs.addWidget(self._categoria)
        layout_inputs.addWidget(box_estructura)
        layout_inputs.addWidget(box_aberturas)
        layout_inputs.addWidget(box_cerramiento)
        layout_inputs.addWidget(self._box_reduccion_gcpi, 1)
        layout_inputs.setContentsMargins(11, 0, 11, 0)

        widget_input = QtWidgets.QWidget()
        widget_input.setLayout(layout_inputs)
        widget_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        layout_principal = QtWidgets.QHBoxLayout()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget_input)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(widget_input.sizeHint().width() + 20)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout_principal.addWidget(scroll_area)
        layout_principal.addWidget(self.grafico, 1)

        self.setLayout(layout_principal)

    def _cambio_tipo_cubierta(self) -> None:
        """Cambia el tipo de cubierta y actualiza widgets y el gráfico."""
        tipo_cubierta = self._combobox_tipo_cubierta.currentData()
        bool_cubierta = tipo_cubierta == TipoCubierta.PLANA
        self._grid_layout_geometria.itemAtPosition(3, 0).widget().setEnabled(
            not bool_cubierta
        )
        self._grid_layout_geometria.itemAtPosition(3, 1).widget().setEnabled(
            not bool_cubierta
        )
        self._generar_escena()

    def _habilitar_deshabilitar_parapeto(self, estado: bool) -> None:
        """Habilita o deshabilita el widget de parapeto.

        Args:
            estado: Indica el estado del checkbox de parapeto.
        """
        if self._checkbox_parapeto.isChecked():
            self._mensaje_parapeto.showMessage(
                "La altura del parapeto solo se utiliza para determinar los coeficientes"
                " de presión para componentes y revestimientos. Para determinar las"
                " presiones sobre el mismo se debe calcular como un cartel elevado"
                " a la altura deseada, tal y como se calcula en el ejemplo Nº3 de la"
                " Guía para el uso del Reglamento Argentino de acción del viento"
                " sobre las construcciones."
            )
        self._spinboxs["parapeto"].setEnabled(estado)

    def _habilitar_deshabilitar_volumen(self, estado: bool) -> None:
        """Habilita o deshabilita el widget de volumen.

        Args:
            estado: Indica el estado del checkbox de unico volumen.
        """
        for i in range(2):
            widget = self._grid_layout_reduccion_gcpi.itemAtPosition(1, i).widget()
            widget.setEnabled(not estado)
        if estado:
            self._volumen_usuario = self._spinbox_volumen.value()
            self.grafico.escena.director.volumen()
        else:
            self._spinbox_volumen.setValue(self._volumen_usuario)

    def _validar(self) -> bool:
        """Valida los datos ingresados."""
        tipo_cubierta = self._combobox_tipo_cubierta.currentData()
        spinbox_altura_alero = self._spinboxs["altura_alero"]
        spinbox_altura_cumbrera = self._spinboxs["altura_cumbrera"]
        spinbox_altura_alero.setStyleSheet("")
        spinbox_altura_cumbrera.setStyleSheet("")
        if tipo_cubierta != TipoCubierta.PLANA:
            if spinbox_altura_alero.value() >= spinbox_altura_cumbrera.value():
                spinbox_altura_alero.setStyleSheet(
                    """QDoubleSpinBox {
                        background-color:#ff6347;
                    }
                    """
                )
                QtWidgets.QToolTip.showText(
                    spinbox_altura_alero.mapToGlobal(QtCore.QPoint()),
                    "Invalid Input",
                )
                return False
        return True

    def parametros(self):
        if not self._validar():
            raise ValueError("Existen parámetros de entrada incorrectos.")
        resultados_spinboxs = {
            key: spinbox.value()
            for key, spinbox in self._spinboxs.items()
            if spinbox.isEnabled()
        }
        altura_cumbrera = resultados_spinboxs.pop(
            "altura_cumbrera", resultados_spinboxs["altura_alero"]
        )
        aberturas = tuple(
            spinbox.value() for spinbox in self._spinboxs_aberturas.values()
        )
        volumen_interno = self._spinbox_volumen.value()
        if (
            self._checkbox_unico_volumen.isChecked()
            or not self._box_reduccion_gcpi.isChecked()
        ):
            volumen_interno = None
        return dict(
            categoria=self._categoria(),
            tipo_cubierta=self._combobox_tipo_cubierta.currentData(),
            alturas_personalizadas=self._alturas_personalizadas.text() or None,
            cerramiento=self._combobox_cerramiento.currentData(),
            reducir_gcpi=self._box_reduccion_gcpi.isChecked(),
            aberturas=aberturas,
            volumen_interno=volumen_interno,
            metodo_sprfv=MetodoSprfv.DIRECCIONAL,
            altura_cumbrera=altura_cumbrera,
            **resultados_spinboxs,
        )

    def _generar_escena(self):
        if self._validar():
            altura_cumbrera = self._spinboxs["altura_cumbrera"].value()
            altura_alero = self._spinboxs["altura_alero"].value()
            ancho = self._spinboxs["ancho"].value()
            longitud = self._spinboxs["longitud"].value()
            tipo_cubierta = self._combobox_tipo_cubierta.currentData()
            elevacion = self._spinboxs["elevacion"].value()
            alero = 0
            if self._checkbox_alero.isChecked():
                alero = self._spinboxs["alero"].value()
            self.grafico.escena.generar(
                ancho,
                longitud,
                altura_alero,
                altura_cumbrera,
                tipo_cubierta,
                alero,
                elevacion,
            )
            self._spinbox_volumen.setValue(self.grafico.escena.director.volumen())

    def _verificar_cerramiento(self):
        """Verifica el cerramiento del edificio.

        Visualiza un widget con los resultados de cerramiento en base a los valores de aberturas ingresados y a la geometría
        del edificio.
        """
        resultados_spinboxs = {
            key: self._spinboxs[key].value()
            for key in (
                "ancho",
                "longitud",
                "elevacion",
                "altura_alero",
                "altura_cumbrera",
            )
        }
        tipo_cubierta = self._combobox_tipo_cubierta.currentData()
        aberturas = tuple(
            spinbox.value() for spinbox in self._spinboxs_aberturas.values()
        )
        self.resultados_cerramiento = WidgetCerramientoEdificio(
            self,
            tipo_cubierta=tipo_cubierta,
            aberturas=aberturas,
            **resultados_spinboxs,
        )


class WidgetCerramientoEdificio(QtWidgets.QWidget):
    """WidgetCerramientoEdificio.

    Visualiza los resultados de la verificación de cerramiento del edificio.
    """

    def __init__(
        self,
        parent: WidgetEstructuraEdificio,
        ancho: float,
        longitud: float,
        elevacion: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        aberturas: Tuple[float, float, float, float, float],
        **kwargs,
    ) -> None:
        """

        Args:
            parent: El widget parent.
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            elevacion: La altura desde el suelo desde donde se consideran las presiones del viento sobre el edificio.
            altura_alero: La altura de alero de la cubierta, medida desde el nivel de suelo.
            altura_cumbrera: La altura de cumbrera de la cubierta, medida desde el nivel de suelo.
            tipo_cubierta: El tipo de cubierta.
            aberturas: Las aberturas del edificio para cada pared y cubierta.
        """
        super().__init__(parent=parent)

        edificio = geometria.Edificio(
            ancho,
            longitud,
            elevacion,
            altura_alero,
            altura_cumbrera,
            tipo_cubierta,
            aberturas=aberturas,
        )
        layout_principal = QtWidgets.QVBoxLayout()

        es_abierto = all(edificio.cerramiento_condicion_1)

        for i in range(4):
            grid_layout = QtWidgets.QGridLayout()
            grid_layout.setColumnStretch(4, 1)

            grid_layout.setHorizontalSpacing(20)
            grid_layout.setVerticalSpacing(10)
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    f"<b>Pared {i + 1} recibiendo presion externa positiva</b>"
                ),
                0,
                0,
                1,
                5,
                QtCore.Qt.AlignCenter,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel("A<sub>0</sub> ≥ 0.8 x A<sub>g</sub>"),
                1,
                0,
                QtCore.Qt.AlignRight,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    f"{edificio.aberturas[0]:.2f} m<sup>2</sup> ≥ 0.8 x {edificio.areas[0]:.2f} m<sup>2</sup>"
                ),
                1,
                2,
            )
            grid_layout.addWidget(
                self._label_estado(edificio.cerramiento_condicion_1[i]),
                1,
                3,
                QtCore.Qt.AlignCenter,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel("A<sub>0</sub> > 1.10 x A<sub>0i</sub>"),
                2,
                0,
                QtCore.Qt.AlignRight,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    f"{edificio.aberturas[0]:.2f} m<sup>2</sup> ≥ 1.10 x {edificio.a0i[0]:.2f} m<sup>2</sup>"
                ),
                2,
                2,
            )
            grid_layout.addWidget(
                self._label_estado(edificio.cerramiento_condicion_2[i]),
                2,
                3,
                QtCore.Qt.AlignCenter,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    "A<sub>0</sub> > min(0.4 m<sup>2</sup>, 0.01 x A<sub>g</sub>)"
                ),
                3,
                0,
                QtCore.Qt.AlignRight,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    f"{edificio.aberturas[0]:.2f} m<sup>2</sup> > {edificio.min_areas[0]:.2f} m<sup>2</sup>"
                ),
                3,
                2,
            )
            grid_layout.addWidget(
                self._label_estado(edificio.cerramiento_condicion_3[i]),
                3,
                3,
                QtCore.Qt.AlignCenter,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel("A<sub>0i</sub> / A<sub>gi</sub> ≤ 0.2"),
                4,
                0,
                QtCore.Qt.AlignRight,
            )
            grid_layout.addWidget(
                QtWidgets.QLabel(
                    f"{edificio.a0i[0]:.2f} m<sup>2</sup> / {edificio.agi[0]:.2f} m<sup>2</sup> ≤ 0.2"
                ),
                4,
                2,
            )
            grid_layout.addWidget(
                self._label_estado(edificio.cerramiento_condicion_4[i]),
                4,
                3,
                QtCore.Qt.AlignCenter,
            )

            for j in range(1, 5):
                grid_layout.addWidget(
                    QtWidgets.QLabel("="), j, 1, QtCore.Qt.AlignCenter
                )

            if es_abierto:
                cerramiento = "Edificio Abierto"
            elif (
                edificio.cerramiento_condicion_2[i]
                and edificio.cerramiento_condicion_3[i]
                and edificio.cerramiento_condicion_4[i]
            ):
                cerramiento = "Edificio Parcialmente Cerrado"
            else:
                cerramiento = "Edificio Cerrado"

            label = QtWidgets.QLabel(f"<h4>{cerramiento}</h4>")
            label.setStyleSheet("color: #4d4d4d;")

            grid_layout.addWidget(label, 1, 4, 4, 1, QtCore.Qt.AlignCenter)

            layout_principal.addLayout(grid_layout)
            layout_principal.setSpacing(30)

        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setLayout(layout_principal)
        self.setWindowTitle("Verificación de cerramiento")
        self.setFixedSize(self.sizeHint())
        self.show()

    @staticmethod
    def _label_estado(estado):
        if estado:
            texto = "✔"
            clase = "verifica"
        else:
            texto = "X"
            clase = "noverifica"

        label = QtWidgets.QLabel(texto)
        label.setProperty("class", clase)
        return label


class WidgetEstructuraCubiertaAislada(WidgetEstructuraBase):
    def __init__(self):
        super().__init__()

        textos_geometria = (
            "Ancho",
            "Altura de Alero",
            "Altura de Cumbrera",
            "Altura de Bloqueo",
            "Longitud",
        )

        self._combobox_tipo_cubierta = QtWidgets.QComboBox()
        for enum in (TipoCubierta.DOS_AGUAS, TipoCubierta.UN_AGUA):
            self._combobox_tipo_cubierta.addItem(enum.value.title(), enum)
        self._combobox_tipo_cubierta.setCurrentText(
            TipoCubierta.DOS_AGUAS.value.title()
        )
        self._combobox_tipo_cubierta.currentTextChanged.connect(
            self._habilitar_deshabilitar_posicion_bloqueo
        )
        self._combobox_tipo_cubierta.currentTextChanged.connect(self._generar_escena)

        datos_spinboxs = (
            ("ancho", 1, 300, 30, " m"),
            ("altura_alero", 1, 200, 6, " m"),
            ("altura_cumbrera", 1, 200, 9, " m"),
            ("altura_bloqueo", 0, 300, 5, " m"),
            ("longitud", 1, 300, 60, " m"),
        )

        self._spinboxs = {}
        for nombre, minimo, maximo, default, sufijo in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setValue(default)
            spinbox.setSuffix(sufijo)
            spinbox.editingFinished.connect(self._generar_escena)
            self._spinboxs[nombre] = spinbox

        self._combobox_posicion_bloqueo = QtWidgets.QComboBox()
        for enum in PosicionBloqueoCubierta:
            self._combobox_posicion_bloqueo.addItem(enum.value.title(), enum)

        self._categoria = WidgetCategoria()

        self._grid_layout_geometria = QtWidgets.QGridLayout()

        self._grid_layout_geometria.addWidget(
            QtWidgets.QLabel("Tipo de Cubierta"), 0, 0, QtCore.Qt.AlignRight
        )
        self._grid_layout_geometria.addWidget(self._combobox_tipo_cubierta, 0, 1)

        for i, texto in enumerate(textos_geometria):
            self._grid_layout_geometria.addWidget(
                QtWidgets.QLabel(texto), i + 1, 0, QtCore.Qt.AlignRight
            )

        for i, spinbox in enumerate(self._spinboxs.values()):
            self._grid_layout_geometria.addWidget(spinbox, i + 1, 1)

        self._categoria = WidgetCategoria()

        self._spinbox_coeficiente_friccion = QtWidgets.QDoubleSpinBox()
        self._spinbox_coeficiente_friccion.setMinimum(0.001)
        self._spinbox_coeficiente_friccion.setMaximum(0.10)
        self._spinbox_coeficiente_friccion.setValue(0.02)

        self.grafico = WidgetGraficoGeometria(Estructura.CUBIERTA_AISLADA)
        self._generar_escena()

        self._grid_layout_geometria.addWidget(
            QtWidgets.QLabel("Posición del bloqueo"), 6, 0, QtCore.Qt.AlignRight
        )
        self._grid_layout_geometria.addWidget(self._combobox_posicion_bloqueo, 6, 1)
        self._grid_layout_geometria.setRowStretch(7, 1)

        layout_friccion = QtWidgets.QHBoxLayout()
        layout_friccion.addWidget(QtWidgets.QLabel("Coeficiente de Fricción"))
        layout_friccion.addWidget(self._spinbox_coeficiente_friccion)

        box_estructura = QtWidgets.QGroupBox("Geometría")
        box_estructura.setLayout(self._grid_layout_geometria)

        box_superficie = QtWidgets.QGroupBox("Superficie")
        box_superficie.setLayout(layout_friccion)

        layout_inputs = QtWidgets.QVBoxLayout()
        layout_inputs.addWidget(self._categoria)
        layout_inputs.addWidget(box_estructura)
        layout_inputs.addWidget(box_superficie)
        layout_inputs.addStretch()
        layout_inputs.setContentsMargins(11, 0, 11, 0)

        widget_input = QtWidgets.QWidget()
        widget_input.setLayout(layout_inputs)
        widget_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        layout_principal = QtWidgets.QHBoxLayout()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget_input)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(widget_input.sizeHint().width() + 20)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout_principal.addWidget(scroll_area)
        layout_principal.addWidget(self.grafico, 1)

        self.setLayout(layout_principal)
        self._habilitar_deshabilitar_posicion_bloqueo()

    def parametros(self):
        resultados_spinboxs = {
            key: spinbox.value()
            for key, spinbox in self._spinboxs.items()
            if spinbox.isEnabled()
        }
        return dict(
            categoria=self._categoria(),
            tipo_cubierta=self._combobox_tipo_cubierta.currentData(),
            posicion_bloqueo=self._combobox_posicion_bloqueo.currentData(),
            coeficiente_friccion=self._spinbox_coeficiente_friccion.value(),
            **resultados_spinboxs,
        )

    def _habilitar_deshabilitar_posicion_bloqueo(self) -> None:
        tipo_cubierta = self._combobox_tipo_cubierta.currentData()
        bool_cubierta = not tipo_cubierta == TipoCubierta.UN_AGUA
        self._grid_layout_geometria.itemAtPosition(6, 0).widget().setHidden(
            bool_cubierta
        )
        self._grid_layout_geometria.itemAtPosition(6, 1).widget().setHidden(
            bool_cubierta
        )

    def _generar_escena(self):
        altura_cumbrera = self._spinboxs["altura_cumbrera"].value()
        altura_alero = self._spinboxs["altura_alero"].value()
        ancho = self._spinboxs["ancho"].value()
        longitud = self._spinboxs["longitud"].value()
        tipo_cubierta = self._combobox_tipo_cubierta.currentData()
        posicion_bloqueo = self._combobox_posicion_bloqueo.currentData()
        self.grafico.escena.generar(
            ancho,
            longitud,
            altura_alero,
            altura_cumbrera,
            tipo_cubierta,
            posicion_bloqueo,
        )


class WidgetEstructuraCartel(WidgetEstructuraBase):
    def __init__(self):
        super().__init__()

        textos_geometria = (
            "Altura Superior",
            "Altura Inferior",
            "Ancho",
            "Profundidad",
        )

        datos_spinboxs = (
            ("altura_superior", 0.1, 300, 10, " m"),
            ("altura_inferior", 0, 200, 0, " m"),
            ("ancho", 0.1, 300, 5, " m"),
            ("profundidad", 0.1, 50, 1, " m"),
        )
        self._spinboxs = {}
        for nombre, minimo, maximo, default, sufijo in datos_spinboxs:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setMinimum(minimo)
            spinbox.setMaximum(maximo)
            spinbox.setValue(default)
            spinbox.setSuffix(sufijo)
            spinbox.editingFinished.connect(self._generar_escena)
            self._spinboxs[nombre] = spinbox

        self._alturas_personalizadas = WidgetLineEditAlturasPersonalizadas()

        self._categoria = WidgetCategoria()

        self._es_parapeto = QtWidgets.QCheckBox("Calcular como parapeto de edificio")
        self._es_parapeto.setToolTip(
            "Si se activa, se considera el parapeto actuando como un cartel a nivel de terreno."
        )

        grid_layout_geometria = QtWidgets.QGridLayout()

        grid_layout_geometria.addWidget(self._es_parapeto, 0, 0, 1, 2)

        for i, texto in enumerate(textos_geometria):
            grid_layout_geometria.addWidget(
                QtWidgets.QLabel(texto), i + 1, 0, QtCore.Qt.AlignRight
            )

        for i, spinbox in enumerate(self._spinboxs.values()):
            grid_layout_geometria.addWidget(spinbox, i + 1, 1)

        grid_layout_geometria.addWidget(QtWidgets.QLabel("Personalizar Alturas:"), 5, 0)
        grid_layout_geometria.addWidget(self._alturas_personalizadas, 6, 0, 1, 2)

        self.grafico = WidgetGraficoGeometria(Estructura.CARTEL)
        self._generar_escena()

        box_estructura = QtWidgets.QGroupBox("Geometría")
        box_estructura.setLayout(grid_layout_geometria)

        layout_inputs = QtWidgets.QVBoxLayout()
        layout_inputs.addWidget(self._categoria)
        layout_inputs.addWidget(box_estructura)
        layout_inputs.addStretch()
        layout_inputs.setContentsMargins(11, 0, 11, 0)

        widget_input = QtWidgets.QWidget()
        widget_input.setLayout(layout_inputs)
        widget_input.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        layout_principal = QtWidgets.QHBoxLayout()

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget_input)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(widget_input.sizeHint().width() + 20)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout_principal.addWidget(scroll_area)
        layout_principal.addWidget(self.grafico, 1)

        self.setLayout(layout_principal)

    def parametros(self):
        if not self._validar():
            raise ValueError("Existen parámetros de entrada incorrectos.")
        resultados_spinboxs = {
            key: spinbox.value()
            for key, spinbox in self._spinboxs.items()
            if spinbox.isEnabled()
        }
        return dict(
            categoria=self._categoria(),
            alturas_personalizadas=self._alturas_personalizadas.text() or None,
            es_parapeto=self._es_parapeto.isChecked(),
            **resultados_spinboxs,
        )

    def _validar(self) -> bool:
        """Valida los datos ingresados."""
        spinbox_altura_superior = self._spinboxs["altura_superior"]
        spinbox_altura_inferior = self._spinboxs["altura_inferior"]
        spinbox_altura_inferior.setStyleSheet("")
        spinbox_altura_superior.setStyleSheet("")
        if spinbox_altura_inferior.value() >= spinbox_altura_superior.value():
            spinbox_altura_inferior.setStyleSheet(
                """QDoubleSpinBox {
                    background-color:#ff6347;
                }
                """
            )
            QtWidgets.QToolTip.showText(
                spinbox_altura_inferior.mapToGlobal(QtCore.QPoint()),
                "Invalid Input",
            )
            return False
        return True

    def _generar_escena(self):
        if self._validar():
            altura_inferior = self._spinboxs["altura_inferior"].value()
            altura_superior = self._spinboxs["altura_superior"].value()
            ancho = self._spinboxs["ancho"].value()
            profundidad = self._spinboxs["profundidad"].value()
            self.grafico.escena.generar(
                ancho,
                profundidad,
                altura_inferior,
                altura_superior,
                posicion_camara=PosicionCamara.FRENTE,
            )
