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

"""El reporte de resultados en pantalla.

Como el reporte nativo lee ``estructura.resultados*`` filtrando y
agrupando la tabla plana, acá se verifica que las tablas muestren las
mismas filas que las plantillas de exportación, que los extremos queden
resaltados y que las páginas de cada tipología armen sus secciones. Son
widgets puros: no necesitan OpenGL ni pandoc (éste sólo participa al
exportar, y lo cubre ``test_reportes.py``).
"""

import pytest
from PyQt6 import QtCore, QtWidgets

from zonda.cirsoc.factores import Rafaga
from zonda.enums import (
    CategoriaExposicion,
    DireccionVientoCubiertaAislada,
    DireccionVientoMetodoDireccionalSprfv,
    Flexibilidad,
    ParedEdificioSprfv,
    ZonaEdificio,
)
from zonda.widgets.reportes import (
    cartel as reporte_cartel,
)
from zonda.widgets.reportes import (
    cubierta_aislada as reporte_cubierta_aislada,
)
from zonda.widgets.reportes import (
    edificio as reporte_edificio,
)
from zonda.widgets.reportes import exportacion, tablas
from zonda.widgets.reportes.exportacion import DialogoExportacion
from zonda.widgets.reportes.navegacion import VistaReporte
from zonda.widgets.reportes.secciones import unidades_desde_settings
from zonda.widgets.reportes.tablas import TablaResultados

from .conftest import SIN_OPENGL

necesita_opengl = pytest.mark.skipif(
    SIN_OPENGL,
    reason="la vista 3D necesita un contexto gráfico real",
)


# --- Helpers -------------------------------------------------------------


def subsecciones(widget: QtWidgets.QWidget) -> list[str]:
    """Los títulos de las subsecciones contenidas en un widget.

    Args:
        widget: La página o vista a recorrer.

    Returns:
        Los títulos, en el orden en que aparecen.
    """
    titulos = []
    for marco in widget.findChildren(QtWidgets.QFrame):
        if marco.property("class") != "subseccion":
            continue
        etiquetas = marco.findChildren(QtWidgets.QLabel)
        if etiquetas:
            titulos.append(etiquetas[0].text())
    return titulos


def resaltadas(tabla: TablaResultados) -> list[tuple[int, int, str]]:
    """Las celdas de la tabla que marcan un extremo.

    Args:
        tabla: La tabla de resultados.

    Returns:
        Los pares fila, columna y texto de cada celda resaltada.
    """
    celdas = []
    for fila in range(tabla.rowCount()):
        for columna in range(tabla.columnCount()):
            item = tabla.item(fila, columna)
            if item is not None and item.font().bold():
                celdas.append((fila, columna, item.text()))
    return celdas


def textos_de_columna(tabla: TablaResultados, columna: int) -> list[str]:
    """Los textos de una columna de la tabla.

    Args:
        tabla: La tabla de resultados.
        columna: El índice de la columna.

    Returns:
        Los textos en el orden de las filas.
    """
    return [tabla.item(fila, columna).text() for fila in range(tabla.rowCount())]


def combo_componentes(página: QtWidgets.QWidget) -> QtWidgets.QComboBox:
    """El desplegable de componentes de una página de C&R.

    Args:
        página: La página de componentes y revestimientos.

    Returns:
        El QComboBox que elige el componente.
    """
    return página.findChildren(QtWidgets.QComboBox)[0]


def apilador_contenido(página: QtWidgets.QWidget) -> QtWidgets.QStackedWidget:
    """El apilador con la página de cada componente.

    Args:
        página: La página de componentes y revestimientos.

    Returns:
        El QStackedWidget que muestra el componente elegido.
    """
    return página.findChildren(QtWidgets.QStackedWidget)[0]


# --- TablaResultados -----------------------------------------------------


def test_las_celdas_no_se_editan(qapp):
    tabla = TablaResultados(("A", "B"), [["1", "2"]])
    banderas = tabla.item(0, 0).flags()
    assert not (banderas & QtCore.Qt.ItemFlag.ItemIsEditable)


