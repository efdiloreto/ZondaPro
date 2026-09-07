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

"""El diálogo de exportación del reporte.

Es la configuración de exportación que vivía al costado del visor web,
con la misma mecánica: el reporte se renderiza con Jinja a Markdown y
pandoc lo convierte al formato elegido. Lo único que desaparece es la vía
HTML→PDF que pasaba por la QWebEngineView; el PDF se exporta por pandoc
con LaTeX, igual que el formato "PDF" de siempre.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtPrintSupport import QPageSetupDialog, QPrinter

from zonda.reportes import Reporte
from zonda.sistema import guardar_archivo_temporal
from zonda.widgets.errores import AvisoError, AvisoExito

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel, CubiertaAislada, Edificio
    from zonda.enums import Unidad

FORMATOS = (
    ("Microsoft Word", ".docx"),
    ("PDF", ".pdf"),
    ("Markdown", ".md"),
    ("LibreOffice Writer", ".odt"),
    ("HTML", ".html"),
)

# Los formatos que reciben el documento de referencia del que adoptan los
# estilos. Para el resto el campo no aplica.
FORMATOS_CON_REFERENCIA = ("Microsoft Word", "LibreOffice Writer")


class DialogoExportacion(QtWidgets.QDialog):
    """El diálogo que exporta el reporte con pandoc.

    Args:
        parent: El widget parent.
        estructura: La estructura calculada.
        plantilla: La plantilla Jinja del reporte.
        unidades: Las unidades de fuerza y presión del reporte.
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        estructura: Edificio | Cartel | CubiertaAislada,
        plantilla: str,
        unidades: dict[str, Unidad],
    ) -> None:
        super().__init__(parent)

        self._reporte = Reporte(plantilla, estructura, unidades)

        # El papel se configura desde acá para el PDF: pandoc lo recibe
        # como variables de geometry y no sabe nada de impresoras.
        self._printer = QPrinter()
        self._printer.setPageMargins(
            QtCore.QMarginsF(25, 10, 10, 10), QtGui.QPageLayout.Unit.Millimeter
        )
        self._printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))

        self._combobox_formatos = QtWidgets.QComboBox()
        for item in FORMATOS:
            self._combobox_formatos.addItem(*item)
        self._combobox_formatos.currentTextChanged.connect(self._actualizar_formato)

        self._boton_configurar_pagina = QtWidgets.QPushButton("Configurar Página")
        self._boton_configurar_pagina.clicked.connect(self._configurar_pagina)

        self._label_seleccion_archivo = QtWidgets.QLabel("Documento de referencia:")
        self._label_seleccion_archivo.setToolTip(
            "Documento de referencia del que se adoptan los estilos al exportar el reporte"
        )

        self._line_edit = QtWidgets.QLineEdit()

        self._boton_seleccionar_archivo = QtWidgets.QPushButton("...")
        self._boton_seleccionar_archivo.setMaximumWidth(30)
        self._boton_seleccionar_archivo.clicked.connect(self._obtener_archivo)

        self._label_aviso_latex = QtWidgets.QLabel(
            '* Esta opción requiere tener "LaTeX" instalado en el sistema. Puede instalarlo via '
            "<a href=www.miktex.org>MiKTeX</a> o <a href=www.tug.org/texlive>TeXLive.</a>"
        )
        self._label_aviso_latex.setWordWrap(True)
        self._label_aviso_latex.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._label_aviso_latex.setOpenExternalLinks(True)

        self._dialogo_seleccionar_archivo = QtWidgets.QFileDialog(self)
        self._dialogo_seleccionar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )
        self._dialogo_seleccionar_archivo.setFileMode(
            QtWidgets.QFileDialog.FileMode.ExistingFile
        )

        self._dialogo_guardar_archivo = QtWidgets.QFileDialog(self)
        self._dialogo_guardar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )

        boton_exportar_reporte = QtWidgets.QPushButton("Exportar")
        boton_exportar_reporte.clicked.connect(self._exportar_reporte)

        layout_exportacion = QtWidgets.QGridLayout()
        layout_exportacion.addWidget(QtWidgets.QLabel("Formato:"), 0, 0)
        layout_exportacion.addWidget(self._combobox_formatos, 0, 1)
        layout_exportacion.addWidget(self._boton_configurar_pagina, 0, 2)
        layout_exportacion.addWidget(self._label_seleccion_archivo, 1, 0, 1, 2)
        layout_exportacion.addWidget(self._line_edit, 2, 0, 1, 2)
        layout_exportacion.addWidget(self._boton_seleccionar_archivo, 2, 2)
        layout_exportacion.addWidget(self._label_aviso_latex, 3, 0, 1, 3)
        layout_exportacion.addWidget(
            boton_exportar_reporte, 5, 0, 1, 3, QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout_exportacion.setRowStretch(4, 1)

        group_box_exportacion = QtWidgets.QGroupBox("Configuración de Exportación")
        group_box_exportacion.setLayout(layout_exportacion)
        group_box_exportacion.setMinimumWidth(500)

        layout_principal = QtWidgets.QVBoxLayout(self)
        layout_principal.addWidget(group_box_exportacion)

        self.setWindowTitle("Exportar Reporte")
        self.setModal(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self._actualizar_formato(self._combobox_formatos.currentText())
        self.show()

    def _configurar_pagina(self) -> None:
        dialogo = QPageSetupDialog(self._printer, self)
        if dialogo.exec():
            impresora = dialogo.printer()
            assert impresora is not None
            self._printer = impresora

    def _obtener_archivo(self) -> None:
        descripcion = self._combobox_formatos.currentText()
        formato = self._combobox_formatos.currentData()
        filtro = f"{descripcion} (*{formato})"
        texto, _ = self._dialogo_seleccionar_archivo.getOpenFileName(
            self, filter=filtro
        )
        if texto:
            self._line_edit.setText(texto)

    def _actualizar_formato(self, descripcion_formato: str) -> None:
        """Muestra u oculta los controles según el formato elegido.

        Args:
            descripcion_formato: La descripción del formato seleccionado.
        """
        es_pdf = descripcion_formato == "PDF"
        con_referencia = descripcion_formato in FORMATOS_CON_REFERENCIA
        self._boton_configurar_pagina.setVisible(es_pdf)
        self._label_aviso_latex.setVisible(es_pdf)
        for widget in (
            self._label_seleccion_archivo,
            self._line_edit,
            self._boton_seleccionar_archivo,
        ):
            widget.setVisible(con_referencia)

    def _exportar_reporte(self) -> None:
        """Le pide al usuario un archivo y escribe el reporte en ese formato."""
        descripcion_formato = self._combobox_formatos.currentText()
        formato = self._combobox_formatos.currentData()
        filtro = f"{descripcion_formato} (*{formato})"
        nombre_archivo, _ = self._dialogo_guardar_archivo.getSaveFileName(
            self,
            filter=filtro,
            directory=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.DocumentsLocation
            ),
        )
        if not nombre_archivo:
            return

        papel = self._papel() if descripcion_formato == "PDF" else None
        ruta_referencia = (
            self._line_edit.text()
            if descripcion_formato in FORMATOS_CON_REFERENCIA
            else ""
        )
        try:
            self._reporte.exportar(
                formato[1:],
                nombre_archivo=nombre_archivo,
                referencia_doc=ruta_referencia,
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
            AvisoExito(
                self,
                f"El reporte se exportó a:\n{nombre_archivo}",
                "Exportación Finalizada",
                nombre_archivo,
            )

    def _papel(self) -> dict[str, str | float]:
        """Los parámetros del papel configurado, como los espera pandoc.

        Returns:
            El diccionario de geometry con tamaño y márgenes en mm.
        """
        tamaño_papel = self._printer.pageLayout().fullRect()
        margenes = self._printer.pageLayout().margins(QtGui.QPageLayout.Unit.Millimeter)
        return dict(
            zip(
                ("left", "top", "right", "bottom"),
                (
                    margenes.left(),
                    margenes.top(),
                    margenes.right(),
                    margenes.bottom(),
                ),
                strict=True,
            ),
            paperwidth=tamaño_papel.width(),
            paperheight=tamaño_papel.height(),
        )
