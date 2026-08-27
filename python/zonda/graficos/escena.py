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

"""La escena 3D: junta los actores y se los publica a la vista de QML.

Los directores crean actores y los agregan acá; la vista los lee de estas
propiedades y se suscribe a las señales. Como todo pasa por propiedades de Qt, no
hay que pedir un redibujado: cambiarle un valor a un actor alcanza para que la
vista se actualice.

La cámara es parte de la escena. Los directores le setean un punto focal y una
posición de ojo —de ahí sale la dirección de la vista— y :meth:`Escena3D.encuadrar`
calcula la distancia que hace entrar toda la estructura en el cuadro.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# `pyqtProperty` existe en runtime pero no está declarado en los stubs.
from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QObject,
    QTimer,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QVector3D

from zonda.enums import Unidad
from zonda.graficos import camara as camara_utils
from zonda.graficos import mallas
from zonda.graficos.colores import TablaColores


class Camara:
    """El punto de vista de la escena.

    Guarda lo que le setean los directores. La distancia a la que se ubica y la
    rotación efectiva las resuelve :mod:`zonda.graficos.camara` al encuadrar.
    """

    def __init__(self) -> None:
        self.punto_focal = np.zeros(3)
        self.posicion = np.array((0.0, 0.0, 1.0))
        self.vector_altura = np.array((0.0, 1.0, 0.0))
        self.proyeccion_paralela = False

    def setear_punto_focal(self, x: float, y: float, z: float) -> None:
        self.punto_focal = np.array((x, y, z), dtype=float)

    def setear_posicion(self, x: float, y: float, z: float) -> None:
        self.posicion = np.array((x, y, z), dtype=float)

    def setear_vector_altura(self, x: float, y: float, z: float) -> None:
        self.vector_altura = np.array((x, y, z), dtype=float)


class Escena3D(QObject):
    """Contiene los actores de una vista 3D y el estado de su cámara."""

    camaraCambiada = pyqtSignal("QVariant")
    """Pide a la vista que aplique una cámara: rotación, distancia y centro."""

    actoresCambiados = pyqtSignal()
    """Avisa que cambió la lista de actores y la vista tiene que rearmarse."""

    tituloCambiado = pyqtSignal()
    escalaCambiada = pyqtSignal()
    medicionPedida = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.camara = Camara()
        self._actores: list[Any] = []
        self._malla_flecha = mallas.MallaFlecha()
        self._titulo = ""
        self._tabla: TablaColores | None = None
        self._unidad = Unidad.N
        self._viewport = (1000.0, 700.0)
        self._aviso_programado = False

    # -- actores -----------------------------------------------------------

    def agregar_actor(self, actor: Any) -> None:
        """Suma un actor a la escena."""
        # El actor se guarda con la escena como padre para que viva mientras
        # viva la escena: la vista de QML sólo tiene referencias débiles.
        actor.setParent(self)
        self._actores.append(actor)
        self._programar_aviso()

    def limpiar(self) -> None:
        """Saca todos los actores. Se usa al regenerar una geometría."""
        for actor in self._actores:
            actor.setParent(None)
            actor.deleteLater()
        self._actores.clear()
        self._programar_aviso()

    @property
    def actores(self) -> tuple[Any, ...]:
        return tuple(self._actores)

    @property
    def actores_presion(self) -> tuple[Any, ...]:
        """Los actores que tienen flecha, es decir los que reciben presión."""
        return tuple(a for a in self._actores if hasattr(a, "flecha"))

    def _actores_de(self, clase: str) -> list[Any]:
        return [a for a in self._actores if a.clase == clase]

    def _programar_aviso(self) -> None:
        """Junta los avisos de la ronda en uno solo.

        Los directores agregan decenas de actores seguidos; avisar en cada uno
        haría que la vista se rearmara decenas de veces.
        """
        if self._aviso_programado:
            return
        self._aviso_programado = True
        QTimer.singleShot(0, self._avisar)

    def _avisar(self) -> None:
        self._aviso_programado = False
        self.actoresCambiados.emit()

    # -- anotaciones -------------------------------------------------------

    def asignar_titulo(self, texto: str) -> None:
        if texto != self._titulo:
            self._titulo = texto
            self.tituloCambiado.emit()

    def asignar_escala(self, tabla_colores: TablaColores, unidad: Unidad) -> None:
        self._tabla = tabla_colores
        self._unidad = unidad
        self.escalaCambiada.emit()

    # -- geometría de la escena -------------------------------------------

    @property
    def puntos(self) -> np.ndarray:
        """Todos los puntos que tienen que entrar en el cuadro.

        Incluye el alcance máximo de las flechas de presión: si no se las
        cuenta, el encuadre las deja fuera de la imagen.
        """
        partes = [actor.puntos for actor in self._actores if hasattr(actor, "puntos")]
        for actor in self.actores_presion:
            alcance = actor.centro + actor.normal * actor.flecha._escala_base
            partes.append(np.array((alcance,)))
        if not partes:
            return np.zeros((1, 3))
        return np.vstack(partes)

    # -- propiedades para la vista ----------------------------------------

    @pyqtProperty("QVariantList", notify=actoresCambiados)
    def caras(self):
        return self._actores_de("poligono")

    @pyqtProperty("QVariantList", notify=actoresCambiados)
    def lineas(self):
        return self._actores_de("lineas")

    @pyqtProperty("QVariantList", notify=actoresCambiados)
    def solidos(self):
        return self._actores_de("solido")

    @pyqtProperty("QVariantList", notify=actoresCambiados)
    def presiones(self):
        return [actor.flecha for actor in self.actores_presion]

    @pyqtProperty(QObject, constant=True)
    def mallaFlecha(self):
        return self._malla_flecha

    @pyqtProperty(str, notify=tituloCambiado)
    def titulo(self) -> str:
        return self._titulo

    @pyqtProperty(QVector3D, notify=actoresCambiados)
    def centro(self) -> QVector3D:
        puntos = self.puntos
        return QVector3D(*((puntos.min(axis=0) + puntos.max(axis=0)) / 2))

    @pyqtProperty(float, notify=actoresCambiados)
    def radio(self) -> float:
        puntos = self.puntos
        radio = float(np.linalg.norm(puntos.max(axis=0) - puntos.min(axis=0)) / 2)
        return radio or 1.0

    @pyqtProperty("QVariantList", notify=escalaCambiada)
    def paradasEscala(self):
        return self._tabla.paradas() if self._tabla else []

    @pyqtProperty("QVariantList", notify=escalaCambiada)
    def etiquetasEscala(self):
        if self._tabla is None:
            return []
        return [
            f"{valor:.2f} {self._unidad.value}/m²" for valor in self._tabla.etiquetas()
        ]

    # -- cámara ------------------------------------------------------------

    def encuadrar(self) -> None:
        """Recalcula la cámara para que la escena entre en el cuadro."""
        self.camaraCambiada.emit(self._datos_camara(*self._viewport))

    @pyqtSlot(float, float)
    def reencuadrar(self, ancho_px: float, alto_px: float) -> None:
        """Vuelve a encuadrar con el tamaño real de la vista."""
        self._viewport = (max(ancho_px, 1.0), max(alto_px, 1.0))
        self.encuadrar()

    def _datos_camara(self, ancho_px: float, alto_px: float) -> dict:
        vista = camara_utils.calcular_vista(
            self.puntos,
            self.camara.punto_focal,
            self.camara.posicion,
            self.camara.vector_altura,
            ancho_px,
            alto_px,
        )
        return {
            "rotacion": vista.rotacion,
            "distancia": vista.distancia,
            "magnificacion": vista.magnificacion,
            "centro": vista.centro,
        }

    # -- comandos de la barra de herramientas ------------------------------

    def pedir_medicion(self, estado: bool) -> None:
        self.medicionPedida.emit(estado)

    @pyqtSlot(QVector3D, QVector3D, result="QVariant")
    def caraBajoRayo(self, origen: QVector3D, direccion: QVector3D) -> dict | None:
        """Dónde pega el rayo del cursor, y qué vértice tiene cerca.

        Hace el trabajo de ``View3D.pick()``, pero pick descarta las caras que
        se ven de dorso: quedan a la vista porque se dibujan sin descarte, y sin
        embargo el clic las atraviesa sin engancharse. Como acá casi toda cara
        se mira de los dos lados, con pick la medición no andaba en media
        escena.

        Args:
            origen: El punto de donde sale el rayo.
            direccion: Hacia dónde va.

        Returns:
            ``{"punto": ..., "vertice": ...}`` con el impacto sobre la cara más
            cercana y el vértice más cercano a ese impacto, o None si el rayo no
            pega contra ninguna cara.
        """
        o = np.array((origen.x(), origen.y(), origen.z()))
        d = np.array((direccion.x(), direccion.y(), direccion.z()))
        mejor: tuple[float, np.ndarray] | None = None
        for actor in self._actores:
            if actor.clase != "poligono" or not actor.visible:
                continue
            golpe = mallas.interseccion_rayo(o, d, actor.puntos)
            if golpe is not None and (mejor is None or golpe[0] < mejor[0]):
                mejor = golpe
        if mejor is None:
            return None
        punto = QVector3D(*mejor[1])
        return {"punto": punto, "vertice": self.puntoMasCercano(punto)}

    @pyqtSlot(QVector3D, result="QVector3D")
    def puntoMasCercano(self, punto: QVector3D) -> QVector3D:
        """El vértice visible más cercano al punto dado.

        La vista devuelve el punto donde el rayo del clic pega contra la malla,
        no un vértice, así que el enganche al vértice se hace acá. Quien llama
        decide si lo usa: la vista lo toma sólo cuando el vértice le queda cerca
        en pantalla (ver ``candidatoEn`` en Visor.qml).

        Se miran las caras y las líneas, no los sólidos: los puntos de un sólido
        son las esquinas de su caja envolvente —están ahí para el encuadre— y no
        caen sobre el cuerpo, así que engancharse a ellas sería medir contra algo
        que no se ve.
        """
        objetivo = np.array((punto.x(), punto.y(), punto.z()))
        visibles = [
            actor.puntos
            for actor in self._actores
            if actor.clase in ("poligono", "lineas") and actor.visible
        ]
        if not visibles:
            return punto
        vertices = np.vstack(visibles)
        indice = int(np.argmin(np.linalg.norm(vertices - objetivo, axis=1)))
        return QVector3D(*vertices[indice])
