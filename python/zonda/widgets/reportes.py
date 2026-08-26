# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtPrintSupport import QPageSetupDialog, QPrinter
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from zonda.enums import Unidad
from zonda.reportes import Reporte
from zonda.sistema import guardar_archivo_temporal
from zonda.widgets import utils_qt
from zonda.widgets.errores import AvisoError, AvisoExito

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel, CubiertaAislada, Edificio


class WidgetReporte(QtWidgets.QWidget):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        plantilla: str,
        estructura: Edificio | Cartel | CubiertaAislada,
    ) -> None:
        """

        Args:
            parent: El widget parent.
            plantilla: La plantilla a utilizar.
            estructura: La estructura de donde se renderizan los resultados.
        """
        super().__init__(parent)

        self.plantilla = plantilla
        self.estructura = estructura

        settings = QtCore.QSettings()
        settings.beginGroup("unidades")
        fuerza = settings.value("fuerza", "N")
        presion = settings.value("presion", "N")
        settings.endGroup()

        self._reporte = Reporte(
            plantilla,
            estructura,
            unidades={"fuerza": Unidad(fuerza), "presion": Unidad(presion)},
        )

        # La vista se deja como viene: nada de WA_NativeWindow ni de
        # WA_DontCreateNativeAncestors. Eran un parche de la época de PyQt5;
        # en Qt6 la QWebEngineView ya se apoya en su propia ventana nativa y
        # forzarla de nuevo hace que en macOS el contenido no se componga: el
        # reporte se ve en blanco aunque la página lo tenga cargado.
        self._vista_web = QWebEngineView()
        self._vista_web.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)

        # Una QWebEngineView siempre tiene página y la página siempre tiene
        # settings; los stubs los declaran opcionales igual.
        pagina = self._vista_web.page()
        assert pagina is not None
        self._pagina = pagina
        pagina_settings = pagina.settings()
        assert pagina_settings is not None

        # printToPdf() tampoco es sincrónico: avisa por esta señal cuando el
        # archivo quedó escrito. Se conecta una sola vez, acá.
        pagina.pdfPrintingFinished.connect(self._pdf_terminado)

        pagina_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, False
        )
        pagina_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False
        )
        pagina_settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False
        )
        pagina_settings.setAttribute(
            QWebEngineSettings.WebAttribute.ErrorPageEnabled, False
        )
        pagina_settings.setAttribute(
            QWebEngineSettings.WebAttribute.PdfViewerEnabled, False
        )

        self._printer = QPrinter()
        self._printer.setPageMargins(
            QtCore.QMarginsF(25, 10, 10, 10), QtGui.QPageLayout.Unit.Millimeter
        )
        self._printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))

        self._vista_web.setHtml(self._reporte.exportar("html"))

        frame = QtWidgets.QFrame()
        frame.setProperty("class", "recuadro")

        layout_frame = QtWidgets.QVBoxLayout()
        layout_frame.addWidget(self._vista_web)
        layout_frame.setContentsMargins(0, 0, 0, 0)

        frame.setLayout(layout_frame)

        items = (
            ("Microsoft Word", ".docx"),
            ("PDF", ".pdf"),
            ("Markdown", ".md"),
            ("LibreOffice Writer", ".odt"),
            ("HTML", ".html"),
        )

        self._combobox_formatos = QtWidgets.QComboBox()
        for item in items:
            self._combobox_formatos.addItem(*item)
        self._combobox_formatos.currentTextChanged.connect(self._actualizar_formato)

        boton_configurar_pagina = QtWidgets.QPushButton("Configurar Página")
        boton_configurar_pagina.clicked.connect(self._configurar_pagina)

        self._checkbox_crear_pdf_html = QtWidgets.QCheckBox("Exportar como PDF")
        self._checkbox_crear_pdf_html.stateChanged.connect(
            boton_configurar_pagina.setVisible
        )

        label_seleccion_archivo = QtWidgets.QLabel("Documento de referencia:")
        label_seleccion_archivo.setToolTip(
            "Documento de referencia del que se adoptan los estilos al exportar el reporte"
        )

        self._line_edit = QtWidgets.QLineEdit()

        boton_seleccionar_archivo = QtWidgets.QPushButton("...")
        boton_seleccionar_archivo.setMaximumWidth(30)

        label_aviso_latex = QtWidgets.QLabel(
            '* Esta opción requiere tener "LaTeX" instalado en el sistema. Puede instalarlo via '
            "<a href=www.miktex.org>MiKTeX</a> o <a href=www.tug.org/texlive>TeXLive.</a>"
        )
        label_aviso_latex.setWordWrap(True)
        label_aviso_latex.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        label_aviso_latex.setOpenExternalLinks(True)

        self._dialogo_seleccionar_archivo = QtWidgets.QFileDialog()
        self._dialogo_seleccionar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )
        self._dialogo_seleccionar_archivo.setFileMode(
            QtWidgets.QFileDialog.FileMode.ExistingFile
        )

        self._dialogo_guardar_archivo = QtWidgets.QFileDialog()
        self._dialogo_guardar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )

        boton_seleccionar_archivo.clicked.connect(self._obtener_archivo)

        boton_exportar_reporte = QtWidgets.QPushButton("Exportar")
        boton_exportar_reporte.clicked.connect(self._exportar_reporte)

        self._layout_exportacion = QtWidgets.QGridLayout()
        self._layout_exportacion.addWidget(QtWidgets.QLabel("Formato:"), 0, 0)
        self._layout_exportacion.addWidget(self._combobox_formatos, 0, 1)
        self._layout_exportacion.addWidget(self._checkbox_crear_pdf_html, 0, 2)
        self._layout_exportacion.addWidget(boton_configurar_pagina, 0, 3)
        self._layout_exportacion.addWidget(label_seleccion_archivo, 1, 0, 1, 2)
        self._layout_exportacion.addWidget(self._line_edit, 2, 0, 1, 5)
        self._layout_exportacion.addWidget(boton_seleccionar_archivo, 2, 6)
        self._layout_exportacion.addWidget(label_aviso_latex, 3, 0, 1, 7)
        self._layout_exportacion.addWidget(
            boton_exportar_reporte, 5, 0, 1, 7, QtCore.Qt.AlignmentFlag.AlignRight
        )
        self._layout_exportacion.setColumnStretch(4, 1)
        self._layout_exportacion.setRowStretch(4, 1)

        group_box_exportacion = QtWidgets.QGroupBox("Configuración de Exportación")
        group_box_exportacion.setLayout(self._layout_exportacion)
        group_box_exportacion.setMinimumWidth(500)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(frame, 1)
        layout_principal.addWidget(group_box_exportacion)

        self.setLayout(layout_principal)

        self._actualizar_formato(self._combobox_formatos.currentText())

        self.setWindowFlags(QtCore.Qt.WindowType.Dialog)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(1200, 700)
        self.setWindowTitle("Reporte")

        self.show()

    def _configurar_pagina(self):
        dialogo = QPageSetupDialog(self._printer, self)
        if dialogo.exec():
            self._printer = dialogo.printer()

    def _obtener_archivo(self):
        #  El método "getOpenFileName" es estatico, por lo tanto tengo que setear
        filtro = f"{self._combobox_formatos.currentText()} (*{self._combobox_formatos.currentData()})"
        texto, _ = self._dialogo_seleccionar_archivo.getOpenFileName(
            self, filter=filtro
        )
        if texto:
            self._line_edit.setText(texto)

    def _actualizar_formato(self, descripcion_formato: str) -> None:
        es_pdf = descripcion_formato == "PDF"
        celda = partial(utils_qt.widget_de_celda, self._layout_exportacion)
        celda(0, 3).setVisible(es_pdf)
        celda(3, 0).setVisible(es_pdf)
        celda(0, 2).setVisible(descripcion_formato == "HTML")
        bool_eleccion_archivo = descripcion_formato in (
            "Microsoft Word",
            "LibreOffice Writer",
        )
        # Acá sí hay celdas vacías: se recorre el rectángulo entero.
        for fila in range(1, 3):
            for columna in range(7):
                item = self._layout_exportacion.itemAtPosition(fila, columna)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None:
                    widget.setEnabled(bool_eleccion_archivo)

    def _exportar_reporte(self):
        descripcion_formato = self._combobox_formatos.currentText()
        formato = self._combobox_formatos.currentData()
        filtro = f"{descripcion_formato} (*{formato})"
        if descripcion_formato == "HTML" and self._checkbox_crear_pdf_html.isChecked():
            filtro = "PDF (*.pdf)"
        nombre_archivo, _ = self._dialogo_guardar_archivo.getSaveFileName(
            filter=filtro,
            directory=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.DocumentsLocation
            ),
        )
        if not nombre_archivo:
            return

        # Los dos formatos que salen de la vista web se resuelven por callback:
        # el aviso de que terminó lo dan ellos, no esta función.
        if descripcion_formato == "HTML":
            if self._checkbox_crear_pdf_html.isChecked():
                self._pagina.printToPdf(nombre_archivo, self._printer.pageLayout())
            else:
                self._exportar_html(nombre_archivo)
            return

        if descripcion_formato == "PDF":
            tamaño_papel = self._printer.pageLayout().fullRect()
            margenes = self._printer.pageLayout().margins(
                QtGui.QPageLayout.Unit.Millimeter
            )
            papel = dict(
                zip(
                    ("left", "top", "right", "bottom"),
                    (
                        margenes.left(),
                        margenes.top(),
                        margenes.right(),
                        margenes.bottom(),
                    ),
                )
            )
            papel.update(
                paperwidth=tamaño_papel.width(), paperheight=tamaño_papel.height()
            )
        else:
            papel = None
        ruta_archivo = self._line_edit.text()
        try:
            self._reporte.exportar(
                formato[1:],
                nombre_archivo=nombre_archivo,
                css=ruta_archivo,
                referencia_doc=ruta_archivo,
                papel=papel,
            )
        except OSError:
            AvisoError(
                self,
                "No se pudo realizar la exportación. Aseguresé que Pandoc está instalado y agregado al PATH del sistema",
                "Error Exportación",
            )
        except RuntimeError as e:
            ruta_archivo_temp = guardar_archivo_temporal(str(e), ".log")
            AvisoError(
                self,
                "No se puedo realizar la exportación. Para mas información consulte el archivo de registro de errores.",
                "Error Exportación",
                ruta_archivo_temp,
            )
        else:
            self._avisar_exportacion(nombre_archivo)

    def _exportar_html(self, nombre_archivo: str) -> None:
        """Guarda el HTML que está mostrando la vista.

        Args:
            nombre_archivo: El archivo donde se escribe el HTML.
        """

        # toHtml() entrega el documento por callback, no lo devuelve. Antes el
        # archivo se abría con un "with" que lo cerraba antes de que llegara la
        # respuesta, así que se escribía sobre un archivo ya cerrado y en el
        # disco quedaba un .html vacío.
        def guardar(html: str | None) -> None:
            if html is None:
                AvisoError(
                    self,
                    "La vista no devolvió el documento HTML.",
                    "Error Exportación",
                )
                return
            try:
                with open(nombre_archivo, "w", encoding="utf-8") as archivo:
                    archivo.write(html)
            except OSError:
                AvisoError(
                    self,
                    "No se pudo escribir el archivo HTML.",
                    "Error Exportación",
                )
            else:
                self._avisar_exportacion(nombre_archivo)

        self._pagina.toHtml(guardar)

    def _pdf_terminado(self, nombre_archivo: str, exito: bool) -> None:
        """Avisa el resultado de imprimir la vista a PDF.

        Args:
            nombre_archivo: El archivo que se pidió escribir.
            exito: Si la impresión terminó bien.
        """
        if exito:
            self._avisar_exportacion(nombre_archivo)
        else:
            AvisoError(
                self,
                "No se pudo generar el PDF.",
                "Error Exportación",
            )

    def _avisar_exportacion(self, nombre_archivo: str) -> None:
        """Avisa que el reporte se exportó y ofrece abrirlo.

        Args:
            nombre_archivo: El archivo que se acaba de escribir.
        """
        AvisoExito(
            self,
            f"El reporte se exportó a:\n{nombre_archivo}",
            "Exportación Finalizada",
            nombre_archivo,
        )
