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

"""La pantalla de bienvenida: elegir el módulo con el que se va a trabajar.

Las opciones generales del programa —configuración, ayuda y acerca de— viven en
la barra de menús de cada módulo (``zonda.widgets.modulos``), no acá.

**La pantalla no se muestra sola.** Quien la crea decide si mostrarla: cuando el
programa arranca abriendo un archivo (`zonda.main`), el módulo que corresponde se
abre directo y la bienvenida queda escondida hasta que se cierre ese módulo.
"""

from PyQt6 import QtCore, QtWidgets

from zonda.enums import Estructura
from zonda.widgets.custom import (
    WidgetBotonModulo,
    WidgetLogo,
    WidgetPanel,
    WidgetSinBorde,
)
from zonda.widgets.modulos import (
    WidgetModuloCartel,
    WidgetModuloCubiertaAislada,
    WidgetModuloEdificio,
)

MODULOS = {
    Estructura.EDIFICIO: WidgetModuloEdificio,
    Estructura.CUBIERTA_AISLADA: WidgetModuloCubiertaAislada,
    Estructura.CARTEL: WidgetModuloCartel,
}


class WidgetBienvenida(WidgetSinBorde):
    def __init__(self):
        """ """

        super().__init__()

        self._modulo = None

        widget_logo = WidgetLogo()

        boton_edificio = WidgetBotonModulo(
            "Edificio", "iconos/edificio.png", self._modulo_edificio
        )

        boton_cubierta_aislada = WidgetBotonModulo(
            "Cubierta Aislada",
            "iconos/cubierta-aislada.png",
            self._modulo_cubierta_aislada,
        )

        boton_cartel = WidgetBotonModulo(
            "Cartel", "iconos/cartel.png", self._modulo_cartel
        )

        boton_salir = QtWidgets.QPushButton("Salir")
        boton_salir.setFixedWidth(75)
        boton_salir.setProperty("class", "salir")
        boton_salir.clicked.connect(self._salir)

        layout_encabezado = QtWidgets.QHBoxLayout()

        layout_encabezado.addWidget(widget_logo)
        layout_encabezado.addStretch()

        widget_encabezado = WidgetPanel()
        widget_encabezado.setLayout(layout_encabezado)

        layout_modulos = QtWidgets.QHBoxLayout()
        layout_modulos.setContentsMargins(25, 25, 25, 11)
        layout_modulos.setSpacing(60)
        layout_modulos.addWidget(boton_edificio)
        layout_modulos.addWidget(boton_cubierta_aislada)
        layout_modulos.addWidget(boton_cartel)

        layout_inferior = QtWidgets.QHBoxLayout()
        layout_inferior.setContentsMargins(25, 11, 25, 11)
        layout_inferior.addStretch()
        layout_inferior.addWidget(boton_salir)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.addWidget(widget_encabezado)
        layout_principal.addLayout(layout_modulos)
        layout_principal.addLayout(layout_inferior)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout_principal)
        self.setWindowFlag(QtCore.Qt.WindowType.Window)

    @property
    def modulo(self):
        """El módulo abierto, o ``None`` si no hay ninguno."""
        return self._modulo

    def abrir_modulo(self, estructura: Estructura):
        """Abre el módulo que corresponde a un tipo de estructura.

        Args:
            estructura: El tipo de estructura del módulo a abrir.

        Returns:
            El módulo abierto.
        """
        modulo = MODULOS[estructura](self)
        # Los módulos se destruyen al cerrarse (``WA_DeleteOnClose``): sin esto
        # la referencia quedaría apuntando a un objeto de Qt ya borrado, y
        # tocarla levantaría ``RuntimeError``.
        modulo.destroyed.connect(self._olvidar_modulo)
        self._modulo = modulo
        return modulo

    def _olvidar_modulo(self) -> None:
        self._modulo = None

    def _modulo_edificio(self):
        self.abrir_modulo(Estructura.EDIFICIO)

    def _modulo_cubierta_aislada(self):
        self.abrir_modulo(Estructura.CUBIERTA_AISLADA)

    def _modulo_cartel(self):
        self.abrir_modulo(Estructura.CARTEL)

    @staticmethod
    def _salir():
        QtWidgets.QApplication.quit()
