"""Contiene clases que representan los módulos para cada tipo de estructura. Cada módulo puede ser usado para ingresar los
datos de la estructura y visualizar sus resultados.
"""

import gc

from PyQt5 import QtWidgets, QtCore

from zonda import __acercade__
from zonda.cirsoc import Edificio, CubiertaAislada, Cartel
from zonda.excepciones import ErrorLineamientos, ErrorEstructura
from zonda.widgets.custom import WidgetPanelEntrada
from zonda.widgets.entrada import (
    WidgetEstructuraEdificio,
    WidgetEstructuraCubiertaAislada,
    WidgetEstructuraCartel,
)
from zonda.widgets.resultados import (
    WidgetResultadosEdificio,
    WidgetResultadosCubiertaAislada,
    WidgetResultadosCartel,
)


class WidgetModuloEdificio(QtWidgets.QWidget):
    titulo = "Edificio"

    def __init__(self, pantalla_bienvenida):
        super().__init__()

        self._widget_resultados = None

        self.pantalla_bienvenida = pantalla_bienvenida
        self.pantalla_bienvenida.hide()

        self._widget_estructura = self._generar_widget_estructura()

        widget_modulo_estructura = QtWidgets.QWidget()

        self._widget_panel_entrada = self._generar_widget_panel_entrada()
        self._widget_panel_entrada.boton_calcular.clicked.connect(
            self._generar_resultados
        )

        layout_estructura = QtWidgets.QVBoxLayout()
        layout_estructura.setContentsMargins(0, 0, 0, 0)
        layout_estructura.setSpacing(15)
        layout_estructura.addWidget(self._widget_panel_entrada)
        layout_estructura.addWidget(self._widget_estructura, 1)

        widget_modulo_estructura.setLayout(layout_estructura)

        self._stacked_widget = QtWidgets.QStackedWidget()
        self._stacked_widget.addWidget(widget_modulo_estructura)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(self._stacked_widget)

        self.setLayout(layout_principal)

        self.setWindowTitle(f"Zonda {__acercade__.__version__} - {self.titulo}")

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlag(QtCore.Qt.Window)

        self.showMaximized()

    def closeEvent(self, e):
        e.ignore()
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Confirmación de Salida",
                "Desea salir del módulo?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            == QtWidgets.QMessageBox.Yes
        ):
            # Se deben implementar los widgets en las subclases.
            if self._widget_resultados is not None:
                self._widget_resultados.finalizar()
            self._widget_estructura.finalizar()
            e.accept()
            self.pantalla_bienvenida.show()

    def _generar_resultados(self):
        try:
            if self._widget_resultados is not None:
                self._widget_resultados.finalizar()
                self._stacked_widget.removeWidget(self._widget_resultados)
                self._widget_resultados.destroy()
                del self._widget_resultados
                gc.collect()
            self._widget_resultados = self._generar_widget_resultados()
            self._stacked_widget.addWidget(self._widget_resultados)
            self._stacked_widget.setCurrentIndex(1)
        except ErrorLineamientos as e:
            QtWidgets.QMessageBox.critical(self, "Error Lineamientos", str(e))
        except ErrorEstructura as e:
            QtWidgets.QMessageBox.critical(self, "Error datos de Entrada", str(e))
        # except ValueError as e:
        #     QtWidgets.QMessageBox.critical(self, "Error parámetros de entrada", str(e))

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key not in ("ciudad", "editar_velocidad")
        }
        edificio = Edificio(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
            **self._widget_panel_entrada.componentes,
        )
        return WidgetResultadosEdificio(edificio)

    @staticmethod
    def _generar_widget_panel_entrada():
        return WidgetPanelEntrada(componentes=True)

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraEdificio()


class WidgetModuloCubiertaAislada(WidgetModuloEdificio):
    titulo = "Cubierta Aislada"

    @staticmethod
    def _generar_widget_panel_entrada():
        return WidgetPanelEntrada()

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraCubiertaAislada()

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key not in ("ciudad", "editar_velocidad", "factor_g_simplificado")
        }
        cubierta_aislada = CubiertaAislada(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
        )
        return WidgetResultadosCubiertaAislada(cubierta_aislada)


class WidgetModuloCartel(WidgetModuloCubiertaAislada):
    titulo = "Cartel"

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraCartel()

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key not in ("ciudad", "editar_velocidad")
        }
        cartel = Cartel(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
        )
        return WidgetResultadosCartel(cartel)