def test_las_filas_tienen_aire_y_la_tabla_ocupa_el_ancho(qapp, edificio):
    """Las filas no van apretadas y las columnas llenan el viewport.

    El alto de fila es uniforme —mínimo 28 px— y al cambiar el tamaño del
    widget el sobrante del viewport se reparte entre las columnas, de modo
    que la tabla ocupe todo el ancho disponible.
    """
    barlovento = edificio.resultados_sprfv.filtrar(
        direccion=DireccionVientoMetodoDireccionalSprfv.PARALELO,
        zona=ZonaEdificio.PAREDES,
        pared=ParedEdificioSprfv.BARLOVENTO,
    )
    tabla = tablas.tabla_presiones(barlovento, unidades_desde_settings())
    assert all(tabla.rowHeight(fila) >= 28 for fila in range(tabla.rowCount()))

    # Un widget oculto no recibe resizeEvent, así que la prueba la muestra
    # para pasar por el reparto real de anchos.
    tabla.show()
    try:
        tabla.resize(800, tabla.height())
        qapp.processEvents()
        ancho_columnas = sum(
            tabla.columnWidth(columna) for columna in range(tabla.columnCount())
        )
        assert ancho_columnas >= 780

        # Si el ancho no alcanza, las columnas vuelven al ancho de
        # contenido y es la página la que se desplaza horizontal.
        anchos_base = list(tabla._anchos_base)
        tabla.resize(100, tabla.height())
        qapp.processEvents()
        assert [
            tabla.columnWidth(columna) for columna in range(tabla.columnCount())
        ] == anchos_base
    finally:
        tabla.close()
        tabla.deleteLater()


def test_los_extremos_de_la_columna_quedan_resaltados(qapp, edificio):
    """La máxima presión y la máxima succión de cada columna llevan negrita.

    Con presión interna, la columna positiva resalta su máximo y la
    negativa su mínimo, y el texto resaltado coincide con el extremo.
    """
    _, filas = edificio.resultados_sprfv.filtrar(
        direccion=DireccionVientoMetodoDireccionalSprfv.PARALELO,
        zona=ZonaEdificio.CUBIERTA,
    ).agrupar("posicion", "caso")[0]
    tabla = tablas.tabla_presiones(filas, unidades_desde_settings())
    indice_pos = tabla.columnCount() - 2
    indice_neg = tabla.columnCount() - 1

    valores_pos = [float(texto) for texto in textos_de_columna(tabla, indice_pos)]
    valores_neg = [float(texto) for texto in textos_de_columna(tabla, indice_neg)]
    maximo = max(valores_pos)
    minimo = min(valores_neg)

    celdas = resaltadas(tabla)
    if maximo > 0:
        assert (valores_pos.index(maximo), indice_pos, f"{maximo:.2f}") in celdas
    if minimo < 0:
        assert (valores_neg.index(minimo), indice_neg, f"{minimo:.2f}") in celdas


def test_la_tabla_de_presiones_adapta_las_columnas(qapp, edificio):
    """Las paredes a barlovento van por altura y traen los dos signos."""
    unidades = unidades_desde_settings()
    barlovento = edificio.resultados_sprfv.filtrar(
        direccion=DireccionVientoMetodoDireccionalSprfv.PARALELO,
        zona=ZonaEdificio.PAREDES,
        pared=ParedEdificioSprfv.BARLOVENTO,
    )
    tabla = tablas.tabla_presiones(barlovento, unidades)
    assert tabla.horizontalHeaderItem(0).text() == "Alturas (m)"
    assert tabla.rowCount() == len({fila.q.altura for fila in barlovento})
    assert tabla.horizontalHeaderItem(5).text().startswith("pn [+GCpi]")
    assert tabla.horizontalHeaderItem(6).text().startswith("pn [-GCpi]")


def test_el_positivo_propio_de_la_zona_dice_positiva(qapp, edificio_con_parapeto):
    """Con parapeto de 1 m, la Zona 2 tiene positivo propio (Nota 5).

    Es el mismo caso que la plantilla exporta como "2 (positiva)".
    """
    componentes = edificio_con_parapeto.resultados_componentes.filtrar(
        zona=ZonaEdificio.CUBIERTA
    )
    for _, filas in componentes.agrupar("pared", "componente"):
        tabla = tablas.tabla_presiones(filas, unidades_desde_settings())
        etiquetas = textos_de_columna(tabla, 0)
        assert "2 (positiva)" in etiquetas
        assert "3 (positiva)" in etiquetas
        # La Zona 1 conserva el positivo único que viaja en "todas": su
        # fila no necesita la aclaración.
        assert "1 (positiva)" not in etiquetas


