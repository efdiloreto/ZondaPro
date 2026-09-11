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

"""El documento de reporte y su exportación a PDF.

Los módulos por tipología arman el modelo de
:mod:`zonda.widgets.reportes.documento` desde ``estructura.resultados*``,
que la vista en pantalla y el exportador a PDF consumen por igual. Acá se
verifica la estructura del documento por tipología, los datos que viajan
a la portada, el pie con la versión de Zonda y la numeración de páginas,
y que el PDF salga bien formado.
"""

from collections.abc import Iterator

import pytest
from PyQt6 import QtCore, QtGui

import zonda.enums as enums
from zonda import __acercade__, pdf
from zonda.cirsoc import Cartel
from zonda.widgets.reportes import cartel as reporte_cartel
from zonda.widgets.reportes import cubierta_aislada as reporte_cubierta_aislada
from zonda.widgets.reportes import documento as modelo
from zonda.widgets.reportes import edificio as reporte_edificio
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.documento import (
    Documento,
    Grupo,
    Nota,
    Pagina,
    Tabla,
    Texto,
)

from .conftest import SIN_OPENGL

necesita_opengl = pytest.mark.skipif(
    SIN_OPENGL,
    reason="la vista 3D necesita un contexto gráfico real",
)


# --- Helpers -------------------------------------------------------------


def pagina(doc: Documento, titulo: str) -> Pagina:
    """La página del documento con el título dado."""
    return next(pagina for pagina in doc.paginas if pagina.titulo == titulo)


def bloques_de_tipo(bloques: list, clase: type) -> Iterator:
    """Recorre los bloques en profundidad y devuelve los de una clase.

    Args:
        bloques: Los bloques a recorrer.
        clase: La clase de bloque buscada.

    Yields:
        Los bloques de la clase, en orden de aparición.
    """
    for bloque in bloques:
        if isinstance(bloque, clase):
            yield bloque
        if isinstance(bloque, modelo.Grupo):
            yield from bloques_de_tipo(bloque.bloques, clase)
        elif isinstance(bloque, modelo.Pestanas):
            for _, contenido in bloque.items:
                yield from bloques_de_tipo(contenido, clase)
        elif isinstance(bloque, modelo.SelectorComponentes):
            for superficie in bloque.superficies:
                for _, contenido in superficie.componentes:
                    yield from bloques_de_tipo(contenido, clase)


def tablas_de_pagina(doc: Documento, titulo_pagina: str) -> Iterator[Tabla]:
    """Las tablas de una página del documento."""
    return bloques_de_tipo(pagina(doc, titulo_pagina).bloques, modelo.Tabla)


def grupos_de_pagina(doc: Documento, titulo_pagina: str) -> Iterator[Grupo]:
    """Los grupos de una página del documento."""
    return bloques_de_tipo(pagina(doc, titulo_pagina).bloques, modelo.Grupo)


def notas_de_pagina(doc: Documento, titulo_pagina: str) -> Iterator[Nota]:
    """Las notas de una página del documento."""
    return bloques_de_tipo(pagina(doc, titulo_pagina).bloques, modelo.Nota)


def etiquetas(tabla: Tabla, columna: int = 0) -> list[str]:
    """Los textos de la primera columna de la tabla."""
    valores = [fila[columna] for fila in tabla.filas]
    return [
        valor.texto if isinstance(valor, modelo.Celda) else valor for valor in valores
    ]


# --- El documento por tipología ------------------------------------------


def test_el_documento_del_edificio_arma_las_paginas(edificio):
    doc = reporte_edificio.documento(edificio)
    nombres = [pagina.titulo for pagina in doc.paginas]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones - SPRFV",
        "Componentes (C&R)",
    ]
    # El resumen es para leer en pantalla: es la única página que no
    # viaja al PDF.
    assert [pagina.exportable for pagina in doc.paginas] == [
        False,
        True,
        True,
        True,
        True,
    ]


def test_el_resumen_del_edificio_destaca_los_extremos(edificio):
    doc = reporte_edificio.documento(edificio)
    tarjetas = bloques_de_tipo(pagina(doc, "Resumen").bloques, modelo.Tarjetas)
    valores = [tarjeta.valor for bloque in tarjetas for tarjeta in bloque.tarjetas]
    assert f"{edificio.velocidad:.2f} m/s" in valores
    assert any(texto.startswith("±") for texto in valores)
    assert any(texto.startswith(("+", "-")) for texto in valores)


def test_las_presiones_sprfv_del_edificio_traen_todas_las_direcciones(edificio):
    doc = reporte_edificio.documento(edificio)
    pestanas = list(
        bloques_de_tipo(pagina(doc, "Presiones - SPRFV").bloques, modelo.Pestanas)
    )
    assert len(pestanas) == 1
    etiquetas_pestanas = [etiqueta for etiqueta, _ in pestanas[0].items]
    assert etiquetas_pestanas == [
        f"{direccion.value.capitalize()} a la cumbrera"
        for direccion in enums.DireccionVientoMetodoDireccionalSprfv
    ]
    tablas_sprfv = list(tablas_de_pagina(doc, "Presiones - SPRFV"))
    assert tablas_sprfv
    # Las paredes a barlovento van por altura y traen los dos signos.
    primera = tablas_sprfv[0]
    assert primera.columnas[0] == "Alturas (m)"
    assert "pn [+GCpi]" in primera.columnas[5]
    assert "pn [-GCpi]" in primera.columnas[6]


