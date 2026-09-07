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

"""Bloques reutilizables que componen el reporte en pantalla.

Cada bloque es el equivalente nativo de lo que las plantillas Jinja arman
para exportar: una `Seccion` es un encabezado de primer nivel, una
`Subseccion` el título de una tabla con su referencia al Reglamento, una
`Tarjeta` un valor destacado del resumen y una `Nota` el pie que explica
los mínimos y las consideraciones del Reglamento.

Los módulos por tipología (`edificio.py`, `cartel.py`,
`cubierta_aislada.py`) combinan estos bloques con las tablas de
`tablas.py`, y las secciones de datos de entrada compartidas viven en
`comunes.py` para que ninguna tipología repita su armado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from zonda.enums import Unidad
from zonda.recursos import icono

if TYPE_CHECKING:
    from collections.abc import Iterable


def unidades_desde_settings() -> dict[str, Unidad]:
    """Las unidades elegidas en la configuración del programa.

    Returns:
        Un diccionario con las claves ``fuerza`` y ``presion``.
    """
    settings = QtCore.QSettings()
    settings.beginGroup("unidades")
    try:
        fuerza = settings.value("fuerza", "N")
        presion = settings.value("presion", "N")
    finally:
        settings.endGroup()
    return {"fuerza": Unidad(fuerza), "presion": Unidad(presion)}


class Seccion(QtWidgets.QWidget):
    """Un encabezado de primer nivel con su contenido apilado.

    Equivale a los títulos ``##`` del reporte exportado: abren cada grupo
    grande de la página y debajo se apilan sus subsecciones, tablas y
    notas.
    """

    def __init__(
        self,
        titulo: str,
        descripcion: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            titulo: El título de la sección.
            descripcion: Un texto introductorio opcional, debajo del título.
            parent: El widget parent.
        """
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        etiqueta_titulo = QtWidgets.QLabel(titulo)
        etiqueta_titulo.setProperty("class", "seccion")
        layout.addWidget(etiqueta_titulo)

        if descripcion:
            etiqueta_descripcion = QtWidgets.QLabel(descripcion)
            etiqueta_descripcion.setWordWrap(True)
            etiqueta_descripcion.setProperty("class", "seccion-descripcion")
            layout.addWidget(etiqueta_descripcion)

        self._layout = layout

    def agregar(self, widget: QtWidgets.QWidget) -> None:
        """Agrega un widget al contenido de la sección.

        Args:
            widget: El widget a agregar.
        """
        self._layout.addWidget(widget)

    def agregar_separador(self) -> None:
        """Agrega una línea divisoria entre dos widgets del contenido."""
        linea = QtWidgets.QFrame()
        linea.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        linea.setProperty("class", "separador")
        self._layout.addWidget(linea)

    def agregar_estiramiento(self) -> None:
        """Agrega un estiramiento al final del contenido."""
        self._layout.addStretch(1)


