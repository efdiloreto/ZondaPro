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

"""La vista del reporte en pantalla.

Es el reemplazo del visor web: un encabezado con el título del reporte y
la acción de exportar, una columna con las secciones —el índice del
documento— y las páginas correspondientes en un apilador. Las páginas las
arma cada tipología (`edificio.py`, `cartel.py`, `cubierta_aislada.py`)
con los bloques de `secciones.py` y `tablas.py`; esta vista sólo sabe
acomodarlas y navegarlas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from zonda.widgets.reportes.exportacion import DialogoExportacion
from zonda.widgets.reportes.secciones import unidades_desde_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from zonda.cirsoc import Cartel, CubiertaAislada, Edificio

ANCHO_MENU = 190


class VistaReporte(QtWidgets.QWidget):
    """El reporte de resultados con widgets nativos.

    Args:
        estructura: La estructura calculada de donde salen los valores.
        plantilla: La plantilla del reporte exportado, que el diálogo de
            exportación usa tal como la usa el visor web que reemplazó.
        titulo: El título del encabezado.
        paginas: Las páginas del reporte, como pares de nombre de sección
            y widget, en el orden del índice.
        parent: El widget parent.
    """

    def __init__(
        self,
        estructura: Edificio | Cartel | CubiertaAislada,
        plantilla: str,
        titulo: str,
        paginas: Sequence[tuple[str, QtWidgets.QWidget]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._estructura = estructura
        self._plantilla = plantilla
        self._unidades = unidades_desde_settings()

        etiqueta_titulo = QtWidgets.QLabel(titulo)
        etiqueta_titulo.setProperty("class", "reporte-titulo")

        etiqueta_codigo = QtWidgets.QLabel("CIRSOC 102-2025")
        etiqueta_codigo.setProperty("class", "reporte-subtitulo")

        columna_titulo = QtWidgets.QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(etiqueta_titulo)
        columna_titulo.addWidget(etiqueta_codigo)

        boton_exportar = QtWidgets.QPushButton("Exportar…")
        boton_exportar.setProperty("class", "reporte-exportar")
        boton_exportar.clicked.connect(self._exportar)

        encabezado = QtWidgets.QHBoxLayout()
        encabezado.setContentsMargins(0, 0, 0, 9)
        encabezado.addLayout(columna_titulo)
        encabezado.addStretch()
        encabezado.addWidget(boton_exportar, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        self._menu = QtWidgets.QListWidget()
        self._menu.setProperty("class", "menu-reporte")
        self._menu.setFixedWidth(ANCHO_MENU)
        self._menu.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._menu.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self._paginas = QtWidgets.QStackedWidget()
        for nombre, pagina in paginas:
            self._menu.addItem(nombre)
            self._paginas.addWidget(self._envolver_en_scroll(pagina))

        cuerpo = QtWidgets.QSplitter()
        cuerpo.setChildrenCollapsible(False)
        cuerpo.addWidget(self._menu)
        cuerpo.addWidget(self._paginas)
        cuerpo.setStretchFactor(0, 0)
        cuerpo.setStretchFactor(1, 1)

        self._menu.currentRowChanged.connect(self._paginas.setCurrentIndex)
        self._menu.setCurrentRow(0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(11, 11, 11, 11)
        layout.addLayout(encabezado)
        layout.addWidget(cuerpo, 1)

    def _envolver_en_scroll(self, pagina: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        """Envuelve una página en un área de desplazamiento.

        Args:
            pagina: La página armada por la tipología.

        Returns:
            El área lista para el apilador.
        """
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(pagina)
        return scroll

    def _exportar(self) -> None:
        """Abre el diálogo de exportación del reporte."""
        DialogoExportacion(self, self._estructura, self._plantilla, self._unidades)