def test_el_caso_positivo_se_nombra_con_angulo_menor_a_diez(
    edificio_angulo_pequeno,
):
    """El reporte lista el caso de presión positiva de la cubierta < 10°."""
    doc = reporte_edificio.documento(edificio_angulo_pequeno)
    titulos = [grupo.titulo for grupo in grupos_de_pagina(doc, "Presiones - SPRFV")]
    assert any("presión positiva" in titulo.lower() for titulo in titulos)


def test_el_positivo_propio_de_la_zona_va_marcado(edificio_con_parapeto):
    """Con parapeto, las Zonas 2 y 3 llevan dos filas y hay que
    diferenciarlas: la Nota 5 de la Figura 5.3-2A les da un positivo
    propio, así que la tabla deja de tener una sola fila."""
    doc = reporte_edificio.documento(edificio_con_parapeto)
    filas = [etiquetas(tabla) for tabla in tablas_de_pagina(doc, "Componentes (C&R)")]
    planas = [texto for filas_tabla in filas for texto in filas_tabla]
    assert "2 (positiva)" in planas
    assert "3 (positiva)" in planas
    # La Zona 1 conserva el positivo único que viaja en "todas".
    assert "1 (positiva)" not in planas


def test_el_documento_del_cartel_arma_las_paginas(cartel):
    doc = reporte_cartel.documento(cartel)
    nombres = [pagina.titulo for pagina in doc.paginas]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones",
    ]
    titulos = [grupo.titulo for grupo in grupos_de_pagina(doc, "Presiones")]
    assert "Caso A" in titulos
    assert "Caso B" in titulos
    assert "Caso C" in titulos


def test_el_resumen_del_cartel_destaca_la_fuerza_de_diseño(cartel):
    doc = reporte_cartel.documento(cartel)
    tarjetas = list(bloques_de_tipo(pagina(doc, "Resumen").bloques, modelo.Tarjetas))
    destacadas = [
        tarjeta.titulo
        for bloque in tarjetas
        for tarjeta in bloque.tarjetas
        if tarjeta.destacada
    ]
    fuerzas = cartel.presiones.fuerzas_totales
    caso_c_gobierna = (
        fuerzas.get(enums.CasoCartel.CASO_C, 0) > fuerzas[enums.CasoCartel.CASO_A]
    )
    if caso_c_gobierna:
        assert "Fuerza Caso C" in destacadas
    else:
        assert "Fuerza Caso A" in destacadas


def test_el_cartel_trae_las_regiones_del_caso_c_y_las_consideraciones(cartel):
    doc = reporte_cartel.documento(cartel)
    tablas_presiones = list(tablas_de_pagina(doc, "Presiones"))
    caso_c = tablas_presiones[2]
    # La fixture tiene B/s = 2, así que el Caso C trae sus dos regiones.
    assert len(caso_c.filas) == len(
        cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_C)
    )
    assert caso_c.filas[0][0].endswith("m")
    textos = list(bloques_de_tipo(pagina(doc, "Presiones").bloques, Texto))
    assert len(textos) == 1
    assert "Caso C (B/s ≥ 2)" in textos[0].texto
    # La conclusión del diseño cierra el resumen y también viaja en las
    # consideraciones, resaltada.
    conclusiones = [
        nota.texto
        for nota in notas_de_pagina(doc, "Resumen")
        if "fuerza de diseño" in nota.texto.lower()
    ]
    assert conclusiones
    assert "<b>" in textos[0].texto


