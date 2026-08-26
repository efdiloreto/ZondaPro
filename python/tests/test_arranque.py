# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

"""Cómo arranca el programa cuando el sistema le pasa un archivo de proyecto.

Abrir un ``.zda`` con doble clic tiene que llevar directo al módulo que le
corresponde, sin pasar por la pantalla de bienvenida.
"""

import ctypes
import ctypes.util
import sys

import pytest
from PyQt6 import QtCore, QtWidgets

from zonda import main as arranque
from zonda import proyecto
from zonda.enums import CategoriaEstructura, Estructura
from zonda.widgets.zonda import WidgetBienvenida

from .conftest import SIN_OPENGL

necesita_opengl = pytest.mark.skipif(
    SIN_OPENGL,
    reason="la vista 3D necesita un contexto gráfico real",
)


@pytest.fixture
def sin_dialogos(monkeypatch):
    """Anota los avisos en lugar de abrirlos: un diálogo modal traba la corrida."""
    avisos = []
    for nombre in ("critical", "warning"):
        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            nombre,
            lambda *args, _tipo=nombre, **kwargs: avisos.append((_tipo, args[2])),
        )
    return avisos


@pytest.fixture
def archivo_cartel(tmp_path):
    """Un proyecto de cartel guardado en disco, sin levantar ninguna ventana."""
    ruta = tmp_path / f"obra{proyecto.EXTENSION}"
    proyecto.guardar(
        ruta,
        Estructura.CARTEL,
        {
            "panel": {"viento": {"velocidad": 45}, "topografia": {}},
            "estructura": {
                "geometria": {
                    "altura_superior": 22.0,
                    "altura_inferior": 7.0,
                    "ancho": 6.5,
                    "profundidad": 1.0,
                },
                "alturas_personalizadas": "",
                "categoria": CategoriaEstructura.II,
                "es_parapeto": False,
            },
        },
    )
    return ruta


# --- El archivo que viene por línea de comandos -------------------------


@pytest.mark.parametrize(
    ("argumentos", "esperado"),
    [
        (["zonda"], None),
        (["zonda", "obra.zda"], "obra.zda"),
        (["zonda", "/ruta/con espacios/obra.zda"], "/ruta/con espacios/obra.zda"),
        (["zonda", "OBRA.ZDA"], "OBRA.ZDA"),
        # Los argumentos de Qt llevan valor: "fusion" no es un archivo.
        (["zonda", "-style", "fusion", "obra.zda"], "obra.zda"),
        (["zonda", "-style", "fusion"], None),
        (["zonda", "cualquier-cosa.txt"], None),
    ],
)
def test_archivo_de_los_argumentos(argumentos, esperado):
    assert arranque._archivo_de_los_argumentos(argumentos) == esperado


# --- El archivo que manda macOS como evento -----------------------------
#
# ``QFileOpenEvent`` no se puede instanciar desde PyQt6, así que se prueba
# ``_recibir()``, que es lo único que hace ``event()`` además de sacarle la ruta
# al evento.


@pytest.fixture
def aplicacion(qapp):
    """La aplicación, con el estado de archivos pendientes limpio.

    ``qapp`` dura toda la sesión: si un test la deja marcada como lista, el
    siguiente vería otra cosa.
    """
    anterior = (qapp._pendiente, qapp._interfaz_lista)
    qapp._pendiente, qapp._interfaz_lista = None, False
    yield qapp
    qapp._pendiente, qapp._interfaz_lista = anterior


def test_el_archivo_que_llega_antes_de_la_interfaz_queda_esperando(aplicacion):
    """En macOS el evento puede llegar antes de que exista una ventana."""
    aplicacion._recibir("/proyectos/obra.zda")

    assert aplicacion.tomar_pendiente() == "/proyectos/obra.zda"
    # Se entrega una sola vez.
    assert aplicacion.tomar_pendiente() is None


def test_el_archivo_que_llega_despues_sale_por_la_senal(aplicacion):
    """Con la aplicación ya corriendo, el archivo se avisa por la señal."""
    pedidos = []
    aplicacion.archivoPedido.connect(pedidos.append)
    aplicacion.tomar_pendiente()  # la interfaz ya está armada

    aplicacion._recibir("/proyectos/otra.zda")

    assert pedidos == ["/proyectos/otra.zda"]
    aplicacion.archivoPedido.disconnect(pedidos.append)


def test_una_ruta_vacia_se_ignora(aplicacion):
    aplicacion._recibir("")

    assert aplicacion.tomar_pendiente() is None


# --- El nombre que muestra macOS ----------------------------------------


