from typing import Optional

from PyQt5 import QtWidgets, QtGui, QtCore

from sse102 import __acercade__
from sse102.enums import CategoriaExposicion, TipoTerrenoTopografia, DireccionTopografia, Flexibilidad
from sse102.widgets import dialogos


class EfectoPulsacion(QtWidgets.QGraphicsOpacityEffect):
    def __init__(self):
        super().__init__()
        self._animacion = QtCore.QPropertyAnimation(self, b"opacity")
        self._animacion.setDuration(1300)
        self._animacion.setStartValue(0.2)
        self._animacion.setKeyValueAt(0.5, 1)
        self._animacion.setEndValue(0.2)
        self._animacion.setLoopCount(-1)

    def iniciar(self):
        self._animacion.start()

    def detener(self):
        self._animacion.stop()


class WidgetBotonModulo(QtWidgets.QWidget):
    def __init__(self, label: str, ruta_qrc_icono: str, funcion: callable) -> None:
        """

        Args:
            label: Label del boton.
            ruta_qrc_icono: La ruta qrc del icono.
            funcion: La funcion que se conecta al boton.
        """
        super().__init__()

        boton = QtWidgets.QPushButton()
        boton.setProperty("class", "modulo")
        boton.setIcon(QtGui.QIcon(ruta_qrc_icono))
        boton.setCursor(QtCore.Qt.PointingHandCursor)
        boton.setIconSize(QtCore.QSize(128, 128))
        boton.clicked.connect(funcion)

        label = QtWidgets.QLabel(label)
        label.setProperty("class", "modulo")
        label.setAlignment(QtCore.Qt.AlignCenter)

        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setSpacing(0)
        layout_principal.addWidget(boton)
        layout_principal.addWidget(label)
        layout_principal.addStretch()

        self.setLayout(layout_principal)


class WidgetBotonPanel(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)


class WidgetBotonPanelIcono(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)


class WidgetPanel(QtWidgets.QWidget):
    def __init__(self, altura_fija: Optional[int] = None) -> None:
        """

        Args:
            altura_fija: La altura fija del widget.
        """
        super().__init__()

        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        if altura_fija is not None:
            self.setFixedHeight(altura_fija)


class WidgetLogo(QtWidgets.QLabel):
    def __init__(self, nombre_archivo="logo.png") -> None:
        """

        Args:
            nombre_archivo: El nombre del archivo.
        """
        super().__init__()
        ruta = ":/imagenes/"
        pixmap = QtGui.QPixmap(ruta + nombre_archivo)
        self.setPixmap(pixmap)


class WidgetPanelEntrada(WidgetPanel):
    def __init__(self, componentes=False):
        super().__init__(altura_fija=57)

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
        boton_dialogo_viento.setIcon(QtGui.QIcon(":/iconos/viento.png"))
        boton_dialogo_viento.setIconSize(QtCore.QSize(32, 32))

        boton_dialogo_topografia = WidgetBotonPanel("TOPOGRAFIA")
        boton_dialogo_topografia.clicked.connect(self._dialogo_topografia)
        boton_dialogo_topografia.setIcon(QtGui.QIcon(":/iconos/topografia.png"))
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
            self.componentes = {"componentes_paredes": None, "componentes_cubierta": None}
            boton_dialogo_componentes = WidgetBotonPanel("C&&R")
            boton_dialogo_componentes.clicked.connect(self._dialogo_componentes)
            boton_dialogo_componentes.setIcon(QtGui.QIcon(":/iconos/componentes.png"))
            boton_dialogo_componentes.setIconSize(QtCore.QSize(32, 32))

            layout_principal.addWidget(boton_dialogo_componentes)

        layout_principal.addStretch()
        layout_principal.addWidget(self.boton_calcular)

        self.setLayout(layout_principal)

    def _dialogo_viento(self):
        dialogo = dialogos.DialogoViento(**self.parametros_viento)
        if dialogo.exec_():
            self.parametros_viento = dialogo.parametros()

    def _dialogo_topografia(self):
        dialogo = dialogos.DialogoTopografia(**self.parametros_topografia)
        if dialogo.exec_():
            self.parametros_topografia = dialogo.parametros()

    def _dialogo_componentes(self):
        dialogo = dialogos.DialogoComponentes(self.componentes)
        if dialogo.exec_():
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
    def __init__(self) -> None:
        super().__init__()

        self.pos_ult = None
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.pos_ult = a0.globalPos()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        try:
            delta = a0.globalPos() - self.pos_ult
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.pos_ult = a0.globalPos()
        except TypeError:
            pass


class WidgetLabelLinkInfo(QtWidgets.QLabel):
    def __init__(self, texto: str, ref: str):
        """

        Args:
            texto: El texto del label.
            ref: El link o referencia donde apunta.
        """

        super().__init__(f'<a style="color: #606060" href={ref}>{texto}</a>')
        self.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.setOpenExternalLinks(True)


class WidgetLinksInfo(QtWidgets.QWidget):
    def __init__(
        self,
        pagina_web: bool = False,
        contacto: bool = False,
        eula: bool = False,
        licencias_terceros: bool = False,
        ayuda: bool = False,
    ):
        super().__init__()

        layout_principal = QtWidgets.QHBoxLayout()
        layout_principal.setContentsMargins(0, 20, 0, 0)
        layout_principal.setAlignment(QtCore.Qt.AlignCenter)
        layout_principal.setSpacing(25)

        if pagina_web:
            layout_principal.addWidget(WidgetLabelLinkInfo("Página Web", __acercade__.__web__))

        if contacto:
            layout_principal.addWidget(WidgetLabelLinkInfo("Contacto", __acercade__.__contacto__))

        if eula:
            layout_principal.addWidget(WidgetLabelLinkInfo("Contrato de licencia", __acercade__.__eula__))

        if licencias_terceros:
            layout_principal.addWidget(
                WidgetLabelLinkInfo("Licencias de terceros", __acercade__.__licencias_terceros__)
            )

        if ayuda:
            layout_principal.addWidget(WidgetLabelLinkInfo("Ayuda", __acercade__.__ayuda__))

        self.setLayout(layout_principal)
