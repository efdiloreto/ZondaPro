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

"""La columna de patrocinadores de la pantalla de bienvenida.

Zonda no le pide nada a nadie al cerrar ni interrumpe el trabajo: quienes
patrocinan el proyecto ocupan una columna fija de la bienvenida, que está a la
vista cada vez que se abre el programa. Mientras no haya ninguno, ese lugar
invita a serlo.

Las instrucciones para patrocinar no están en el programa: viven en el
repositorio (``PATROCINIO.md``), y desde acá se abre ese enlace. Así los
montos y las condiciones se pueden cambiar sin publicar una versión nueva.

Lo que compra un nivel es visibilidad, nunca funcionalidad. Zonda hace lo mismo
para todo el mundo, que es lo que corresponde en un programa GPL y lo que
sostiene el argumento de por qué vale la pena patrocinarlo.
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, patrocinadores, recursos
from zonda.enums import NivelPatrocinio
from zonda.widgets.custom import WidgetPanel

ALTO_LOGO_ORO = 40
"""Alto en píxeles de los logos de oro dentro de la columna."""

ALTO_LOGO_PLATA = 30
"""Alto en píxeles de los logos de plata dentro de la columna."""

INVITACION = "Tu estudio puede estar acá"
"""El enlace de abajo de la columna cuando ya hay patrocinadores."""

CLAVE_ICONO = "iconos/apoyo.png"
"""La ilustración del bloque de invitación.

