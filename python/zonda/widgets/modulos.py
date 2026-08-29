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

"""Contiene clases que representan los módulos para cada tipo de estructura. Cada módulo puede ser usado para ingresar los
datos de la estructura y visualizar sus resultados.

Cada módulo lleva una barra de menús con las acciones de archivo —nuevo, abrir,
guardar, guardar como— y las opciones generales del programa —configuración,
ayuda y acerca de—, que antes vivían en la pantalla de bienvenida.

Por eso el módulo es un ``QMainWindow`` y no un ``QWidget`` suelto: es la
ventana principal la que sabe ubicar y dibujar una ``QMenuBar`` como corresponde
en cada plataforma. Metida a mano en un layout, nada de eso funciona.

**La barra de menús es la que se adapta a cada sistema.** En macOS es nativa: no
se dibuja adentro de la ventana sino en la barra global, arriba de la pantalla,
y Qt le da el mismo aspecto que a cualquier aplicación del sistema. En Windows y
en Linux es la barra de menús de siempre, adentro de la ventana. Además, las
acciones marcadas con ``MenuRole`` las **reubica Qt sola**: en macOS
"Configuración" termina en *Zonda > Preferencias* y "Acerca de" en *Zonda >
Acerca de*, que es donde las busca quien usa una Mac, mientras que en Windows y
Linux se quedan en los menús donde se las declaró.

Las acciones no se dibujan dentro de la ventana: el contenido de la ventana es
sólo la entrada de datos y los resultados.

Los íconos de las acciones de archivo los pone Qt (``QIcon.fromTheme`` con el
estilo activo como respaldo), así que se ven como los del sistema en cada
plataforma en lugar de imponer un set propio. macOS no los muestra —su barra de
menús no lleva íconos—; Windows y Linux sí.
"""

import gc
import webbrowser
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import __acercade__, proyecto, recursos
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio
from zonda.enums import Estructura
from zonda.excepciones import ErrorArchivo, ErrorEstructura, ErrorLineamientos
from zonda.widgets.custom import WidgetAcercaDe, WidgetPanelEntrada
from zonda.widgets.dialogos import DialogoConfiguracion
from zonda.widgets.entrada import (
    WidgetEstructuraCartel,
    WidgetEstructuraCubiertaAislada,
    WidgetEstructuraEdificio,
)
from zonda.widgets.resultados import (
    WidgetResultadosCartel,
    WidgetResultadosCubiertaAislada,
    WidgetResultadosEdificio,
)


def _icono_estandar(
    tema: str, respaldo: QtWidgets.QStyle.StandardPixmap
) -> QtGui.QIcon:
    """El ícono que ya trae Qt para una acción estándar.

    Se prefiere el ícono del tema del escritorio —lo hay en Linux— y se cae al
    del estilo activo, que existe en todas las plataformas y nunca es nulo.

    Args:
        tema: El nombre freedesktop del ícono, por ejemplo ``"document-save"``.
        respaldo: El ícono del estilo a usar si el tema no tiene ninguno.
    """
    icono = QtGui.QIcon.fromTheme(tema)
    if not icono.isNull():
        return icono
    estilo = QtWidgets.QApplication.style()
    assert estilo is not None
    return estilo.standardIcon(respaldo)


