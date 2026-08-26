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

"""Encuadre de la cámara de la vista 3D.

Los directores definen cada vista con un punto focal y una posición de ojo: de
ahí sale la *dirección* de la mirada. La distancia la calcula este módulo, para
que la estructura entre completa en el cuadro.

El ``OrbitCameraController`` de QtQuick3D.Helpers impone el esquema de la escena:
la cámara tiene que ser hija de un ``Node`` (el origen), ubicada sobre su eje +Z
local; el controlador rota el origen y mueve la cámara sobre ese eje. Entonces
una "vista" acá es una rotación del origen más una distancia, no una posición
absoluta.

El encuadre se calcula por vista, proyectando los puntos de la escena sobre los
ejes de la cámara. Con la esfera envolvente alcanzaría, pero deja mucho aire
cuando la escena es alargada, que es el caso de casi todas estas estructuras.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PyQt6.QtGui import QQuaternion, QVector3D

# El eje vertical de cada vista. La vista superior usa (1, 0, 0) porque mirando
# hacia abajo el (0, 1, 0) se degenera.
ARRIBA_POR_DEFECTO = np.array((0.0, 1.0, 0.0))
ARRIBA_SUPERIOR = np.array((1.0, 0.0, 0.0))

MARGEN = 1.1
"""Aire alrededor de la escena, para que no quede pegada a los bordes."""

# La magnificación de la OrthographicCamera de Qt Quick 3D es "píxeles por
# unidad de mundo": con magnificación 1 un metro mide un píxel. No está dicho en
# la documentación de Qt; se midió sobre una cara de 10 x 5 m en la vista de
# frente, que sale con relación 2.00 y ocupando lo previsto.


@dataclass(frozen=True)
class Vista:
    """Lo que hay que setear en QML para una posición de cámara."""

    rotacion: QQuaternion
    distancia: float
    magnificacion: float
    centro: QVector3D


def rotacion(direccion: np.ndarray, arriba: np.ndarray) -> QQuaternion:
    """La rotación que lleva el +Z local del origen sobre ``direccion``.

    Se arma la base ortonormal a mano en lugar de calcular ángulos de Euler:
    ``eulerRotation`` depende del orden en que Qt aplica las rotaciones, y con la
    base explícita el resultado no admite ambigüedad.
    """
    z = direccion / np.linalg.norm(direccion)
    if abs(float(np.dot(z, arriba))) > 0.999:
        arriba = (
            ARRIBA_SUPERIOR
            if not np.allclose(arriba, ARRIBA_SUPERIOR)
            else ARRIBA_POR_DEFECTO
        )
    x = np.cross(arriba, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return QQuaternion.fromAxes(QVector3D(*x), QVector3D(*y), QVector3D(*z))


def calcular_vista(
    puntos: np.ndarray,
    foco: np.ndarray,
    ojo: np.ndarray,
    arriba: np.ndarray,
    ancho_px: float,
    alto_px: float,
    campo_visual: float = 60.0,
) -> Vista:
    """Calcula la vista que encuadra ``puntos`` mirando desde ``ojo``.

    Args:
        puntos: Todos los puntos que tienen que entrar en el cuadro.
        foco: El punto focal que setea el director. Sólo define la dirección de
            la vista; la distancia la fija el encuadre.
        ojo: La posición de cámara que setea el director.
        arriba: El vector vertical de la vista.
        ancho_px: El ancho del viewport, para la relación de aspecto.
        alto_px: El alto del viewport.
        campo_visual: El ``fieldOfView`` vertical de la cámara cónica.

    Returns:
        La vista, con la rotación del origen, la distancia de la cámara, la
        magnificación de la cámara ortográfica y el centro del encuadre.
    """
    direccion = np.asarray(ojo, dtype=float) - np.asarray(foco, dtype=float)
    if np.linalg.norm(direccion) < 1e-9:
        direccion = np.array((0.0, 0.0, 1.0))
    giro = rotacion(direccion, arriba)

    base = np.column_stack(
        [
            _a_numpy(giro.rotatedVector(QVector3D(*eje)))
            for eje in ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        ]
    )
    proyectados = np.asarray(puntos, dtype=float) @ base
    minimos, maximos = proyectados.min(axis=0), proyectados.max(axis=0)
    semi = (maximos - minimos) / 2 * MARGEN
    semi = np.maximum(semi, 1e-6)
    centro = base @ ((minimos + maximos) / 2)

    aspecto = max(ancho_px, 1) / max(alto_px, 1)
    tan_vertical = math.tan(math.radians(campo_visual) / 2)
    tan_horizontal = tan_vertical * aspecto

    # Encuadre exacto: para cada punto, la cámara tiene que estar al menos a
    # `profundidad + medida / tan(fov/2)`. Alcanza con tomar el máximo.
    relativos = proyectados - (minimos + maximos) / 2
    requeridas = relativos[:, 2] + np.maximum(
        np.abs(relativos[:, 1]) * MARGEN / tan_vertical,
        np.abs(relativos[:, 0]) * MARGEN / tan_horizontal,
    )
    distancia = float(requeridas.max())

    magnificacion = min(
        max(alto_px, 1) / (2 * semi[1]), max(ancho_px, 1) / (2 * semi[0])
    )

    return Vista(giro, distancia, float(magnificacion), QVector3D(*centro))


def _a_numpy(vector: QVector3D) -> np.ndarray:
    return np.array((vector.x(), vector.y(), vector.z()))
