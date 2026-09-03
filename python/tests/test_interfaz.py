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

"""Smoke tests de la interfaz PyQt6.

Corren sobre la plataforma ``offscreen`` de Qt (ver ``conftest.py``), así que no
necesitan un servidor gráfico.
"""

import sys

import pytest
from PyQt6 import QtWidgets

from zonda import recursos

from .conftest import SIN_OPENGL

necesita_opengl = pytest.mark.skipif(
    SIN_OPENGL,
    reason="la vista 3D necesita un contexto gráfico real",
)


def test_la_aplicacion_arranca(qapp):
    assert isinstance(qapp, QtWidgets.QApplication)


def test_la_hoja_de_estilos_se_aplica(qapp):
    """Es el recurso que main() carga al inicio."""
    qapp.setStyleSheet(recursos.texto("qss/zonda.qss"))
    assert qapp.styleSheet()


def test_los_iconos_del_paquete_cargan(qapp):
    """Un QIcon con ruta inválida se construye igual pero queda nulo."""
    assert not recursos.icono("iconos/zonda.ico").isNull()


def test_los_pixmaps_del_paquete_cargan(qapp):
    assert not recursos.pixmap("imagenes/logo.png").isNull()


@pytest.mark.parametrize(
    "clave",
    [
        "iconos/edificio.png",
        "iconos/cartel.png",
        "iconos/cubierta-aislada.png",
        "iconos/regla.png",
        "iconos/screenshot.png",
    ],
)
def test_iconos_de_la_barra_de_herramientas(qapp, clave):
    assert not recursos.icono(clave).isNull()


def test_la_ventana_de_bienvenida_se_construye(qapp):
    from zonda.widgets.zonda import WidgetBienvenida

    widget = WidgetBienvenida()
    assert widget is not None
    widget.close()


def test_los_archivos_de_la_vista_estan_en_el_paquete():
    """El .qml y sus shaders se distribuyen junto al código.

    Si falta el .qml no hay vista 3D. Si faltan los shaders, los contornos y las
    líneas quedan sin grosor, las flechas sin borde, y el material no compila.
    """
    from zonda.widgets.graficos import RUTA_VISOR

    assert RUTA_VISOR.is_file()
    for shader in ("contorno.vert", "contorno.frag", "silueta.vert"):
        assert (RUTA_VISOR.parent / shader).is_file(), shader


@necesita_opengl
def test_la_vista_3d_carga_sin_errores(qapp):
    """Un error de QML deja el widget vacío sin levantar ninguna excepción."""
    from PyQt6.QtCore import QUrl
    from PyQt6.QtQuickWidgets import QQuickWidget

    from zonda.graficos.escena import Escena3D
    from zonda.widgets.graficos import RUTA_VISOR

    widget = QQuickWidget()
    widget.rootContext().setContextProperty("escenaPython", Escena3D())
    widget.setSource(QUrl.fromLocalFile(str(RUTA_VISOR)))

    assert [error.toString() for error in widget.errors()] == []
    assert widget.status() == QQuickWidget.Status.Ready
    assert isinstance(widget, QtWidgets.QWidget)


# --- Las pantallas que arman escenas 3D ---------------------------------
#
# Regresión: estas eran las pantallas que rompían al abrir un módulo. No se
# cubrían porque los tests corrían siempre en modo offscreen, donde la vista 3D
# ni siquiera se puede crear.


@necesita_opengl
@pytest.mark.parametrize(
    "nombre",
    [
        "WidgetEstructuraEdificio",
        "WidgetEstructuraCubiertaAislada",
        "WidgetEstructuraCartel",
    ],
)
def test_las_pantallas_de_entrada_generan_su_escena(qapp, nombre):
    from zonda.widgets import entrada

    widget = getattr(entrada, nombre)()
    assert widget is not None
    widget.close()


@necesita_opengl
def test_resultados_edificio(qapp, edificio):
    from zonda.widgets.resultados import WidgetResultadosEdificio

    widget = WidgetResultadosEdificio(edificio)
    assert widget is not None
    widget.close()


