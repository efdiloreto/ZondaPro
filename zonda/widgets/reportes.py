from __future__ import annotations

from typing import TYPE_CHECKING, Union

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtPrintSupport import QPageSetupDialog, QPrinter
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

from zonda.enums import Unidad
from zonda.reportes import Reporte
from zonda.sistema import guardar_archivo_temporal
from zonda.widgets.errores import AvisoError

if TYPE_CHECKING:
    from zonda.cirsoc import Edificio, Cartel, CubiertaAislada


class WidgetReporte(QtWidgets.QWidget):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        plantilla: str,
        estructura: Union[Edificio, Cartel, CubiertaAislada],
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

        self._vista_web = QWebEngineView()
        self._vista_web.setAutoFillBackground(False)
        self._vista_web.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self._vista_web.setAttribute(QtCore.Qt.WA_NativeWindow, True)
        self._vista_web.setAttribute(QtCore.Qt.WA_DontCreateNativeAncestors, True)

        pagina_settings = self._vista_web.page().settings()
        pagina_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, False)
        pagina_settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        pagina_settings.setAttribute(
            QWebEngineSettings.JavascriptCanAccessClipboard, False
        )
        pagina_settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)
        pagina_settings.setAttribute(QWebEngineSettings.PdfViewerEnabled, False)

        self._printer = QPrinter()
        self._printer.setPageMargins(25, 10, 10, 10, QPrinter.Millimeter)
        self._printer.setPageSize(QPrinter.A4)

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
        label_aviso_latex.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        label_aviso_latex.setOpenExternalLinks(True)

        self._dialogo_seleccionar_archivo = QtWidgets.QFileDialog()
        self._dialogo_seleccionar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptSave
        )
        self._dialogo_seleccionar_archivo.setFileMode(
            QtWidgets.QFileDialog.ExistingFile
        )

        self._dialogo_guardar_archivo = QtWidgets.QFileDialog()
        self._dialogo_guardar_archivo.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)

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
            boton_exportar_reporte, 5, 0, 1, 7, QtCore.Qt.AlignRight
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

        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMinimumSize(1200, 700)
        self.setWindowTitle("Reporte")

        self.show()

    def _configurar_pagina(self):
        dialogo = QPageSetupDialog(self._printer, self)
        if dialogo.exec_():
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
        self._layout_exportacion.itemAtPosition(0, 3).widget().setVisible(es_pdf)
        self._layout_exportacion.itemAtPosition(3, 0).widget().setVisible(es_pdf)
        self._layout_exportacion.itemAtPosition(0, 2).widget().setVisible(
            descripcion_formato == "HTML"
        )
        bool_eleccion_archivo = descripcion_formato in (
            "Microsoft Word",
            "LibreOffice Writer",
        )
        for fila in range(1, 3):
            for columna in range(7):
                item = self._layout_exportacion.itemAtPosition(fila, columna)
                if item is not None:
                    widget = item.widget()
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
                QtCore.QStandardPaths.DocumentsLocation
            ),
        )
        if nombre_archivo:
            if descripcion_formato == "HTML":
                if self._checkbox_crear_pdf_html.isChecked():
                    pl = self._printer.pageLayout()
                    self._vista_web.page().printToPdf(nombre_archivo, pl)
                    return
                else:
                    with open(nombre_archivo, "w") as archivo:
                        self._vista_web.page().toHtml(archivo.write)
                    return
            elif descripcion_formato == "PDF":
                tamaño_papel = self._printer.pageLayout().fullRect()
                papel = dict(
                    zip(
                        ("left", "top", "right", "bottom"),
                        self._printer.getPageMargins(QPrinter.Millimeter),
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
                mensaje = AvisoError(
                    self,
                    "No se pudo realizar la exportación. Aseguresé que Pandoc está instalado y agregado al PATH del sistema",
                    "Error Exportación",
                )
            except RuntimeError as e:
                ruta_archivo_temp = guardar_archivo_temporal(str(e), ".log")
                mensaje = AvisoError(
                    self,
                    "No se puedo realizar la exportación. Para mas información consulte el archivo de registro de errores.",
                    "Error Exportación",
                    ruta_archivo_temp,
                )
