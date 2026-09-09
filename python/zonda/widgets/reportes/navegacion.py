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

Es un encabezado con el título del reporte y la acción de exportar, una
columna con las secciones —el índice del documento— y las páginas
correspondientes en un apilador. Las páginas salen del modelo de
:mod:`zonda.widgets.reportes.documento`, armado por cada tipología
(`edificio.py`, `cartel.py`, `cubierta_aislada.py`); esta vista sólo sabe
acomodarlas y navegarlas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from zonda.widgets.reportes.exportacion import DialogoExportacion
from zonda.widgets.reportes.secciones import armar_vista

if TYPE_CHECKING:
    from zonda.widgets.reportes.documento import Documento

ANCHO_MENU = 190


class VistaReporte(QtWidgets.QWidget):
    """El reporte de resultados con widgets nativos.

    Args:
        documento: El modelo del documento a mostrar.
        parent: El widget parent.
    """

    def __init__(
        self,
        documento: Documento,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._documento = documento

        etiqueta_titulo = QtWidgets.QLabel(documento.titulo)
        etiqueta_titulo.setProperty("class", "reporte-titulo")

        etiqueta_codigo = QtWidgets.QLabel("CIRSOC 102-2025")
        etiqueta_codigo.setProperty("class", "reporte-subtitulo")

        columna_titulo = QtWidgets.QVBoxLayout()
        columna_titulo.setSpacing(0)
        columna_titulo.addWidget(etiqueta_titulo)
        columna_titulo.addWidget(etiqueta_codigo)

        boton_exportar = QtWidgets.QPushButton("Exportar")
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
        for nombre, pagina in armar_vista(documento):
            self._menu.addItem(nombre)
            self._paginas.addWidget(self._envolver_en_scroll(pagina))

        cuerpo = QtWidgets.QSplitter()
        cuerpo.setChildrenCollapsible(False)
        # El sizeHint del menú (256px) es más ancho que su ancho fijo y
        # el splitter arranca ahí, dejando un hueco muerto en su panel:
        # se le fija el reparto inicial y el handle mide lo mismo que el
        # margen derecho, para que el hueco a cada lado del contenido
        # sea igual.
        cuerpo.setHandleWidth(13)
        cuerpo.addWidget(self._menu)
        cuerpo.addWidget(self._paginas)
        cuerpo.setSizes([ANCHO_MENU, 1])
        cuerpo.setStretchFactor(0, 0)
        cuerpo.setStretchFactor(1, 1)

        self._menu.currentRowChanged.connect(self._paginas.setCurrentIndex)
        self._menu.setCurrentRow(0)

        layout = QtWidgets.QVBoxLayout(self)
        # El margen derecho es el mismo hueco que queda entre la barra y
        # el contenido: 13px de cada lado del área de resultados.
        layout.setContentsMargins(11, 11, 13, 11)
        layout.addLayout(encabezado)
        layout.addWidget(cuerpo, 1)

    def _envolver_en_scroll(self, pagina: QtWidgets.QWidget) -> QtWidgets.QScrollArea:
        """Envuelve una página en un área de desplazamiento.

        Args:
            pagina: La página armada desde el modelo.

        Returns:
            El área lista para el apilador.
        """
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        # Aire entre el contenido y la barra de desplazamiento: cuando la
        # barra aparece, no le pega a las tablas.
        scroll.setViewportMargins(0, 0, 12, 0)
        scroll.setWidget(pagina)
        return scroll

    def _exportar(self) -> None:
        """Abre el diálogo de exportación del reporte."""
        DialogoExportacion(self, self._documento)