def test_el_cartel_sin_caso_c_no_lo_considera():
    """Con B/s < 2 el Caso C no se considera y el reporte lo dice."""
    cartel = Cartel(
        profundidad=1,
        ancho=8,
        altura_inferior=5,
        altura_superior=10,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    doc = reporte_cartel.documento(cartel)
    titulos = [grupo.titulo for grupo in grupos_de_pagina(doc, "Presiones")]
    assert "Caso C" not in titulos
    textos = list(bloques_de_tipo(pagina(doc, "Presiones").bloques, Texto))
    assert "no corresponde considerar el Caso C" in textos[0].texto


def test_el_cartel_con_topografia_muestra_los_datos(cartel_con_topografia):
    """El documento tiene que poder mostrar los datos de topografía del
    cartel."""
    doc = reporte_cartel.documento(cartel_con_topografia)
    bloques_datos = list(
        bloques_de_tipo(pagina(doc, "Datos de entrada").bloques, modelo.Datos)
    )
    valores = [valor for bloque in bloques_datos for _, valor in bloque.filas]
    assert "50.00 m" in valores
    assert "20.00 m" in valores


def test_la_cubierta_aislada_arma_las_paginas(cubierta_aislada_con_componentes):
    doc = reporte_cubierta_aislada.documento(cubierta_aislada_con_componentes)
    nombres = [pagina.titulo for pagina in doc.paginas]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones normales",
        "Presiones laterales",
        "Componentes (C&R)",
    ]
    pestanas = list(
        bloques_de_tipo(pagina(doc, "Presiones normales").bloques, modelo.Pestanas)
    )
    assert len(pestanas[0].items) == len(enums.DireccionVientoCubiertaAislada)
    # El título de la dirección viaja en la pestaña: el grupo de adentro
    # no lo repite, sólo lleva la referencia al Reglamento.
    for etiqueta, bloques in pestanas[0].items:
        (grupo,) = bloques
        assert grupo.titulo == ""
        assert grupo.referencia
        assert f"Viento {etiqueta}" not in grupo.titulo
    # Cada zona de componentes trae su positivo y su negativo, con la
    # distancia "a" en la referencia.
    selector = next(
        bloques_de_tipo(
            pagina(doc, "Componentes (C&R)").bloques, modelo.SelectorComponentes
        )
    )
    nombres_componentes = [
        nombre
        for superficie in selector.superficies
        for nombre, _ in superficie.componentes
    ]
    assert nombres_componentes == ["Chapa", "Correa"]
    tabla = next(tablas_de_pagina(doc, "Componentes (C&R)"))
    planas = etiquetas(tabla)
    assert "1 (positiva)" in planas
    assert "1 (negativa)" in planas
    assert "3 (positiva)" in planas
    assert "3 (negativa)" in planas
    grupos_componentes = list(grupos_de_pagina(doc, "Componentes (C&R)"))
    assert any("a: 1.00 m" in (grupo.referencia or "") for grupo in grupos_componentes)


def test_la_cubierta_aislada_sin_componentes_no_trae_la_seccion(cubierta_aislada):
    """Sin componentes cargados, la sección de C&R no aparece."""
    doc = reporte_cubierta_aislada.documento(cubierta_aislada)
    assert [pagina.titulo for pagina in doc.paginas][-1] == "Presiones laterales"


def test_la_tabla_de_rafaga_de_estructura_flexible_trae_resonancia():
    from zonda.cirsoc.factores import Rafaga

    flexible = Rafaga(
        20,
        30,
        7,
        4.2,
        45,
        0.5,
        0.02,
        enums.Flexibilidad.FLEXIBLE,
        False,
        enums.CategoriaExposicion.B,
    )
    tabla = tablas.tabla_rafaga(flexible, enums.Flexibilidad.FLEXIBLE)
    assert "gR" in tabla.columnas
    assert "R" in tabla.columnas

    rigida = Rafaga(
        20,
        30,
        7,
        4.2,
        45,
        0.5,
        0.02,
        enums.Flexibilidad.RIGIDA,
        False,
        enums.CategoriaExposicion.B,
    )
    tabla = tablas.tabla_rafaga(rigida, enums.Flexibilidad.RIGIDA)
    assert "gR" not in tabla.columnas


# --- La portada, el pie y el PDF -----------------------------------------


def test_la_portada_lleva_el_titulo_y_el_reglamento(qapp, edificio):
    """El documento abre con el título y el reglamento; no hay grupo de
    datos del proyecto ni sección de observaciones."""
    doc = reporte_edificio.documento(edificio)
    texto = pdf.crear_documento(
        doc, QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    ).toPlainText()
    assert doc.titulo in texto
    assert "CIRSOC 102-2025" in texto
    assert "Datos de Proyecto" not in texto
    assert "Proyectista" not in texto
    assert "Observaciones" not in texto
    assert "Máxima presión" not in texto


def test_el_pie_lleva_la_version_y_la_numeracion():
    """La firma con la versión de Zonda y la numeración de páginas no
    se pueden sacar: las dibuja el exportador en todas las páginas."""
    assert pdf.texto_pie_version() == f"Zonda {__acercade__.__version__}"
    assert pdf.texto_pie_pagina(2, 7) == "Página 2 de 7"


def test_exportar_pdf_genera_un_pdf_valido(qapp, edificio, tmp_path):
    destino = tmp_path / "reporte.pdf"
    pdf.exportar_pdf(reporte_edificio.documento(edificio), str(destino))
    contenido = destino.read_bytes()
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 10_000


def test_exportar_pdf_repagina_tablas_largas(qapp, tmp_path):
    """Con h > 20 m las paredes van por altura: las tablas crecen y el
    documento reparte el contenido en varias páginas, repitiendo el
    encabezado de cada tabla."""
    from zonda.cirsoc import Edificio

    edificio = Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=22,
        altura_cumbrera=23,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        componentes_paredes={"Viga": 10.0},
        componentes_cubierta={"Correa": 5.0},
    )
    destino = tmp_path / "reporte-grande.pdf"
    pdf.exportar_pdf(reporte_edificio.documento(edificio), str(destino))
    assert destino.read_bytes().startswith(b"%PDF")

    # En una hoja chica, el mismo documento necesita varias páginas.
    imagen = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    doc = pdf.crear_documento(reporte_edificio.documento(edificio), imagen)
    doc.setPageSize(QtCore.QSizeF(500, 600))
    assert doc.pageCount() > 1
