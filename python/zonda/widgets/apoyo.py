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

"""La pantalla de apoyo al proyecto y la franja de patrocinadores.

Zonda no le pide nada a nadie al cerrar ni interrumpe el trabajo: el pedido vive
en la pantalla de bienvenida, que es donde el usuario ya está mirando, y no
tapa ni demora nada. Los de nivel oro aparecen además en una franja fija abajo
de la bienvenida.

Lo que compra un nivel es visibilidad, nunca funcionalidad. Zonda hace lo mismo
para todo el mundo, que es lo que corresponde en un programa GPL y lo que
sostiene el argumento de por qué vale la pena apoyarlo.
"""

from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, patrocinadores, recursos
from zonda.enums import NivelPatrocinio
from zonda.widgets.custom import WidgetPanel

ALTO_LOGO_ORO = 34
"""Alto en píxeles de los logos de oro, tanto en la franja como en el diálogo."""

ALTO_LOGO_PLATA = 26
"""Alto en píxeles de los logos de plata dentro del diálogo."""

INVITACION = "Tu estudio puede estar acá"
"""Lo que dice la franja mientras no haya ningún patrocinador de oro."""

NIVELES = {
    NivelPatrocinio.ORO: (
        "Oro",
        "Logo en la pantalla de bienvenida de Zonda, primer lugar en esta"
        " pantalla y mención en las notas de cada versión.",
    ),
    NivelPatrocinio.PLATA: (
        "Plata",
        "Logo y enlace en esta pantalla.",
    ),
    NivelPatrocinio.BRONCE: (
        "Bronce",
        "Tu nombre en esta pantalla y en el repositorio.",
    ),
}
"""Qué incluye cada nivel. Los precios no están acá: viven en la web, así que
cambiarlos no obliga a publicar una versión nueva del programa."""


def _abrir(url: str) -> None:
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
            _abrir(self._web)


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


def _fuente_de_titulo(widget: QtWidgets.QWidget) -> QtGui.QFont:
    """La fuente de los rótulos chicos, derivada de la del sistema.

    Se deriva en lugar de fijar un tamaño en píxeles para que la interfaz
    siga la escala de fuentes del sistema operativo: con "texto grande"
    activado, un tamaño fijo en px no crece y el rótulo queda ilegible.

    Args:
        widget: De quién se toma la fuente base.

    Returns: La fuente del rótulo.
    """
    fuente = widget.font()
    fuente.setPointSize(max(7, fuente.pointSize() - 2))
    fuente.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
    return fuente


class WidgetSeccionPatrocinadores(WidgetPanel):
    """El pie de la bienvenida con quienes apoyan el proyecto.

    Está siempre visible: es la contrapartida de que Zonda no interrumpa el
    trabajo con ningún pedido. Muestra oro y plata —bronce vive en el diálogo,
    que es donde hay lugar para una lista larga— y, mientras no haya nadie,
    invita en lugar de dejar un hueco.
    """

    apoyo_solicitado = QtCore.pyqtSignal()
    """Se emite al hacer clic en la invitación."""

    def __init__(self, lista: tuple[patrocinadores.Patrocinador, ...]) -> None:
        """
        Args:
            lista: Todos los patrocinadores. La sección se queda con los que
                llevan logo en pantalla.
        """
        super().__init__()

        self.setProperty("class", "patrocinadores")

        agrupados = patrocinadores.mezclados_por_nivel(lista)
        alto = {
            NivelPatrocinio.ORO: ALTO_LOGO_ORO,
            NivelPatrocinio.PLATA: ALTO_LOGO_PLATA,
        }

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(25, 10, 25, 10)
        layout.setSpacing(16)

        titulo = QtWidgets.QLabel("Con el apoyo de")
        titulo.setFont(_fuente_de_titulo(self))
        titulo.setStyleSheet("color: #707070;")
        layout.addWidget(titulo)

        mostrados = 0
        for nivel in (NivelPatrocinio.ORO, NivelPatrocinio.PLATA):
            for patrocinador in agrupados.get(nivel, ()):
                layout.addWidget(_widget_patrocinador(patrocinador, alto[nivel]))
                mostrados += 1

        if not mostrados:
            invitacion = QtWidgets.QLabel(
                f'<a style="color: #1858a8" href="#">{INVITACION}</a>'
            )
            invitacion.setToolTip("Conocé cómo apoyar el proyecto")
            invitacion.linkActivated.connect(lambda _: self.apoyo_solicitado.emit())
            invitacion.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            layout.addWidget(invitacion)

        layout.addStretch()
        self.setLayout(layout)


