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

"""El arranque del programa.

Zonda se puede abrir de dos maneras: solo, que lleva a la pantalla de
bienvenida, o **desde un archivo de proyecto**, que salta la bienvenida y abre
directo el módulo que le corresponde al archivo.

Cómo llega ese archivo depende del sistema:

- **Windows y Linux** lo pasan en la línea de comandos: ``zonda proyecto.zda``.
- **macOS no usa la línea de comandos para esto.** El archivo llega como un
  ``QEvent.Type.FileOpen`` a la ``QApplication``, y puede llegar *antes* de que
  exista una ventana. Por eso ``Aplicacion`` lo guarda apenas lo recibe y
  ``main()`` lo consulta cuando la interfaz ya está armada.

Que el doble clic sobre un ``.zda`` llegue hasta acá es otra cosa: hay que
registrar la extensión en el sistema, y eso lo hace el empaquetado
(ver AGENTS.md).
"""

import ctypes
import ctypes.util
import sys
from pathlib import Path

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QFontDatabase

from zonda import __acercade__, proyecto, recursos
from zonda.excepciones import ErrorArchivo
from zonda.widgets.zonda import WidgetBienvenida

_UTF8 = 0x08000100
"""``kCFStringEncodingUTF8``, que CoreFoundation no expone como símbolo."""


class Aplicacion(QtWidgets.QApplication):
    """La ``QApplication`` del programa, atenta a los archivos que abre el sistema.

    Los archivos que llegan antes de que la interfaz esté lista se guardan y se
    recuperan con ``tomar_pendiente()``. Los que llegan después —el usuario abre
    otro proyecto con Zonda ya corriendo— salen por ``archivoPedido``.
    """

    archivoPedido = QtCore.pyqtSignal(str)

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._pendiente: str | None = None
        self._interfaz_lista = False

    def event(self, a0: QtCore.QEvent | None) -> bool:
        if a0 is not None and a0.type() == QtCore.QEvent.Type.FileOpen:
            self._recibir(a0.file())  # type: ignore[attr-defined]
            return True
        return super().event(a0)

    def _recibir(self, ruta: str) -> None:
        if not ruta:
            return
        if self._interfaz_lista:
            self.archivoPedido.emit(ruta)
        else:
            self._pendiente = ruta

    def tomar_pendiente(self) -> str | None:
        """Da por lista la interfaz y devuelve el archivo que quedó esperando.

        Se despacha lo que haya en la cola antes de mirar: en macOS el evento
        del doble clic puede estar todavía sin entregar cuando se arma la
        interfaz.
        """
        self.processEvents()
        self._interfaz_lista = True
        ruta, self._pendiente = self._pendiente, None
        return ruta


def _archivo_de_los_argumentos(argumentos: list[str]) -> str | None:
    """El archivo de proyecto que se pasó por línea de comandos, si hay alguno.

    Se busca por extensión y no "el primer argumento suelto" porque entre los
    argumentos vienen también los de Qt, y algunos llevan valor: en
    ``zonda -style fusion obra.zda`` el primer argumento que no es una opción es
    ``fusion``. El sistema siempre pasa la ruta completa del documento, así que
    la extensión alcanza.

    Args:
        argumentos: Los argumentos del programa, empezando por su propio nombre.
    """
    for argumento in argumentos[1:]:
        if argumento.lower().endswith(proyecto.EXTENSION):
            return argumento
    return None


def nombrar_la_aplicacion_en_macos(nombre: str) -> None:
    """Le pone el nombre de Zonda al bundle en ejecución. Sólo hace algo en macOS.

    En macOS el menú de la aplicación —el primero, el que lleva "Acerca de" y
    "Salir"— **no lee** ``applicationName``. El plugin cocoa de Qt saca ese
    nombre del ``CFBundleName`` del bundle en ejecución, y recién si la clave
    falta cae en ``applicationName``:

        QString qt_mac_applicationName()   // qtbase, qcocoahelpers.mm
        {
            QString appName;
            CFTypeRef string = CFBundleGetValueForInfoDictionaryKey(
                CFBundleGetMainBundle(), CFSTR("CFBundleName"));
            ...
            if (appName.isEmpty())  // recién acá mira applicationName
        }

    Sin empaquetar, el bundle en ejecución es el de ``Python.framework``, que
    trae ``CFBundleName = Python``. De ahí que el menú dijera "Python" por más
    que ``setApplicationName()`` estuviera puesto.

    ``CFBundleGetInfoDictionary()`` devuelve el diccionario vivo del bundle, no
    una copia, así que escribirle la clave alcanza. Tiene que pasar **antes** de
    construir la ``QApplication``: el menú de la aplicación se arma cuando Qt
    inicializa el plugin cocoa, y ese nombre no se vuelve a leer después.

    Cuando haya empaquetado, el ``.app`` va a traer su propio ``CFBundleName``
    con este mismo nombre y esta función queda escribiendo lo que ya estaba.

    Args:
        nombre: El nombre que tiene que mostrar el sistema.
    """
    if sys.platform != "darwin":
        return

    ruta = ctypes.util.find_library("CoreFoundation")
    if ruta is None:  # pragma: no cover - no pasa en un macOS sano
        return
    cf = ctypes.cdll.LoadLibrary(ruta)

    cf.CFBundleGetMainBundle.restype = ctypes.c_void_p
    cf.CFBundleGetInfoDictionary.restype = ctypes.c_void_p
    cf.CFBundleGetInfoDictionary.argtypes = [ctypes.c_void_p]
    cf.CFStringCreateWithCString.restype = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_uint32,
    ]
    cf.CFDictionarySetValue.restype = None
    cf.CFDictionarySetValue.argtypes = [ctypes.c_void_p] * 3
    cf.CFRelease.restype = None
    cf.CFRelease.argtypes = [ctypes.c_void_p]

    diccionario = cf.CFBundleGetInfoDictionary(cf.CFBundleGetMainBundle())
    if not diccionario:  # pragma: no cover - un proceso sin bundle
        return

    clave = cf.CFStringCreateWithCString(None, b"CFBundleName", _UTF8)
    valor = cf.CFStringCreateWithCString(None, nombre.encode(), _UTF8)
    cf.CFDictionarySetValue(diccionario, clave, valor)
    # El diccionario se queda con lo suyo; estas dos referencias son nuestras.
    cf.CFRelease(clave)
    cf.CFRelease(valor)