@necesita_opengl
def test_resultados_edificio_plana_tiene_caso_cubierta_barlovento(qapp):
    """La cubierta plana (ángulo < 10°) muestra el caso de cubierta barlovento.

    El nuevo Reglamento agrega el caso de presión positiva a las cubiertas de
    ángulo menor que 10° con viento normal a la cumbrera, incluida la plana.
    """
    from zonda import enums
    from zonda.cirsoc import Edificio
    from zonda.widgets.resultados import WidgetResultadosEdificioSprfvMetodoDireccional

    edificio = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=6,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    widget = WidgetResultadosEdificioSprfvMetodoDireccional(edificio)
    combobox = widget._combobox_presion_cubierta_inclinada
    assert combobox is not None

    widget._combobox_direccion.setCurrentIndex(
        widget._combobox_direccion.findData(
            enums.DireccionVientoMetodoDireccionalSprfv.NORMAL
        )
    )
    assert combobox.isEnabled()
    combobox.setCurrentText("Presión positiva")
    widget.close()


@necesita_opengl
def test_resultados_cartel(qapp, cartel):
    from zonda.widgets.resultados import WidgetResultadosCartel

    widget = WidgetResultadosCartel(cartel)
    assert widget is not None
    widget.close()


@necesita_opengl
def test_resultados_cubierta_aislada(qapp, cubierta_aislada):
    from zonda.widgets.resultados import WidgetResultadosCubiertaAislada

    widget = WidgetResultadosCubiertaAislada(cubierta_aislada)
    assert widget is not None
    widget.close()


# --- El event loop y la vista 3D ----------------------------------------


@necesita_opengl
def test_el_event_loop_sobrevive_al_paint_de_la_vista_3d(qtbot):
    """Abre una pantalla con escena 3D y comprueba que Qt sigue despachando.

    Es la regresión que dejaba la aplicación colgada al abrir un módulo: la
    ventana aparecía y nada volvía a responder.
    """
    from PyQt6.QtCore import QTimer

    from zonda.widgets.entrada import WidgetEstructuraEdificio

    widget = WidgetEstructuraEdificio()
    qtbot.addWidget(widget)
    with qtbot.waitExposed(widget):
        widget.show()

    latidos = []
    temporizador = QTimer()
    temporizador.timeout.connect(lambda: latidos.append(1))
    temporizador.start(50)
    qtbot.waitUntil(lambda: len(latidos) >= 3, timeout=5000)
    temporizador.stop()


@necesita_opengl
def test_la_captura_de_imagen_devuelve_una_imagen(qtbot, edificio, tmp_path):
    from zonda.widgets.graficos import WidgetPresiones
    from zonda.widgets.resultados import WidgetResultadosEdificio

    widget = WidgetResultadosEdificio(edificio)
    qtbot.addWidget(widget)
    with qtbot.waitExposed(widget):
        widget.show()

    grafico = widget.findChildren(WidgetPresiones)[0]
    destino = tmp_path / "captura.png"
    assert grafico.capturar(str(destino))
    assert destino.stat().st_size > 0


@necesita_opengl
def test_la_herramienta_de_medicion_se_activa(qtbot, edificio):
    from zonda.widgets.graficos import WidgetPresiones
    from zonda.widgets.resultados import WidgetResultadosEdificio

    widget = WidgetResultadosEdificio(edificio)
    qtbot.addWidget(widget)
    with qtbot.waitExposed(widget):
        widget.show()

    grafico = widget.findChildren(WidgetPresiones)[0]
    grafico.escena3d.pedir_medicion(True)
    grafico.escena3d.pedir_medicion(False)


# --- Guardar y abrir un proyecto ----------------------------------------
#
# El archivo guarda el estado de las pantallas de entrada, no los resultados.
# Lo que importa es que abrirlo deje la pantalla exactamente como estaba.


@necesita_opengl
@pytest.mark.parametrize(
    ("nombre", "estructura"),
    [
        ("WidgetEstructuraEdificio", "EDIFICIO"),
        ("WidgetEstructuraCubiertaAislada", "CUBIERTA_AISLADA"),
        ("WidgetEstructuraCartel", "CARTEL"),
    ],
)
def test_la_pantalla_de_entrada_va_y_vuelve_del_archivo(
    qapp, tmp_path, nombre, estructura
):
    from zonda import proyecto
    from zonda.enums import Estructura
    from zonda.widgets import entrada

    widget = getattr(entrada, nombre)()
    widget._spinboxs["ancho"].setValue(23.5)
    esperado = widget.estado()

    archivo = tmp_path / f"proyecto{proyecto.EXTENSION}"
    proyecto.guardar(archivo, Estructura[estructura], esperado)
    _, guardado = proyecto.abrir(archivo)

    otro = getattr(entrada, nombre)()
    otro.cargar_estado(guardado)

    assert otro.estado() == esperado
    # El estado tiene que seguir sirviendo para calcular.
    assert isinstance(otro.parametros(), dict)

    widget.finalizar()
    otro.finalizar()


