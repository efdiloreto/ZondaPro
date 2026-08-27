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

import webbrowser
from collections.abc import Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, recursos
from zonda.enums import (
    CategoriaExposicion,
    DireccionTopografia,
    Flexibilidad,
    TipoTerrenoTopografia,
)
from zonda.widgets import dialogos


class WidgetBotonModulo(QtWidgets.QWidget):
    def __init__(
        self, label: str, clave_icono: str, funcion: Callable[[], None]
    ) -> None:
        """

        Args:
            label: Label del boton.
            clave_icono: El alias del ícono dentro de los recursos.
            funcion: La funcion que se conecta al boton.
        """
        super().__init__()

        boton = QtWidgets.QPushButton()
        boton.setProperty("class", "modulo")
        boton.setIcon(recursos.icono(clave_icono))
        boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton.setIconSize(QtCore.QSize(128, 128))
        boton.clicked.connect(funcion)

        widget_label = QtWidgets.QLabel(label)
        widget_label.setProperty("class", "modulo")
        widget_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setSpacing(0)
        layout_principal.addWidget(boton)
        layout_principal.addWidget(widget_label)
        layout_principal.addStretch()

        self.setLayout(layout_principal)


class WidgetBotonPanel(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding
        )


class WidgetPanel(QtWidgets.QWidget):
    def __init__(self, altura_fija: int | None = None) -> None:
        """

        Args:
            altura_fija: La altura fija del widget.
        """
        super().__init__()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        if altura_fija is not None:
            self.setFixedHeight(altura_fija)


class WidgetLogo(QtWidgets.QLabel):
    def __init__(self, nombre_archivo="logo.png") -> None:
        """

        Args:
            nombre_archivo: El nombre del archivo.
        """
        super().__init__()
        self.setPixmap(recursos.pixmap(f"imagenes/{nombre_archivo}"))


class WidgetPanelEntrada(WidgetPanel):
    def __init__(self, componentes=False):
        super().__init__(altura_fija=57)

        self._tiene_componentes = componentes

        self.parametros_viento = {
            "categoria_exp": CategoriaExposicion.A,
            "velocidad": 45,
            "frecuencia": 1,
            "beta": 0.02,
            "flexibilidad": Flexibilidad.RIGIDA,
            "ciudad": "Buenos Aires",
            "factor_g_simplificado": True,
            "editar_velocidad": False,
        }

        self.parametros_topografia = {
            "considerar_topografia": False,
            "tipo_terreno": TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
            "direccion": DireccionTopografia.BARLOVENTO,
            "distancia_cresta": 50,
            "distancia_barlovento_sotavento": 50,
            "altura_terreno": 40,
        }

        widget_logo = WidgetLogo(nombre_archivo="logo-secundario.png")

        boton_dialogo_viento = WidgetBotonPanel("VIENTO")
        boton_dialogo_viento.clicked.connect(self._dialogo_viento)
        boton_dialogo_viento.setIcon(recursos.icono("iconos/viento.png"))
        boton_dialogo_viento.setIconSize(QtCore.QSize(32, 32))

        boton_dialogo_topografia = WidgetBotonPanel("TOPOGRAFIA")
        boton_dialogo_topografia.clicked.connect(self._dialogo_topografia)
        boton_dialogo_topografia.setIcon(recursos.icono("iconos/topografia.png"))
        boton_dialogo_topografia.setIconSize(QtCore.QSize(32, 32))

        self.boton_calcular = WidgetBotonPanel("CALCULAR")
        self.boton_calcular.setProperty("class", "accion")

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.setSpacing(0)
        layout_principal.setContentsMargins(11, 0, 0, 0)
        layout_principal.addWidget(widget_logo)
        layout_principal.addStretch()
        layout_principal.addWidget(boton_dialogo_viento)
        layout_principal.addWidget(boton_dialogo_topografia)

        if componentes:
            self.componentes = {
                "componentes_paredes": None,
                "componentes_cubierta": None,
            }
            boton_dialogo_componentes = WidgetBotonPanel("C&&R")
            boton_dialogo_componentes.clicked.connect(self._dialogo_componentes)
            boton_dialogo_componentes.setIcon(recursos.icono("iconos/componentes.png"))
            boton_dialogo_componentes.setIconSize(QtCore.QSize(32, 32))

            layout_principal.addWidget(boton_dialogo_componentes)

        layout_principal.addStretch()
        layout_principal.addWidget(self.boton_calcular)

        self.setLayout(layout_principal)

    def estado(self):
        """Los parámetros del panel, tal como se guardan en el archivo."""
        estado = {
            "viento": dict(self.parametros_viento),
            "topografia": dict(self.parametros_topografia),
        }
        if self._tiene_componentes:
            estado["componentes"] = {
                zona: dict(componentes) if componentes else None
                for zona, componentes in self.componentes.items()
            }
        return estado

    def cargar_estado(self, estado) -> None:
        """Deja el panel como lo dejó ``estado``."""
        self.parametros_viento = dict(estado["viento"])
        self.parametros_topografia = dict(estado["topografia"])
        if self._tiene_componentes:
            componentes = estado.get("componentes")
            if componentes is not None:
                self.componentes = {
                    zona: dict(valores) if valores else None
                    for zona, valores in componentes.items()
                }

    def _dialogo_viento(self):
        dialogo = dialogos.DialogoViento(**self.parametros_viento)
        if dialogo.exec():
            self.parametros_viento = dialogo.parametros()

    def _dialogo_topografia(self):
        dialogo = dialogos.DialogoTopografia(**self.parametros_topografia)
        if dialogo.exec():
            self.parametros_topografia = dialogo.parametros()

    def _dialogo_componentes(self):
        dialogo = dialogos.DialogoComponentes(self.componentes)
        if dialogo.exec():
            self.componentes = dialogo.componentes()