def abrir_proyecto(bienvenida: WidgetBienvenida, ruta: str | Path) -> bool:
    """Abre un archivo de proyecto en el módulo que le corresponde.

    Args:
        bienvenida: La pantalla de bienvenida, que es la que abre los módulos.
        ruta: El archivo de proyecto.

    Returns:
        Si quedó un módulo abierto con el archivo cargado.
    """
    # Se lee dos veces —acá para saber de qué módulo es, y de nuevo adentro del
    # módulo para cargarlo—. Son unos pocos kB de JSON, y a cambio el módulo
    # queda con una sola forma de cargar un archivo.
    try:
        estructura, _ = proyecto.abrir(ruta)
    except ErrorArchivo as error:
        QtWidgets.QMessageBox.critical(None, "Error al abrir el archivo", str(error))
        return False

    modulo = bienvenida.modulo
    if modulo is None:
        modulo = bienvenida.abrir_modulo(estructura)
    elif modulo.estructura is not estructura:
        QtWidgets.QMessageBox.warning(
            modulo,
            "Otro módulo abierto",
            f'El archivo es del módulo "{estructura.value.title()}", y ahora está'
            f' abierto el de "{modulo.titulo}". Cerrá este módulo y volvé a abrir'
            " el archivo.",
        )
        return True

    modulo.pedir_abrir(ruta)
    modulo.raise_()
    modulo.activateWindow()
    return True


def instalar_traducciones(app: QtWidgets.QApplication) -> None:
    """Pone en español los textos que escribe Qt.

    Los botones estándar de los diálogos —"Close", "Cancel"— no los escribe
    Zonda sino Qt, así que salen en inglés mientras no se carguen sus
    traducciones. Los ``.qm`` vienen con PyQt6; si un empaquetado los dejara
    afuera, ``load`` devuelve ``False`` y los textos quedan como estaban, que es
    lo mismo que pasaba antes.

    El idioma va fijo: la interfaz de Zonda está en español, no sigue al del
    sistema.
    """
    ruta = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)
    espanol = QtCore.QLocale(QtCore.QLocale.Language.Spanish)

    for catalogo in ("qtbase", "qtwebengine"):
        # Qt se queda con una referencia al traductor, no con una copia: si se
        # lo lleva el recolector de basura los textos vuelven al inglés. El
        # padre lo mantiene vivo mientras viva la aplicación.
        traductor = QtCore.QTranslator(app)
        if traductor.load(espanol, catalogo, "_", str(ruta)):
            app.installTranslator(traductor)


def main():
    # Antes que nada: el nombre que muestra macOS se fija en el bundle y hay que
    # escribirlo antes de que exista la QApplication.
    nombrar_la_aplicacion_en_macos(__acercade__.__nombre__)

    # QtWebEngine (lo usa el visor de reportes) exige contextos OpenGL
    # compartidos, y el atributo tiene que fijarse antes de instanciar la
    # QApplication. Dejarlo explícito evita depender del orden de los imports.
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts
    )

    app = Aplicacion(sys.argv)
    app.setOrganizationName(__acercade__.__compania__)
    app.setOrganizationDomain(__acercade__.__web_compania__)
    app.setApplicationName(__acercade__.__nombre__)
    app.setWindowIcon(recursos.icono("iconos/zonda.ico"))
    app.setStyle("fusion")

    # Zonda se dibuja siempre en claro, siga el sistema el tema que siga: la
    # hoja de estilo y la vista 3D tienen los colores escritos a mano —fondo
    # #ededed, tinta negra— y con la paleta oscura del sistema quedaban textos
    # claros sobre fondos claros. Fijar el esquema acá alcanza para todo,
    # incluido el visor de reportes: es la paleta lo que ve QtWebEngine para
    # resolver ``prefers-color-scheme``.
    app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)

    # Antes de armar cualquier widget: los textos se resuelven al construirlos.
    instalar_traducciones(app)

    QFontDatabase.addApplicationFont(
        str(recursos.ruta("fuentes/Oswald-VariableFont_wght.ttf"))
    )

    app.setStyleSheet(recursos.texto("qss/zonda.qss"))

    # Se mantiene la referencia para que el recolector de basura no cierre la
    # ventana apenas termina esta función.
    bienvenida = WidgetBienvenida()
    app.archivoPedido.connect(lambda ruta: abrir_proyecto(bienvenida, ruta))

    ruta = app.tomar_pendiente() or _archivo_de_los_argumentos(app.arguments())
    if ruta is None or not abrir_proyecto(bienvenida, ruta):
        bienvenida.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
