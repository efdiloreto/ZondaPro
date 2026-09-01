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

INVITACION = "Podés estar acá"
"""El enlace de abajo de la columna cuando ya hay patrocinadores."""

TEXTO_SIN_PATROCINADORES = "Este espacio es para nuestros patrocinadores"
"""Lo que ocupa la columna mientras no haya ningún patrocinador."""

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
    """El logo de un patrocinador, clickeable.

    Qué pasa al tocarlo depende del nivel, y es lo que cada uno compró: el de
    oro abre su perfil dentro del programa; el de plata, el enlace que haya
    elegido —su sitio o su correo—.

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

        self._patrocinador = patrocinador
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

        self._es_oro = patrocinador.nivel is NivelPatrocinio.ORO
        if self._es_oro:
            self.setToolTip(f"Conocé a {patrocinador.nombre}")
        else:
            self.setToolTip(patrocinador.nombre)

        if self._es_oro or self._web:
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev: QtGui.QMouseEvent | None) -> None:
        if ev is None:
            return
        if self._es_oro:
            DialogoPatrocinador(self, self._patrocinador)
        elif self._web:
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
            # El botón se va al fondo de la columna: es la acción que cierra el
            # bloque, y arrimado al texto competía con él.
            layout.addStretch()
            layout.addWidget(self._boton_apoyo())

        self.setLayout(layout)

    def _invitacion(self) -> list[QtWidgets.QWidget]:
        """El bloque que ocupa la columna mientras no haya patrocinadores.

        Returns: La ilustración -si el recurso está- y el texto.
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

        texto = QtWidgets.QLabel(TEXTO_SIN_PATROCINADORES)
        texto.setWordWrap(True)
        texto.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        texto.setStyleSheet("color: #505050;")
        widgets.append(texto)

        return widgets

    def _boton_apoyo(self) -> QtWidgets.QPushButton:
        """El botón que lleva a las instrucciones para patrocinar.

        Returns: El botón.
        """
        boton = QtWidgets.QPushButton("Apoyá el proyecto")
        boton.setProperty("class", "apoyo")
        boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton.setToolTip("Se abre el repositorio, con los niveles y cómo sumarse")
        boton.clicked.connect(lambda _=False: abrir_enlace(__acercade__.__apoyo__))
        return boton

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


def _titulo(widget: QtWidgets.QWidget, texto: str) -> QtWidgets.QLabel:
    """Un rótulo de sección, del mismo tratamiento que "Patrocinado por".

    Args:
        widget: De quién se toma la fuente base.
        texto: Qué dice.

    Returns: El rótulo.
    """
    label = QtWidgets.QLabel(texto)
    label.setFont(fuente_de_rotulo(widget))
    label.setStyleSheet("color: #707070;")
    return label


class DialogoPatrocinador(QtWidgets.QDialog):
    """El perfil de un patrocinador de oro.

    Es lo que compra ese nivel: no un enlace que se va del programa, sino una
    pantalla propia adentro. Se arma con lo que la entrada traiga, así que una
    sin descripción o sin ciudad se muestra igual, más corta.
    """

    ALTO_LOGO = 72
    """El alto del logo en el perfil, en píxeles."""

    ANCHO_TEXTO = 420
    """A qué ancho se envuelve la descripción, en píxeles."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        patrocinador: patrocinadores.Patrocinador,
    ) -> None:
        """
        Args:
            parent: Sobre qué ventana se abre.
            patrocinador: De quién es el perfil.
        """
        super().__init__(parent)

        self._patrocinador = patrocinador

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(6)

        if patrocinador.logo is not None:
            layout.addWidget(
                LabelLogo(patrocinador, self.ALTO_LOGO),
                alignment=QtCore.Qt.AlignmentFlag.AlignLeft,
            )
            layout.addSpacing(10)

        nombre = QtWidgets.QLabel(patrocinador.nombre)
        fuente_nombre = nombre.font()
        fuente_nombre.setPointSize(fuente_nombre.pointSize() + 4)
        fuente_nombre.setWeight(QtGui.QFont.Weight.Medium)
        nombre.setFont(fuente_nombre)
        layout.addWidget(nombre)

        for texto in (patrocinador.rubro, patrocinador.ciudad):
            if texto:
                label = QtWidgets.QLabel(texto)
                label.setStyleSheet("color: #606060;")
                layout.addWidget(label)

        if patrocinador.descripcion:
            descripcion = QtWidgets.QLabel(patrocinador.descripcion)
            descripcion.setWordWrap(True)
            descripcion.setFixedWidth(self.ANCHO_TEXTO)
            layout.addSpacing(10)
            layout.addWidget(descripcion)

        if patrocinador.desde or patrocinador.fundador:
            partes = []
            if patrocinador.desde:
                partes.append(f"Patrocina Zonda desde {patrocinador.desde}")
            if patrocinador.fundador:
                partes.append("Fundador")
            leyenda = QtWidgets.QLabel(" · ".join(partes))
            leyenda.setFont(fuente_de_rotulo(self, mayusculas=False))
            leyenda.setStyleSheet("color: #808080;")
            layout.addSpacing(10)
            layout.addWidget(leyenda)

        layout.addSpacing(10)
        layout.addWidget(self._botones())
        layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)

        self.setLayout(layout)
        self.setWindowTitle(patrocinador.nombre)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.show()

    def _botones(self) -> QtWidgets.QDialogButtonBox:
        """Los accesos al sitio y al correo, si la entrada los trae.

        Returns: La botonera.
        """
        botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        botones.rejected.connect(self.reject)

        for texto, enlace in (
            ("Ir al sitio", self._patrocinador.web),
            ("Escribirles", self._patrocinador.contacto),
        ):
            if not enlace:
                continue
            boton = botones.addButton(
                texto, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
            )
            if boton is not None:
                boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                boton.clicked.connect(lambda _=False, e=enlace: abrir_enlace(e))

        return botones


class DialogoAgradecimientos(QtWidgets.QDialog):
    """Quiénes hacen posible el proyecto: los tres niveles y quienes ponen tiempo.

    Es el único lugar donde figuran los de bronce, y es lo que ese nivel compra.
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """
        Args:
            parent: Sobre qué ventana se abre.
        """
        super().__init__(parent)

        lista = patrocinadores.cargar()
        agrupados = patrocinadores.mezclados_por_nivel(lista)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(8)

        intro = QtWidgets.QLabel(
            "Zonda es libre y gratuito. Estos son los estudios que lo patrocinan"
            " y las personas que le ponen tiempo."
        )
        intro.setWordWrap(True)
        intro.setFixedWidth(420)
        layout.addWidget(intro)
        layout.addSpacing(10)

        for nivel, del_nivel in agrupados.items():
            layout.addWidget(_titulo(self, nivel.value))
            for patrocinador in del_nivel:
                layout.addWidget(QtWidgets.QLabel(patrocinador.nombre))
            layout.addSpacing(8)

        equipo = patrocinadores.colaboradores()
        if equipo:
            layout.addWidget(_titulo(self, "Colaboran con su tiempo"))
            for colaborador in equipo:
                texto = colaborador.nombre
                if colaborador.aporte:
                    texto += f" — {colaborador.aporte}"
                layout.addWidget(QtWidgets.QLabel(texto))
            layout.addSpacing(8)

        if not agrupados and not equipo:
            layout.addWidget(
                QtWidgets.QLabel(
                    "Todavía no hay a quién agradecerle. Podés ser el primero."
                )
            )
            layout.addSpacing(8)

        botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)

        self.setLayout(layout)
        self.setWindowTitle("Agradecimientos")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.show()