@pytest.mark.skipif(sys.platform != "darwin", reason="el bundle es cosa de macOS")
def test_el_bundle_queda_con_el_nombre_del_programa():
    """Sin esto, el menú de la aplicación y el Dock dicen "Python".

    Se lee la clave con la misma llamada que usa Qt —
    ``CFBundleGetValueForInfoDictionaryKey``, ver ``qt_mac_applicationName()``—
    y no el diccionario que se escribió, así que la prueba falla si alguna vez
    CoreFoundation deja de devolver el diccionario vivo del bundle.
    """
    arranque.nombrar_la_aplicacion_en_macos("Zonda")

    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    cf.CFBundleGetMainBundle.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_uint32,
    ]
    cf.CFBundleGetValueForInfoDictionaryKey.restype = ctypes.c_void_p
    cf.CFBundleGetValueForInfoDictionaryKey.argtypes = [ctypes.c_void_p] * 2
    cf.CFStringGetCString.restype = ctypes.c_bool
    cf.CFStringGetCString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_long,
        ctypes.c_uint32,
    ]

    clave = cf.CFStringCreateWithCString(None, b"CFBundleName", arranque._UTF8)
    valor = cf.CFBundleGetValueForInfoDictionaryKey(cf.CFBundleGetMainBundle(), clave)
    buffer = ctypes.create_string_buffer(256)

    assert valor
    assert cf.CFStringGetCString(valor, buffer, 256, arranque._UTF8)
    assert buffer.value.decode() == "Zonda"


def test_fuera_de_macos_no_toca_nada(monkeypatch):
    """En Windows y Linux el nombre sale de ``setApplicationName()``."""
    monkeypatch.setattr(arranque.sys, "platform", "linux")
    monkeypatch.setattr(
        arranque.ctypes.util,
        "find_library",
        lambda _: pytest.fail("no tendría que buscar CoreFoundation"),
    )

    arranque.nombrar_la_aplicacion_en_macos("Zonda")


# --- Abrir el proyecto en el módulo que corresponde ---------------------


@necesita_opengl
def test_abre_el_modulo_del_archivo_salteando_la_bienvenida(
    qapp, archivo_cartel, sin_dialogos
):
    bienvenida = WidgetBienvenida()

    assert arranque.abrir_proyecto(bienvenida, archivo_cartel)

    modulo = bienvenida.modulo
    assert modulo is not None
    assert modulo.estructura is Estructura.CARTEL
    assert modulo._widget_estructura._spinboxs["ancho"].value() == 6.5
    assert archivo_cartel.name in modulo.windowTitle()
    assert not modulo._hay_cambios()
    assert not bienvenida.isVisible()
    assert sin_dialogos == []

    modulo._widget_estructura.finalizar()


def test_un_archivo_roto_no_abre_ningun_modulo(qapp, tmp_path, sin_dialogos):
    """Se avisa y se sigue: quien llama muestra la bienvenida."""
    roto = tmp_path / f"roto{proyecto.EXTENSION}"
    roto.write_text("esto no es json {", encoding="utf-8")
    bienvenida = WidgetBienvenida()

    assert not arranque.abrir_proyecto(bienvenida, roto)

    assert bienvenida.modulo is None
    assert [tipo for tipo, _ in sin_dialogos] == ["critical"]


@necesita_opengl
def test_un_archivo_de_otro_modulo_no_pisa_el_abierto(
    qapp, archivo_cartel, sin_dialogos
):
    """Sólo se trabaja con un módulo por vez; el que está abierto no se toca."""
    bienvenida = WidgetBienvenida()
    modulo = bienvenida.abrir_modulo(Estructura.EDIFICIO)

    assert arranque.abrir_proyecto(bienvenida, archivo_cartel)

    assert bienvenida.modulo is modulo
    assert [tipo for tipo, _ in sin_dialogos] == ["warning"]

    modulo._widget_estructura.finalizar()


@necesita_opengl
def test_la_bienvenida_olvida_el_modulo_cuando_se_destruye(qapp):
    """Si no, la referencia apuntaría a un objeto de Qt ya borrado."""
    bienvenida = WidgetBienvenida()
    modulo = bienvenida.abrir_modulo(Estructura.CARTEL)
    modulo._widget_estructura.finalizar()

    modulo.deleteLater()
    # processEvents() no despacha los borrados diferidos; hay que pedirlos.
    QtCore.QCoreApplication.sendPostedEvents(
        None, QtCore.QEvent.Type.DeferredDelete.value
    )

    assert bienvenida.modulo is None


def test_los_botones_estandar_quedan_en_espanol(qapp):
    """Los textos de Qt se traducen; si no, los diálogos mezclan dos idiomas."""
    arranque.instalar_traducciones(qapp)

    caja = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        | QtWidgets.QDialogButtonBox.StandardButton.Close
    )

    assert {boton.text() for boton in caja.buttons()} == {
        "Aceptar",
        "Cancelar",
        "Cerrar",
    }