@necesita_opengl
def test_cargar_un_estado_no_abre_el_aviso_de_parapeto(qapp):
    """El aviso es para cuando lo tilda el usuario, no para cuando se abre un archivo.

    El estado se arma a mano en vez de tildando el checkbox: hacerlo sobre el
    widget dispara justamente el ``QErrorMessage`` modal que este test quiere
    ver que *no* aparezca, y deja la corrida esperando a que alguien lo cierre.
    """
    from zonda.widgets.entrada import WidgetEstructuraEdificio

    widget = WidgetEstructuraEdificio()
    estado = widget.estado()
    estado["parapeto"] = True
    estado["geometria"]["parapeto"] = 0.8

    widget.cargar_estado(estado)

    assert widget._checkbox_parapeto.isChecked()
    assert widget._spinboxs["parapeto"].isEnabled()
    assert not widget._mensaje_parapeto.isVisible()

    widget.finalizar()


@necesita_opengl
def test_el_panel_de_entrada_va_y_vuelve_del_archivo(qapp, tmp_path):
    from zonda import proyecto
    from zonda.enums import Estructura
    from zonda.widgets.custom import WidgetPanelEntrada

    panel = WidgetPanelEntrada(componentes=True)
    panel.parametros_viento["velocidad"] = 52
    panel.parametros_topografia["considerar_topografia"] = True
    panel.componentes = {
        "componentes_paredes": {"Chapa": 3.5},
        "componentes_cubierta": None,
    }
    esperado = panel.estado()

    archivo = tmp_path / f"panel{proyecto.EXTENSION}"
    proyecto.guardar(archivo, Estructura.EDIFICIO, esperado)
    _, guardado = proyecto.abrir(archivo)

    otro = WidgetPanelEntrada(componentes=True)
    otro.cargar_estado(guardado)

    assert otro.estado() == esperado


# --- La barra de herramientas del módulo --------------------------------


@pytest.fixture
def modulo(qapp):
    """Un módulo de edificio, cerrado sin pasar por el diálogo de confirmación."""
    from PyQt6 import QtWidgets

    from zonda.widgets.modulos import WidgetModuloEdificio

    # El padre se guarda en una variable: sin una referencia viva de Python, el
    # recolector se lo lleva, al destruirse en C++ arrastra al hijo, y el
    # teardown de abajo revienta con RuntimeError sobre un objeto ya borrado.
    padre = QtWidgets.QWidget()
    widget = WidgetModuloEdificio(padre)
    yield widget
    widget._widget_estructura.finalizar()
    widget.deleteLater()
    del padre


@necesita_opengl
def test_el_modulo_es_una_ventana_principal(modulo):
    """La QMenuBar la tiene que ubicar la ventana, no un layout.

    Es lo que hace que Qt la dibuje como corresponde en cada plataforma: en
    macOS el menú va a la barra global del sistema, no adentro de la ventana.
    """
    from PyQt6 import QtWidgets

    assert isinstance(modulo, QtWidgets.QMainWindow)
    assert modulo.centralWidget() is modulo._stacked_widget
    assert [accion.text() for accion in modulo.menuBar().actions()] == [
        "&Archivo",
        "A&yuda",
    ]


@necesita_opengl
def test_el_menu_trae_las_acciones_con_atajo(modulo):
    acciones = {
        accion.text(): accion
        for menu in modulo.menuBar().actions()
        for accion in menu.menu().actions()
        if accion.text()
    }

    assert list(acciones) == [
        "Nuevo",
        "Abrir...",
        "Guardar",
        "Guardar Como...",
        "Configuración...",
        "Cerrar Módulo",
        "Ayuda de Zonda",
        "Acerca de Zonda",
    ]
    sin_atajo = [
        texto for texto, accion in acciones.items() if not accion.shortcut().toString()
    ]
    # QKeySequence.StandardKey.Preferences solo resuelve a un atajo en macOS
    # (Cmd+,); en Windows y Linux no existe la convencion y queda vacio.
    esperado = ["Acerca de Zonda"]
    if sys.platform != "darwin":
        esperado.insert(0, "Configuración...")
    assert sin_atajo == esperado