def test_la_tabla_de_componentes_de_cubierta_aislada_trae_ambos_signos(
    qapp, cubierta_aislada_con_componentes
):
    filas = cubierta_aislada_con_componentes.resultados_componentes.filtrar(
        componente="Chapa"
    )
    tabla = tablas.tabla_componentes_cubierta_aislada(filas, unidades_desde_settings())
    etiquetas = textos_de_columna(tabla, 0)
    assert "1 (positiva)" in etiquetas
    assert "1 (negativa)" in etiquetas


def test_la_tabla_de_cubierta_aislada_trae_friccion(qapp, cubierta_aislada):
    filas = cubierta_aislada.resultados.filtrar(
        direccion=DireccionVientoCubiertaAislada.GAMMA_0
    )
    tabla = tablas.tabla_cubierta_aislada(filas, unidades_desde_settings())
    indice_friccion = tabla.columnCount() - 1
    esperado = f"{filas[0].presion_friccion:.2f}"
    assert all(texto == esperado for texto in textos_de_columna(tabla, indice_friccion))


def test_la_tabla_del_cartel_trae_las_regiones_del_caso_c(qapp, cartel):
    from zonda.enums import CasoCartel

    unidades = unidades_desde_settings()
    caso_a = cartel.resultados.filtrar(caso=CasoCartel.CASO_A)
    tabla = tablas.tabla_cartel(caso_a, cartel.cf.limites_regiones, unidades)
    assert tabla.columnCount() == 5
    assert tabla.rowCount() == 1

    if cartel.cf.aplica_caso_c:
        caso_c = cartel.resultados.filtrar(caso=CasoCartel.CASO_C)
        tabla_c = tablas.tabla_cartel(caso_c, cartel.cf.limites_regiones, unidades)
        assert tabla_c.rowCount() == len(caso_c)
        assert tabla_c.item(0, 0).text().endswith("m")


def test_la_tabla_de_rafaga_de_estructura_flexible_trae_resonancia(qapp):
    flexible = Rafaga(
        20,
        30,
        7,
        4.2,
        45,
        0.5,
        0.02,
        Flexibilidad.FLEXIBLE,
        False,
        CategoriaExposicion.B,
    )
    tabla = tablas.tabla_rafaga(flexible, Flexibilidad.FLEXIBLE)
    titulos = [
        tabla.horizontalHeaderItem(columna).text()
        for columna in range(tabla.columnCount())
    ]
    assert "gR" in titulos
    assert "R" in titulos

    rigida = Rafaga(
        20,
        30,
        7,
        4.2,
        45,
        0.5,
        0.02,
        Flexibilidad.RIGIDA,
        False,
        CategoriaExposicion.B,
    )
    tabla = tablas.tabla_rafaga(rigida, Flexibilidad.RIGIDA)
    titulos = [
        tabla.horizontalHeaderItem(columna).text()
        for columna in range(tabla.columnCount())
    ]
    assert "gR" not in titulos


def test_la_tabla_topografica_muestra_los_parametros(qapp, cartel_con_topografia):
    tabla = tablas.tabla_topografia(
        cartel_con_topografia.topografia,
        cartel_con_topografia.topografia.parametros.k3[-1],
    )
    assert tabla.rowCount() == 1
    assert tabla.columnCount() == 7


# --- Las vistas por tipología -------------------------------------------


def test_la_vista_del_edificio_arma_las_paginas(qapp, edificio):
    vista = reporte_edificio.vista(edificio)
    nombres = [vista._menu.item(i).text() for i in range(vista._menu.count())]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones - SPRFV",
        "Componentes (C&R)",
    ]


def test_el_resumen_del_edificio_destaca_los_extremos(qapp, edificio):
    vista = reporte_edificio.vista(edificio)
    resumen = vista._paginas.widget(0)
    valores = [
        etiqueta.text()
        for etiqueta in resumen.findChildren(QtWidgets.QLabel)
        if etiqueta.property("class") == "tarjeta-valor"
    ]
    # La velocidad básica y el coeficiente de presión interna están siempre;
    # el máximo o el mínimo de la tabla aparece con su signo.
    assert f"{edificio.velocidad:.2f} m/s" in valores
    assert any(texto.startswith("±") for texto in valores)
    assert any(texto.startswith(("+", "-")) for texto in valores)


