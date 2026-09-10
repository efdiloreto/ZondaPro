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

"""Bloques reutilizables del reporte en pantalla y su armado.

Los widgets (``Seccion``, ``Subseccion``, ``TablaDatos``, ``Tarjeta``,
``Nota``) son la forma visual de los bloques del modelo de
:mod:`zonda.widgets.reportes.documento`; ``armar_vista`` y
``armar_pagina`` recorren el modelo y los instancian. El PDF recorre el
mismo modelo sin pasar por acá.

Los módulos por tipología (`edificio.py`, `cartel.py`,
`cubierta_aislada.py`) arman el modelo con las tablas de `tablas.py`, y
los grupos de datos de entrada compartidos viven en `comunes.py` para que
ninguna tipología repita su armado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from zonda.enums import Unidad
from zonda.recursos import icono
from zonda.widgets.custom import crear_capsula, crear_segmento
from zonda.widgets.reportes import documento
from zonda.widgets.reportes.tablas import TablaResultados

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from zonda.widgets.reportes.documento import Bloque, Documento, Pagina

# El ancho que comparten el desplegable y la cápsula de superficies del
# selector de componentes.
ANCHO_SELECTOR = 260


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


# --- El armado de la vista desde el modelo -------------------------------


def armar_vista(documento_reporte: Documento) -> list[tuple[str, QtWidgets.QWidget]]:
    """Arma las páginas de la vista desde el modelo del documento.

    Args:
        documento_reporte: El documento a mostrar.

    Returns:
        Las páginas como pares de nombre de sección y widget, en el orden
        del índice.
    """
    return [
        (pagina.titulo, armar_pagina(pagina)) for pagina in documento_reporte.paginas
    ]


def armar_pagina(pagina: Pagina) -> QtWidgets.QWidget:
    """Arma la página de una tipología desde el modelo.

    Args:
        pagina: La página a armar.

    Returns:
        El widget de la página, con sus secciones apiladas.
    """
    contenedor = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(18)

    seccion = Seccion(pagina.titulo, descripcion=pagina.descripcion)
    _armar_bloques(pagina.bloques, seccion.agregar)
    layout.addWidget(seccion)
    layout.addStretch(1)
    return contenedor


def _armar_bloques(
    bloques: list[Bloque], agregar: Callable[[QtWidgets.QWidget], None]
) -> None:
    """Convierte los bloques del modelo en widgets y los agrega.

    Args:
        bloques: Los bloques a convertir, en orden de lectura.
        agregar: El callback que acomoda cada widget (el layout de la
            sección, de la subsección o de la pestaña).
    """
    for bloque in bloques:
        if isinstance(bloque, documento.Grupo):
            subseccion = Subseccion(bloque.titulo, referencia=bloque.referencia)
            _armar_bloques(bloque.bloques, subseccion.agregar)
            agregar(subseccion)
        elif isinstance(bloque, documento.Datos):
            agregar(TablaDatos(bloque.filas))
        elif isinstance(bloque, documento.Tabla):
            agregar(TablaResultados(bloque.columnas, bloque.filas))
        elif isinstance(bloque, documento.Tarjetas):
            agregar(
                fila_tarjetas(
                    *[
                        Tarjeta(
                            tarjeta.titulo,
                            tarjeta.valor,
                            detalle=tarjeta.detalle,
                            destacada=tarjeta.destacada,
                        )
                        for tarjeta in bloque.tarjetas
                    ]
                )
            )
        elif isinstance(bloque, documento.Nota):
            agregar(Nota(bloque.texto, bloque.titulo))
        elif isinstance(bloque, documento.Texto):
            etiqueta = QtWidgets.QLabel(bloque.texto)
            etiqueta.setWordWrap(True)
            etiqueta.setTextFormat(QtCore.Qt.TextFormat.RichText)
            agregar(etiqueta)
        elif isinstance(bloque, documento.Titulo):
            etiqueta = QtWidgets.QLabel(bloque.texto)
            etiqueta.setProperty("class", "grupo-tabla")
            agregar(etiqueta)
        elif isinstance(bloque, documento.Pestanas):
            agregar(_armar_pestanas(bloque))
        elif isinstance(bloque, documento.SelectorComponentes):
            agregar(_armar_selector(bloque))


def _armar_pestanas(pestanas: documento.Pestanas) -> QtWidgets.QTabWidget:
    """Convierte un bloque de pestañas en un ``QTabWidget``.

    Args:
        pestanas: El bloque con el contenido de cada pestaña.

    Returns:
        El widget con las pestañas.
    """
    pestañas = QtWidgets.QTabWidget()
    for etiqueta, bloques in pestanas.items:
        contenedor = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(contenedor)
        # El margen separa el contenido del pane de la pestaña, que es el
        # borde que dibuja el QTabWidget a su alrededor.
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(12)
        _armar_bloques(bloques, layout.addWidget)
        layout.addStretch(1)
        pestañas.addTab(contenedor, etiqueta)
    return pestañas


def _armar_selector(selector: documento.SelectorComponentes) -> QtWidgets.QWidget:
    """Convierte el selector de componentes en cápsula y desplegable.

    Args:
        selector: El bloque con las superficies y sus componentes.

    Returns:
        El widget con los selectores y el apilador de contenido.
    """
    superficies = []
    for superficie in selector.superficies:
        nombres = [nombre for nombre, _ in superficie.componentes]
        páginas = [_armar_contenido(bloques) for _, bloques in superficie.componentes]
        superficies.append((superficie.etiqueta, nombres, páginas))
    return apilador_componentes(superficies)


def _armar_contenido(bloques: list[Bloque]) -> QtWidgets.QWidget:
    """El contenido de una pestaña o de un componente, apilado.

    Args:
        bloques: Los bloques del contenido.

    Returns:
        El widget con los bloques.
    """
    contenedor = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    _armar_bloques(bloques, layout.addWidget)
    layout.addStretch(1)
    return contenedor


def apilador_componentes(
    superficies: list[tuple[str, list[str], list[QtWidgets.QWidget]]],
) -> QtWidgets.QWidget:
    """El selector de componentes de la página de C&R.

    Muestra de a un componente por vez: una cápsula segmentada elige la
    superficie cuando hay más de una —pared o cubierta en el edificio— y
    un desplegable elige el componente; el contenido de cada uno va en un
    apilador. Cuando sólo hay una superficie la cápsula no aparece y si
    además no tiene componentes —un parapeto solo— la fila de selectores
    se omite.

    Args:
        superficies: Por cada superficie, su etiqueta, los nombres de sus
            componentes y la página de cada uno, en el mismo orden.

    Returns:
        El widget con los selectores y el apilador de contenido.
    """
    apilador = QtWidgets.QStackedWidget()
    arranques: list[int] = []
    for _, _, páginas in superficies:
        arranques.append(apilador.count())
        for página in páginas:
            apilador.addWidget(página)

    combo = QtWidgets.QComboBox()
    combo.setProperty("class", "selector-componente")
    combo.setMinimumWidth(ANCHO_SELECTOR)

    fila_selectores = QtWidgets.QWidget()
    layout_selectores = QtWidgets.QHBoxLayout(fila_selectores)
    layout_selectores.setContentsMargins(0, 0, 0, 0)
    layout_selectores.setSpacing(9)

    grupo: QtWidgets.QButtonGroup | None = None
    if len(superficies) > 1:
        grupo = QtWidgets.QButtonGroup(fila_selectores)
        grupo.setExclusive(True)
        segmentos = []
        for indice, (etiqueta, _, _) in enumerate(superficies):
            segmento = crear_segmento(etiqueta)
            # Más bajo que los del panel: acá es un selector de página,
            # no la barra principal.
            segmento.setProperty("compacto", True)
            segmento.setChecked(indice == 0)
            grupo.addButton(segmento, indice)
            segmentos.append(segmento)
        # La cápsula entera mide lo mismo que el desplegable: los
        # segmentos reparten el ancho, con la letra baja del QSS.
        ancho_segmento = (ANCHO_SELECTOR - 3 * (len(segmentos) - 1)) // len(segmentos)
        for segmento in segmentos:
            segmento.setFixedWidth(ancho_segmento)
        layout_selectores.addWidget(crear_capsula(*segmentos))
    layout_selectores.addWidget(combo)
    layout_selectores.addStretch(1)

    estado = {"superficie": 0}

    def _mostrar_superficie(indice: int) -> None:
        """Conmuta la superficie: repuebla el desplegable con sus
        componentes y muestra el primero."""
        estado["superficie"] = indice
        nombres = superficies[indice][1]
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(nombres)
        combo.blockSignals(False)
        combo.setVisible(bool(nombres))
        apilador.setCurrentIndex(arranques[indice])

    def _mostrar_componente(indice: int) -> None:
        """Muestra la página del componente elegido de la superficie."""
        apilador.setCurrentIndex(arranques[estado["superficie"]] + indice)

    if grupo is not None:
        grupo.idClicked.connect(_mostrar_superficie)
    combo.currentIndexChanged.connect(_mostrar_componente)
    _mostrar_superficie(0)

    contenedor = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(9)
    if grupo is not None or any(nombres for _, nombres, _ in superficies):
        layout.addWidget(fila_selectores)
    layout.addWidget(apilador)
    return contenedor


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
        if titulo:
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

        # El contenido del reporte va un punto más grande que el resto de
        # la interfaz: es la letra que se lee de corrido, no la del chrome.
        fuente = self.font()
        fuente.setPointSize(fuente.pointSize() + 1)
        self.setFont(fuente)

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
