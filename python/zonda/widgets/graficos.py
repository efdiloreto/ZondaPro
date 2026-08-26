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

"""Los widgets que muestran las vistas 3D de geometría y de presiones.

Cada widget es un ``QWidget`` con una barra de herramientas vertical y, al lado,
la vista 3D: un ``QQuickWidget`` que carga ``zonda/graficos/Visor.qml`` y recibe
la escena como propiedad de contexto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtQuickWidgets import QQuickWidget

from zonda import recursos
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio
from zonda.enums import (
    Estructura,
    PosicionCamara,
    SistemaResistente,
    Unidad,
)
from zonda.graficos.escena import Escena3D
from zonda.graficos.escenas import (
    aisladas as escena_aisladas,
)
from zonda.graficos.escenas import (
    cartel as escena_cartel,
)
from zonda.graficos.escenas import (
    edificio as escena_edificio,
)
from zonda.graficos.escenas import (
    geometrias,
)

RUTA_VISOR = Path(__file__).resolve().parent.parent / "graficos" / "Visor.qml"


class WidgetGraficoBase(QtWidgets.QWidget):
    """Vista 3D con su barra de comandos.

    La barra trae las acciones comunes: las vistas fijas, el tipo de
    proyección, el zoom y la captura de imagen.

    Las subclases tienen que asignar ``escena``: es la escena de
    ``zonda.graficos.escenas`` que maneja el director y las actualizaciones.
    """

    escena: Any

    def __init__(self) -> None:
        super().__init__()

        self.escena3d = Escena3D(self)

        self._quick = QQuickWidget()
        self._quick.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        contexto = self._quick.rootContext()
        assert contexto is not None
        contexto.setContextProperty("escenaPython", self.escena3d)

        self._quick.setSource(QtCore.QUrl.fromLocalFile(str(RUTA_VISOR)))

        # Sin raíz no hay vista: si el .qml no compiló, mejor enterarse acá que
        # cuando alguien toque el zoom. La anotación es la que deja el atributo
        # como no opcional para el resto de la clase.
        raiz = self._quick.rootObject()
        assert raiz is not None, "no se pudo cargar Visor.qml"
        self._raiz: QQuickItem = raiz

        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._toolbar.setIconSize(QtCore.QSize(24, 24))
        self._toolbar.setProperty("class", "graficos")

        vistas = (
            (
                "iconos/restablecer-vista.png",
                "Restablecer Vista",
                PosicionCamara.PERSPECTIVA,
            ),
            ("iconos/vista-frente.png", "Vista Frente", PosicionCamara.FRENTE),
            (
                "iconos/vista-contrafrente.png",
                "Vista Contrafrente",
                PosicionCamara.CONTRAFRENTE,
            ),
            (
                "iconos/vista-derecha.png",
                "Vista Lateral Derecha",
                PosicionCamara.DERECHA,
            ),
            (
                "iconos/vista-izquierda.png",
                "Vista Lateral Izquierda",
                PosicionCamara.IZQUIERDA,
            ),
            ("iconos/vista-superior.png", "Vista Superior", PosicionCamara.SUPERIOR),
        )
        for icono, texto, posicion in vistas:
            self._agregar_accion(
                icono, texto, lambda _=False, p=posicion: self.aplicar_vista(p)
            )

        accion_conica = self._agregar_accion(
            "iconos/perspectiva-conica.png",
            "Perspectiva Cónica",
            lambda estado: self._raiz.setProperty("conica", estado),
        )
        accion_conica.setCheckable(True)
        accion_conica.setChecked(True)

        self._agregar_accion(
            "iconos/acercar.png", "Acercar", lambda _=False: self._zoom(1.25)
        )
        self._agregar_accion(
            "iconos/alejar.png", "Alejar", lambda _=False: self._zoom(0.8)
        )
        self._agregar_accion(
            "iconos/screenshot.png", "Capturar Imagen", self._capturar_imagen
        )

        marco = QtWidgets.QFrame()
        marco.setProperty("class", "recuadro")
        layout_marco = QtWidgets.QVBoxLayout()
        layout_marco.addWidget(self._quick)
        layout_marco.setContentsMargins(0, 0, 0, 0)
        marco.setLayout(layout_marco)

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.addWidget(marco, 1)
        layout_principal.addWidget(self._toolbar)
        layout_principal.setContentsMargins(5, 0, 0, 0)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setLayout(layout_principal)

    def _agregar_accion(self, icono: str, texto: str, funcion) -> QtGui.QAction:
        accion = QtGui.QAction(recursos.icono(icono), texto, self)
        accion.triggered.connect(funcion)
        self._toolbar.addAction(accion)
        return accion

    def aplicar_vista(self, posicion: PosicionCamara) -> None:
        """Lleva la cámara a una de las vistas fijas."""
        self.escena.director.setear_posicion_camara(self.escena3d.camara, posicion)

    def _zoom(self, factor: float) -> None:
        # `acercar()` la define Visor.qml, así que no está en los stubs de Qt.
        self._raiz.acercar(factor)  # type: ignore[attr-defined]

    def _capturar_imagen(self) -> None:
        nombre, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guardar Imagen", "Captura.png", filter="PNG (*.png)"
        )
        if nombre:
            self._quick.grab().save(nombre)

    def capturar(self, ruta: str) -> bool:
        """Guarda la vista como PNG, sin diálogo. Se usa desde los tests."""
        return self._quick.grab().save(ruta)

    def finalizar(self) -> None:
        """Libera la vista antes de cerrar el widget."""
        self._quick.setSource(QtCore.QUrl())
        self.escena3d.limpiar()


class WidgetGraficoGeometria(WidgetGraficoBase):
    """Vista 3D de la geometría de una estructura, mientras se la define."""

    def __init__(self, estructura: Estructura) -> None:
        self.estructura = estructura
        super().__init__()
        self.escena = geometrias.Geometria(self.escena3d, self.estructura)


class WidgetPresiones(WidgetGraficoBase):
    """Vista 3D de presiones, con los comandos propios de las flechas."""

    def __init__(self) -> None:
        super().__init__()

        accion_medir = self._agregar_accion(
            "iconos/regla.png",
            "Medir Distancia",
            lambda estado: self.escena3d.pedir_medicion(estado),
        )
        accion_medir.setCheckable(True)

        settings = QtCore.QSettings()
        settings.beginGroup("unidades")
        self._unidad_presion = settings.value("presion", "N")
        self._unidad_fuerza = settings.value("fuerza", "N")
        settings.endGroup()

    def _crear_comandos_presiones(self) -> None:
        self._agregar_accion(
            "iconos/aumentar-flecha.png",
            "Aumentar Escalas Flechas",
            lambda _=False: self.escena.aumentar_escala_flechas(),
        )
        self._agregar_accion(
            "iconos/disminuir-flecha.png",
            "Disminuir Escalas Flechas",
            lambda _=False: self.escena.disminuir_escala_flechas(),
        )
        self._agregar_accion(
            "iconos/aumentar-texto.png",
            "Aumentar Tamaño Texto Presiones",
            lambda _=False: self.escena.aumentar_tamanio_label_presion(),
        )
        self._agregar_accion(
            "iconos/disminuir-texto.png",
            "Disminuir Tamaño Texto Presiones",
            lambda _=False: self.escena.disminuir_tamanio_label_presion(),
        )


class WidgetGraficoEdificioPresiones(WidgetPresiones):
    """Vista 3D de las presiones de viento sobre un edificio."""

    def __init__(
        self, edificio: Edificio, sistema_resistente: SistemaResistente
    ) -> None:
        """
        Args:
            edificio: Una instancia de Edificio.
            sistema_resistente: El sistema resistente con el que se calcularon
                las presiones.
        """
        super().__init__()

        self.sistema_resistente = sistema_resistente
        escenas = {
            SistemaResistente.SPRFV: escena_edificio.PresionesSprfvMetodoDireccional,
            SistemaResistente.COMPONENTES: escena_edificio.PresionesComponentes,
        }

        self.escena = escenas[sistema_resistente](
            self.escena3d, edificio, Unidad(self._unidad_presion)
        )
        self._crear_comandos_presiones()
        self.aplicar_vista(PosicionCamara.PERSPECTIVA)


class WidgetGraficoCubiertaAisladaPresiones(WidgetPresiones):
    """Vista 3D de las presiones de viento sobre una cubierta aislada."""

    def __init__(self, cubierta_aislada: CubiertaAislada) -> None:
        """
        Args:
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__()

        self.escena = escena_aisladas.Presiones(
            self.escena3d, cubierta_aislada, Unidad(self._unidad_presion)
        )
        self._crear_comandos_presiones()
        self.aplicar_vista(PosicionCamara.PERSPECTIVA)


class WidgetGraficoCartelPresiones(WidgetPresiones):
    """Vista 3D de las presiones de viento sobre un cartel."""

    def __init__(self, cartel: Cartel) -> None:
        """
        Args:
            cartel: Una instancia de Cartel.
        """
        super().__init__()

        self.escena = escena_cartel.Presiones(
            self.escena3d,
            cartel,
            Unidad(self._unidad_presion),
            Unidad(self._unidad_fuerza),
        )
        self._crear_comandos_presiones()
        self.aplicar_vista(PosicionCamara.FRENTE)
