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
    CategoriaEstructura,
    CategoriaExposicion,
    DireccionTopografia,
    Flexibilidad,
    TipoTerrenoTopografia,
)
from zonda.widgets import dialogos


def abrir_enlace(url: str) -> None:
    """Abre un enlace en el navegador del sistema.

    Args:
        url: La dirección a abrir.
    """
    # Igual que en el aviso de actualizaciones: se lo pide al sistema
    # operativo, que es lo único que funciona en las tres plataformas.
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


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
        # El boton es solo icono: sin nombre accesible, un lector de pantalla
        # anuncia "boton" tres veces y no hay forma de saber cual es cual.
        boton.setAccessibleName(label)
        boton.setToolTip(label)
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
    def __init__(self, componentes=False, solo_cubierta=False, hay_parapeto=None):
        super().__init__(altura_fija=57)

        self._tiene_componentes = componentes
        self._solo_cubierta = solo_cubierta
        # Callable que indica si hay que pedir el área efectiva del parapeto
        # en el diálogo de componentes; None para los módulos sin parapeto.
        self._hay_parapeto = hay_parapeto

        self.parametros_viento = {
            "categoria_exp": CategoriaExposicion.B,
            "velocidad": 55.1,
            "frecuencia": 1,
            "beta": 0.02,
            "flexibilidad": Flexibilidad.RIGIDA,
            "ciudad": "Buenos Aires",
            "factor_g_simplificado": True,
            "editar_velocidad": False,
            "altitud": 0.0,
            "categoria_riesgo_viento": CategoriaEstructura.II,
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
        boton_dialogo_viento.setProperty("class", "dialogo")
        boton_dialogo_viento.clicked.connect(self._dialogo_viento)

        boton_dialogo_topografia = WidgetBotonPanel("TOPOGRAFIA")
        boton_dialogo_topografia.setProperty("class", "dialogo")
        boton_dialogo_topografia.clicked.connect(self._dialogo_topografia)

        self.boton_calcular = WidgetBotonPanel("CALCULAR")
        self.boton_calcular.setProperty("class", "accion")

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(11, 0, 11, 0)
        layout_principal.addWidget(widget_logo)
        layout_principal.addStretch()
        layout_principal.addWidget(
            boton_dialogo_viento, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout_principal.addWidget(
            boton_dialogo_topografia, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        if componentes:
            self.componentes = {
                "componentes_paredes": None,
                "componentes_cubierta": None,
                "area_parapeto": None,
            }
            boton_dialogo_componentes = WidgetBotonPanel("C&&R")
            boton_dialogo_componentes.setProperty("class", "dialogo")
            boton_dialogo_componentes.clicked.connect(self._dialogo_componentes)

            layout_principal.addWidget(
                boton_dialogo_componentes, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
            )

        layout_principal.addStretch()
        layout_principal.addWidget(
            self.boton_calcular, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        self.setLayout(layout_principal)

    def estado(self):
        """Los parámetros del panel, tal como se guardan en el archivo."""
        estado = {
            "viento": dict(self.parametros_viento),
            "topografia": dict(self.parametros_topografia),
        }
        if self._tiene_componentes:
            estado["componentes"] = {
                zona: (
                    valores
                    if zona == "area_parapeto"
                    else (dict(valores) if valores else None)
                )
                for zona, valores in self.componentes.items()
            }
        return estado

    def cargar_estado(self, estado) -> None:
        """Deja el panel como lo dejó ``estado``."""
        self.parametros_viento = dict(estado["viento"])
        if "altitud" not in self.parametros_viento:
            self.parametros_viento["altitud"] = 0.0
        if "categoria_riesgo_viento" not in self.parametros_viento:
            self.parametros_viento["categoria_riesgo_viento"] = CategoriaEstructura.II
        self.parametros_topografia = dict(estado["topografia"])
        if self._tiene_componentes:
            componentes = estado.get("componentes")
            if componentes is not None:
                self.componentes = {
                    zona: (
                        valores
                        if zona == "area_parapeto"
                        else (dict(valores) if valores else None)
                    )
                    for zona, valores in componentes.items()
                }
                # Los proyectos de versiones anteriores no traen el área del
                # parapeto: falta cargarla antes de calcular.
                self.componentes.setdefault("area_parapeto", None)

    def _dialogo_viento(self):
        dialogo = dialogos.DialogoViento(**self.parametros_viento)
        if dialogo.exec():
            self.parametros_viento = dialogo.parametros()

    def _dialogo_topografia(self):
        dialogo = dialogos.DialogoTopografia(**self.parametros_topografia)
        if dialogo.exec():
            self.parametros_topografia = dialogo.parametros()

    def _dialogo_componentes(self):
        dialogo = dialogos.DialogoComponentes(
            self.componentes,
            solo_cubierta=self._solo_cubierta,
            con_parapeto=self._hay_parapeto() if self._hay_parapeto else False,
        )
        if dialogo.exec():
            self.componentes = dialogo.componentes()


def crear_segmento(texto: str, clase: str = "segmento") -> WidgetBotonPanel:
    """Crea un botón segmento, marcable, con la clase del QSS.

    Lo usan la barra de resultados del panel y los selectores de las
    páginas de componentes del reporte. En la barra van con la clase de
    los botones de diálogo, porque comparten el look.

    Args:
        texto: El rótulo del segmento.
        clase: La clase que viste al botón en el QSS.

    Returns:
        El botón creado, sin grupo: quien lo usa lo agrega al suyo.
    """
    boton = WidgetBotonPanel(texto)
    boton.setProperty("class", clase)
    boton.setCheckable(True)
    return boton


def crear_capsula(*botones: WidgetBotonPanel) -> QtWidgets.QWidget:
    """Arma una cápsula con los segmentos dados.

    El valor de la clase va sin acento porque los selectores del QSS no
    lo llevan bien.

    Args:
        *botones: Los segmentos del grupo exclusivo, en orden.

    Returns:
        El contenedor de la cápsula.
    """
    cápsula = QtWidgets.QWidget()
    cápsula.setProperty("class", "capsula")

    layout = QtWidgets.QHBoxLayout(cápsula)
    layout.setContentsMargins(3, 3, 3, 3)
    layout.setSpacing(3)

    for boton in botones:
        layout.addWidget(boton)

    return cápsula


class WidgetPanelResultados(WidgetPanel):
    def __init__(self, sistemas: bool = False):
        super().__init__(altura_fija=57)

        self.boton_volver = WidgetBotonPanel("VOLVER")
        self.boton_volver.setProperty("class", "dialogo")

        layout_botones = QtWidgets.QHBoxLayout()
        layout_botones.setSpacing(10)
        layout_botones.setContentsMargins(11, 0, 0, 0)
        layout_botones.addWidget(
            self.boton_volver, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout_botones.addStretch()

        # Los botones del panel son un grupo exclusivo: marcan qué página
        # del apilador de resultados se muestra y hacen de índice del
        # módulo. Van sueltos, todos con el look de los botones de
        # diálogo, y el marcado se llena de gris.
        self.grupo_botones = QtWidgets.QButtonGroup(self)
        self.grupo_botones.setExclusive(True)

        if sistemas:
            self.boton_sprfv = self._crear_segmento("3D - SPRFV", 0, chequeada=True)
            self.boton_componentes = self._crear_segmento("3D - C&&R", 1)
            self.boton_componentes.setEnabled(False)
            layout_botones.addWidget(
                self.boton_sprfv, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            layout_botones.addWidget(
                self.boton_componentes, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        else:
            self.boton_3d = self._crear_segmento("3D", 0, chequeada=True)
            layout_botones.addWidget(
                self.boton_3d, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
            )

        self.boton_reporte = self._crear_segmento("REPORTE", 2 if sistemas else 1)
        layout_botones.addWidget(
            self.boton_reporte, 0, QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        layout_botones.addStretch()

        self.setLayout(layout_botones)

    def _crear_segmento(self, texto: str, id: int, chequeada: bool = False):
        """Crea un segmento del grupo y la agrega a él.

        Args:
            texto: El rótulo del segmento.
            id: El id con el que el grupo lo reporta al conmutar.
            chequeada: Si arranca marcado.

        Returns:
            El botón creado.
        """
        boton = crear_segmento(texto, clase="dialogo")
        boton.setChecked(chequeada)
        self.grupo_botones.addButton(boton, id)
        return boton


def enlaces_de_autores(color: str = "#606060") -> str:
    """Los nombres de los autores, cada uno enlazado a su perfil.

    Devuelve el fragmento y no un widget porque los dos lugares que lo usan
    —el "Acerca de" y el pie de la pantalla de inicio— lo meten dentro de un
    texto propio.

    Args:
        color: Con qué color se dibujan los enlaces.

    Returns: El HTML con un enlace por autor, separados por coma.
    """
    return ", ".join(
        f'<a style="color: {color}" href="{perfil}">{nombre}</a>'
        for nombre, perfil in __acercade__.__autores__
    )


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
            " CIRSOC 102-2025."
        )
        label_descripcion.setWordWrap(True)
        # El ancho fijo es el que le da altura al texto: con `SetFixedSize` el
        # layout necesita saber cuánto ocupa el párrafo ya envuelto.
        label_descripcion.setFixedWidth(430)

        label_garantia = QtWidgets.QLabel(
            "Zonda se distribuye SIN NINGUNA GARANTÍA, bajo los términos de la"
            " Licencia Pública General de GNU, versión 3 o posterior."
        )
        label_garantia.setWordWrap(True)
        label_garantia.setFixedWidth(430)

        label_copyright = QtWidgets.QLabel(
            f"Copyright © {__acercade__.anios_copyright()} {__acercade__.__autor__}."
        )
        label_copyright.setWordWrap(True)
        label_copyright.setFixedWidth(430)

        label_logo_gnu = QtWidgets.QLabel()
        label_logo_gnu.setPixmap(recursos.pixmap("imagenes/gplv3.png"))

        informacion = (
            ("Versión", QtWidgets.QLabel(__acercade__.__version__)),
            ("Licencia", QtWidgets.QLabel(__acercade__.__licencia__)),
            ("Autores", _label_autores()),
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
        layout_principal.addWidget(label_garantia)
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


def _label_autores() -> QtWidgets.QLabel:
    """Los autores del "Acerca de", cada uno enlazado a su perfil.

    Returns: El label con los dos enlaces.
    """
    label = QtWidgets.QLabel(enlaces_de_autores())
    # Con TextBrowserInteraction los enlaces entran en la cadena del tabulador,
    # cosa que un label de sólo lectura no da por sí solo.
    label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
    label.setOpenExternalLinks(True)
    return label


def _linea_horizontal() -> QtWidgets.QFrame:
    """El separador que dibuja el estilo del sistema."""
    linea = QtWidgets.QFrame()
    linea.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    linea.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return linea