class WidgetPanelResultados(WidgetPanel):
    def __init__(self, edificio: bool = False):
        super().__init__(altura_fija=57)

        self.boton_volver = WidgetBotonPanel("VOLVER")

        self.boton_generar_reporte = WidgetBotonPanel("REPORTE")
        self.boton_generar_reporte.setProperty("class", "accion")

        layout_botones = QtWidgets.QHBoxLayout()
        layout_botones.setContentsMargins(0, 0, 0, 0)
        layout_botones.addWidget(self.boton_volver)
        layout_botones.addStretch()

        if edificio:
            self.boton_sprfv = WidgetBotonPanel("SPRFV")
            self.boton_sprfv.setProperty("class", "tab")
            self.boton_sprfv.setCheckable(True)
            self.boton_sprfv.setChecked(True)
            layout_botones.addWidget(self.boton_sprfv)

            self.boton_componentes = WidgetBotonPanel("C&&R")
            self.boton_componentes.setProperty("class", "tab")
            self.boton_componentes.setEnabled(False)
            self.boton_componentes.setCheckable(True)

            layout_botones.addWidget(self.boton_componentes)
            layout_botones.addStretch()

            grupo_botones = QtWidgets.QButtonGroup(self)
            grupo_botones.setExclusive(True)
            grupo_botones.addButton(self.boton_sprfv, 0)
            grupo_botones.addButton(self.boton_componentes, 1)

        layout_botones.addWidget(self.boton_generar_reporte)

        self.setLayout(layout_botones)


class WidgetSinBorde(QtWidgets.QWidget):
    """Una ventana sin barra de título, que se arrastra desde cualquier lado.

    La posición del puntero se pide con ``globalPosition()``, que devuelve un
    ``QPointF``. El ``globalPos()`` de Qt5 no existe más: al llamarlo saltaba un
    ``AttributeError``, y como PyQt6 aborta el proceso cuando un virtual
    reimplementado levanta una excepción, un clic sobre la ventana cerraba el
    programa de golpe.
    """

    def __init__(self) -> None:
        super().__init__()

        self._pos_ult: QtCore.QPoint | None = None
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)

    def mousePressEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is None:
            return
        self._pos_ult = a0.globalPosition().toPoint()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        # Sin un press previo no hay desde dónde medir el arrastre.
        if a0 is None or self._pos_ult is None:
            return
        pos = a0.globalPosition().toPoint()
        delta = pos - self._pos_ult
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self._pos_ult = pos