Si el archivo no está, el bloque se arma igual sin imagen: es decoración, y no
tiene por qué impedir que se vea la invitación."""


def abrir_enlace(url: str) -> None:
    """Abre un enlace en el navegador del sistema.

    Args:
        url: La dirección a abrir.
    """
    # Igual que en el aviso de actualizaciones: se lo pide al sistema
    # operativo, que es lo único que funciona en las tres plataformas.
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


class LabelLogo(QtWidgets.QLabel):
    """El logo de un patrocinador, que lleva a su sitio si tiene uno.

    Escala el pixmap contra la densidad de la pantalla en lugar de dejar que Qt
    lo estire al dibujar: en un monitor HiDPI, un logo reducido sin tener en
    cuenta el ``devicePixelRatio`` se ve notablemente sucio.
    """

    def __init__(self, patrocinador: patrocinadores.Patrocinador, alto: int) -> None:
        """
        Args:
            patrocinador: De quién es el logo. Tiene que tener uno.
            alto: El alto final en píxeles lógicos.
        """
        super().__init__()

        self._web = patrocinador.web

        ratio = 1.0
        pantalla = QtGui.QGuiApplication.primaryScreen()
        if pantalla is not None:
            ratio = pantalla.devicePixelRatio()

        pixmap = QtGui.QPixmap(str(patrocinador.logo))
        pixmap = pixmap.scaledToHeight(
            int(alto * ratio), QtCore.Qt.TransformationMode.SmoothTransformation
        )
        pixmap.setDevicePixelRatio(ratio)
        self.setPixmap(pixmap)

        self.setToolTip(patrocinador.nombre)
        if self._web:
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is not None and self._web:
            abrir_enlace(self._web)


def _widget_patrocinador(
    patrocinador: patrocinadores.Patrocinador, alto: int
) -> QtWidgets.QWidget:
    """El widget con que se muestra a un patrocinador.

    Args:
        patrocinador: A quién mostrar.
        alto: El alto del logo, si tiene.

    Returns: El logo, o su nombre como enlace cuando no hay logo -que es el
        caso de bronce y el de un archivo que falta-.
    """
    if patrocinador.logo is not None:
        return LabelLogo(patrocinador, alto)

    nombre = patrocinador.nombre
    if not patrocinador.web:
        return QtWidgets.QLabel(nombre)

    label = QtWidgets.QLabel(
        f'<a style="color: #606060" href="{patrocinador.web}">{nombre}</a>'
    )
    label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
    label.setOpenExternalLinks(True)
    return label


def fuente_de_rotulo(widget: QtWidgets.QWidget, mayusculas: bool = True) -> QtGui.QFont:
    """La fuente de los rótulos chicos, derivada de la del sistema.

    Se deriva en lugar de fijar un tamaño en píxeles para que la interfaz siga
    la escala de fuentes del sistema operativo: con "texto grande" activado, un
    tamaño fijo en px no crece y el rótulo queda ilegible.

    Args:
        widget: De quién se toma la fuente base.
        mayusculas: Si el texto va en versalitas. Va en ``False`` cuando el
            texto lleva nombres propios o siglas —"GPLv3" en mayúsculas se lee
            mal—.

    Returns: La fuente del rótulo.
    """
    fuente = widget.font()
    fuente.setPointSize(max(7, fuente.pointSize() - 2))
    if mayusculas:
        fuente.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
    return fuente


class WidgetSeccionPatrocinadores(WidgetPanel):
    """La columna lateral de la bienvenida con quienes patrocinan Zonda.

    Está siempre visible y ocupa un lugar propio, no un renglón al pie: es la
    contrapartida de que el programa no interrumpa el trabajo con ningún
    pedido, y es lo que un estudio compra cuando patrocina. Muestra oro y
    plata; bronce figura en el repositorio, que es donde entra una lista larga.

    Mientras no haya patrocinadores, el mismo lugar muestra la invitación a
    serlo, que es lo que va a estar en pantalla los primeros meses.
    """

    ANCHO = 210
    """El ancho fijo de la columna, en píxeles.

    Fijo y no elástico para que los logos no bailen de tamaño al agrandar la
    ventana, y para que el bloque de módulos se quede con todo lo que sobra.
    """

    def __init__(self, lista: tuple[patrocinadores.Patrocinador, ...]) -> None:
        """
        Args:
            lista: Todos los patrocinadores. La columna se queda con los que
                llevan logo en pantalla.
        """
        super().__init__()

        self.setProperty("class", "patrocinadores")
        self.setFixedWidth(self.ANCHO)

        agrupados = patrocinadores.mezclados_por_nivel(lista)
        alto = {
            NivelPatrocinio.ORO: ALTO_LOGO_ORO,
            NivelPatrocinio.PLATA: ALTO_LOGO_PLATA,
        }

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        logos = [
            _widget_patrocinador(patrocinador, alto[nivel])
            for nivel in (NivelPatrocinio.ORO, NivelPatrocinio.PLATA)
            for patrocinador in agrupados.get(nivel, ())
        ]

        # Sin patrocinadores no se encabeza con "Patrocinado por": no hay nadie
        # que lo esté, y el rótulo sobre una columna vacía se lee como un error.
        if logos:
            titulo = QtWidgets.QLabel("Patrocinado por")
            titulo.setFont(fuente_de_rotulo(self))
            titulo.setStyleSheet("color: #707070;")
            layout.addWidget(titulo)

            for widget in logos:
                layout.addWidget(widget, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

            layout.addStretch()
            layout.addWidget(self._enlace_chico())
        else:
            for widget in self._invitacion():
                layout.addWidget(widget)
            layout.addStretch()

        self.setLayout(layout)

    def _invitacion(self) -> list[QtWidgets.QWidget]:
        """El bloque que ocupa la columna mientras no haya patrocinadores.

        Returns: La ilustración -si el recurso está-, el texto y el botón.
        """
        widgets: list[QtWidgets.QWidget] = []

        pixmap = recursos.pixmap(CLAVE_ICONO)
        if not pixmap.isNull():
            ilustracion = QtWidgets.QLabel()
            ilustracion.setPixmap(
                pixmap.scaledToWidth(
                    96, QtCore.Qt.TransformationMode.SmoothTransformation
                )
            )
            ilustracion.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
            widgets.append(ilustracion)

        texto = QtWidgets.QLabel(
            "<b>Zonda es libre y gratuito.</b><br><br>"
            "Este espacio es de los estudios que lo patrocinan."
        )
        texto.setWordWrap(True)
        texto.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        texto.setStyleSheet("color: #505050;")
        widgets.append(texto)

        boton = QtWidgets.QPushButton("Apoyá el proyecto")
        boton.setProperty("class", "apoyo")
        boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton.setToolTip("Se abre el repositorio, con los niveles y cómo sumarse")
        boton.clicked.connect(lambda _=False: abrir_enlace(__acercade__.__apoyo__))
        widgets.append(boton)

        return widgets

    def _enlace_chico(self) -> QtWidgets.QLabel:
        """El enlace del pie de la columna cuando ya hay patrocinadores.

        Returns: El enlace al repositorio.
        """
        enlace = QtWidgets.QLabel(
            f'<a style="color: #1858a8" href="{__acercade__.__apoyo__}">{INVITACION}</a>'
        )
        enlace.setWordWrap(True)
        enlace.setFont(fuente_de_rotulo(self))
        enlace.setToolTip("Se abre el repositorio, con los niveles y cómo sumarse")
        enlace.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        enlace.setOpenExternalLinks(True)
        enlace.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        return enlace