def test_la_pagina_sprfv_del_edificio_con_parapeto_trae_el_parapeto(
    qapp, edificio_plana_con_parapeto
):
    vista = reporte_edificio.vista(edificio_plana_con_parapeto)
    pagina_sprfv = vista._paginas.widget(3)
    assert "Parapeto" in subsecciones(pagina_sprfv)
    # Las notas del Reglamento acompañan a las tablas.
    textos = [
        etiqueta.text() for etiqueta in pagina_sprfv.findChildren(QtWidgets.QLabel)
    ]
    assert any("Art. 2.1.5" in texto for texto in textos)


def test_la_pagina_de_componentes_nombra_los_componentes(qapp, edificio):
    vista = reporte_edificio.vista(edificio)
    pagina_componentes = vista._paginas.widget(4)
    titulos = subsecciones(pagina_componentes)
    assert any(titulo.startswith("Componente: Viga (10 m²)") for titulo in titulos)
    assert any(titulo.startswith("Componente: Correa (5 m²)") for titulo in titulos)


def test_la_pagina_de_componentes_del_edificio_filtra_por_superficie(qapp, edificio):
    """La cápsula elige la superficie y el desplegable queda con sus
    componentes: primero se ve el de pared y al conmutar, el de cubierta.
    """
    vista = reporte_edificio.vista(edificio)
    página = vista._paginas.widget(4)
    combo = combo_componentes(página)
    apilador = apilador_contenido(página)

    # Arranca en el primer componente de pared.
    assert combo.currentText() == "Viga"
    assert subsecciones(apilador.currentWidget()) == ["Componente: Viga (10 m²)"]

    cubierta = next(
        boton
        for boton in página.findChildren(QtWidgets.QPushButton)
        if boton.text() == "CUBIERTA"
    )
    cubierta.click()
    assert combo.currentText() == "Correa"
    assert subsecciones(apilador.currentWidget()) == ["Componente: Correa (5 m²)"]


def test_la_pagina_de_componentes_muestra_el_componente_elegido(
    qapp, cubierta_aislada_con_componentes
):
    """El desplegable conmuta el contenido: sólo se ve la tabla del
    componente seleccionado."""
    vista = reporte_cubierta_aislada.vista(cubierta_aislada_con_componentes)
    página = vista._paginas.widget(5)
    combo = combo_componentes(página)
    apilador = apilador_contenido(página)

    assert combo.currentText() == "Chapa"
    assert subsecciones(apilador.currentWidget()) == ["Componente: Chapa (0.5 m²)"]

    combo.setCurrentIndex(1)
    assert combo.currentText() == "Correa"
    assert subsecciones(apilador.currentWidget()) == ["Componente: Correa (2 m²)"]


def test_la_vista_del_cartel_trae_las_consideraciones(qapp, cartel):
    vista = reporte_cartel.vista(cartel)
    nombres = [vista._menu.item(i).text() for i in range(vista._menu.count())]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones",
    ]
    pagina_presiones = vista._paginas.widget(3)
    assert "Consideraciones" in subsecciones(pagina_presiones)


def test_la_vista_de_la_cubierta_aislada_arma_las_paginas(
    qapp, cubierta_aislada_con_componentes
):
    vista = reporte_cubierta_aislada.vista(cubierta_aislada_con_componentes)
    nombres = [vista._menu.item(i).text() for i in range(vista._menu.count())]
    assert nombres == [
        "Resumen",
        "Datos de entrada",
        "Parámetros de cálculo",
        "Presiones normales",
        "Presiones laterales",
        "Componentes (C&R)",
    ]
    pagina_normales = vista._paginas.widget(3)
    pestañas = pagina_normales.findChildren(QtWidgets.QTabWidget)[0]
    assert pestañas.count() == len(DireccionVientoCubiertaAislada)


def test_la_vista_de_cubierta_aislada_sin_componentes_no_trae_la_pagina(
    qapp, cubierta_aislada
):
    vista = reporte_cubierta_aislada.vista(cubierta_aislada)
    assert vista._menu.count() == 5


def test_la_topografia_no_considerada_se_dice_en_datos(qapp, edificio):
    vista = reporte_edificio.vista(edificio)
    pagina_datos = vista._paginas.widget(1)
    textos = [
        etiqueta.text() for etiqueta in pagina_datos.findChildren(QtWidgets.QLabel)
    ]
    assert "No considerada" in textos