class WidgetLabelLinkInfo(QtWidgets.QLabel):
    def __init__(self, texto: str, ref: str):
        """

        Args:
            texto: El texto del label.
            ref: El link o referencia donde apunta.
        """

        super().__init__(f'<a style="color: #606060" href={ref}>{texto}</a>')
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.setOpenExternalLinks(True)


class WidgetAcercaDe(QtWidgets.QDialog):
    """El "Acerca de" del programa.

    La GPLv3 pide que cada copia diga que es software libre, quién la escribió,
    dónde está el código y dónde leer la licencia, así que el logo de la GNU y
    el botón "Licencia" no son decoración: son parte de lo que hay que mostrar.
    """

    def __init__(self, parent):
        super().__init__(parent)

        widget_logo = WidgetLogo()
        widget_logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        label_descripcion = QtWidgets.QLabel(
            "Zonda es un software libre y de código abierto destinado a calcular"
            " las cargas de viento sobre las estructuras de acuerdo al Reglamento"
            " Argentino de Acción del Viento sobre las Construcciones"
            " CIRSOC 102-2005."
        )
        label_descripcion.setWordWrap(True)
        # El ancho fijo es el que le da altura al texto: con `SetFixedSize` el
        # layout necesita saber cuánto ocupa el párrafo ya envuelto.
        label_descripcion.setFixedWidth(430)

        label_copyright = QtWidgets.QLabel(
            f"Copyright © {__acercade__.__anio_inicio__}"
            f" {__acercade__.__autor__}. Zonda se distribuye SIN NINGUNA GARANTÍA,"
            " bajo los términos de la Licencia Pública General de GNU,"
            " versión 3 o posterior."
        )
        label_copyright.setWordWrap(True)
        label_copyright.setFixedWidth(430)

        label_logo_gnu = QtWidgets.QLabel()
        label_logo_gnu.setPixmap(recursos.pixmap("imagenes/gplv3.png"))

        informacion = (
            ("Versión", QtWidgets.QLabel(__acercade__.__version__)),
            ("Licencia", QtWidgets.QLabel(__acercade__.__licencia__)),
            (
                "Autores",
                WidgetLabelLinkInfo(__acercade__.__autor__, __acercade__.__autor_web__),
            ),
            (
                "E-Mail",
                WidgetLabelLinkInfo(
                    __acercade__.__autor_email__, __acercade__.__contacto__
                ),
            ),
            ("Source", WidgetLabelLinkInfo(__acercade__.__web__, __acercade__.__web__)),
        )

        layout_info = QtWidgets.QGridLayout()
        for fila, (titulo, widget) in enumerate(informacion):
            layout_info.addWidget(QtWidgets.QLabel(f"{titulo}:"), fila, 0)
            layout_info.addWidget(widget, fila, 1)
        layout_info.addWidget(
            label_logo_gnu,
            0,
            3,
            len(informacion),
            1,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        layout_info.setColumnStretch(2, 1)

        botones = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        boton_licencia = botones.addButton(
            "Licencia", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole
        )
        boton_licencia.clicked.connect(
            lambda _=False: webbrowser.open(__acercade__.__licencia_url__)
        )
        botones.rejected.connect(self.reject)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(widget_logo)
        layout_principal.addSpacing(20)
        layout_principal.addWidget(label_descripcion)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(label_copyright)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(_linea_horizontal())
        layout_principal.addLayout(layout_info)
        layout_principal.addWidget(_linea_horizontal())
        layout_principal.addSpacing(10)
        layout_principal.addWidget(botones)
        # Que el layout fije el tamaño evita calcular a mano la altura que
        # terminan ocupando los párrafos envueltos.
        layout_principal.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetFixedSize
        )

        self.setLayout(layout_principal)

        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setWindowTitle("Acerca de Zonda")
        self.show()


def _linea_horizontal() -> QtWidgets.QFrame:
    """El separador que dibuja el estilo del sistema."""
    linea = QtWidgets.QFrame()
    linea.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    linea.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return linea
