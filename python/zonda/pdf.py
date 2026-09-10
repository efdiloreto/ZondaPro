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

"""La exportación del reporte a PDF con el motor de texto nativo de Qt.

El documento se construye con la API de texto enriquecido de Qt
(``QTextCursor``, ``QTextTable``, ``QTextCharFormat``) recorriendo el
modelo de :mod:`zonda.widgets.reportes.documento`, y se escribe con
``QPdfWriter``: el resultado es un PDF vectorial con texto seleccionable,
no una impresión de widgets ni una imagen.

El pie de página se dibuja con ``QPainter`` sobre cada página: la firma
"Zonda {versión}" en Oswald a la izquierda y la numeración a la derecha,
alineados con los márgenes del contenido, y la línea corriendo de borde
a borde de la hoja. Los márgenes los fija este módulo, de modo que el
pie nunca queda cortado ni pisa el contenido.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui

from zonda import __acercade__, recursos
from zonda.widgets.reportes import documento

if TYPE_CHECKING:
    pass

# La paleta del documento: texto en negro, grises para los fondos y
# líneas, y rojo sólo para el empuje máximo de las tablas.
_TEXTO = "#1a1a1a"
_GRIS = "#555555"
_BORDE = "#cfcfcf"
_ZEBRA = "#f2f2f2"
_FONDO_ENCABEZADO = "#e4e4e4"
_FONDO_NOTA = "#f5f5f5"
_COLOR_MAXIMO = "#a5373d"
_COLOR_MINIMO = "#4d4d4d"

# Los márgenes de la hoja y la altura del pie, en milímetros. Los fija
# este módulo: el pie se dibuja dentro del margen inferior y no depende
# de la configuración de impresora.
_MARGEN_MM = 18.0
_PIE_MM = 10.0
_RESOLUCION = 300

_CENTRO = QtGui.QTextBlockFormat()
_CENTRO.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


def texto_pie_version() -> str:
    """La firma del pie: el nombre del programa con su versión.

    Viaja en todas las páginas del PDF y no se puede sacar.

    Returns:
        El texto armado con la versión del programa.
    """
    return f"Zonda {__acercade__.__version__}"


def texto_pie_pagina(numero: int, total: int) -> str:
    """El texto del pie derecho con la numeración.

    Args:
        numero: El número de página, desde 1.
        total: La cantidad total de páginas.

    Returns:
        El texto armado.
    """
    return f"Página {numero} de {total}"


def exportar_pdf(
    documento_reporte: documento.Documento,
    ruta: str,
    layout: QtGui.QPageLayout | None = None,
) -> None:
    """Escribe el documento como PDF en la ruta indicada.

    Args:
        documento_reporte: El modelo del reporte a exportar.
        ruta: La ruta del archivo de salida.
        layout: El papel y la orientación elegidos en la configuración de
            página; por defecto, A4 vertical.

    Raises:
        OSError: Si el archivo no se puede escribir.
    """
    writer = QtGui.QPdfWriter(ruta)
    if layout is not None:
        writer.setPageLayout(layout)
    writer.setPageMargins(
        QtCore.QMarginsF(_MARGEN_MM, _MARGEN_MM, _MARGEN_MM, _MARGEN_MM),
        QtGui.QPageLayout.Unit.Millimeter,
    )
    writer.setResolution(_RESOLUCION)
    doc = crear_documento(documento_reporte, writer)
    _pintar(doc, writer)


def _fuente_base() -> QtGui.QFont:
    """La fuente sans-serif del documento: la propia de cada sistema."""
    fuente = QtGui.QFont()
    fuente.setPointSizeF(10)
    return fuente


def _formato(
    tamaño: float,
    color: str = _TEXTO,
    negrita: bool = False,
    cursiva: bool = False,
) -> QtGui.QTextCharFormat:
    """Un formato de carácter del documento.

    Args:
        tamaño: El tamaño en puntos.
        color: El color del texto.
        negrita: Si el texto va en negrita.
        cursiva: Si el texto va en cursiva.

    Returns:
        El formato armado.
    """
    formato = QtGui.QTextCharFormat()
    formato.setFontPointSize(tamaño)
    formato.setForeground(QtGui.QColor(color))
    if negrita:
        formato.setFontWeight(QtGui.QFont.Weight.Bold)
    if cursiva:
        formato.setFontItalic(True)
    return formato


_FORMATO_TITULO = _formato(16, _TEXTO, negrita=True)
_FORMATO_SUBTITULO = _formato(10, _GRIS)
_FORMATO_SUBTITULO_PORTADA = _formato(10, _GRIS, negrita=True)
_FORMATO_SECCION = _formato(13, _TEXTO, negrita=True)
_FORMATO_GRUPO = _formato(11, _TEXTO, negrita=True)
_FORMATO_REFERENCIA = _formato(8.5, _GRIS, cursiva=True)
_FORMATO_ROTULO = _formato(9, _GRIS, negrita=True)
_FORMATO_CUERPO = _formato(10)
_FORMATO_DATO_ETIQUETA = _formato(9, _GRIS)
_FORMATO_DATO_VALOR = _formato(9)
_FORMATO_CELDA = _formato(8.5)
_FORMATO_ENCABEZADO = _formato(8.5, _TEXTO, negrita=True)
_FORMATO_NOTA_TITULO = _formato(8.5, _GRIS, negrita=True)
_FORMATO_NOTA = _formato(9)
_FORMATO_MAXIMO = _formato(8.5, _COLOR_MAXIMO, negrita=True)
_FORMATO_MINIMO = _formato(8.5, _COLOR_MINIMO, negrita=True)
_FORMATO_PIE = _formato(8.5, _GRIS)

_PARRAFO = QtGui.QTextBlockFormat()
_PARRAFO.setBottomMargin(8)
_SECCION_BLOQUE = QtGui.QTextBlockFormat()
_SECCION_BLOQUE.setTopMargin(28)
_SECCION_BLOQUE.setBottomMargin(8)
_BLOQUE_PRIMERA_SECCION = QtGui.QTextBlockFormat()
_BLOQUE_PRIMERA_SECCION.setTopMargin(60)
_BLOQUE_PRIMERA_SECCION.setBottomMargin(8)
_GRUPO_BLOQUE = QtGui.QTextBlockFormat()
_GRUPO_BLOQUE.setTopMargin(20)
_GRUPO_BLOQUE.setBottomMargin(4)
_REFERENCIA_BLOQUE = QtGui.QTextBlockFormat()
_REFERENCIA_BLOQUE.setBottomMargin(12)
_SUBTITULO_BLOQUE = QtGui.QTextBlockFormat()
_SUBTITULO_BLOQUE.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
_SUBTITULO_BLOQUE.setBottomMargin(36)


class _Documento:
    """El armado del ``QTextDocument`` desde el modelo.

    Mantiene el cursor al final del documento entre elementos: las
    tablas devuelven el cursor pasado a la línea siguiente a la tabla,
    que es el único punto donde el cursor de Qt queda dentro de la
    estructura.
    """

    def __init__(self) -> None:
        self.doc = QtGui.QTextDocument()
        self.doc.setDefaultFont(_fuente_base())
        self.doc.setDocumentMargin(0)
        self.cursor = QtGui.QTextCursor(self.doc)
        self._primero = True

    def _preparar_bloque(self, bloque: QtGui.QTextBlockFormat | None = None) -> None:
        """Abre un párrafo nuevo con el formato dado, si no es el
        primero del documento."""
        if self._primero:
            self._primero = False
            if bloque is not None:
                self.cursor.setBlockFormat(bloque)
            return
        self.cursor.insertBlock(bloque or _PARRAFO)

    def texto(
        self,
        texto: str,
        formato: QtGui.QTextCharFormat,
        bloque: QtGui.QTextBlockFormat | None = None,
    ) -> None:
        """Inserta un párrafo de texto plano."""
        self._preparar_bloque(bloque)
        self.cursor.setCharFormat(formato)
        self.cursor.insertText(texto, formato)

    def html(self, texto: str) -> None:
        """Inserta un fragmento de texto enriquecido."""
        self._preparar_bloque()
        self.cursor.insertHtml(texto)

    def tabla(self, tabla: documento.Tabla) -> None:
        """Inserta una tabla de resultados con encabezado repetible.

        La primera fila viaja como encabezado (``setHeaderRowCount``),
        así que Qt la repite cuando la tabla salta de página.
        """
        filas = len(tabla.filas) + 1
        columnas = len(tabla.columnas)
        formato = QtGui.QTextTableFormat()
        formato.setBorder(0)
        formato.setCellSpacing(0)
        formato.setCellPadding(4)
        formato.setTopMargin(16)
        formato.setBottomMargin(20)
        formato.setWidth(
            QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 100)
        )
        formato.setColumnWidthConstraints(_anchos_relativos(tabla))
        formato.setHeaderRowCount(1)
        tabla_qt = self.cursor.insertTable(filas, columnas, formato)
        assert tabla_qt is not None

        for columna, titulo in enumerate(tabla.columnas):
            celda = tabla_qt.cellAt(0, columna)
            formato_celda = QtGui.QTextTableCellFormat()
            formato_celda.setBackground(QtGui.QColor(_FONDO_ENCABEZADO))
            celda.setFormat(formato_celda)
            cursor_celda = celda.firstCursorPosition()
            cursor_celda.setBlockFormat(_CENTRO)
            cursor_celda.setCharFormat(_FORMATO_ENCABEZADO)
            cursor_celda.insertText(titulo, _FORMATO_ENCABEZADO)

        for numero_fila, fila in enumerate(tabla.filas, start=1):
            zebra = numero_fila % 2 == 0
            for columna, valor in enumerate(fila):
                texto, clase = (
                    (valor.texto, valor.clase)
                    if isinstance(valor, documento.Celda)
                    else (valor, None)
                )
                celda = tabla_qt.cellAt(numero_fila, columna)
                formato_celda = QtGui.QTextTableCellFormat()
                if zebra:
                    formato_celda.setBackground(QtGui.QColor(_ZEBRA))
                formato_celda.setBottomBorder(0.6)
                formato_celda.setBottomBorderBrush(QtGui.QColor(_BORDE))
                formato_celda.setBottomBorderStyle(
                    QtGui.QTextFrameFormat.BorderStyle.BorderStyle_Solid
                )
                celda.setFormat(formato_celda)
                cursor_celda = celda.firstCursorPosition()
                cursor_celda.setBlockFormat(_CENTRO)
                if clase == "maximo":
                    cursor_celda.setCharFormat(_FORMATO_MAXIMO)
                    cursor_celda.insertText(texto, _FORMATO_MAXIMO)
                elif clase == "minimo":
                    cursor_celda.setCharFormat(_FORMATO_MINIMO)
                    cursor_celda.insertText(texto, _FORMATO_MINIMO)
                else:
                    cursor_celda.setCharFormat(_FORMATO_CELDA)
                    cursor_celda.insertText(texto, _FORMATO_CELDA)

        self.cursor = tabla_qt.lastCursorPosition()
        self.cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock)

    def datos(self, datos: documento.Datos) -> None:
        """Inserta pares etiqueta-valor, sin bordes."""
        formato = QtGui.QTextTableFormat()
        formato.setBorder(0)
        formato.setCellSpacing(0)
        formato.setCellPadding(2)
        formato.setTopMargin(4)
        formato.setBottomMargin(12)
        formato.setWidth(QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 78))
        ancho_etiqueta = QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 52)
        ancho_valor = QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 48)
        formato.setColumnWidthConstraints([ancho_etiqueta, ancho_valor])
        tabla_qt = self.cursor.insertTable(len(datos.filas), 2, formato)
        assert tabla_qt is not None
        for fila, (etiqueta, valor) in enumerate(datos.filas):
            cursor_etiqueta = tabla_qt.cellAt(fila, 0).firstCursorPosition()
            cursor_etiqueta.setCharFormat(_FORMATO_DATO_ETIQUETA)
            cursor_etiqueta.insertText(etiqueta, _FORMATO_DATO_ETIQUETA)
            cursor_valor = tabla_qt.cellAt(fila, 1).firstCursorPosition()
            cursor_valor.setCharFormat(_FORMATO_DATO_VALOR)
            cursor_valor.insertText(valor, _FORMATO_DATO_VALOR)
        self.cursor = tabla_qt.lastCursorPosition()
        self.cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock)

    def nota(self, nota: documento.Nota) -> None:
        """Inserta una nota destacada en un recuadro suave."""
        formato = QtGui.QTextTableFormat()
        formato.setBorder(0)
        formato.setCellSpacing(0)
        formato.setCellPadding(6)
        formato.setTopMargin(12)
        formato.setBottomMargin(16)
        formato.setWidth(
            QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 100)
        )
        tabla_qt = self.cursor.insertTable(1, 1, formato)
        assert tabla_qt is not None
        celda = tabla_qt.cellAt(0, 0)
        formato_celda = QtGui.QTextTableCellFormat()
        formato_celda.setBackground(QtGui.QColor(_FONDO_NOTA))
        celda.setFormat(formato_celda)
        cursor_celda = celda.firstCursorPosition()
        cursor_celda.setCharFormat(_FORMATO_NOTA_TITULO)
        cursor_celda.insertText(nota.titulo, _FORMATO_NOTA_TITULO)
        cursor_celda.insertBlock()
        cursor_celda.setCharFormat(_FORMATO_NOTA)
        cursor_celda.insertText(nota.texto, _FORMATO_NOTA)
        self.cursor = tabla_qt.lastCursorPosition()
        self.cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock)

    def bloques(self, bloques: list[documento.Bloque]) -> None:
        """Inserta una lista de bloques del modelo, en orden."""
        for bloque in bloques:
            self.bloque(bloque)

    def bloque(self, bloque: documento.Bloque) -> None:
        """Inserta un bloque del modelo, según su tipo."""
        if isinstance(bloque, documento.Grupo):
            if bloque.titulo:
                self.texto(bloque.titulo, _FORMATO_GRUPO, _GRUPO_BLOQUE)
            if bloque.referencia:
                self.texto(
                    f"Ref: {bloque.referencia}", _FORMATO_REFERENCIA, _REFERENCIA_BLOQUE
                )
            self.bloques(bloque.bloques)
        elif isinstance(bloque, documento.Datos):
            self.datos(bloque)
        elif isinstance(bloque, documento.Tabla):
            self.tabla(bloque)
        elif isinstance(bloque, documento.Tarjetas):
            # Las tarjetas son la forma de resumen de la pantalla: el
            # PDF no exporta la página de resumen y acá no llegan.
            pass
        elif isinstance(bloque, documento.Nota):
            self.nota(bloque)
        elif isinstance(bloque, documento.Texto):
            self.html(bloque.texto)
        elif isinstance(bloque, documento.Titulo):
            self.texto(bloque.texto, _FORMATO_ROTULO)
        elif isinstance(bloque, documento.Pestanas):
            for etiqueta, bloques in bloque.items:
                self.texto(etiqueta, _FORMATO_GRUPO, _GRUPO_BLOQUE)
                self.bloques(bloques)
        elif isinstance(bloque, documento.SelectorComponentes):
            for superficie in bloque.superficies:
                self.texto(superficie.etiqueta, _FORMATO_GRUPO, _GRUPO_BLOQUE)
                for _, bloques in superficie.componentes:
                    self.bloques(bloques)


def crear_documento(
    documento_reporte: documento.Documento,
    dispositivo: QtGui.QPaintDevice,
) -> QtGui.QTextDocument:
    """Construye el ``QTextDocument`` del reporte.

    Args:
        documento_reporte: El modelo del reporte.
        dispositivo: El dispositivo de pintura (el ``QPdfWriter``), para
            que las métricas de las fuentes coincidan con la salida.

    Returns:
        El documento armado, sin paginar.
    """
    armado = _Documento()
    layout = armado.doc.documentLayout()
    assert layout is not None
    layout.setPaintDevice(dispositivo)

    armado.texto(documento_reporte.titulo, _FORMATO_TITULO, _CENTRO)
    armado.texto("CIRSOC 102-2025", _FORMATO_SUBTITULO_PORTADA, _SUBTITULO_BLOQUE)

    primera_seccion = True
    for pagina in documento_reporte.paginas:
        if not pagina.exportable:
            continue
        # La primera sección abre con más aire, para que el título de la
        # portada no quede pegado a los datos que le siguen.
        bloque_seccion = _BLOQUE_PRIMERA_SECCION if primera_seccion else _SECCION_BLOQUE
        primera_seccion = False
        armado.texto(pagina.titulo, _FORMATO_SECCION, bloque_seccion)
        if pagina.descripcion:
            armado.texto(pagina.descripcion, _FORMATO_SUBTITULO)
        armado.bloques(pagina.bloques)
    return armado.doc


def _anchos_relativos(
    tabla: documento.Tabla,
) -> list[QtGui.QTextLength]:
    """Los anchos porcentuales de las columnas de una tabla.

    Mide el contenido de cada columna con las métricas de la fuente de
    celda y reparte el 100 % en proporción, con un piso para que los
    títulos apretados no se vuelvan ilegibles.

    Args:
        tabla: La tabla del modelo.

    Returns:
        Las restricciones de ancho para el formato de tabla.
    """
    metricas = QtGui.QFontMetricsF(_FORMATO_CELDA.font())
    anchos = []
    for columna, titulo in enumerate(tabla.columnas):
        ancho = metricas.horizontalAdvance(titulo)
        for fila in tabla.filas:
            valor = fila[columna]
            texto = valor.texto if isinstance(valor, documento.Celda) else valor
            ancho = max(ancho, metricas.horizontalAdvance(texto))
        anchos.append(ancho + 16)
    total = sum(anchos)
    piso = 7.0
    reparto = [max(piso, 100 * ancho / total) for ancho in anchos]
    escala = 100 / sum(reparto)
    return [
        QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, ancho * escala)
        for ancho in reparto
    ]


def _pintar(doc: QtGui.QTextDocument, writer: QtGui.QPdfWriter) -> None:
    """Pagina el documento y lo escribe en el PDF, con el pie por página.

    Args:
        doc: El documento ya armado.
        writer: El escritor de PDF destino.
    """
    layout = writer.pageLayout()
    dpi = writer.resolution()
    contenido = layout.paintRectPixels(dpi)
    doc.setPageSize(QtCore.QSizeF(contenido.width(), contenido.height()))
    total = doc.pageCount()

    px_mm = dpi / 25.4
    margen = round(_MARGEN_MM * px_mm)
    base_pie = round(contenido.height() + (_MARGEN_MM - _PIE_MM) * px_mm)

    painter = QtGui.QPainter(writer)
    try:
        for numero in range(total):
            if numero:
                writer.newPage()
            painter.save()
            painter.translate(0, -numero * contenido.height())
            doc.drawContents(
                painter,
                QtCore.QRectF(
                    0,
                    numero * contenido.height(),
                    contenido.width(),
                    contenido.height(),
                ),
            )
            painter.restore()
            # La línea del pie corre de borde a borde de la hoja; los
            # textos quedan alineados con los márgenes del contenido.
            _pie(painter, margen, contenido.width(), base_pie, numero + 1, total)
    finally:
        painter.end()


@functools.cache
def _familia_oswald() -> str:
    """La familia de la tipografía de la marca, Oswald.

    Se carga de los recursos empaquetados al primer uso, con la
    aplicación ya creada: ``QFontDatabase`` la necesita viva. La
    aplicación ya la registra al arrancar; registrarla de nuevo es
    inocuo, así que el PDF sale bien aunque se exporte en un test sin la
    ventana de arranque.
    """
    identificador = QtGui.QFontDatabase.addApplicationFont(
        str(recursos.ruta("fuentes/Oswald-VariableFont_wght.ttf"))
    )
    familias = QtGui.QFontDatabase.applicationFontFamilies(identificador)
    return familias[0] if familias else _fuente_base().families()[0]


def _pie(
    painter: QtGui.QPainter,
    margen: int,
    ancho: int,
    base: int,
    numero: int,
    total: int,
) -> None:
    """Dibuja el pie de una página.

    La firma con la versión va a la izquierda, en Oswald y alineada con
    el margen izquierdo del contenido, y la numeración a la derecha,
    alineada con el margen derecho; la línea corre de borde a borde del
    papel.

    Args:
        painter: El pintor del escritor de PDF, ya ubicado en la página.
        margen: El margen lateral del contenido, en píxeles; los textos
            del pie arrancan ahí y la línea lo excede hasta el borde.
        ancho: El ancho del área de contenido.
        base: La línea base del texto del pie.
        numero: El número de página, desde 1.
        total: La cantidad total de páginas.
    """
    fuente = QtGui.QFont(_FORMATO_PIE.font())
    fuente.setPointSizeF(8.5)
    painter.setFont(fuente)
    dispositivo = painter.device()
    assert dispositivo is not None
    metricas = QtGui.QFontMetricsF(fuente, dispositivo)
    painter.setPen(QtGui.QColor(_GRIS))

    px_mm = dispositivo.logicalDpiY() / 25.4
    firma = texto_pie_version()
    pagina = texto_pie_pagina(numero, total)

    fuente_firma = QtGui.QFont(_familia_oswald())
    fuente_firma.setPointSizeF(10)
    painter.setFont(fuente_firma)
    painter.drawText(QtCore.QPointF(0, base), firma)
    painter.setFont(fuente)
    painter.drawText(
        QtCore.QPointF(ancho - metricas.horizontalAdvance(pagina), base), pagina
    )

    linea = QtGui.QPen(QtGui.QColor(_BORDE), 0.8)
    painter.setPen(linea)
    # La línea queda bien arriba del texto: la firma y la numeración no
    # deben pegarse a ella.
    y_linea = base - 7 * px_mm
    painter.drawLine(
        QtCore.QPointF(-margen, y_linea), QtCore.QPointF(ancho + margen, y_linea)
    )