class Subseccion(QtWidgets.QFrame):
    """Un título de segundo nivel con el detalle que lo acompaña.

    Equivale a los títulos ``###`` de las plantillas: encabeza una tabla o
    un grupo de datos y muestra la referencia al Reglamento, que en la
    exportación viaja como pie de tabla.
    """

    def __init__(
        self,
        titulo: str,
        referencia: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            titulo: El título de la subsección.
            referencia: La referencia al Reglamento (figura o tabla).
            parent: El widget parent.
        """
        super().__init__(parent)
        self.setProperty("class", "subseccion")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 11)
        layout.setSpacing(7)

        fila_titulo = QtWidgets.QHBoxLayout()
        etiqueta_titulo = QtWidgets.QLabel(titulo)
        etiqueta_titulo.setProperty("class", "subseccion-titulo")
        # Sin ajuste de línea: un título con word-wrap dentro de esta fila
        # achica el ancho que pide y se parte en dos aunque la tarjeta sobre
        # de ancho. Los títulos son de una línea por diseño.
        fila_titulo.addWidget(etiqueta_titulo)
        fila_titulo.addStretch()
        if referencia:
            etiqueta_referencia = QtWidgets.QLabel(f"Ref: {referencia}")
            etiqueta_referencia.setProperty("class", "referencia")
            fila_titulo.addWidget(etiqueta_referencia)
        layout.addLayout(fila_titulo)

        self._layout = layout

    def agregar(self, widget: QtWidgets.QWidget) -> None:
        """Agrega un widget al contenido de la subsección.

        Args:
            widget: El widget a agregar.
        """
        self._layout.addWidget(widget)


class TablaDatos(QtWidgets.QWidget):
    """Pares etiqueta-valor, la forma de los datos de entrada.

    Los valores se dejan seleccionables con el mouse: quien arma el
    cálculo suele copiarlos a la memoria o a la planilla.
    """

    def __init__(
        self,
        filas: Iterable[tuple[str, str]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            filas: Los pares etiqueta, valor en el orden en que se muestran.
            parent: El widget parent.
        """
        super().__init__(parent)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(3)

        for fila, (etiqueta, valor) in enumerate(filas):
            etiqueta_valor = QtWidgets.QLabel(etiqueta)
            etiqueta_valor.setProperty("class", "dato-etiqueta")
            layout.addWidget(etiqueta_valor, fila, 0)

            etiqueta_resultado = QtWidgets.QLabel(valor)
            etiqueta_resultado.setProperty("class", "dato-valor")
            etiqueta_resultado.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(etiqueta_resultado, fila, 1)

        layout.setColumnStretch(2, 1)


class Tarjeta(QtWidgets.QFrame):
    """Un valor destacado del resumen.

    Es la forma de resaltar sin llenar la pantalla de números: la tarjeta
    muestra un solo valor con su etiqueta y, si hace falta, una línea de
    detalle que dice dónde se produce.
    """

    def __init__(
        self,
        titulo: str,
        valor: str,
        detalle: str | None = None,
        destacada: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            titulo: La etiqueta que dice qué es el valor.
            valor: El valor, ya formateado con su unidad.
            detalle: Una línea pequeña debajo del valor, por ejemplo la
                ubicación donde se produce.
            destacada: Si la tarjeta resalta un resultado clave, como la
                fuerza de diseño o los valores extremos.
            parent: El widget parent.
        """
        super().__init__(parent)
        self.setProperty("class", "tarjeta")
        self.setProperty("destacada", destacada)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(1)

        etiqueta_titulo = QtWidgets.QLabel(titulo)
        etiqueta_titulo.setProperty("class", "tarjeta-titulo")
        layout.addWidget(etiqueta_titulo)

        etiqueta_valor = QtWidgets.QLabel(valor)
        etiqueta_valor.setProperty("class", "tarjeta-valor")
        etiqueta_valor.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(etiqueta_valor)

        if detalle:
            etiqueta_detalle = QtWidgets.QLabel(detalle)
            etiqueta_detalle.setProperty("class", "tarjeta-detalle")
            etiqueta_detalle.setWordWrap(True)
            layout.addWidget(etiqueta_detalle)


def fila_tarjetas(*tarjetas: Tarjeta) -> QtWidgets.QWidget:
    """Acomoda tarjetas en una fila, repartiendo el ancho por igual.

    Args:
        *tarjetas: Las tarjetas a acomodar.

    Returns:
        El widget con la fila.
    """
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(9)
    if not tarjetas:
        return widget
    for tarjeta in tarjetas:
        layout.addWidget(tarjeta, 1)
    return widget


class Nota(QtWidgets.QFrame):
    """Una consideración del Reglamento, destacada del resto del contenido.

    Equivale a las notas al pie de las tablas exportadas: los mínimos de
    los Arts. 2.1.5 y 5.2.2, las aclaraciones sobre el parapeto y todo
    lo que el ingeniero tiene que leer aunque no revise los números.
    """

    def __init__(
        self,
        texto: str,
        titulo: str = "Nota",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Args:
            texto: El cuerpo de la nota.
            titulo: El rótulo de la nota.
            parent: El widget parent.
        """
        super().__init__(parent)
        self.setProperty("class", "nota")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 8)
        layout.setSpacing(9)

        etiqueta_icono = QtWidgets.QLabel()
        etiqueta_icono.setPixmap(icono("iconos/informacion.png").pixmap(16, 16))
        etiqueta_icono.setFixedWidth(16)
        etiqueta_icono.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(etiqueta_icono)

        columna = QtWidgets.QVBoxLayout()
        columna.setSpacing(1)
        etiqueta_titulo = QtWidgets.QLabel(titulo)
        etiqueta_titulo.setProperty("class", "nota-titulo")
        columna.addWidget(etiqueta_titulo)
        etiqueta_texto = QtWidgets.QLabel(texto)
        etiqueta_texto.setWordWrap(True)
        etiqueta_texto.setProperty("class", "nota-texto")
        columna.addWidget(etiqueta_texto)
        layout.addLayout(columna, 1)