class WidgetModuloEdificio(QtWidgets.QMainWindow):
    titulo = "Edificio"
    estructura = Estructura.EDIFICIO

    def __init__(self, pantalla_bienvenida):
        super().__init__()

        self._widget_resultados = None
        self._ruta_archivo: Path | None = None

        self.pantalla_bienvenida = pantalla_bienvenida
        self.pantalla_bienvenida.hide()

        self._widget_estructura = self._generar_widget_estructura()

        widget_modulo_estructura = QtWidgets.QWidget()

        self._widget_panel_entrada = self._generar_widget_panel_entrada()
        self._widget_panel_entrada.boton_calcular.clicked.connect(
            self._generar_resultados
        )

        layout_estructura = QtWidgets.QVBoxLayout()
        layout_estructura.setContentsMargins(0, 0, 0, 0)
        layout_estructura.setSpacing(15)
        layout_estructura.addWidget(self._widget_panel_entrada)
        layout_estructura.addWidget(self._widget_estructura, 1)

        widget_modulo_estructura.setLayout(layout_estructura)

        self._stacked_widget = QtWidgets.QStackedWidget()
        self._stacked_widget.addWidget(widget_modulo_estructura)

        self._crear_acciones()
        self._generar_menubar()
        self.setCentralWidget(self._stacked_widget)

        # El estado inicial es lo que restaura "Nuevo", y el punto de partida
        # contra el que se comparan los cambios sin guardar.
        self._estado_inicial = self._estado()
        self._estado_guardado = self._estado_inicial
        self._actualizar_titulo()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        self.showMaximized()

    # --- Las acciones y el menú --------------------------------------------

    def _crear_acciones(self) -> None:
        """Crea las acciones del módulo.

        Los ``MenuRole`` son los que dejan que macOS se lleve "Configuración"
        y "Acerca de" al menú de la aplicación; en el resto de las plataformas
        no cambian nada.
        """
        estandar = QtWidgets.QStyle.StandardPixmap
        atajos = QtGui.QKeySequence.StandardKey
        roles = QtGui.QAction.MenuRole

        self._accion_nuevo = self._crear_accion(
            "Nuevo",
            self._nuevo,
            _icono_estandar("document-new", estandar.SP_FileIcon),
            atajos.New,
        )
        self._accion_abrir = self._crear_accion(
            "Abrir...",
            self.pedir_abrir,
            _icono_estandar("document-open", estandar.SP_DirOpenIcon),
            atajos.Open,
        )
        self._accion_guardar = self._crear_accion(
            "Guardar",
            self._guardar,
            _icono_estandar("document-save", estandar.SP_DialogSaveButton),
            atajos.Save,
        )
        self._accion_guardar_como = self._crear_accion(
            "Guardar Como...",
            self._guardar_como,
            _icono_estandar("document-save-as", estandar.SP_DialogSaveButton),
            atajos.SaveAs,
        )
        self._accion_cerrar = self._crear_accion(
            "Cerrar Módulo", self.close, atajo=atajos.Close
        )

        self._accion_configuracion = self._crear_accion(
            "Configuración...",
            self._dialogo_configuracion,
            recursos.icono("iconos/configuracion.png"),
            atajos.Preferences,
            rol=roles.PreferencesRole,
        )
        self._accion_ayuda = self._crear_accion(
            "Ayuda de Zonda",
            lambda: webbrowser.open(__acercade__.__ayuda__),
            recursos.icono("iconos/ayuda.png"),
            atajos.HelpContents,
        )
        self._accion_acerca_de = self._crear_accion(
            "Acerca de Zonda",
            self._acerca_de,
            recursos.icono("iconos/informacion.png"),
            rol=roles.AboutRole,
        )

    def _crear_accion(
        self, texto, funcion, icono=None, atajo=None, rol=None
    ) -> QtGui.QAction:
        accion = QtGui.QAction(texto, self)
        if icono is not None:
            accion.setIcon(icono)
        if atajo is not None:
            accion.setShortcut(atajo)
        if rol is not None:
            accion.setMenuRole(rol)
        # Las acciones se disparan con un booleano que ninguna de estas usa.
        accion.triggered.connect(lambda _=False: funcion())
        return accion

    def _generar_menubar(self) -> QtWidgets.QMenuBar:
        """Arma la barra de menús.

        ``QMainWindow.menuBar()`` la crea la primera vez que se la pide y la
        ubica donde corresponde: adentro de la ventana en Windows y Linux, y en
        la barra global del sistema en macOS.
        """
        barra = self.menuBar()
        assert barra is not None

        menu_archivo = barra.addMenu("&Archivo")
        assert menu_archivo is not None
        menu_archivo.addAction(self._accion_nuevo)
        menu_archivo.addAction(self._accion_abrir)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self._accion_guardar)
        menu_archivo.addAction(self._accion_guardar_como)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self._accion_configuracion)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self._accion_cerrar)

        menu_ayuda = barra.addMenu("A&yuda")
        assert menu_ayuda is not None
        menu_ayuda.addAction(self._accion_ayuda)
        menu_ayuda.addSeparator()
        menu_ayuda.addAction(self._accion_acerca_de)

        return barra

    def _acerca_de(self):
        WidgetAcercaDe(self)

    def _dialogo_configuracion(self):
        DialogoConfiguracion(self)

    # --- El archivo de proyecto -------------------------------------------

    def _estado(self):
        """El estado de las dos pantallas de entrada, que es lo que se guarda."""
        return {
            "panel": self._widget_panel_entrada.estado(),
            "estructura": self._widget_estructura.estado(),
        }

    def _cargar_estado(self, estado) -> None:
        self._widget_panel_entrada.cargar_estado(estado["panel"])
        self._widget_estructura.cargar_estado(estado["estructura"])

    def _hay_cambios(self) -> bool:
        return self._estado() != self._estado_guardado

    def _confirmar_descartar(self, pregunta: str) -> bool:
        """Ofrece guardar antes de perder los cambios.

        Args:
            pregunta: Qué se está por hacer, para el texto del diálogo.

        Returns:
            Si se puede seguir adelante.
        """
        if not self._hay_cambios():
            return True
        boton = QtWidgets.QMessageBox.StandardButton
        respuesta = QtWidgets.QMessageBox.question(
            self,
            "Cambios sin guardar",
            f"El proyecto tiene cambios sin guardar. {pregunta}",
            boton.Save | boton.Discard | boton.Cancel,
            boton.Save,
        )
        if respuesta == boton.Save:
            return self._guardar()
        return respuesta == boton.Discard

    def _nuevo(self) -> None:
        if not self._confirmar_descartar(
            "¿Desea guardarlos antes de empezar uno nuevo?"
        ):
            return
        self._cargar_estado(self._estado_inicial)
        self._limpiar_resultados()
        self._ruta_archivo = None
        self._estado_guardado = self._estado()
        self._actualizar_titulo()

    def cargar_archivo(self, ruta: str | Path) -> None:
        """Carga un archivo de proyecto en el módulo.

        No pregunta nada: descarta lo que haya en pantalla. Quien la llama se
        ocupa de los cambios sin guardar (ver ``pedir_abrir()``).

        Args:
            ruta: El archivo a cargar.

        Raises:
            ErrorArchivo: Si el archivo no se puede leer, está dañado, o es de
                otro tipo de estructura.
        """
        # Si el archivo viene incompleto la carga puede fallar a mitad de
        # camino: se vuelve a lo que había para no dejar la pantalla mezclando
        # los datos de dos proyectos.
        respaldo = self._estado()
        try:
            estructura, estado = proyecto.abrir(ruta)
            if estructura is not self.estructura:
                raise ErrorArchivo(
                    f'El archivo es del módulo "{estructura.value.title()}".'
                    " Se abre desde ese módulo."
                )
            self._cargar_estado(estado)
        except ErrorArchivo:
            self._cargar_estado(respaldo)
            raise
        except (KeyError, TypeError, ValueError) as error:
            self._cargar_estado(respaldo)
            raise ErrorArchivo("El archivo está incompleto o dañado.") from error
        self._limpiar_resultados()
        self._ruta_archivo = Path(ruta)
        self._estado_guardado = self._estado()
        self._actualizar_titulo()

    def pedir_abrir(self, ruta: str | Path | None = None) -> None:
        """Abre un archivo, avisando de los cambios sin guardar y de los errores.

        Args:
            ruta: El archivo a abrir. Si es ``None`` se le pide al usuario, que
                es lo que hace la acción "Abrir" del menú.
        """
        if not self._confirmar_descartar(
            "¿Desea guardarlos antes de abrir otro archivo?"
        ):
            return
        if ruta is None:
            nombre, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Abrir Proyecto", self._carpeta_inicial(), proyecto.FILTRO
            )
            if not nombre:
                return
            ruta = nombre
        try:
            self.cargar_archivo(ruta)
        except ErrorArchivo as error:
            QtWidgets.QMessageBox.critical(
                self, "Error al abrir el archivo", str(error)
            )

    def _guardar(self) -> bool:
        """Guarda sobre el archivo abierto; si no hay ninguno, pide uno."""
        if self._ruta_archivo is None:
            return self._guardar_como()
        return self._escribir(self._ruta_archivo)

    def _guardar_como(self) -> bool:
        nombre, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guardar Proyecto", self._ruta_sugerida(), proyecto.FILTRO
        )
        if not nombre:
            return False
        ruta = Path(nombre)
        if not ruta.suffix:
            ruta = ruta.with_suffix(proyecto.EXTENSION)
        return self._escribir(ruta)

    def _escribir(self, ruta: Path) -> bool:
        estado = self._estado()
        try:
            proyecto.guardar(ruta, self.estructura, estado)
        except ErrorArchivo as error:
            QtWidgets.QMessageBox.critical(
                self, "Error al guardar el archivo", str(error)
            )
            return False
        self._ruta_archivo = ruta
        self._estado_guardado = estado
        self._actualizar_titulo()
        return True

    def _carpeta_inicial(self) -> str:
        """Vacío deja que Qt use la última carpeta visitada."""
        if self._ruta_archivo is None:
            return ""
        return str(self._ruta_archivo.parent)

    def _ruta_sugerida(self) -> str:
        if self._ruta_archivo is not None:
            return str(self._ruta_archivo)
        return str(Path.home() / f"{self.titulo}{proyecto.EXTENSION}")

    def _actualizar_titulo(self) -> None:
        nombre = "Sin título" if self._ruta_archivo is None else self._ruta_archivo.name
        self.setWindowTitle(
            f"Zonda {__acercade__.__version__} - {self.titulo} - {nombre}"
        )

    # --- Los resultados ----------------------------------------------------

    def closeEvent(self, e):
        e.ignore()
        if self._hay_cambios():
            if not self._confirmar_descartar(
                "¿Desea guardarlos antes de salir del módulo?"
            ):
                return
        elif (
            QtWidgets.QMessageBox.question(
                self,
                "Confirmación de Salida",
                "Desea salir del módulo?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return
        # Se deben implementar los widgets en las subclases.
        if self._widget_resultados is not None:
            self._widget_resultados.finalizar()
        self._widget_estructura.finalizar()
        e.accept()
        self.pantalla_bienvenida.show()

    def _limpiar_resultados(self):
        """Descarta la pantalla de resultados y vuelve a la de entrada."""
        if self._widget_resultados is None:
            return
        self._widget_resultados.finalizar()
        self._stacked_widget.removeWidget(self._widget_resultados)
        self._widget_resultados.destroy()
        self._widget_resultados = None
        gc.collect()
        self._stacked_widget.setCurrentIndex(0)

    def _generar_resultados(self):
        try:
            self._limpiar_resultados()
            self._widget_resultados = self._generar_widget_resultados()
            self._stacked_widget.addWidget(self._widget_resultados)
            self._stacked_widget.setCurrentIndex(1)
        except ErrorLineamientos as e:
            QtWidgets.QMessageBox.critical(self, "Error Lineamientos", str(e))
        except ErrorEstructura as e:
            QtWidgets.QMessageBox.critical(self, "Error datos de Entrada", str(e))
        # except ValueError as e:
        #     QtWidgets.QMessageBox.critical(self, "Error parámetros de entrada", str(e))

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key not in ("ciudad", "editar_velocidad", "categoria_riesgo_viento")
        }
        edificio = Edificio(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
            **self._widget_panel_entrada.componentes,
        )
        return WidgetResultadosEdificio(edificio)

    @staticmethod
    def _generar_widget_panel_entrada():
        return WidgetPanelEntrada(componentes=True)

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraEdificio()


class WidgetModuloCubiertaAislada(WidgetModuloEdificio):
    titulo = "Cubierta Aislada"
    estructura = Estructura.CUBIERTA_AISLADA

    @staticmethod
    def _generar_widget_panel_entrada():
        return WidgetPanelEntrada()

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraCubiertaAislada()

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key
            not in (
                "ciudad",
                "editar_velocidad",
                "factor_g_simplificado",
                "categoria_riesgo_viento",
            )
        }
        cubierta_aislada = CubiertaAislada(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
        )
        return WidgetResultadosCubiertaAislada(cubierta_aislada)


class WidgetModuloCartel(WidgetModuloCubiertaAislada):
    titulo = "Cartel"
    estructura = Estructura.CARTEL

    @staticmethod
    def _generar_widget_estructura():
        return WidgetEstructuraCartel()

    def _generar_widget_resultados(self):
        parametros_viento = {
            key: value
            for key, value in self._widget_panel_entrada.parametros_viento.items()
            if key not in ("ciudad", "editar_velocidad", "categoria_riesgo_viento")
        }
        cartel = Cartel(
            **self._widget_estructura.parametros(),
            **parametros_viento,
            **self._widget_panel_entrada.parametros_topografia,
        )
        return WidgetResultadosCartel(cartel)
