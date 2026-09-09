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

El reporte se renderiza con Jinja a Markdown y pandoc lo convierte a
PDF por LaTeX. El diálogo carga los datos del informe —nombre del
proyecto, proyectista, empresa, ubicación y observaciones— que viajan a
la portada y a la sección final de observaciones; el footer con la
versión de Zonda lo agrega la plantilla y no se puede sacar.
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


class DialogoExportacion(QtWidgets.QDialog):
    """El diálogo que exporta el reporte a PDF con pandoc.

    Args:
        parent: El widget parent.
        estructura: La estructura calculada.
        plantilla: La plantilla Jinja del reporte.
        unidades: Las unidades de fuerza y presión del reporte.
        nombre_proyecto: El nombre con el que arranca el campo del
            proyecto: el del archivo ``.zda`` abierto, si lo hay.
    """

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        estructura: Edificio | Cartel | CubiertaAislada,
        plantilla: str,
        unidades: dict[str, Unidad],
        nombre_proyecto: str = "",
    ) -> None:
        super().__init__(parent)

        self._estructura = estructura
        self._plantilla = plantilla
        self._unidades = unidades

        # El papel se configura desde acá para el PDF: pandoc lo recibe
        # como variables de geometry y no sabe nada de impresoras.
        self._printer = QPrinter()
        self._printer.setPageMargins(
            QtCore.QMarginsF(25, 10, 10, 10), QtGui.QPageLayout.Unit.Millimeter
        )
        self._printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))

        self._edicion_nombre = QtWidgets.QLineEdit(nombre_proyecto)
        self._edicion_proyectista = QtWidgets.QLineEdit()
        self._edicion_empresa = QtWidgets.QLineEdit()
        self._edicion_ubicacion = QtWidgets.QLineEdit()
        self._edicion_observaciones = QtWidgets.QPlainTextEdit()
        self._edicion_observaciones.setMaximumHeight(68)

        self._boton_configurar_pagina = QtWidgets.QPushButton("Configurar Página")
        self._boton_configurar_pagina.clicked.connect(self._configurar_pagina)

        self._label_aviso_latex = QtWidgets.QLabel(
            '* La exportación requiere tener "LaTeX" instalado en el sistema. Puede instalarlo via '
            "<a href=www.miktex.org>MiKTeX</a> o <a href=www.tug.org/texlive>TeXLive.</a>"
        )
        self._label_aviso_latex.setWordWrap(True)
        self._label_aviso_latex.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._label_aviso_latex.setOpenExternalLinks(True)

        self._dialogo_guardar_archivo = QtWidgets.QFileDialog(self)
        self._dialogo_guardar_archivo.setAcceptMode(
            QtWidgets.QFileDialog.AcceptMode.AcceptSave
        )
        self._dialogo_guardar_archivo.setDefaultSuffix("pdf")

        boton_exportar_reporte = QtWidgets.QPushButton("Exportar")
        boton_exportar_reporte.clicked.connect(self._exportar_reporte)

        layout_exportacion = QtWidgets.QGridLayout()
        layout_exportacion.addWidget(QtWidgets.QLabel("Nombre del proyecto:"), 0, 0)
        layout_exportacion.addWidget(self._edicion_nombre, 0, 1, 1, 2)
        layout_exportacion.addWidget(QtWidgets.QLabel("Proyectista:"), 1, 0)
        layout_exportacion.addWidget(self._edicion_proyectista, 1, 1, 1, 2)
        layout_exportacion.addWidget(QtWidgets.QLabel("Empresa / Estudio:"), 2, 0)
        layout_exportacion.addWidget(self._edicion_empresa, 2, 1, 1, 2)
        layout_exportacion.addWidget(QtWidgets.QLabel("Ubicación:"), 3, 0)
        layout_exportacion.addWidget(self._edicion_ubicacion, 3, 1, 1, 2)
        layout_exportacion.addWidget(
            QtWidgets.QLabel("Observaciones:"), 4, 0, QtCore.Qt.AlignmentFlag.AlignTop
        )
        layout_exportacion.addWidget(self._edicion_observaciones, 4, 1, 1, 2)
        layout_exportacion.addWidget(self._boton_configurar_pagina, 5, 0)
        layout_exportacion.addWidget(self._label_aviso_latex, 5, 1, 1, 2)
        layout_exportacion.addWidget(
            boton_exportar_reporte, 7, 0, 1, 3, QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout_exportacion.setRowStretch(6, 1)

        group_box_exportacion = QtWidgets.QGroupBox("Datos del Informe")
        group_box_exportacion.setLayout(layout_exportacion)
        group_box_exportacion.setMinimumWidth(500)

        layout_principal = QtWidgets.QVBoxLayout(self)
        layout_principal.addWidget(group_box_exportacion)

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
        """Le pide al usuario un archivo y escribe el reporte en PDF.

        El reporte se arma recién acá, con los datos del informe tal
        como quedaron en los campos.
        """
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
            self._reporte = Reporte(
                self._plantilla,
                self._estructura,
                self._unidades,
                datos_proyecto={
                    "nombre": self._edicion_nombre.text().strip(),
                    "proyectista": self._edicion_proyectista.text().strip(),
                    "empresa": self._edicion_empresa.text().strip(),
                    "ubicacion": self._edicion_ubicacion.text().strip(),
                    "observaciones": self._edicion_observaciones.toPlainText().strip(),
                },
            )
            self._reporte.exportar(
                "pdf", nombre_archivo=nombre_archivo, papel=self._papel()
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
