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

"""La pantalla de inicio: por dónde se empieza a trabajar.

Desde acá se elige el módulo, se retoma un proyecto reciente o se abre uno del
disco, y se llega a las opciones generales del programa —ayuda, configuración y
acerca de—, que de otro modo obligarían a abrir un módulo cualquiera para
alcanzarlas. Con un módulo abierto esas mismas opciones están en su barra de
menús (``zonda.widgets.modulos``).

También es donde se avisa que hay una versión nueva, en una franja que no
interrumpe nada.

**La pantalla no se muestra sola.** Quien la crea decide si mostrarla: cuando el
programa arranca abriendo un archivo (`zonda.main`), el módulo que corresponde se
abre directo y la bienvenida queda escondida hasta que se cierre ese módulo.
"""

from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from zonda import (
    __acercade__,
    actualizaciones,
    patrocinadores,
    proyecto,
    recientes,
    recursos,
)
from zonda.actualizaciones import Actualizacion, BuscadorActualizaciones
from zonda.enums import Estructura
from zonda.excepciones import ErrorArchivo
from zonda.widgets.apoyo import (
    WidgetSeccionPatrocinadores,
    abrir_enlace,
    fuente_de_rotulo,
)
from zonda.widgets.custom import (
    WidgetAcercaDe,
    WidgetBotonModulo,
    WidgetLogo,
    WidgetPanel,
    enlaces_de_autores,
)
from zonda.widgets.dialogos import DialogoConfiguracion
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

URL_REPORTAR = f"{__acercade__.__ayuda__}/new/choose"
"""El formulario de reporte del repositorio, con sus plantillas."""


