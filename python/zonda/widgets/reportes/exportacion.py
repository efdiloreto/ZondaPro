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

El reporte vive en el modelo de :mod:`zonda.widgets.reportes.documento`
y se exporta a PDF con el motor de texto de Qt (:mod:`zonda.pdf`), sin
dependencias externas. El diálogo deja elegir el papel y la orientación
de la página; los márgenes y el pie —con la versión de Zonda y la
numeración— los fija el exportador y no se pueden sacar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtPrintSupport import QPageSetupDialog, QPrinter

from zonda import pdf
from zonda.widgets.errores import AvisoError, AvisoExito

if TYPE_CHECKING:
    from zonda.widgets.reportes.documento import Documento


class DialogoExportacion(QtWidgets.QDialog):
    """El diálogo que exporta el reporte a PDF.

    Args:
        parent: El widget parent.
        documento: El modelo del documento a exportar.
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        documento: Documento,
    ) -> None:
        super().__init__(parent)

        self._documento = documento

        # El papel se configura desde acá para el PDF: el tamaño y la
        # orientación viajan al escritor; los márgenes los fija el
        # exportador.
        self._printer = QPrinter()
        self._printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))

        self._boton_configurar_pagina = QtWidgets.QPushButton("Configurar Página")
        self._boton_configurar_pagina.clicked.connect(self._configurar_pagina)

        self._dialogo_guardar_archivo = QtWidgets.QFileDialog(self)
        self._dialogo_guardar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )
        self._dialogo_guardar_archivo.setDefaultSuffix("pdf")

        boton_exportar_reporte = QtWidgets.QPushButton("Exportar")
        boton_exportar_reporte.clicked.connect(self._exportar_reporte)

        layout_exportacion = QtWidgets.QHBoxLayout()
        layout_exportacion.addWidget(self._boton_configurar_pagina)
        layout_exportacion.addStretch(1)
        layout_exportacion.addWidget(boton_exportar_reporte)

        self.setLayout(layout_exportacion)
        self.setWindowTitle("Exportar Reporte")
        self.setModal(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self.show()

    def _configurar_pagina(self) -> None:
        dialogo = QPageSetupDialog(self._printer, self)
        if dialogo.exec():
            impresora = dialogo.printer()
            assert impresora is not None
            self._printer = impresora

    def _exportar_reporte(self) -> None:
        """Le pide al usuario un archivo y escribe el reporte en PDF."""
        nombre_archivo, _ = self._dialogo_guardar_archivo.getSaveFileName(
            self,
            filter="PDF (*.pdf)",
            directory=QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.DocumentsLocation
            ),
        )
        if not nombre_archivo:
            return

        try:
            pdf.exportar_pdf(
                self._documento,
                nombre_archivo,
                layout=self._printer.pageLayout(),
            )
        except OSError:
            AvisoError(
                self,
                "No se pudo realizar la exportación. Verifique que la carpeta "
                "de destino permita escribir el archivo.",
                "Error Exportación",
            )
        else:
            AvisoExito(
                self,
                f"El reporte se exportó a:\n{nombre_archivo}",
                "Exportación Finalizada",
                nombre_archivo,
            )
