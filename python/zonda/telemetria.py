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

"""La telemetría de Zonda: un ping anónimo por arranque.

Es de lo más chata que puede ser: cada vez que alguien abre el programa sale
un único pedido con un número aleatorio que identifica la instalación, la
versión de Zonda y el sistema operativo. El receptor (``telemetria/`` en la
raíz del repositorio) le agrega el país y un hash diario de la IP; ni acá ni
allá se guarda la IP cruda ni viaja ningún dato personal ni del contenido de
los proyectos.

El identificador se genera al azar la primera vez que hace falta y vive en
``QSettings``, como los proyectos recientes. La decisión de participar
también: arranca activada y la casilla de Configuración es el único lugar
donde se apaga —el modelo de Homebrew—, así que ``participa()`` devuelve
siempre un bool y nadie tiene que preguntar nada.

Si ``__acercade__.__telemetria__`` está vacía —no hay receptor desplegado, o
éste es un fork con otro receptor— todo el módulo queda inerte: ``url_ping()``
devuelve cadena vacía y quien llama no tiene que preguntar nada.
"""

import os
import platform
import uuid

from PyQt6 import QtCore, QtNetwork

from zonda import __acercade__

GRUPO_SETTINGS = "telemetria"
"""El grupo de ``QSettings`` con la decisión del usuario y el identificador."""

TIEMPO_LIMITE_MS = 5000
"""Cuánto se espera al receptor antes de abandonar el ping."""


def url_ping() -> str:
    """La dirección del receptor, o cadena vacía si no hay telemetría.

    Returns: La URL a la que mandar el ping.
    """
    if not __acercade__.__telemetria__:
        return ""
    return f"{__acercade__.__telemetria__}/ping"


def participa() -> bool:
    """Si esta instalación manda las estadísticas anónimas.

    La telemetría arranca activada —sin preguntar nada a nadie— y la única
    forma de apagarla es la casilla de Configuración, que escribe acá, o la
    variable de entorno ``ZONDA_SIN_TELEMETRIA``, para quien prefiere no
    tocar la configuración (CI, sesiones temporales, scripts).

    Returns: ``True`` por defecto, o ``False`` si el usuario la desactivó.
    """
    if os.environ.get("ZONDA_SIN_TELEMETRIA"):
        return False

    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    valor = settings.value("participa", True)
    settings.endGroup()

    # Según el formato y el sistema, el booleano vuelve como bool o como
    # "true"/"false" escrito en la configuración.
    return str(valor).lower() in ("true", "1")


def setear_participa(valor: bool) -> None:
    """Anota la decisión del usuario de la casilla de Configuración.

    Args:
        valor: Si esta instalación manda las estadísticas anónimas.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    settings.setValue("participa", valor)
    settings.endGroup()
    settings.sync()


def id_anonimo() -> str:
    """El identificador de esta instalación, generado la primera vez.

    Es un UUID al azar, sin ningún vínculo con la persona ni con el
    hardware: sirve para contar instalaciones sin saber quién es nadie.

    Returns: El identificador, que no cambia entre sesiones.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    guardado = str(settings.value("id", "") or "")
    if not guardado:
        guardado = str(uuid.uuid4())
        settings.setValue("id", guardado)
        settings.sync()
    settings.endGroup()
    return guardado


def carga() -> dict[str, str]:
    """Lo que viaja en el ping. Nada más que esto, nunca.

    Returns: El payload del pedido.
    """
    return {
        "id": id_anonimo(),
        "version": __acercade__.__version__,
        "so": platform.system().lower(),
    }


class Telemetria(QtCore.QObject):
    """Le manda al receptor el ping del arranque.

    La consulta es asincrónica, con el mismo espíritu que la búsqueda de
    actualizaciones: se lanza con ``registrar_sesion()`` y a nadie le importa
    cómo termina. Sin internet, detrás de un proxy o con el receptor caído,
    el programa sigue como si nada.

    Si el usuario la desactivó o no hay receptor configurado, no sale nada.
    """

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._red = QtNetwork.QNetworkAccessManager(self)

    def registrar_sesion(self) -> None:
        """Manda el ping, si corresponde. Llamarlo de nuevo lo repite."""
        url = url_ping()
        if not url or participa() is not True:
            return

        pedido = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        pedido.setHeader(
            QtNetwork.QNetworkRequest.KnownHeaders.ContentTypeHeader,
            "application/json",
        )
        # Sin límite, una red que traga los paquetes en silencio deja el
        # pedido colgado toda la sesión.
        pedido.setTransferTimeout(TIEMPO_LIMITE_MS)

        documento = QtCore.QJsonDocument.fromVariant(carga())
        respuesta = self._red.post(pedido, documento.toJson())
        if respuesta is None:  # pragma: no cover - no pasa con un pedido válido
            return
        respuesta.finished.connect(respuesta.deleteLater)