class WidgetBienvenida(QtWidgets.QWidget):
    """La ventana desde la que se elige el módulo y se ve quién apoya Zonda.

    Es una ventana común del sistema, con su barra de título, sus botones de
    minimizar y cerrar y su posición recordada entre sesiones. Antes era una
    ventana sin borde que se arrastraba desde cualquier lado: se veía distinta
    de todo lo demás del escritorio y no ofrecía nada a cambio.
    """

    GRUPO_SETTINGS = "bienvenida"
    """El grupo de ``QSettings`` donde se recuerda la geometría."""

    ANCHO_PROYECTOS = 250
    """El ancho fijo de la columna de proyectos, en píxeles."""

    ANCHO_CARPETA = 190
    """Hasta dónde se muestra la carpeta de un proyecto reciente, en píxeles."""

    TAMANIO_INICIAL = QtCore.QSize(1140, 660)
    """Con qué tamaño abre la primera vez, antes de que haya nada recordado.

    Tiene que ser mayor que el mínimo, y el mínimo lo fija el contenido: los
    tres módulos con su descripción más la columna de patrocinadores. Si se
    alarga una descripción o se ensancha la columna, esto sube con ellas —hay
    un test que lo verifica—.
    """

    def __init__(self, buscador: BuscadorActualizaciones | None = None):
        """
        Args:
            buscador: Quien averigua si hay una versión nueva publicada. Si no
                se pasa ninguno, no se avisa de actualizaciones.
        """

        super().__init__()

        # Los tres modulos derivan de WidgetModuloEdificio.
        self._modulo: WidgetModuloEdificio | None = None
        self._buscador = buscador
        self._actualizacion: Actualizacion | None = None
        # Es un JSON chico al lado de los logos: se lee una sola vez, al armar
        # la ventana, y no vuelve a tocarse en toda la sesion.
        self._patrocinadores = patrocinadores.cargar()

        self._label_actualizacion = QtWidgets.QLabel()
        self._franja_actualizacion = self._crear_franja_actualizacion()

        boton_edificio = WidgetBotonModulo(
            "Edificio",
            "iconos/edificio.png",
            self._modulo_edificio,
        )

        boton_cubierta_aislada = WidgetBotonModulo(
            "Cubierta Aislada",
            "iconos/cubierta-aislada.png",
            self._modulo_cubierta_aislada,
        )

        boton_cartel = WidgetBotonModulo(
            "Cartel",
            "iconos/cartel.png",
            self._modulo_cartel,
        )

        layout_modulos = QtWidgets.QHBoxLayout()
        layout_modulos.setContentsMargins(25, 25, 25, 11)
        layout_modulos.setSpacing(30)
        layout_modulos.addStretch()
        layout_modulos.addWidget(boton_edificio)
        layout_modulos.addWidget(boton_cubierta_aislada)
        layout_modulos.addWidget(boton_cartel)
        layout_modulos.addStretch()

        centro = QtWidgets.QVBoxLayout()
        centro.setContentsMargins(0, 0, 0, 0)
        centro.addStretch()
        centro.addLayout(layout_modulos)
        centro.addStretch()

        # Las dos columnas son fijas y el centro se lleva lo que sobra: al
        # agrandar la ventana crecen los módulos, no las barras laterales.
        cuerpo = QtWidgets.QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self._bloque_proyectos())
        cuerpo.addLayout(centro)
        cuerpo.addWidget(WidgetSeccionPatrocinadores(self._patrocinadores))

        # El encabezado, la franja y el pie cruzan la ventana entera, por
        # encima y por debajo de las dos columnas.
        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        layout_principal.addWidget(self._encabezado())
        layout_principal.addWidget(self._franja_actualizacion)
        layout_principal.addLayout(cuerpo)
        layout_principal.addWidget(self._pie())

        self.setLayout(layout_principal)

        self.setWindowTitle(f"Zonda {__acercade__.__version__}")
        # El mínimo sale del tamaño que pide el contenido: por debajo de eso los
        # tres módulos no entran en una fila y la columna se empieza a recortar.
        self.setMinimumSize(self.sizeHint())
        self.resize(self.TAMANIO_INICIAL)
        self._restaurar_geometria()

        self._avisar_de_actualizacion()

    def _encabezado(self) -> WidgetPanel:
        """El panel de arriba: el logo y qué hace el programa.

        Returns: El encabezado.
        """
        # En Oswald, la tipografía de la marca: el encabezado es lo único que
        # acompaña al logo y tiene que leerse como parte de él, no como un
        # texto pegado al lado.
        base = self.font().pointSize()

        titulo = QtWidgets.QLabel("Cálculo de cargas de viento")
        fuente_titulo = QtGui.QFont("Oswald")
        fuente_titulo.setPointSize(base + 5)
        fuente_titulo.setWeight(QtGui.QFont.Weight.Medium)
        # En versalitas desde la fuente y no escrito en mayúsculas: un lector de
        # pantalla lee "Cálculo", no "C-Á-L-C-U-L-O".
        fuente_titulo.setCapitalization(QtGui.QFont.Capitalization.AllUppercase)
        fuente_titulo.setLetterSpacing(QtGui.QFont.SpacingType.PercentageSpacing, 104)
        titulo.setFont(fuente_titulo)
        titulo.setStyleSheet("color: #1a1a1a;")

        reglamento = QtWidgets.QLabel(__acercade__.__reglamento__)
        fuente_reglamento = QtGui.QFont("Oswald")
        fuente_reglamento.setPointSize(base)
        fuente_reglamento.setWeight(QtGui.QFont.Weight.Medium)
        # El espaciado entre letras separa el número de reglamento del título
        # sin necesidad de otro color ni otro tamaño.
        fuente_reglamento.setLetterSpacing(
            QtGui.QFont.SpacingType.PercentageSpacing, 112
        )
        reglamento.setFont(fuente_reglamento)
        reglamento.setStyleSheet("color: #707070;")

        layout_bajada = QtWidgets.QVBoxLayout()
        layout_bajada.setContentsMargins(0, 0, 0, 0)
        layout_bajada.setSpacing(0)
        layout_bajada.addWidget(titulo)
        layout_bajada.addWidget(reglamento)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(25, 14, 25, 14)
        layout.setSpacing(20)
        layout.addWidget(WidgetLogo())
        layout.addWidget(self._separador_vertical())
        layout.addLayout(layout_bajada)
        layout.addStretch()
        layout.addLayout(self._datos_del_programa())

        encabezado = WidgetPanel()
        encabezado.setLayout(layout)
        return encabezado

    @staticmethod
    def _separador_vertical() -> QtWidgets.QFrame:
        """Una línea vertical para separar bloques del encabezado.

        Returns: La línea.
        """
        separador = QtWidgets.QFrame()
        separador.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        separador.setStyleSheet("color: #c4c4c4;")
        return separador

    def _datos_del_programa(self) -> QtWidgets.QVBoxLayout:
        """La versión y la licencia, contra el borde derecho de la barra.

        Returns: El bloque de los dos renglones.
        """
        base = self.font().pointSize()

        version = QtWidgets.QLabel(f"Versión {__acercade__.__version__}")
        fuente_version = QtGui.QFont("Oswald")
        fuente_version.setPointSize(base + 2)
        fuente_version.setWeight(QtGui.QFont.Weight.Medium)
        version.setFont(fuente_version)
        version.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        version.setStyleSheet("color: #505050;")

        licencia = QtWidgets.QLabel(__acercade__.__licencia__)
        licencia.setFont(fuente_de_rotulo(self, mayusculas=False))
        licencia.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        licencia.setStyleSheet("color: #808080;")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(version)
        layout.addWidget(licencia)
        return layout

    def _bloque_proyectos(self) -> QtWidgets.QWidget:
        """Abrir un proyecto y los últimos que se usaron.

        Hasta ahora, para retomar un cálculo había que entrar a un módulo y
        recién ahí ir a Archivo → Abrir, aun sabiendo perfectamente cuál era el
        archivo.

        Returns: El bloque, sin la parte de recientes si no hay ninguno.
        """
        boton_abrir = QtWidgets.QPushButton("Abrir proyecto...")
        boton_abrir.setIcon(recursos.icono("iconos/carpeta.png"))
        boton_abrir.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton_abrir.clicked.connect(self._pedir_abrir_proyecto)

        self._titulo_recientes = QtWidgets.QLabel("Proyectos recientes")
        self._titulo_recientes.setFont(fuente_de_rotulo(self))
        self._titulo_recientes.setStyleSheet("color: #707070;")

        self._layout_recientes = QtWidgets.QVBoxLayout()
        self._layout_recientes.setContentsMargins(0, 0, 0, 0)
        self._layout_recientes.setSpacing(2)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(boton_abrir)
        layout.addSpacing(6)
        layout.addWidget(self._titulo_recientes)
        layout.addLayout(self._layout_recientes)
        layout.addStretch()

        bloque = WidgetPanel()
        bloque.setProperty("class", "proyectos")
        bloque.setFixedWidth(self.ANCHO_PROYECTOS)
        bloque.setLayout(layout)
        return bloque

    def _recargar_recientes(self) -> None:
        """Rearma la lista de proyectos recientes.

        Corre cada vez que la ventana se muestra, no una sola vez al armarla:
        se vuelve acá después de guardar un proyecto en un módulo, y la lista
        tiene que tenerlo. Son seis ``is_file()``, así que no molesta que
        también se dispare al restaurar la ventana minimizada.
        """
        while (item := self._layout_recientes.takeAt(0)) is not None:
            if (fila := item.layout()) is not None:
                while (hijo := fila.takeAt(0)) is not None:
                    if (widget := hijo.widget()) is not None:
                        widget.deleteLater()
                fila.deleteLater()

        ultimos = recientes.listar()
        self._titulo_recientes.setVisible(bool(ultimos))
        for ruta in ultimos:
            self._layout_recientes.addLayout(self._fila_reciente(ruta))

    def showEvent(self, a0: QtGui.QShowEvent | None) -> None:
        self._recargar_recientes()
        super().showEvent(a0)

    def _fila_reciente(self, ruta: Path) -> QtWidgets.QVBoxLayout:
        """Un proyecto de la lista de recientes.

        El nombre va en un botón y no en un enlace de texto para que se pueda
        llegar con el tabulador y abrirlo con Enter, que un ``QLabel`` con
        ``<a href>`` no permite.

        Args:
            ruta: El archivo.

        Returns: La fila: el nombre arriba y la carpeta debajo, que es lo que
            entra en una columna angosta.
        """
        boton = QtWidgets.QPushButton(ruta.name)
        boton.setProperty("class", "reciente")
        boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton.setToolTip(str(ruta))
        boton.clicked.connect(lambda _=False, r=ruta: self.abrir_proyecto(r))

        # El texto se recorta antes de entrar al label: la ventana fija su
        # ancho mínimo a partir del sizeHint, así que una ruta larga guardada
        # en la configuración obligaría a abrir la ventana más ancha.
        carpeta = QtWidgets.QLabel()
        carpeta.setStyleSheet("color: #808080; padding-left: 6px;")
        carpeta.setText(
            QtGui.QFontMetrics(carpeta.font()).elidedText(
                self._carpeta_para_mostrar(ruta),
                QtCore.Qt.TextElideMode.ElideMiddle,
                self.ANCHO_CARPETA,
            )
        )
        carpeta.setToolTip(str(ruta))

        fila = QtWidgets.QVBoxLayout()
        fila.setContentsMargins(0, 0, 0, 6)
        fila.setSpacing(0)
        fila.addWidget(boton)
        fila.addWidget(carpeta)
        return fila

    @staticmethod
    def _carpeta_para_mostrar(ruta: Path) -> str:
        """La carpeta de un proyecto, abreviada con ``~`` si está en el home.

        Args:
            ruta: El archivo.

        Returns: La carpeta, para mostrar al lado del nombre.
        """
        carpeta = ruta.parent
        try:
            return f"~/{carpeta.relative_to(Path.home())}"
        except ValueError:
            # Está fuera del home: un disco externo, una carpeta de red.
            return str(carpeta)

    def _pedir_abrir_proyecto(self) -> None:
        """Pide un archivo y lo abre en el módulo que corresponda."""
        nombre, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Abrir Proyecto", "", proyecto.FILTRO
        )
        if nombre:
            self.abrir_proyecto(nombre)

    def _pie(self) -> WidgetPanel:
        """El panel de abajo: de quién es Zonda y adónde ir por ayuda.

        Estos accesos vivían sólo en el menú de los módulos, así que había que
        abrir un módulo para llegar a "Acerca de", a la ayuda o a las unidades,
        aunque la preferencia de unidades es del programa entero.

        Returns: El pie.
        """
        copyright_ = QtWidgets.QLabel(f"© {enlaces_de_autores('#606060')}")
        copyright_.setFont(fuente_de_rotulo(self, mayusculas=False))
        copyright_.setStyleSheet("color: #808080;")
        # Los perfiles de los autores se alcanzan con el tabulador.
        copyright_.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        copyright_.setOpenExternalLinks(True)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(25, 8, 25, 8)
        layout.setSpacing(16)
        layout.addWidget(copyright_)
        layout.addStretch()

        enlaces = (
            ("Ayuda", lambda: abrir_enlace(__acercade__.__ayuda__)),
            ("Reportar un problema", lambda: abrir_enlace(URL_REPORTAR)),
            ("Configuración...", lambda: DialogoConfiguracion(self)),
            ("Acerca de", lambda: WidgetAcercaDe(self)),
        )
        for texto, accion in enlaces:
            boton = QtWidgets.QPushButton(texto)
            boton.setProperty("class", "enlace")
            boton.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            boton.clicked.connect(lambda _=False, f=accion: f())
            layout.addWidget(boton)

        pie = WidgetPanel()
        pie.setProperty("class", "pie")
        pie.setLayout(layout)
        return pie

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
        self._avisar_de_actualizacion()
        return modulo

    def abrir_proyecto(self, ruta: str | Path) -> bool:
        """Abre un archivo de proyecto en el módulo que le corresponde.

        Vive acá y no en ``zonda.main`` porque la bienvenida es la que abre los
        módulos, y porque el botón "Abrir proyecto..." de esta misma pantalla la
        necesita: ``main`` importa este módulo, así que no puede ser al revés.

        Args:
            ruta: El archivo de proyecto.

        Returns:
            Si quedó un módulo abierto con el archivo cargado.
        """
        # Se lee dos veces —acá para saber de qué módulo es, y de nuevo adentro
        # del módulo para cargarlo—. Son unos pocos kB de JSON, y a cambio el
        # módulo queda con una sola forma de cargar un archivo.
        try:
            estructura, _ = proyecto.abrir(ruta)
        except ErrorArchivo as error:
            QtWidgets.QMessageBox.critical(
                self, "Error al abrir el archivo", str(error)
            )
            return False

        modulo = self._modulo
        if modulo is None:
            modulo = self.abrir_modulo(estructura)
        elif modulo.estructura is not estructura:
            QtWidgets.QMessageBox.warning(
                modulo,
                "Otro módulo abierto",
                f'El archivo es del módulo "{estructura.value.title()}", y ahora'
                f' está abierto el de "{modulo.titulo}". Cerrá este módulo y'
                " volvé a abrir el archivo.",
            )
            return True

        modulo.pedir_abrir(ruta)
        modulo.raise_()
        modulo.activateWindow()
        return True

    def _crear_franja_actualizacion(self) -> WidgetPanel:
        """La franja que avisa que hay una versión nueva.

        Nace escondida y aparece cuando la consulta a GitHub encuentra algo.
        Reemplaza al cartel modal que había antes, que interrumpía justo cuando
        la persona iba a trabajar y, si se lo cerraba sin leer, no volvía hasta
        la sesión siguiente.

        Returns: La franja, todavía sin texto y oculta.
        """
        self._label_actualizacion.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._label_actualizacion.setOpenExternalLinks(True)

        boton_cerrar = QtWidgets.QToolButton()
        boton_cerrar.setText("✕")
        boton_cerrar.setAutoRaise(True)
        boton_cerrar.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        boton_cerrar.setToolTip("No volver a avisarme de esta versión")
        boton_cerrar.clicked.connect(self._ignorar_actualizacion)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(25, 6, 14, 6)
        layout.addWidget(self._label_actualizacion)
        layout.addStretch()
        layout.addWidget(boton_cerrar)

        franja = WidgetPanel()
        franja.setProperty("class", "actualizacion")
        franja.setLayout(layout)
        franja.hide()
        return franja

    def _avisar_de_actualizacion(self) -> None:
        """Engancha la franja al resultado de la consulta de versiones.

        Se llama una sola vez, al terminar de armar la ventana. Si la consulta
        a GitHub todavía no volvió, la franja aparece sola cuando llegue.
        """
        if self._buscador is None:
            return

        if self._buscador.actualizacion is not None:
            self._mostrar_aviso(self._buscador.actualizacion)
            return

        # El stub de PyQt6 no declara el parametro de tipo de conexion, pero
        # existe: sin SingleShotConnection el aviso se repetiria si la senal
        # volviera a emitirse.
        self._buscador.encontrada.connect(  # type: ignore[call-arg]
            self._mostrar_aviso,
            QtCore.Qt.ConnectionType.SingleShotConnection,
        )

    def _mostrar_aviso(self, actualizacion: Actualizacion) -> None:
        """Muestra la franja con la versión encontrada.

        Args:
            actualizacion: La versión nueva y de dónde se baja.
        """
        self._actualizacion = actualizacion
        self._label_actualizacion.setText(
            f"Ya está disponible <b>Zonda {actualizacion.version}</b>."
            f' <a style="color: #1858a8" href="{actualizacion.url}">'
            "Ir a la descarga</a>"
        )
        self._franja_actualizacion.show()

    def _ignorar_actualizacion(self) -> None:
        """Cierra la franja y no vuelve a avisar de esa versión.

        Es lo que hacía el check del cartel que había antes: sin esto, cerrarla
        valdría sólo para esta sesión. De filtrar las versiones ignoradas ya se
        encarga ``actualizaciones.leer_respuesta()``.
        """
        if self._actualizacion is not None:
            actualizaciones.ignorar_version(self._actualizacion.version)
        self._franja_actualizacion.hide()

    def _restaurar_geometria(self) -> None:
        """Vuelve a poner la ventana donde estaba la última vez.

        Si no hay nada guardado —primera corrida— o lo guardado no se puede
        aplicar —cambió la cantidad de monitores, por ejemplo—, Qt deja que el
        sistema la ubique, que es el comportamiento correcto.
        """
        settings = QtCore.QSettings()
        settings.beginGroup(self.GRUPO_SETTINGS)
        geometria = settings.value("geometria")
        settings.endGroup()

        if isinstance(geometria, QtCore.QByteArray):
            self.restoreGeometry(geometria)

    def _guardar_geometria(self) -> None:
        """Anota dónde quedó la ventana, para la próxima sesión."""
        settings = QtCore.QSettings()
        settings.beginGroup(self.GRUPO_SETTINGS)
        settings.setValue("geometria", self.saveGeometry())
        settings.endGroup()
        settings.sync()

    def closeEvent(self, a0: QtGui.QCloseEvent | None) -> None:
        self._guardar_geometria()
        super().closeEvent(a0)

    def _olvidar_modulo(self) -> None:
        self._modulo = None

    def _modulo_edificio(self):
        self.abrir_modulo(Estructura.EDIFICIO)

    def _modulo_cubierta_aislada(self):
        self.abrir_modulo(Estructura.CUBIERTA_AISLADA)

    def _modulo_cartel(self):
        self.abrir_modulo(Estructura.CARTEL)
