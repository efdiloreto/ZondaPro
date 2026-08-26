# Copyright (c) 2023, Eduardo Di Loreto <efdiloreto@gmail.com>

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

"""Los actores que puede contener una escena 3D.

Un actor es un objeto de Qt (``QObject``) con propiedades: la vista de QML se
suscribe a ellas, así que para actualizar el dibujo alcanza con cambiarle un
valor al actor. No hay que pedir un redibujado a mano.

Hay cuatro clases de actores:

``ActorPresion``
    Un polígono con su contorno. Si además recibe presión, arrastra una flecha
    normal a la cara y una etiqueta con el valor.
``ActorLineas``
    Segmentos, para los soportes de las cubiertas aisladas.
``ActorSolido``
    Un cuerpo con malla propia, para el soporte del cartel.
``ActorTexto2D`` y ``ActorBarraEscala``
    No son cuerpos: son las anotaciones que se dibujan encima de la escena.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial, wraps
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import ArrayLike

# `pyqtProperty` existe en runtime pero no está declarado en los stubs.
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal  # type: ignore[attr-defined]
from PyQt6.QtGui import QColor, QQuaternion, QVector3D

from zonda.graficos import mallas
from zonda.graficos.directores.utils_iter import aplicar_func_recursivamente
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.enums import Unidad
    from zonda.graficos.colores import TablaColores
    from zonda.graficos.escena import Escena3D

COLOR_POR_DEFECTO = "Gainsboro"
ESCALA_BASE_FLECHA = 7.0
"""Largo de la flecha, en metros, para la presión de mayor valor absoluto."""

TAMANIO_TEXTO_BASE = 9.0
"""Tamaño en puntos de las etiquetas de presión."""

EJE_FLECHA = QVector3D(0, 1, 0)
"""La malla de la flecha apunta a +Y; la orientación la da un cuaternión."""


def color(nombre: str | None = None) -> QColor:
    """Obtiene un color desde su nombre.

    Args:
        nombre: El nombre del color. Si es None se adopta "Gainsboro".

    Returns:
        El color.
    """
    return QColor(nombre or COLOR_POR_DEFECTO)


class Poligono:
    """Los puntos de un polígono plano, sin nada de dibujo.

    Es lo que se pasan entre sí los directores cuando necesitan recortar una
    zona o calcular un área.
    """

    def __init__(self, puntos: ArrayLike) -> None:
        # El TypeError no es defensivo: `aplicar_func_recursivamente` distingue
        # "un polígono" de "una secuencia de polígonos" intentando iterar y
        # viendo si falla. Si acá se aceptara un punto suelto, un polígono se
        # convertiría en cuatro actores degenerados sin que nada avise.
        arreglo = np.asarray(puntos, dtype=float)
        if arreglo.ndim != 2 or arreglo.shape[1] != 3:
            raise TypeError("se esperaba una secuencia de puntos (x, y, z)")
        self.puntos = arreglo

    def __len__(self) -> int:
        return len(self.puntos)

    def area(self) -> float:
        """El área del polígono en m²."""
        return mallas.area(self.puntos)


def crear_poligono(puntos: ArrayLike) -> Poligono:
    """Crea un polígono a partir de sus vértices."""
    return Poligono(puntos)


def recortar_poligono(
    poligono: Poligono, origen: ArrayLike, normal: ArrayLike
) -> Poligono | None:
    """Recorta un polígono con un plano y devuelve la parte que queda.

    Implementa el algoritmo de Sutherland-Hodgman: se recorre el contorno y cada
    arista que cruza el plano aporta el punto de intersección. Se conserva el
    lado positivo del plano, que es el que apunta en la dirección de la normal.

    Args:
        poligono: El polígono a recortar.
        origen: Un punto del plano de corte.
        normal: La normal del plano de corte.

    Returns:
        El polígono recortado, o None si no queda nada del lado positivo.
    """
    p = poligono.puntos
    o = np.asarray(origen, dtype=float)
    n = np.asarray(normal, dtype=float)
    norma = np.linalg.norm(n)
    if norma == 0:
        return poligono
    n = n / norma

    distancias = (p - o) @ n
    resultado: list[np.ndarray] = []
    for i in range(len(p)):
        j = (i + 1) % len(p)
        di, dj = distancias[i], distancias[j]
        if di >= 0:
            resultado.append(p[i])
        if (di > 0 > dj) or (di < 0 < dj):
            resultado.append(p[i] + (p[j] - p[i]) * (di / (di - dj)))

    if len(resultado) < 3:
        return None
    return Poligono(np.array(resultado))


class ActorMixin:
    """Comportamiento común: mostrarse, ocultarse y sumarse a la escena."""

    clase = ""
    escena: Escena3D

    def asignar_visible(self, visible: bool) -> None:
        raise NotImplementedError

    def _agregar(self) -> None:
        self.escena.agregar_actor(self)

    def mostrar(self) -> None:
        self.asignar_visible(True)

    def ocultar(self) -> None:
        self.asignar_visible(False)


class ActorLineas(QObject, ActorMixin):
    """Segmentos sueltos, tomados de a pares."""

    clase = "lineas"
    cambiado = pyqtSignal()

    def __init__(
        self, escena: Escena3D, puntos: ArrayLike, color_lineas: str | None = None
    ) -> None:
        super().__init__()
        self.escena = escena
        self.puntos = np.asarray(puntos, dtype=float).reshape(-1, 3)
        self._malla = mallas.MallaLineas(self.puntos)
        self._color = color(color_lineas)
        self._visible = True
        self._agregar()

    @pyqtProperty(QObject, constant=True)
    def malla(self):
        return self._malla

    @pyqtProperty(QColor, notify=cambiado)
    def color(self) -> QColor:
        return self._color

    @pyqtProperty(bool, notify=cambiado)
    def visible(self) -> bool:
        return self._visible

    def asignar_visible(self, visible: bool) -> None:
        if visible != self._visible:
            self._visible = visible
            self.cambiado.emit()


class ActorSolido(QObject, ActorMixin):
    """Un cuerpo con malla propia."""

    clase = "solido"
    cambiado = pyqtSignal()

    def __init__(
        self,
        escena: Escena3D,
        malla,
        puntos: ArrayLike,
        color_solido: str | None = None,
    ) -> None:
        super().__init__()
        self.escena = escena
        self.puntos = np.asarray(puntos, dtype=float).reshape(-1, 3)
        self._malla = malla
        self._color = color(color_solido)
        self._visible = True
        self._agregar()

    @pyqtProperty(QObject, constant=True)
    def malla(self):
        return self._malla

    @pyqtProperty(QColor, notify=cambiado)
    def color(self) -> QColor:
        return self._color

    @pyqtProperty(bool, notify=cambiado)
    def visible(self) -> bool:
        return self._visible

    def asignar_visible(self, visible: bool) -> None:
        if visible != self._visible:
            self._visible = visible
            self.cambiado.emit()


def cilindro(
    escena: Escena3D,
    radio: float,
    altura: float,
    centro_xz: tuple[float, float],
    y_base: float = 0.0,
    color_solido: str | None = None,
) -> ActorSolido:
    """Crea el actor de un cilindro vertical."""
    malla = mallas.MallaCilindro(radio, altura, centro_xz, y_base)
    cx, cz = centro_xz
    puntos = (
        (cx - radio, y_base, cz - radio),
        (cx + radio, y_base + altura, cz + radio),
    )
    return ActorSolido(escena, malla, puntos, color_solido)


class ActorTexto2D(QObject, ActorMixin):
    """El título de la escena, dibujado sobre la vista."""

    clase = "texto"

    def __init__(self, escena: Escena3D) -> None:
        super().__init__()
        self.escena = escena
        self._agregar()

    def setear_texto(self, texto: str) -> None:
        """Setea el texto del título."""
        self.escena.asignar_titulo(texto)

    def asignar_visible(self, visible: bool) -> None:
        pass


class ActorBarraEscala(QObject, ActorMixin):
    """La barra con la escala de colores y sus valores."""

    clase = "escala"

    def __init__(
        self, escena: Escena3D, tabla_colores: TablaColores, unidad: Unidad
    ) -> None:
        super().__init__()
        self.escena = escena
        self.escena.asignar_escala(tabla_colores, unidad)
        self._agregar()

    def asignar_visible(self, visible: bool) -> None:
        pass


class ActorFlechaPresion(QObject):
    """La flecha normal a una cara, con la etiqueta del valor de presión.

    El sentido lo da el signo: con presión positiva la flecha empuja contra la
    cara, con succión sale de ella. El largo es proporcional al valor.
    """

    cambiado = pyqtSignal()

    def __init__(self, actor_presion: ActorPresion) -> None:
        super().__init__()
        self._actor = actor_presion
        self._largo = 0.0
        self._texto = ""
        self._visible = False
        self._empuje = True
        self._escala_base = ESCALA_BASE_FLECHA
        self._tamanio_texto = TAMANIO_TEXTO_BASE

    @pyqtProperty(QVector3D, notify=cambiado)
    def posicion(self) -> QVector3D:
        """El origen de la flecha, que es su base."""
        if self._empuje:
            return QVector3D(*(self._actor.centro + self._actor.normal * self._largo))
        return QVector3D(*self._actor.centro)

    @pyqtProperty(QQuaternion, notify=cambiado)
    def rotacion(self) -> QQuaternion:
        direccion = -self._actor.normal if self._empuje else self._actor.normal
        return QQuaternion.rotationTo(EJE_FLECHA, QVector3D(*direccion))

    @pyqtProperty(float, notify=cambiado)
    def largo(self) -> float:
        return self._largo

    @pyqtProperty(QVector3D, notify=cambiado)
    def posicionEtiqueta(self) -> QVector3D:
        """Donde va la etiqueta: en el extremo de la flecha alejado de la cara."""
        return QVector3D(
            *(self._actor.centro + self._actor.normal * self._largo * 1.05)
        )

    @pyqtProperty(str, notify=cambiado)
    def texto(self) -> str:
        return self._texto

    @pyqtProperty(float, notify=cambiado)
    def tamanioTexto(self) -> float:
        return self._tamanio_texto

    @pyqtProperty(bool, notify=cambiado)
    def visible(self) -> bool:
        return self._visible and self._actor.visible

    def asignar_presion(self, valor: float, texto: str, maximo: float) -> None:
        """Escala y orienta la flecha, y le pone el texto a la etiqueta.

        Args:
            valor: La presión, ya convertida a la unidad de la escena.
            texto: El texto de la etiqueta.
            maximo: La presión de mayor valor absoluto de la escena, que fija la
                escala de todas las flechas.
        """
        self._largo = abs(valor) / maximo * self._escala_base if maximo else 0.0
        self._empuje = valor >= 0
        self._texto = texto
        self._visible = True
        self.cambiado.emit()

    def asignar_visible(self, visible: bool) -> None:
        if visible != self._visible:
            self._visible = visible
            self.cambiado.emit()

    def mostrar(self) -> None:
        self.asignar_visible(True)

    def ocultar(self) -> None:
        self.asignar_visible(False)

    def aumentar_escala(self) -> None:
        self._cambiar_escala(1.1111)

    def disminuir_escala(self) -> None:
        self._cambiar_escala(0.9)

    def aumentar_tamanio_texto(self) -> None:
        self._cambiar_tamanio_texto(1.1111)

    def disminuir_tamanio_texto(self) -> None:
        self._cambiar_tamanio_texto(0.9)

    def _cambiar_escala(self, factor: float) -> None:
        self._escala_base *= factor
        self._largo *= factor
        self.cambiado.emit()

    def _cambiar_tamanio_texto(self, factor: float) -> None:
        self._tamanio_texto = max(TAMANIO_TEXTO_BASE, self._tamanio_texto * factor)
        self.cambiado.emit()


class ActorPresion(QObject, ActorMixin):
    """Un polígono de la escena, con o sin presión.

    Cuando lleva presión, el color del polígono sale de la escala de colores y
    se le agrega una flecha con su etiqueta.
    """

    clase = "poligono"
    cambiado = pyqtSignal()

    def __init__(
        self,
        escena: Escena3D,
        puntos_poligono: ArrayLike | None = None,
        poligono: Poligono | None = None,
        color_cara: str | None = None,
        tabla_colores: TablaColores | None = None,
        presion: bool = False,
        mostrar: bool = True,
    ) -> None:
        """
        Args:
            escena: La escena que junta los actores.
            puntos_poligono: Los puntos X, Y, Z que forman el polígono.
            poligono: El polígono ya armado, si no se pasan los puntos.
            color_cara: El color de la cara.
            tabla_colores: La escala de colores de la escena.
            presion: Indica si hay que agregarle la flecha y la etiqueta.
            mostrar: Indica si se muestra al crearse.
        """
        super().__init__()
        self.escena = escena
        # O llega el polígono ya armado o llegan los puntos para armarlo.
        if not poligono:
            assert puntos_poligono is not None, "faltan el polígono y sus puntos"
            poligono = crear_poligono(puntos_poligono)
        self._poligono = poligono
        self.color_base = color(color_cara)
        self.tabla_colores = tabla_colores
        self._max_valor_presion = 0.0
        if tabla_colores is not None:
            self._max_valor_presion = max(
                abs(tabla_colores.minimo), abs(tabla_colores.maximo)
            )

        puntos = self._poligono.puntos
        self.normal = mallas.normal(puntos)
        self.centro = mallas.centro(puntos)
        self._malla = mallas.MallaPoligono(puntos)
        self._contorno = mallas.MallaContorno(puntos)
        self._color = self.color_base
        self._visible = mostrar

        if presion and tabla_colores is not None:
            self.flecha = ActorFlechaPresion(self)

        self._agregar()

    # -- propiedades para la vista ----------------------------------------

    @pyqtProperty(QObject, constant=True)
    def malla(self):
        return self._malla

    @pyqtProperty(QObject, constant=True)
    def contorno(self):
        return self._contorno

    @pyqtProperty(QColor, notify=cambiado)
    def color(self) -> QColor:
        return self._color

    @pyqtProperty(bool, notify=cambiado)
    def visible(self) -> bool:
        return self._visible

    # -- estado ------------------------------------------------------------

    @property
    def poligono(self) -> Poligono:
        return self._poligono

    @property
    def puntos(self) -> np.ndarray:
        return self._poligono.puntos

    def asignar_presion(
        self, presion: float, unidad: Unidad, str_extra: str = ""
    ) -> None:
        """Asigna un valor de presión al actor.

        El color del polígono sale de la escala, la flecha se escala y se
        orienta según el signo, y la etiqueta toma el valor.

        Args:
            presion: El valor de presión en N/m².
            unidad: La unidad en la que se muestra.
            str_extra: Un texto a agregar en la etiqueta.
        """
        # Solo tiene sentido en un actor creado con escala de colores y flecha
        # (``presion=True``); sin la escala no hay de dónde sacar el color.
        assert self.tabla_colores is not None
        presion = convertir_unidad(presion, unidad)
        self._asignar_color(self.tabla_colores.color(presion))
        self.flecha.asignar_presion(
            presion,
            f"{presion:.2f} {unidad.value}/m² {str_extra}".strip(),
            self._max_valor_presion,
        )
        self.mostrar()

    def asignar_visible(self, visible: bool) -> None:
        if visible != self._visible:
            self._visible = visible
            self.cambiado.emit()
            if hasattr(self, "flecha"):
                self.flecha.cambiado.emit()

    def _asignar_color(self, nuevo: QColor) -> None:
        if nuevo != self._color:
            self._color = nuevo
            self.cambiado.emit()


def actores_poligonos(
    func: Callable | None = None,
    *,
    crear_atributo: bool = False,
    color: str | None = None,
    presion: bool = False,
    mostrar: bool = False,
) -> Any:
    """Crea actores de polígono a partir de un método que devuelve puntos.

    Se usa como decorador de un método de clase. El método devuelve las
    coordenadas —sueltas, en tuplas o en diccionarios anidados— y el decorador
    arma un actor por cada polígono, respetando esa misma estructura.

    Args:
        func: La función o método decorado.
        crear_atributo: Indica si hay que crear en la clase un atributo que
            referencie a los actores generados. El nombre es "actores_" más el
            nombre del método.
        color: El color de los polígonos generados.
        presion: Indica si los polígonos reciben presión, es decir si hay que
            agregarles flecha y etiqueta.
        mostrar: Indica si se muestran al crearse.

    Notes:
        La clase que contiene al método tiene que tener el atributo ``escena``, y
        además ``tabla_colores`` si los actores son de presión.

    Returns:
        Los actores generados a partir de los puntos que devuelve el método.
    """
    if func is None:
        return partial(
            actores_poligonos,
            crear_atributo=crear_atributo,
            color=color,
            presion=presion,
            mostrar=mostrar,
        )

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        puntos = func(self, *args, **kwargs)
        tabla_colores = getattr(self, "tabla_colores", None)
        actores = aplicar_func_recursivamente(
            puntos,
            lambda x: ActorPresion(
                self.escena,
                x,
                color_cara=color,
                tabla_colores=tabla_colores,
                presion=presion,
                mostrar=mostrar,
            ),
        )
        if crear_atributo:
            setattr(self, f"actores_{func.__name__}", actores)

    return wrapped


__all__ = [
    "ESCALA_BASE_FLECHA",
    "TAMANIO_TEXTO_BASE",
    "ActorBarraEscala",
    "ActorFlechaPresion",
    "ActorLineas",
    "ActorPresion",
    "ActorSolido",
    "ActorTexto2D",
    "Poligono",
    "actores_poligonos",
    "cilindro",
    "color",
    "crear_poligono",
    "recortar_poligono",
]
