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

"""Mallas de Qt Quick 3D para los cuerpos que dibuja Zonda.

Qt Quick 3D no tiene primitivas para polígonos arbitrarios, así que las mallas se
construyen a mano: se arma el buffer de vértices con su normal y el índice de
triángulos, y se sube a un :class:`QQuick3DGeometry`.

Las coordenadas son las mismas que usan los directores: Y es la altura y Z la
profundidad, que crece hacia atrás en negativo.
"""

from __future__ import annotations

import struct

import numpy as np
from numpy.typing import ArrayLike
from PyQt6.QtGui import QVector3D
from PyQt6.QtQuick3D import QQuick3DGeometry

_F32 = QQuick3DGeometry.Attribute.ComponentType.F32Type
_U32 = QQuick3DGeometry.Attribute.ComponentType.U32Type
_POSICION = QQuick3DGeometry.Attribute.Semantic.PositionSemantic
_NORMAL = QQuick3DGeometry.Attribute.Semantic.NormalSemantic
_INDICE = QQuick3DGeometry.Attribute.Semantic.IndexSemantic
# Qt Quick 3D expone un juego fijo de semánticas y COLOR es el único vec4 que
# sobra, así que por ahí viajan los dos datos que ningún atributo estándar
# contempla: el otro extremo de la arista con su lado en las líneas gruesas, y la
# normal suavizada en la flecha.
_EXTREMO = QQuick3DGeometry.Attribute.Semantic.ColorSemantic
_NORMAL_SUAVE = _EXTREMO


def normal(puntos: ArrayLike) -> np.ndarray:
    """Calcula la normal de un polígono plano por el método de Newell.

    Newell funciona con cualquier cantidad de vértices y no se degenera cuando
    tres puntos consecutivos son casi colineales, que es lo que pasaría con un
    simple producto vectorial.

    Args:
        puntos: Los vértices del polígono, en orden.

    Returns:
        La normal unitaria. El sentido lo define el orden de los puntos, que es
        justamente para lo que los directores invierten algunas secuencias.
    """
    p = np.asarray(puntos, dtype=float)
    siguiente = np.roll(p, -1, axis=0)
    n = np.array(
        (
            np.sum((p[:, 1] - siguiente[:, 1]) * (p[:, 2] + siguiente[:, 2])),
            np.sum((p[:, 2] - siguiente[:, 2]) * (p[:, 0] + siguiente[:, 0])),
            np.sum((p[:, 0] - siguiente[:, 0]) * (p[:, 1] + siguiente[:, 1])),
        )
    )
    norma = np.linalg.norm(n)
    if norma == 0:
        return np.array((0.0, 0.0, 1.0))
    return n / norma


def centro(puntos: ArrayLike) -> np.ndarray:
    """El centro del polígono, donde se ancla la flecha de presión."""
    return np.asarray(puntos, dtype=float).mean(axis=0)


def area(puntos: ArrayLike) -> float:
    """El área de un polígono plano, por la fórmula de Newell."""
    p = np.asarray(puntos, dtype=float)
    if len(p) < 3:
        return 0.0
    return float(np.linalg.norm(np.cross(p, np.roll(p, -1, axis=0)).sum(axis=0)) / 2)


def interseccion_rayo(
    origen: ArrayLike, direccion: ArrayLike, puntos: ArrayLike
) -> tuple[float, np.ndarray] | None:
    """Dónde atraviesa un rayo a un polígono plano.

    Se usa para saber qué cara hay debajo del cursor. No mira de qué lado viene
    el rayo: una cara sirve igual vista de frente que de dorso, que es como se
    la ve acá —los polígonos se dibujan sin descarte y los directores invierten
    el orden de los puntos a propósito.

    Args:
        origen: El punto de donde sale el rayo.
        direccion: Hacia dónde va, sin necesidad de estar normalizada.
        puntos: Los vértices del polígono, en orden.

    Returns:
        El parámetro del rayo —cuántas veces ``direccion`` hay que avanzar— y el
        punto de impacto, o None si el rayo no lo toca.
    """
    p = np.asarray(puntos, dtype=float)
    if len(p) < 3:
        return None
    o = np.asarray(origen, dtype=float)
    d = np.asarray(direccion, dtype=float)
    n = normal(p)

    denominador = float(d @ n)
    if abs(denominador) < 1e-12:  # el rayo corre paralelo al plano
        return None
    t = float((p[0] - o) @ n / denominador)
    if t <= 0:  # el plano quedó atrás
        return None
    impacto = o + d * t

    # Se resuelve la pertenencia en 2D, tirando el eje donde el polígono se ve
    # más de canto: es el que menos precisión aporta.
    ejes = [i for i in range(3) if i != int(np.argmax(np.abs(n)))]
    if not _punto_en_poligono(impacto[ejes], p[:, ejes]):
        return None
    return t, impacto


