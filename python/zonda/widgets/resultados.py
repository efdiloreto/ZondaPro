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

"""Contiene clases que representan los resultados para las diferentes estructuras. Estas estan compuestas por el widget
gráfico y otros widgets que permiten interactuar con el mismo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from zonda.enums import (
    CasoCartel,
    DireccionVientoMetodoDireccionalSprfv,
    ExtremoPresion,
    PosicionCubiertaAleroSprfv,
    SistemaResistente,
    TipoCubierta,
    TipoPresionComponentesParedesCubierta,
    TipoPresionCubiertaAislada,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaEdificio,
)
from zonda.excepciones import ErrorLineamientos
from zonda.sistema import guardar_archivo_temporal
from zonda.widgets import utils_qt
from zonda.widgets.custom import WidgetPanelResultados
from zonda.widgets.errores import AvisoError
from zonda.widgets.graficos import (
    WidgetGraficoCartelPresiones,
    WidgetGraficoCubiertaAisladaPresiones,
    WidgetGraficoEdificioPresiones,
)
from zonda.widgets.reportes import WidgetReporte

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel, CubiertaAislada, Edificio


class WidgetResultadosMixin:
    def _reporte(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
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
            QtWidgets.QApplication.restoreOverrideCursor()

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
        self._combobox_gcpi.currentIndexChanged.connect(
            self.grafico.escena.actualizar_gcpi
        )
        self._combobox_gcpi.currentIndexChanged.connect(
            self._actualizar_combobox_alturas
        )

        self._combobox_direccion = QtWidgets.QComboBox()
        for enum in DireccionVientoMetodoDireccionalSprfv:
            self._combobox_direccion.addItem(
                f"{enum.value.capitalize()} a la Cumbrera", enum
            )
        self._combobox_direccion.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_direccion_viento(
                self._combobox_direccion.currentData()
            )
        )
        self._combobox_direccion.currentIndexChanged.connect(
            self._actualizar_direccion_viento
        )
        self._combobox_direccion.currentIndexChanged.connect(
            self._actualizar_combobox_alturas
        )

        self._layout_parametros = QtWidgets.QGridLayout()

        self._layout_parametros.addWidget(
            QtWidgets.QLabel("Presión Interna"),
            0,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self._layout_parametros.addWidget(self._combobox_gcpi, 0, 1)

        self._layout_parametros.addWidget(
            QtWidgets.QLabel("Dirección del Viento"),
            1,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self._layout_parametros.addWidget(self._combobox_direccion, 1, 1)

        # La cubierta a barlovento tiene dos casos de presión con el viento
        # normal a la cumbrera: cuando el ángulo llega a 10° y, según el
        # nuevo Reglamento, también cuando es menor que 10°. Las filas lo
        # dicen con su clave de caso. Aplica a dos aguas, un agua y plana.
        casos_cubierta = edificio.resultados_sprfv.filtrar(
            zona=ZonaEdificio.CUBIERTA
        ).valores("caso")
        if any(casos_cubierta):
            # Con ángulo menor que 10° el caso positivo de la cubierta se
            # aplica a todo el faldón, sin distinguir posición.
            self._cubierta_casos_por_zona = any(
                fila.caso is not None and fila.posicion is None
                for fila in edificio.resultados_sprfv.filtrar(
                    zona=ZonaEdificio.CUBIERTA
                )
            )
            self._combobox_presion_cubierta_inclinada = QtWidgets.QComboBox()
            for enum in TipoPresionCubiertaBarloventoSprfv:
                self._combobox_presion_cubierta_inclinada.addItem(
                    enum.value.capitalize(), enum
                )
            self._combobox_presion_cubierta_inclinada.currentTextChanged.connect(
                lambda: self.grafico.escena.actualizar_presion_cubierta_inclinada(
                    self._combobox_presion_cubierta_inclinada.currentData()
                )
            )
            numero_filas = self._layout_parametros.rowCount()
            self._layout_parametros.addWidget(
                QtWidgets.QLabel("Presión Cubierta Barlovento"), numero_filas, 0
            )
            self._layout_parametros.addWidget(
                self._combobox_presion_cubierta_inclinada, numero_filas, 1
            )

        if edificio.geometria.tipo_cubierta == TipoCubierta.UN_AGUA:
            self._combobox_posicion_cubierta_un_agua = QtWidgets.QComboBox()
            for enum in PosicionCubiertaAleroSprfv:
                self._combobox_posicion_cubierta_un_agua.addItem(
                    enum.value.capitalize(), enum
                )
            self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(
                lambda: self.grafico.escena.actualizar_posicion_cubierta_un_agua(
                    self._combobox_posicion_cubierta_un_agua.currentData()
                )
            )
            self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(
                self._actualizar_combobox_alturas
            )
            self._combobox_posicion_cubierta_un_agua.currentIndexChanged.connect(
                self._actualizar_direccion_viento
            )
            numero_filas = self._layout_parametros.rowCount()
            self._layout_parametros.addWidget(
                QtWidgets.QLabel("Posición Cubierta"),
                numero_filas,
                0,
                QtCore.Qt.AlignmentFlag.AlignRight,
            )
            self._layout_parametros.addWidget(
                self._combobox_posicion_cubierta_un_agua, numero_filas, 1
            )

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
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self._layout_parametros.addWidget(
            self._combobox_alturas_barlovento, numero_filas, 1
        )

        self._layout_parametros.setRowStretch(self._layout_parametros.rowCount(), 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")

        box_parametros.setLayout(self._layout_parametros)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(box_parametros)
        layout_principal.addStretch()
        layout_principal.addWidget(self.grafico, 1)

        # Se inicializa con la dirección actual (paralelo)
        self.grafico.escena.actualizar_direccion_viento(
            self._combobox_direccion.currentData()
        )

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
        combobox_posicion_cubierta = getattr(
            self, "_combobox_posicion_cubierta_un_agua", None
        )
        if (
            combobox_posicion_cubierta is not None
            and direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
        ):
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
        bool_direccion = (
            self._combobox_direccion.currentData()
            == DireccionVientoMetodoDireccionalSprfv.NORMAL
        )

        combobox_caso_cubierta_inclinada = getattr(
            self, "_combobox_presion_cubierta_inclinada", None
        )
        combobox_posicion_cubierta_un_agua = getattr(
            self, "_combobox_posicion_cubierta_un_agua", None
        )
        for widget in (
            combobox_caso_cubierta_inclinada,
            combobox_posicion_cubierta_un_agua,
        ):
            if widget is not None:
                indice = self._layout_parametros.indexOf(widget)
                if (
                    widget is combobox_caso_cubierta_inclinada
                    and combobox_posicion_cubierta_un_agua is not None
                    and bool_direccion
                ):
                    if not getattr(self, "_cubierta_casos_por_zona", False):
                        posicion_cubierta_un_agua = (
                            combobox_posicion_cubierta_un_agua.currentData()
                        )
                        bool_visualizar = (
                            posicion_cubierta_un_agua
                            == PosicionCubiertaAleroSprfv.BARLOVENTO
                        )
                    else:
                        bool_visualizar = True
                else:
                    bool_visualizar = bool_direccion
                widget.setEnabled(bool_visualizar)
                # El label del combobox, que se agrega justo antes que él.
                utils_qt.widget_de_indice(
                    self._layout_parametros, indice - 1
                ).setEnabled(bool_visualizar)


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

        self.grafico = WidgetGraficoEdificioPresiones(
            edificio, SistemaResistente.COMPONENTES
        )

        self._layout_parametros = QtWidgets.QGridLayout()

        self._combobox_gcpi = QtWidgets.QComboBox()
        self._combobox_gcpi.addItems(("+GCpi", "-GCpi"))
        self._combobox_gcpi.currentIndexChanged.connect(
            self.grafico.escena.actualizar_gcpi
        )

        self._layout_parametros.addWidget(
            QtWidgets.QLabel("Presión Interna"),
            0,
            0,
            QtCore.Qt.AlignmentFlag.AlignRight,
        )
        self._layout_parametros.addWidget(self._combobox_gcpi, 0, 1)

        self._combobox_presion_componentes = QtWidgets.QComboBox()
        for enum in TipoPresionComponentesParedesCubierta:
            self._combobox_presion_componentes.addItem(enum.value.capitalize(), enum)
        self._combobox_presion_componentes.currentTextChanged.connect(
            lambda: self.grafico.escena.actualizar_tipo_presion(
                self._combobox_presion_componentes.currentData()
            )
        )

        self._layout_parametros.addWidget(
            QtWidgets.QLabel("Presión"), 1, 0, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._layout_parametros.addWidget(self._combobox_presion_componentes, 1, 1)

        if edificio.componentes_cubierta is not None:
            self._combobox_componentes_cubierta = QtWidgets.QComboBox()
            self._combobox_componentes_cubierta.addItems(
                edificio.componentes_cubierta.keys()
            )
            self._combobox_componentes_cubierta.currentTextChanged.connect(
                self.grafico.escena.actualizar_componente_cubierta
            )
            self._layout_parametros.addWidget(
                QtWidgets.QLabel("Componente Cubierta"),
                2,
                0,
                QtCore.Qt.AlignmentFlag.AlignRight,
            )
            self._layout_parametros.addWidget(self._combobox_componentes_cubierta, 2, 1)

        if edificio.componentes_paredes is not None:
            numero_filas = self._layout_parametros.rowCount()

            self._combobox_componentes_paredes = QtWidgets.QComboBox()
            self._combobox_componentes_paredes.addItems(
                edificio.componentes_paredes.keys()
            )
            self._combobox_componentes_paredes.currentTextChanged.connect(
                self.grafico.escena.actualizar_componente_pared
            )

            self._layout_parametros.addWidget(
                QtWidgets.QLabel("Componente Pared"),
                numero_filas,
                0,
                QtCore.Qt.AlignmentFlag.AlignRight,
            )
            self._layout_parametros.addWidget(
                self._combobox_componentes_paredes, numero_filas, 1
            )

            # Con la Figura 5.4-1 (h > 20 m) las paredes se evalúan con qz a
            # la altura elegida (Nota 4), en los dos modos del signo.
            if self.grafico.escena.por_altura_paredes:
                self._combobox_alturas_paredes = QtWidgets.QComboBox()
                for altura in self.grafico.escena.alturas_presiones_paredes:
                    self._combobox_alturas_paredes.addItem(f"{altura:.2f} m", altura)
                self._combobox_alturas_paredes.setCurrentIndex(
                    self._combobox_alturas_paredes.count() - 1
                )
                self._combobox_alturas_paredes.currentTextChanged.connect(
                    self._actualizar_altura_paredes
                )

                numero_filas += 1
                self._layout_parametros.addWidget(
                    QtWidgets.QLabel("Altura Presión Paredes"),
                    numero_filas,
                    0,
                    QtCore.Qt.AlignmentFlag.AlignRight,
                )
                self._layout_parametros.addWidget(
                    self._combobox_alturas_paredes, numero_filas, 1
                )

        numero_filas = self._layout_parametros.rowCount()
        self._layout_parametros.setRowStretch(numero_filas, 1)

        box_parametros = QtWidgets.QGroupBox("Parámetros")
        box_parametros.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        box_parametros.setLayout(self._layout_parametros)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(box_parametros)
        layout_principal.addStretch()
        layout_principal.addWidget(self.grafico, 1)

        if hasattr(self, "_combobox_componentes_paredes"):
            self.grafico.escena.actualizar_componente_pared(
                self._combobox_componentes_paredes.currentText()
            )
            if hasattr(self, "_combobox_alturas_paredes"):
                self._actualizar_altura_paredes()

        if hasattr(self, "_combobox_componentes_cubierta"):
            self.grafico.escena.actualizar_componente_cubierta(
                self._combobox_componentes_cubierta.currentText()
            )

        self.setLayout(layout_principal)

    def _actualizar_altura_paredes(self) -> None:
        """Actualiza la altura a la que se evalúan las paredes.

        Con la Figura 5.4-1 (h > 20 m) las paredes se evalúan con qz a la
        altura elegida (Nota 4), tanto en la presión positiva como en la
        negativa.
        """
        self.grafico.escena.actualizar_altura_paredes(
            self._combobox_alturas_paredes.currentData()
        )


class WidgetResultadosEdificio(QtWidgets.QWidget, WidgetResultadosMixin):
    plantilla_reporte = "edificio.md"

    def __init__(self, edificio):
        super().__init__()

        self._estructura = edificio

        self._stacked_widget = QtWidgets.QStackedWidget()

        widget_resultados_sprfv = WidgetResultadosEdificioSprfvMetodoDireccional(
            edificio
        )
        self._stacked_widget.addWidget(widget_resultados_sprfv)

        widget_panel_resultados = WidgetPanelResultados(edificio=True)

        widget_panel_resultados.boton_volver.clicked.connect(self._volver)
        widget_panel_resultados.boton_sprfv.clicked.connect(
            lambda: self._stacked_widget.setCurrentIndex(0)
        )
        widget_panel_resultados.boton_generar_reporte.clicked.connect(self._reporte)

        if any((edificio.componentes_paredes, edificio.componentes_cubierta)):
            try:
                # Se verifica que la referencia del código exista
                widget_resultados_componentes = WidgetResultadosEdificioComponentes(
                    self._estructura
                )
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
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msg.setWindowTitle("Advertencia Lineamientos")
                msg.setText(mensaje)
                msg.exec()

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
            lambda: self.grafico.escena.actualizar_tipo_presion(
                combobox_tipo_presion.currentData()
            )
        )

        combobox_extremo_presion = QtWidgets.QComboBox()
        for enum in ExtremoPresion:
            combobox_extremo_presion.addItem(enum.value.title(), enum)
        combobox_extremo_presion.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_extremo_presion(
                combobox_extremo_presion.currentData()
            )
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
    widgets que interactuan con este para el caso de la Figura 4.4-1 considerado.
    """

    plantilla_reporte = "cartel.md"

    def __init__(self, cartel: Cartel) -> None:
        """

        Args:
            cartel: Una instancia de Cartel.
        """
        super().__init__()

        self._estructura = cartel

        self.grafico = WidgetGraficoCartelPresiones(cartel)

        widget_panel_resultados = WidgetPanelResultados()

        widget_panel_resultados.boton_volver.clicked.connect(self._volver)
        widget_panel_resultados.boton_generar_reporte.clicked.connect(self._reporte)

        casos = [
            CasoCartel.CASO_A,
            CasoCartel.CASO_B,
            *(caso for caso in (CasoCartel.CASO_C,) if cartel.cf.aplica_caso_c),
        ]

        combobox_caso = QtWidgets.QComboBox()
        for caso in casos:
            combobox_caso.addItem(caso.value, caso)
        combobox_caso.currentIndexChanged.connect(
            lambda: self.grafico.escena.actualizar_caso(combobox_caso.currentData())
        )

        layout_parametros = QtWidgets.QGridLayout()

        layout_parametros.addWidget(QtWidgets.QLabel("Caso"), 0, 0)
        layout_parametros.addWidget(combobox_caso, 0, 1)
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

        self.grafico.escena.actualizar_caso(combobox_caso.currentData())

        self.setLayout(layout_principal)