class DialogoApoyo(QtWidgets.QDialog):
    """La pantalla que explica el proyecto, los niveles y quiénes ya apoyan."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        lista: tuple[patrocinadores.Patrocinador, ...],
    ) -> None:
        """
        Args:
            parent: La ventana sobre la que se abre.
            lista: Los patrocinadores a mostrar.
        """
        super().__init__(parent)

        widget_logo = QtWidgets.QLabel()
        widget_logo.setPixmap(recursos.pixmap("imagenes/logo.png"))
        widget_logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        descripcion = QtWidgets.QLabel(
            "Zonda es software libre y gratuito, y lo va a seguir siendo. Está"
            " hecho y mantenido por muy poca gente, en el tiempo que le queda"
            " libre, y le ahorra horas de cálculo y verificación a cada"
            " profesional que lo usa."
            "<br><br>"
            "Si te resulta útil en tu trabajo, apoyarlo es lo que permite que"
            " siga actualizado —con los reglamentos, con los sistemas"
            " operativos y con los errores que aparecen—. Los estudios que lo"
            " apoyan aparecen acá y en la pantalla de inicio."
        )
        descripcion.setWordWrap(True)
        descripcion.setFixedWidth(460)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(widget_logo)
        layout_principal.addSpacing(16)
        layout_principal.addWidget(descripcion)
        layout_principal.addSpacing(16)
        layout_principal.addWidget(self._widget_niveles())

        agrupados = patrocinadores.mezclados_por_nivel(lista)
        if agrupados:
            layout_principal.addSpacing(16)
            layout_principal.addWidget(self._widget_lista(agrupados))

        botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        boton_apoyar = botones.addButton(
            "Quiero apoyar el proyecto",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        # ``addButton`` sólo devuelve None si el rol no existe, pero el stub lo
        # declara opcional y sin el chequeo no tipa.
        if boton_apoyar is not None:
            boton_apoyar.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            boton_apoyar.clicked.connect(lambda _=False: _abrir(__acercade__.__apoyo__))
        botones.rejected.connect(self.reject)

        layout_principal.addSpacing(16)
        layout_principal.addWidget(botones)
        # Igual que en "Acerca de": que el layout fije el tamaño evita calcular
        # a mano la altura que terminan ocupando los párrafos envueltos.
        layout_principal.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetFixedSize
        )

        self.setLayout(layout_principal)
        self.setWindowTitle("Apoyá el proyecto")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

    def _widget_niveles(self) -> QtWidgets.QWidget:
        """Los tres niveles con lo que incluye cada uno.

        Returns: El widget con la grilla de niveles.
        """
        grilla = QtWidgets.QGridLayout()
        grilla.setHorizontalSpacing(14)
        grilla.setVerticalSpacing(8)

        for fila, (nivel, (titulo, detalle)) in enumerate(NIVELES.items()):
            label_titulo = QtWidgets.QLabel(titulo.upper())
            label_titulo.setStyleSheet("font-weight: bold;")
            label_titulo.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

            label_detalle = QtWidgets.QLabel(detalle)
            label_detalle.setWordWrap(True)
            label_detalle.setFixedWidth(380)

            grilla.addWidget(label_titulo, fila, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            grilla.addWidget(label_detalle, fila, 1)
            del nivel

        widget = QtWidgets.QWidget()
        widget.setLayout(grilla)
        return widget

    def _widget_lista(
        self,
        agrupados: dict[NivelPatrocinio, tuple[patrocinadores.Patrocinador, ...]],
    ) -> QtWidgets.QWidget:
        """La lista de quienes ya apoyan, por nivel.

        Args:
            agrupados: Los patrocinadores por nivel, ya barajados.

        Returns: El widget con la lista.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        altos = {
            NivelPatrocinio.ORO: ALTO_LOGO_ORO,
            NivelPatrocinio.PLATA: ALTO_LOGO_PLATA,
            NivelPatrocinio.BRONCE: ALTO_LOGO_PLATA,
        }

        for nivel, lista in agrupados.items():
            titulo = QtWidgets.QLabel(NIVELES[nivel][0].upper())
            titulo.setStyleSheet("color: #808080; font-size: 10px;")
            layout.addWidget(titulo)

            fila = QtWidgets.QHBoxLayout()
            fila.setSpacing(14)
            for patrocinador in lista:
                fila.addWidget(_widget_patrocinador(patrocinador, altos[nivel]))
            fila.addStretch()
            layout.addLayout(fila)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        return widget