def _punto_en_poligono(punto: np.ndarray, contorno: np.ndarray) -> bool:
    """Regla par-impar: cuántas aristas cruza un rayo horizontal desde el punto."""
    x, y = punto
    xs, ys = contorno[:, 0], contorno[:, 1]
    xs_sig, ys_sig = np.roll(xs, -1), np.roll(ys, -1)
    # Aristas que el rayo cruza en altura. El > y el <= asimétricos hacen que un
    # vértice cuente una sola vez.
    cruza = (ys > y) != (ys_sig > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_corte = xs + (y - ys) * (xs_sig - xs) / (ys_sig - ys)
    return bool(np.count_nonzero(cruza & (x < x_corte)) % 2)


class MallaPoligono(QQuick3DGeometry):
    """Un polígono plano, listo para usarse como ``geometry`` de un ``Model``.

    Triangula en abanico, que alcanza para todos los polígonos que generan los
    directores: paredes, faldones y zonas de cubierta son siempre convexos, y la
    pared de frente a dos aguas es un pentágono también convexo. Un polígono
    cóncavo saldría mal y necesitaría una triangulación real.
    """

    def __init__(self, puntos: ArrayLike) -> None:
        super().__init__()
        p = np.asarray(puntos, dtype=float)
        n = normal(p)

        vertices = bytearray()
        for punto in p:
            vertices += struct.pack("<6f", *punto, *n)

        indices = bytearray()
        for i in range(1, len(p) - 1):
            indices += struct.pack("<3I", 0, i, i + 1)

        self.setStride(24)  # 3 floats de posición + 3 de normal
        self.setVertexData(bytes(vertices))
        self.setIndexData(bytes(indices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_NORMAL, 12, _F32)
        self.addAttribute(_INDICE, 0, _U32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.setBounds(QVector3D(*p.min(axis=0)), QVector3D(*p.max(axis=0)))
        self.update()  # type: ignore[attr-defined]


class _LineaGruesa(QQuick3DGeometry):
    """Base de las mallas de línea con ancho fijo en píxeles.

    Las APIs gráficas modernas no rasterizan líneas de más de un píxel: Metal y
    Direct3D ni siquiera tienen ese estado y en Vulkan es una feature opcional,
    así que ``QRhi`` no lo expone y Qt Quick 3D no tiene dónde ponerlo. El grosor
    se fabrica acá: cada segmento deja de ser una línea y pasa a ser un
    rectángulo de cuatro vértices que ``contorno.vert`` abre en pantalla.

    Los cuatro vértices nacen pegados sobre los extremos del segmento, o sea que
    la malla por sí sola no tiene área. Cada uno lleva, además de su posición, el
    *otro* extremo de su segmento y de qué lado abrirse. Guardar el otro extremo
    en lugar de una dirección ya calculada es lo que le permite al shader
    trabajar después de proyectar, y por eso el ancho no termina dependiendo de
    la distancia a la cámara.
    """

    def _armar(self, segmentos: np.ndarray) -> None:
        """Sube los buffers a partir de un arreglo (n, 2, 3) de segmentos."""
        vertices = bytearray()
        indices = bytearray()
        for i, (a, b) in enumerate(segmentos):
            # El lado se invierte en el extremo B: allá la dirección del segmento
            # apunta al revés, y con ella la perpendicular que saca el shader.
            for punto, otro, lado in (
                (a, b, 1.0),
                (a, b, -1.0),
                (b, a, -1.0),
                (b, a, 1.0),
            ):
                vertices += struct.pack("<7f", *punto, *otro, lado)
            base = i * 4
            indices += struct.pack(
                "<6I", base, base + 1, base + 3, base, base + 3, base + 2
            )

        self.setStride(28)  # 3 floats de posición + 3 del otro extremo + 1 de lado
        self.setVertexData(bytes(vertices))
        self.setIndexData(bytes(indices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_EXTREMO, 12, _F32)
        self.addAttribute(_INDICE, 0, _U32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        puntos = segmentos.reshape(-1, 3)
        self.setBounds(QVector3D(*puntos.min(axis=0)), QVector3D(*puntos.max(axis=0)))
        self.update()  # type: ignore[attr-defined]


class MallaContorno(_LineaGruesa):
    """El borde de un polígono, cerrando el último punto contra el primero.

    No se despega de la cara acá: el shader acerca el contorno a la cámara, que
    resuelve el problema de Z sin desplazar la geometría y además funciona
    mirando la cara de los dos lados.
    """

    def __init__(self, puntos: ArrayLike) -> None:
        super().__init__()
        p = np.asarray(puntos, dtype=float)
        self._armar(np.stack((p, np.roll(p, -1, axis=0)), axis=1))


class MallaLineas(_LineaGruesa):
    """Segmentos sueltos, tomando los puntos de a pares.

    Se usa para los soportes de las cubiertas aisladas.
    """

    def __init__(self, puntos: ArrayLike) -> None:
        super().__init__()
        self._armar(np.asarray(puntos, dtype=float).reshape(-1, 2, 3))


class MallaFlecha(QQuick3DGeometry):
    """Una flecha de largo 1 con la base en el origen y la punta en +Y.

    La orientación no va acá: la resuelve con un cuaternión el ``Node`` que la
    contiene, así una sola malla sirve para todas las flechas de la escena.

    Cada vértice lleva dos normales: la de su cara, que es la que ilumina —la
    flecha se ve facetada—, y la suavizada, que es el promedio de las caras que
    tocan esa posición. La suavizada es sobre la que ``silueta.vert`` hincha la
    flecha para dibujarle el borde: con la de cara el borde se abriría en cada
    arista y quedaría con muescas.
    """

    def __init__(
        self,
        radio_vastago: float = 0.03,
        radio_punta: float = 0.1,
        largo_punta: float = 0.3,
        segmentos: int = 30,
    ) -> None:
        super().__init__()

        angulos = np.linspace(0, 2 * np.pi, segmentos, endpoint=False)
        cos, sen = np.cos(angulos), np.sin(angulos)
        y_union = 1 - largo_punta

        def anillo(radio: float, y: float) -> np.ndarray:
            return np.column_stack((cos * radio, np.full(segmentos, y), sen * radio))

        base_vastago = anillo(radio_vastago, 0.0)
        tope_vastago = anillo(radio_vastago, y_union)
        base_punta = anillo(radio_punta, y_union)
        punta = np.array((0.0, 1.0, 0.0))

        caras: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for i in range(segmentos):
            j = (i + 1) % segmentos
            caras.append((base_vastago[i], tope_vastago[i], tope_vastago[j]))
            caras.append((base_vastago[i], tope_vastago[j], base_vastago[j]))
            caras.append((base_punta[i], punta, base_punta[j]))
            caras.append((base_punta[j], np.array((0.0, y_union, 0.0)), base_punta[i]))
            caras.append((base_vastago[j], np.array((0.0, 0.0, 0.0)), base_vastago[i]))

        normales = []
        acumuladas: dict[tuple[float, ...], np.ndarray] = {}
        for a, b, c in caras:
            n = np.cross(b - a, c - a)
            norma = np.linalg.norm(n)
            n = n / norma if norma else np.array((0.0, 1.0, 0.0))
            normales.append(n)
            # Las caras vienen sueltas, sin índice, así que las que comparten un
            # vértice se juntan por su posición. Se redondea porque los anillos
            # se calculan con senos y cosenos.
            for v in (a, b, c):
                clave = tuple(np.round(v, 6))
                acumuladas[clave] = acumuladas.get(clave, np.zeros(3)) + n

        suavizadas = {}
        for clave, suma in acumuladas.items():
            norma = np.linalg.norm(suma)
            # El promedio sólo se anula si dos caras opuestas se cancelan, que en
            # esta malla no pasa. Igual no puede salir un vector nulo: el shader
            # lo normaliza y quedaría en NaN.
            suavizadas[clave] = suma / norma if norma else np.array((0.0, 1.0, 0.0))

        vertices = bytearray()
        for (a, b, c), n in zip(caras, normales):
            for v in (a, b, c):
                # El cuarto float de la normal suavizada no se usa: COLOR es un
                # vec4 y va completo.
                vertices += struct.pack(
                    "<10f", *v, *n, *suavizadas[tuple(np.round(v, 6))], 0.0
                )

        self.setStride(40)  # posición + normal de cara + normal suavizada (vec4)
        self.setVertexData(bytes(vertices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_NORMAL, 12, _F32)
        self.addAttribute(_NORMAL_SUAVE, 24, _F32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        r = max(radio_punta, radio_vastago)
        self.setBounds(QVector3D(-r, 0, -r), QVector3D(r, 1, r))
        self.update()  # type: ignore[attr-defined]


class MallaCilindro(QQuick3DGeometry):
    """Un cilindro vertical, para el soporte del cartel.

    Se arma a mano en lugar de escalar la primitiva ``#Cylinder`` de Qt Quick 3D,
    que mide 100 unidades: así las dimensiones quedan en metros como el resto de
    la escena.
    """

    def __init__(
        self,
        radio: float,
        altura: float,
        centro_xz: tuple[float, float],
        y_base: float = 0.0,
        segmentos: int = 50,
    ) -> None:
        super().__init__()
        cx, cz = centro_xz
        angulos = np.linspace(0, 2 * np.pi, segmentos, endpoint=False)
        cos, sen = np.cos(angulos), np.sin(angulos)
        abajo = np.column_stack(
            (cx + cos * radio, np.full(segmentos, y_base), cz + sen * radio)
        )
        arriba = abajo + np.array((0.0, altura, 0.0))

        vertices = bytearray()
        for i in range(segmentos):
            j = (i + 1) % segmentos
            n = np.array((cos[i], 0.0, sen[i]))
            for v in (abajo[i], arriba[i], arriba[j], abajo[i], arriba[j], abajo[j]):
                vertices += struct.pack("<6f", *v, *n)
            for v in (arriba[i], np.array((cx, y_base + altura, cz)), arriba[j]):
                vertices += struct.pack("<6f", *v, 0.0, 1.0, 0.0)

        self.setStride(24)
        self.setVertexData(bytes(vertices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_NORMAL, 12, _F32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.setBounds(
            QVector3D(cx - radio, y_base, cz - radio),
            QVector3D(cx + radio, y_base + altura, cz + radio),
        )
        self.update()  # type: ignore[attr-defined]