def test_la_topografia_considerada_muestra_la_tabla(qapp, cartel_con_topografia):
    vista = reporte_cartel.vista(cartel_con_topografia)
    pagina_parametros = vista._paginas.widget(2)
    tablas_parametros = pagina_parametros.findChildren(TablaResultados)
    # Con el factor de ráfaga simplificado quedan dos: las constantes de
    # terreno y el factor topográfico.
    assert len(tablas_parametros) == 2
    encabezados = [
        tablas_parametros[i].horizontalHeaderItem(c).text()
        for i in range(len(tablas_parametros))
        for c in range(tablas_parametros[i].columnCount())
    ]
    assert "K1/(H/Lh)" in encabezados


# --- El diálogo de exportación ------------------------------------------


def test_el_dialogo_de_exportacion_muestra_lo_que_corresponde(qapp, edificio):
    dialogo = DialogoExportacion(
        None,
        edificio,
        "edificio.md",
        unidades_desde_settings(),
        nombre_proyecto="Mi Proyecto",
    )
    try:
        # Sin formatos que elegir: el papel y el aviso de LaTeX están
        # siempre, porque la salida única es el PDF.
        assert not dialogo._boton_configurar_pagina.isHidden()
        assert not dialogo._label_aviso_latex.isHidden()

        # Los datos del informe: el nombre llega prellenado del archivo
        # abierto y el resto arranca vacío.
        assert dialogo._edicion_nombre.text() == "Mi Proyecto"
        assert dialogo._edicion_proyectista.text() == ""
        assert dialogo._edicion_empresa.text() == ""
        assert dialogo._edicion_ubicacion.text() == ""
        assert dialogo._edicion_observaciones.toPlainText() == ""
    finally:
        dialogo.close()
        dialogo.deleteLater()


def test_el_dialogo_de_exportacion_usa_los_datos_tipeados(qapp, edificio, monkeypatch):
    """Al exportar, el reporte se arma recién con los datos del informe
    tal como quedaron en los campos, y se convierte a PDF."""
    capturado: dict = {}

    class ReporteStub:
        def __init__(self, plantilla, estructura, unidades, datos_proyecto=None):
            capturado["datos_proyecto"] = datos_proyecto

        def exportar(self, formato, nombre_archivo=None, **kwargs):
            capturado["formato"] = formato
            capturado["nombre_archivo"] = nombre_archivo

    monkeypatch.setattr(exportacion, "Reporte", ReporteStub)
    monkeypatch.setattr(exportacion, "AvisoExito", lambda *args, **kwargs: None)

    dialogo = DialogoExportacion(
        None, edificio, "edificio.md", unidades_desde_settings()
    )
    try:
        dialogo._edicion_nombre.setText("Proyecto X")
        dialogo._edicion_observaciones.setPlainText("Sin observaciones.")
        dialogo._dialogo_guardar_archivo.getSaveFileName = lambda *args, **kwargs: (
            "/tmp/reporte.pdf",
            "PDF (*.pdf)",
        )
        dialogo._exportar_reporte()
    finally:
        dialogo.close()
        dialogo.deleteLater()

    assert capturado["formato"] == "pdf"
    assert capturado["nombre_archivo"] == "/tmp/reporte.pdf"
    assert capturado["datos_proyecto"]["nombre"] == "Proyecto X"
    assert capturado["datos_proyecto"]["observaciones"] == "Sin observaciones."
    assert capturado["datos_proyecto"]["proyectista"] == ""


# --- La integración con la pantalla de resultados -----------------------


@necesita_opengl
def test_la_pestaña_reporte_del_cartel_agrega_la_pagina(qtbot, cartel):
    from zonda.widgets.resultados import WidgetResultadosCartel

    widget = WidgetResultadosCartel(cartel)
    qtbot.addWidget(widget)
    assert widget._stacked_widget.count() == 1
    widget._cambiar_pagina(1)
    assert widget._stacked_widget.count() == 2
    assert isinstance(widget._stacked_widget.widget(1), VistaReporte)
    # La página se reusa mientras las unidades no cambien.
    widget._cambiar_pagina(0)
    widget._cambiar_pagina(1)
    assert widget._stacked_widget.count() == 2


@necesita_opengl
def test_la_pestaña_reporte_del_edificio_agrega_la_pagina(qtbot, edificio):
    from zonda.widgets.resultados import WidgetResultadosEdificio

    widget = WidgetResultadosEdificio(edificio)
    qtbot.addWidget(widget)
    assert widget._stacked_widget.count() == 2
    widget._cambiar_pagina(2)
    assert widget._stacked_widget.count() == 3
    assert isinstance(widget._stacked_widget.widget(2), VistaReporte)
    widget.finalizar()
