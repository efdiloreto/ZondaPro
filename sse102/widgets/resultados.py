"""Contiene clases que representan los resultados para las diferentes estructuras. Estas estan compuestas por el widget
gráfico y otros widgets que permiten interactuar con el mismo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import qApp

from sse102.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    TipoCubierta,
    TipoPresionCubiertaBarloventoSprfv,
    PosicionCubiertaAleroSprfv,
    SistemaResistente,
    TipoPresionComponentesParedesCubierta,
    TipoPresionCubiertaAislada,
    ExtremoPresion,
)
from sse102.excepciones import ErrorLineamientos
from sse102.sistema import guardar_archivo_temporal
from sse102.widgets.custom import WidgetPanelResultados
from sse102.widgets.errores import AvisoError
from sse102.widgets.graficos import (
    WidgetGraficoEdificioPresiones,
    WidgetGraficoCubiertaAisladaPresiones,
    WidgetGraficoCartelPresiones,
)
from sse102.widgets.reportes import WidgetReporte

if TYPE_CHECKING:
    from sse102.cirsoc import Edificio, CubiertaAislada, Cartel


class WidgetResultadosMixin:
    def _reporte(self):
        try:
            qApp.setOverrideCursor(QtCore.Qt.WaitCursor)
            WidgetReporte(self, self.plantilla_reporte, self._estructura)
        except OSError:
            AvisoError(
                self,
                "No se pudo visualizar el reporte. Aseguresé que Pandoc está instalado y agregado al PATH del sistema",
                "Error Reporte",
            )
        except RuntimeError as e:
            ruta_archivo_temp = guardar_archivo_temporal(str(e), ".log")
            AvisoError(
                self,
                "No se pudo visualizar el reporte. Para mas información consulte el archivo de registro de errores.",
                "Error Reporte",
                ruta_archivo_temp,
            )
        finally:
            qApp.restoreOverrideCursor()

    def _volver(self):
        self.parentWidget().setCurrentIndex(0)

    def finalizar(self) -> None:
        self.grafico.finalizar()


class WidgetResultadosEdificioSprfvMetodoDireccional(QtWidgets.QWidget):
    """WidgetResultadosEdificioSprfvMetodoDireccional.

    Representa el widget que visualiza los resultados para el SPRFV de un edificio. Presenta el gráfico junto con otros
    widgets que interactuan con este para cambiar la dirección del viento, entre otras opciones.
    """

    def __init__(self, edificio: Edificio) -> None:
        """

        Args:
            edificio: Una instancia de Edificio.
        """
        super().__init__()

        self.grafico = WidgetGraficoEdificioPresiones(edificio, SistemaResistente.SPRFV)

        self._combobox_gcpi = QtWidgets.QComboBox()
        self._combobox_gcpi.addItems(("+GCpi", "-GCpi"))
        self._combobox_gcpi.currentIndexChanged.connect(self.grafico.escena.actualizar_gcpi)
        self._combobox_gcpi.currentIndexChanged.connect(self._actualizar_combobox_alturas)

        self._combobox_direccion = QtWidgets.QComboBox()
        for enum in DireccionVientoMetodoDireccionalSprfv:
            self._combobox_direccion.addItem(f"{enum.value.capitalize()} a la Cumbrera", enum)
        self._combobox_direccion.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_direccion_viento(self._combobox_direccion.currentData())
        )
        self._combobox_direccion.currentIndexChanged.connect(self._actualizar_direccion_viento)
        self._combobox_direccion.currentIndexChanged.connect(self._actualizar_combobox_alturas)

        self._layout_parametros = QtWidgets.QGridLayout()

        self._layout_parametros.addWidget(QtWidgets.QLabel("Presión Interna"), 0, 0, QtCore.Qt.AlignRight)
        self._layout_parametros.addWidget(self._combobox_gcpi, 0, 1)

        self._layout_parametros.addWidget(QtWidgets.QLabel("Dirección del Viento"), 1, 0, QtCore.Qt.AlignRight)
        self._layout_parametros.addWidget(self._combobox_direccion, 1, 1)

        if edificio.geometria.tipo_cubierta in (TipoCubierta.DOS_AGUAS, TipoCubierta.UN_AGUA):
            if not edificio.cp.cubierta.sprfv.normal_como_paralelo:

                self._combobox_presion_cubierta_inclinada = QtWidgets.QComboBox()
                for enum in TipoPresionCubiertaBarloventoSprfv:
                    self._combobox_presion_cubierta_inclinada.addItem(enum.value.capitalize(), enum)
                self._combobox_presion_cubierta_inclinada.currentTextChanged.connect(
                    lambda: self.grafico.escena.actualizar_presion_cubierta_inclinada(
                        self._combobox_presion_cubierta_inclinada.currentData()
                    )
                )
                numero_filas = self._layout_parametros.rowCount()
                self._layout_parametros.addWidget(QtWidgets.QLabel("Presión Cubierta Barlovento"), numero_filas, 0)
                self._layout_parametros.addWidget(self._combobox_presion_cubierta_inclinada, numero_filas, 1)

            if edificio.geometria.tipo_cubierta == TipoCubierta.UN_AGUA:

                self._combobox_posicion_cubierta_un_agua = QtWidgets.QComboBox()
                for enum in PosicionCubiertaAleroSprfv:
                    self._combobox_posicion_cubierta_un_agua.addItem(enum.value.capitalize(), enum)
                self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(
                    lambda: self.grafico.escena.actualizar_posicion_cubierta_un_agua(
                        self._combobox_posicion_cubierta_un_agua.currentData()
                    )
                )
                self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(self._actualizar_combobox_alturas)
                self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(self._actualizar_direccion_viento)
                numero_filas = self._layout_parametros.rowCount()
                self._layout_parametros.addWidget(
                    QtWidgets.QLabel("Posición Cubierta"), numero_filas, 0, QtCore.Qt.AlignRight
                )
                self._layout_parametros.addWidget(self._combobox_posicion_cubierta_un_agua, numero_filas, 1)

        self._combobox_alturas_barlovento = QtWidgets.QComboBox()
        self._combobox_alturas_barlovento.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_altura_pared_barlovento(
                self._combobox_alturas_barlovento.currentData()
            )
        )

        numero_filas = self._layout_parametros.rowCount()
        self._layout_parametros.addWidget(
            QtWidgets.QLabel("Altura Pared Barlovento"),
            numero_filas,
            0,
            QtCore.Qt.AlignRight,
        )
        self._layout_parametros.addWidget(self._combobox_alturas_barlovento, numero_filas, 1)

        self._layout_parametros.setRowStretch(self._layout_parametros.rowCount(), 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")

        box_parametros.setLayout(self._layout_parametros)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(box_parametros)
        layout_principal.addStretch()
        layout_principal.addWidget(self.grafico, 1)

        # Se inicializa con la dirección actual (paralelo)
        self.grafico.escena.actualizar_direccion_viento(self._combobox_direccion.currentData())

        # Los widgets correspondientes empiezan desactivados para la direccion actual (paralelo)
        self._actualizar_direccion_viento()
        self._actualizar_combobox_alturas()

        self.setLayout(layout_principal)

    def _actualizar_combobox_alturas(self) -> None:
        """Actualiza el combobox de alturas de pared barlovento.

        El indice del combobox es forzado a actualizarse cada vez que el metodo es llamado, independientemente de si
        mantiene el mismo valor. Esto hace que por ejemplo, para casos donde hay que cambiar la presion interna de la
        pared, se actualize para la nueva presión usando la misma altura.
        """

        direccion = self._combobox_direccion.currentData()
        if direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            alturas = self.grafico.escena.alturas_presiones_lateral
        else:
            alturas = self.grafico.escena.alturas_presiones_frente
        altura_actual = self.grafico.escena.alturas_presion_barlovento[direccion]
        combobox_posicion_cubierta = getattr(self, "_combobox_posicion_cubierta_un_agua", None)
        if combobox_posicion_cubierta is not None and direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            posicion_cubierta = combobox_posicion_cubierta.currentData()
            if posicion_cubierta == PosicionCubiertaAleroSprfv.SOTAVENTO:
                alturas = self.grafico.escena.alturas_presiones_frente
            else:
                alturas = self.grafico.escena.alturas_presiones_lateral
            altura_actual = altura_actual[posicion_cubierta]

        self._combobox_alturas_barlovento.blockSignals(True)
        self._combobox_alturas_barlovento.setCurrentIndex(-1)

        # Define si hay que actualizar los elementos del combobox
        if self._combobox_alturas_barlovento.count() != len(alturas):
            self._combobox_alturas_barlovento.clear()
            for altura in alturas:
                self._combobox_alturas_barlovento.addItem(f"{altura:.2f} m", altura)
        indice = self._combobox_alturas_barlovento.findData(altura_actual)
        self._combobox_alturas_barlovento.blockSignals(False)
        self._combobox_alturas_barlovento.setCurrentIndex(indice)

    def _actualizar_direccion_viento(self) -> None:
        """Activa o desactiva los widgets que solo son utilizados cuando la direccion del viento es normal a la cumbrera."""
        bool_direccion = self._combobox_direccion.currentData() == DireccionVientoMetodoDireccionalSprfv.NORMAL

        combobox_caso_cubierta_inclinada = getattr(self, "_combobox_presion_cubierta_inclinada", None)
        combobox_posicion_cubierta_un_agua = getattr(self, "_combobox_posicion_cubierta_un_agua", None)
        for widget in (combobox_caso_cubierta_inclinada, combobox_posicion_cubierta_un_agua):
            if widget is not None:
                indice = self._layout_parametros.indexOf(widget)
                if (
                    widget is combobox_caso_cubierta_inclinada
                    and combobox_posicion_cubierta_un_agua is not None
                    and bool_direccion
                ):
                    posicion_cubierta_un_agua = combobox_posicion_cubierta_un_agua.currentData()
                    bool_visualizar = posicion_cubierta_un_agua == PosicionCubiertaAleroSprfv.BARLOVENTO
                else:
                    bool_visualizar = bool_direccion
                widget.setEnabled(bool_visualizar)
                self._layout_parametros.itemAt(indice - 1).widget().setEnabled(bool_visualizar)


class WidgetResultadosEdificioComponentes(QtWidgets.QWidget):
    """WidgetResultadosEdificioComponentes.

    Representa el widget que visualiza los resultados para los componentes de un edificio. Presenta el gráfico junto con
    otros widgets que interactuan con este para cambiar la dirección del viento, entre otras opciones.
    """

    def __init__(self, edificio: Edificio) -> None:
        """

        Args:
            edificio: Una instancia de Edificio.
        """
        super().__init__()

        self.grafico = WidgetGraficoEdificioPresiones(edificio, SistemaResistente.COMPONENTES)

        self._layout_parametros = QtWidgets.QGridLayout()

        self._combobox_gcpi = QtWidgets.QComboBox()
        self._combobox_gcpi.addItems(("+GCpi", "-GCpi"))
        self._combobox_gcpi.currentIndexChanged.connect(self.grafico.escena.actualizar_gcpi)

        self._layout_parametros.addWidget(QtWidgets.QLabel("Presión Interna"), 0, 0, QtCore.Qt.AlignRight)
        self._layout_parametros.addWidget(self._combobox_gcpi, 0, 1)

        self._combobox_presion_componentes = QtWidgets.QComboBox()
        for enum in TipoPresionComponentesParedesCubierta:
            self._combobox_presion_componentes.addItem(enum.value.capitalize(), enum)
        self._combobox_presion_componentes.currentTextChanged.connect(
            lambda: self.grafico.escena.actualizar_tipo_presion(self._combobox_presion_componentes.currentData())
        )

        self._layout_parametros.addWidget(QtWidgets.QLabel("Presión"), 1, 0, QtCore.Qt.AlignRight)
        self._layout_parametros.addWidget(self._combobox_presion_componentes, 1, 1)

        if edificio.componentes_cubierta is not None:
            self._combobox_componentes_cubierta = QtWidgets.QComboBox()
            self._combobox_componentes_cubierta.addItems(edificio.componentes_cubierta.keys())
            self._combobox_componentes_cubierta.currentTextChanged.connect(
                self.grafico.escena.actualizar_componente_cubierta
            )
            self._layout_parametros.addWidget(QtWidgets.QLabel("Componente Cubierta"), 2, 0, QtCore.Qt.AlignRight)
            self._layout_parametros.addWidget(self._combobox_componentes_cubierta, 2, 1)

        if edificio.componentes_paredes is not None:
            numero_filas = self._layout_parametros.rowCount()

            self._combobox_componentes_paredes = QtWidgets.QComboBox()
            self._combobox_componentes_paredes.addItems(edificio.componentes_paredes.keys())
            self._combobox_componentes_paredes.currentTextChanged.connect(
                self.grafico.escena.actualizar_componente_pared
            )

            self._layout_parametros.addWidget(
                QtWidgets.QLabel("Componente Pared"), numero_filas, 0, QtCore.Qt.AlignRight
            )
            self._layout_parametros.addWidget(self._combobox_componentes_paredes, numero_filas, 1)

            if edificio.cp.paredes.componentes.referencia == "Figura 8":
                self._combobox_alturas_barlovento = QtWidgets.QComboBox()
                for altura in edificio.geometria.alturas:
                    self._combobox_alturas_barlovento.addItem(f"{altura} m", altura)
                self._combobox_alturas_barlovento.setCurrentIndex(self._combobox_alturas_barlovento.count() - 1)
                self._combobox_alturas_barlovento.currentTextChanged.connect(self._actualizar_altura_pared_barlovento)

                self._layout_parametros.addWidget(
                    QtWidgets.QLabel("Altura Pared Barlovento"),
                    numero_filas + 1,
                    0,
                    QtCore.Qt.AlignRight,
                )
                self._layout_parametros.addWidget(self._combobox_alturas_barlovento, numero_filas + 1, 1)

                self._combobox_presion_componentes.currentTextChanged.connect(self._actualizar_altura_pared_barlovento)
                self._combobox_gcpi.currentTextChanged.connect(self._actualizar_altura_pared_barlovento)
                self._combobox_componentes_paredes.currentTextChanged.connect(self._actualizar_altura_pared_barlovento)

        numero_filas = self._layout_parametros.rowCount()
        self._layout_parametros.setRowStretch(numero_filas, 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")
        box_parametros.setAlignment(QtCore.Qt.AlignCenter)

        box_parametros.setLayout(self._layout_parametros)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(box_parametros)
        layout_principal.addStretch()
        layout_principal.addWidget(self.grafico, 1)

        if hasattr(self, "_combobox_componentes_paredes"):
            self.grafico.escena.actualizar_componente_pared(self._combobox_componentes_paredes.currentText())
            if hasattr(self, "_combobox_alturas_barlovento"):
                self._actualizar_altura_pared_barlovento()

        if hasattr(self, "_combobox_componentes_cubierta"):
            self.grafico.escena.actualizar_componente_cubierta(self._combobox_componentes_cubierta.currentText())

        self.setLayout(layout_principal)

    def _actualizar_altura_pared_barlovento(self) -> None:
        """Actualiza la altura a la que se calcula la presion de la pared barlovento. Solo es válido para la Figura 8 del
        Reglamento.
        """
        self.grafico.escena.actualizar_altura_pared_barlovento(self._combobox_alturas_barlovento.currentData())


class WidgetResultadosEdificio(QtWidgets.QWidget, WidgetResultadosMixin):

    plantilla_reporte = "edificio.md"

    def __init__(self, edificio):
        super().__init__()

        self._estructura = edificio

        self._stacked_widget = QtWidgets.QStackedWidget()

        widget_resultados_sprfv = WidgetResultadosEdificioSprfvMetodoDireccional(edificio)
        self._stacked_widget.addWidget(widget_resultados_sprfv)

        widget_panel_resultados = WidgetPanelResultados(edificio=True)

        widget_panel_resultados.boton_volver.clicked.connect(self._volver)
        widget_panel_resultados.boton_sprfv.clicked.connect(lambda: self._stacked_widget.setCurrentIndex(0))
        widget_panel_resultados.boton_generar_reporte.clicked.connect(self._reporte)

        if any((edificio.componentes_paredes, edificio.componentes_cubierta)):
            try:
                # Se verifica que la referencia del código exista
                widget_resultados_componentes = WidgetResultadosEdificioComponentes(self._estructura)
                self._stacked_widget.addWidget(widget_resultados_componentes)
                widget_panel_resultados.boton_componentes.setEnabled(True)
                widget_panel_resultados.boton_componentes.clicked.connect(
                    lambda: self._stacked_widget.setCurrentIndex(1)
                )
            except ErrorLineamientos as error:
                mensaje = (
                    str(error)
                    + " No se pudieron determinar las presiones sobre los componentes.\n\n Verifique la geometría o elimine los componentes necesarios."
                )
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle("Advertencia Lineamientos")
                msg.setText(mensaje)
                msg.exec_()

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(widget_panel_resultados)
        layout_principal.addWidget(self._stacked_widget, 1)

        self.setLayout(layout_principal)

    def finalizar(self) -> None:
        for i in range(self._stacked_widget.count()):
            widget = self._stacked_widget.widget(i)
            widget.grafico.finalizar()


class WidgetResultadosCubiertaAislada(QtWidgets.QWidget, WidgetResultadosMixin):
    """WidgetResultadosCubiertaAislada.

    Representa el widget que visualiza los resultados para cubiertas aisladas. Presenta el gráfico junto con otros
    widgets que interactuan con este para cambiar el tipo de presión, entre otras opciones.
    """

    plantilla_reporte = "cubierta-aislada.md"

    def __init__(self, cubierta_aislada: CubiertaAislada) -> None:
        """

        Args:
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__()

        self._estructura = cubierta_aislada

        self.grafico = WidgetGraficoCubiertaAisladaPresiones(cubierta_aislada)

        widget_panel_resultados = WidgetPanelResultados()

        widget_panel_resultados.boton_volver.clicked.connect(self._volver)
        widget_panel_resultados.boton_generar_reporte.clicked.connect(self._reporte)

        combobox_tipo_presion = QtWidgets.QComboBox()
        for enum in TipoPresionCubiertaAislada:
            combobox_tipo_presion.addItem(enum.value.title(), enum)
        combobox_tipo_presion.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_tipo_presion(combobox_tipo_presion.currentData())
        )

        combobox_extremo_presion = QtWidgets.QComboBox()
        for enum in ExtremoPresion:
            combobox_extremo_presion.addItem(enum.value.title(), enum)
        combobox_extremo_presion.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_extremo_presion(combobox_extremo_presion.currentData())
        )

        layout_parametros = QtWidgets.QGridLayout()

        layout_parametros.addWidget(QtWidgets.QLabel("Presión"), 0, 0)
        layout_parametros.addWidget(combobox_tipo_presion, 0, 1)
        layout_parametros.addWidget(combobox_extremo_presion, 0, 2)
        layout_parametros.setRowStretch(1, 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")
        box_parametros.setLayout(layout_parametros)

        layout_resultados = QtWidgets.QHBoxLayout()
        layout_resultados.setContentsMargins(11, 11, 11, 11)
        layout_resultados.addWidget(box_parametros)
        layout_resultados.addStretch()
        layout_resultados.addWidget(self.grafico, 1)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(widget_panel_resultados)
        layout_principal.addLayout(layout_resultados, 1)

        self.grafico.escena.actualizar_tipo_presion(combobox_tipo_presion.currentData())

        self.setLayout(layout_principal)


class WidgetResultadosCartel(QtWidgets.QWidget, WidgetResultadosMixin):
    """WidgetResultadosCartel.

    Representa el widget que visualiza los resultados para carteles. Presenta el gráfico junto con otros
    widgets que interactuan con este para la altura de presión.
    """

    plantilla_reporte = "cartel.md"

    def __init__(self, cartel: Cartel) -> None:
        """

        Args:
            cartel: Una instancia de CubiertaAislada.
        """
        super().__init__()

        self._estructura = cartel

        self.grafico = WidgetGraficoCartelPresiones(cartel)

        widget_panel_resultados = WidgetPanelResultados()

        widget_panel_resultados.boton_volver.clicked.connect(self._volver)
        widget_panel_resultados.boton_generar_reporte.clicked.connect(self._reporte)

        combobox_altura = QtWidgets.QComboBox()
        for altura in cartel.geometria.alturas:
            combobox_altura.addItem(f"{altura:.2f} m", altura)
        combobox_altura.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_altura(combobox_altura.currentData())
        )

        layout_parametros = QtWidgets.QGridLayout()

        layout_parametros.addWidget(QtWidgets.QLabel("Altura"), 0, 0)
        layout_parametros.addWidget(combobox_altura, 0, 1)
        layout_parametros.setRowStretch(1, 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")
        box_parametros.setLayout(layout_parametros)

        layout_resultados = QtWidgets.QHBoxLayout()
        layout_resultados.setContentsMargins(11, 11, 11, 11)
        layout_resultados.addWidget(box_parametros)
        layout_resultados.addStretch()
        layout_resultados.addWidget(self.grafico, 1)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(widget_panel_resultados)
        layout_principal.addLayout(layout_resultados, 1)

        self.grafico.escena.actualizar_altura(combobox_altura.currentData())

        self.setLayout(layout_principal)
