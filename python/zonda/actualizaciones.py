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

"""La búsqueda de versiones nuevas de Zonda entre las releases de GitHub.

La consulta sale una sola vez por sesión, apenas arranca el programa, y **falla
en silencio**: sin internet, detrás de un proxy o con GitHub caído, Zonda no
tiene nada que decir al respecto. Mientras no haya ninguna release publicada la
API contesta 404, que para esto es otra forma de "no hay nada nuevo".

Quién muestra el aviso es la capa de widgets; acá sólo se averigua si hay algo
que avisar.
"""

import json
from dataclasses import dataclass

from packaging.version import InvalidVersion, Version
from PyQt6 import QtCore, QtNetwork

from zonda import __acercade__

TIEMPO_LIMITE_MS = 5000
"""Cuánto se espera a GitHub antes de abandonar la consulta."""

GRUPO_SETTINGS = "actualizaciones"
"""El grupo de ``QSettings`` donde se anota qué versión no volver a avisar."""


def url_api() -> str:
    """La dirección de la API que informa cuál es la última release publicada.

    Se arma a partir de ``__web__`` en lugar de escribirla a mano para que un
    fork del proyecto consulte sus propias releases con sólo cambiar esa
    constante.

    Returns: La URL a consultar.
    """
    repositorio = QtCore.QUrl(__acercade__.__web__).path().strip("/")
    return f"https://api.github.com/repos/{repositorio}/releases/latest"


@dataclass(frozen=True)
class Actualizacion:
    """Una versión de Zonda más nueva que la que está corriendo."""

    version: str
    url: str


def version_de_tag(tag: str) -> Version | None:
    """Interpreta como número de versión el tag de una release.

    Los tags que publica el empaquetado llevan una ``v`` adelante —``v1.0.1``—
    que no es parte del número.

    Args:
        tag: El nombre del tag, tal como lo devuelve la API.

    Returns: La versión, o ``None`` si el tag no tiene forma de versión.
    """
    if not tag:
        return None
    try:
        return Version(tag.removeprefix("v"))
    except InvalidVersion:
        return None


def version_instalada() -> Version | None:
    """La versión de Zonda que está corriendo.

    Returns: La versión, o ``None`` si ``__version__`` quedó mal escrita.
    """
    try:
        return Version(__acercade__.__version__)
    except InvalidVersion:
        return None


def version_ignorada() -> str:
    """La versión sobre la que el usuario pidió que no se le avise más.

    Returns: El número de versión, o una cadena vacía si no pidió nada.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    valor = settings.value("version_ignorada", "")
    settings.endGroup()
    return str(valor or "")


def ignorar_version(version: str) -> None:
    """Anota que no hay que volver a avisar de una versión.

    Args:
        version: El número de versión a callar.
    """
    settings = QtCore.QSettings()
    settings.beginGroup(GRUPO_SETTINGS)
    settings.setValue("version_ignorada", version)
    settings.endGroup()
    settings.sync()


def leer_respuesta(datos: object) -> Actualizacion | None:
    """Saca de la respuesta de GitHub la versión nueva, si la hay.

    Devuelve ``None`` cuando la publicada no es más nueva que la instalada y
    cuando es justo la que el usuario pidió no volver a ver, así que quien
    llama no tiene que decidir nada.

    Args:
        datos: La respuesta de la API ya interpretada como JSON.

    Returns: La actualización a avisar, o ``None`` si no hay nada que decir.
    """
    if not isinstance(datos, dict):
        return None

    publicada = version_de_tag(str(datos.get("tag_name", "")))
    instalada = version_instalada()
    if publicada is None or instalada is None or publicada <= instalada:
        return None

    if str(publicada) == version_ignorada():
        return None

    url = str(datos.get("html_url") or __acercade__.__web__)
    return Actualizacion(version=str(publicada), url=url)


class BuscadorActualizaciones(QtCore.QObject):
    """Le pregunta a GitHub si hay una versión de Zonda más nueva que ésta.

    La consulta es asincrónica: se lanza con ``buscar()`` y el resultado llega
    por ``encontrada``. Quien se enganche después de que la respuesta ya volvió
    se la pierde, así que hay que mirar también ``actualizacion``.
    """

    encontrada = QtCore.pyqtSignal(object)
    """Lleva la ``Actualizacion``. Va tipada como ``object`` porque las señales
    de Qt no manejan dataclasses de Python."""

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._red = QtNetwork.QNetworkAccessManager(self)
        self._actualizacion: Actualizacion | None = None
        self._consultado = False

    @property
    def actualizacion(self) -> Actualizacion | None:
        """La versión nueva, si la consulta ya volvió y encontró una."""
        return self._actualizacion

    def buscar(self) -> None:
        """Lanza la consulta. Llamarla de nuevo no hace nada."""
        if self._consultado:
            return
        self._consultado = True

        pedido = QtNetwork.QNetworkRequest(QtCore.QUrl(url_api()))
        pedido.setRawHeader(b"Accept", b"application/vnd.github+json")
        # Sin límite, una red que traga los paquetes en silencio deja el pedido
        # colgado toda la sesión.
        pedido.setTransferTimeout(TIEMPO_LIMITE_MS)

        respuesta = self._red.get(pedido)
        if respuesta is None:  # pragma: no cover - no pasa con un pedido valido
            return
        respuesta.finished.connect(lambda: self._recibir(respuesta))

    def _recibir(self, respuesta: QtNetwork.QNetworkReply) -> None:
        respuesta.deleteLater()

        if respuesta.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            return

        try:
            datos = json.loads(respuesta.readAll().data().decode())
        except (ValueError, UnicodeDecodeError):
            return

        actualizacion = leer_respuesta(datos)
        if actualizacion is not None:
            self._actualizacion = actualizacion
            self.encontrada.emit(actualizacion)