@necesita_opengl
def test_las_acciones_de_plataforma_llevan_su_menu_role(modulo):
    """Son las que macOS se lleva al menú de la aplicación."""
    from PyQt6 import QtGui

    assert (
        modulo._accion_configuracion.menuRole()
        == QtGui.QAction.MenuRole.PreferencesRole
    )
    assert modulo._accion_acerca_de.menuRole() == QtGui.QAction.MenuRole.AboutRole


@necesita_opengl
def test_las_acciones_no_se_dibujan_dentro_de_la_ventana(modulo):
    """El contenido de la ventana es sólo la entrada y los resultados.

    Las acciones viven en la barra de menús, que en macOS ni siquiera está
    adentro de la ventana.

    Se buscan sólo los hijos directos: la vista 3D tiene su propia barra con los
    comandos de cámara, y esa sí va adentro.
    """
    from PyQt6 import QtCore, QtWidgets

    assert not modulo.findChildren(
        QtWidgets.QToolBar,
        options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly,
    )


@necesita_opengl
def test_las_acciones_de_archivo_llevan_icono(modulo):
    """macOS no los muestra, pero Windows y Linux sí."""
    sin_icono = [
        accion.text()
        for accion in (
            modulo._accion_nuevo,
            modulo._accion_abrir,
            modulo._accion_guardar,
            modulo._accion_guardar_como,
        )
        if accion.icon().isNull()
    ]

    assert sin_icono == []


@necesita_opengl
def test_guardar_y_abrir_desde_el_modulo(modulo, tmp_path):
    from zonda import proyecto

    assert not modulo._hay_cambios()

    modulo._widget_estructura._spinboxs["ancho"].setValue(77.5)
    assert modulo._hay_cambios()

    archivo = tmp_path / f"edificio{proyecto.EXTENSION}"
    assert modulo._escribir(archivo)
    assert not modulo._hay_cambios()
    assert archivo.name in modulo.windowTitle()

    modulo._nuevo()
    assert modulo._widget_estructura._spinboxs["ancho"].value() == 30.0
    assert not modulo._hay_cambios()

    _, estado = proyecto.abrir(archivo)
    modulo._cargar_estado(estado)
    assert modulo._widget_estructura._spinboxs["ancho"].value() == 77.5


def test_widget_cerramiento_edificio(qapp):
    from zonda import enums
    from zonda.widgets.entrada import WidgetCerramientoEdificio

    widget = WidgetCerramientoEdificio(
        parent=None,
        ancho=10.0,
        longitud=20.0,
        elevacion=0.0,
        altura_alero=5.0,
        altura_cumbrera=5.0,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        aberturas=(20.0, 1.0, 1.0, 1.0, 0.0),
    )
    assert widget.windowTitle() == "Verificación de cerramiento"
    widget.close()


def test_dialogo_viento(qapp):
    from zonda.enums import CategoriaEstructura, CategoriaExposicion, Flexibilidad
    from zonda.widgets.dialogos import DialogoViento

    dialogo = DialogoViento(
        categoria_exp=CategoriaExposicion.B,
        velocidad=55.1,
        frecuencia=1.0,
        beta=0.02,
        flexibilidad=Flexibilidad.RIGIDA,
        ciudad="Buenos Aires",
        factor_g_simplificado=True,
        editar_velocidad=False,
        altitud=500.0,
        categoria_riesgo_viento=CategoriaEstructura.II,
    )
    assert dialogo._spinboxs["velocidad"].value() == pytest.approx(55.1)
    assert dialogo._spinboxs["altitud"].value() == 500.0

    # Cambiar ciudad actualiza velocidad
    dialogo._combobox_ciudades.setCurrentText("Rosario")
    assert dialogo._spinboxs["velocidad"].value() == pytest.approx(61.2)

    # Cambiar mapa a Cat I actualiza velocidad para Rosario
    dialogo._combobox_mapa.setCurrentIndex(
        dialogo._combobox_mapa.findData(CategoriaEstructura.I)
    )
    assert dialogo._spinboxs["velocidad"].value() == pytest.approx(57.1)

    dialogo.close()
