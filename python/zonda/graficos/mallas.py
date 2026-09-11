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
from typing import Any

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
# sobra: por ahí viaja el dato que ningún atributo estándar contempla en las
# líneas gruesas, el otro extremo de la arista con el lado por el que abrirse.
_EXTREMO = QQuick3DGeometry.Attribute.Semantic.ColorSemantic


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


class MallaTrazo(QQuick3DGeometry):
    """El trazo de una polilínea con esquinas a inglete, para el glow.

    A diferencia de ``MallaContorno`` —un rectángulo por arista con tapas
    cuadradas que rellenan las esquinas— acá cada esquina aporta dos vértices
    con las direcciones de los dos tramos que la forman: el shader calcula el
    inglete en pantalla y no hay superposiciones. Eso hace que un trazo
    translúcido no acumule color en las esquinas, como le pasaba al glow.

    Cada vértice lleva su posición, la esquina *previa* de la polilínea con el
    lado por el que abrirse (COLOR), y la esquina *siguiente* (NORMAL): con
    las dos direcciones proyectadas sale el inglete, sin importar por dónde
    mire la cámara.

    Args:
        polilineas: Pares ``(puntos, cerrado)``. En un trazo abierto la
            primera y la última esquina no tienen un tramo previo o siguiente,
            y quedan a tope recto.
    """

    def __init__(self, polilineas) -> None:
        super().__init__()
        self._armar(polilineas)

    def _armar(self, polilineas) -> None:
        if not polilineas:
            return
        vertices = bytearray()
        indices = bytearray()
        base = 0
        for puntos, cerrado in polilineas:
            p = np.asarray(puntos, dtype=float)
            n = len(p)
            previa = np.roll(p, 1, axis=0)
            siguiente = np.roll(p, -1, axis=0)
            if not cerrado:
                # Los extremos de un trazo abierto no tienen un tramo del otro
                # lado: el shader cae en la perpendicular del tramo que sí hay.
                previa[0] = p[0]
                siguiente[-1] = p[-1]
            for i in range(n):
                for lado in (1.0, -1.0):
                    vertices += struct.pack(
                        "<10f", *p[i], *previa[i], lado, *siguiente[i]
                    )
            # Un quad entre cada par de esquinas contiguas; en un trazo cerrado
            # el último vuelve contra la primera esquina.
            for i in range(n if cerrado else n - 1):
                j = (i + 1) % n
                a, b = base + 2 * i, base + 2 * j
                indices += struct.pack("<6I", a, a + 1, b + 1, a, b + 1, b)
            base += 2 * n

        self.setStride(40)  # 3 de posición + 4 de COLOR + 3 de NORMAL
        self.setVertexData(bytes(vertices))
        self.setIndexData(bytes(indices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_EXTREMO, 12, _F32)
        self.addAttribute(_NORMAL, 28, _F32)
        self.addAttribute(_INDICE, 0, _U32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        puntos = np.vstack([np.asarray(p, dtype=float) for p, _ in polilineas])
        self.setBounds(QVector3D(*puntos.min(axis=0)), QVector3D(*puntos.max(axis=0)))
        self.update()  # type: ignore[attr-defined]


class MallaLineas(_LineaGruesa):
    """Segmentos sueltos, tomando los puntos de a pares.

    Se usa para los soportes de las cubiertas aisladas.
    """

    def __init__(self, puntos: ArrayLike) -> None:
        super().__init__()
        self._armar(np.asarray(puntos, dtype=float).reshape(-1, 2, 3))


RADIO_VASTAGO_FLECHA = 0.35
"""Distancia del eje a la esquina de la sección del vastago, en metros."""

RADIO_PUNTA_FLECHA = 0.75
"""Distancia del eje a la esquina de la base de la punta, en metros."""

LARGO_PUNTA_FLECHA = 2.25
"""El largo de la punta, en metros: es fijo, no escala con la presión."""


def _seccion_flecha(radio: float, y: float = 0.0) -> np.ndarray:
    """Las cuatro esquinas de un cuadrado de circunradio ``radio``.

    Los cuadrados de la flecha comparten centro y orientación —sus esquinas
    caen a 45° de los ejes— para que las caras del vastago queden paralelas a
    las de la pirámide.
    """
    angulos = np.pi / 4 + np.linspace(0, 2 * np.pi, 4, endpoint=False)
    return np.column_stack(
        (np.cos(angulos) * radio, np.full(4, y), np.sin(angulos) * radio)
    )


class MallaVastagoFlecha(QQuick3DGeometry):
    """El vastago de la flecha: un prisma de largo 1 con la base en el origen.

    La punta lo completa más arriba y la orientación la resuelve con un
    cuaternión el ``Node`` que los contiene, así unas pocas mallas sirven para
    todas las flechas de la escena. La vista lo estira sólo en Y: la sección
    queda constante y con ella el grosor, sin importar el largo que le pida la
    presión.

    Cada vértice lleva la normal de su cara, que es la que ilumina: el prisma
    se ve facetado.
    """

    def __init__(self, radio: float = RADIO_VASTAGO_FLECHA) -> None:
        super().__init__()
        base = _seccion_flecha(radio, 0.0)
        tope = _seccion_flecha(radio, 1.0)
        origen = np.array((0.0, 0.0, 0.0))

        caras: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for i in range(4):
            j = (i + 1) % 4
            caras.append((base[i], tope[i], tope[j]))
            caras.append((base[i], tope[j], base[j]))
            caras.append((base[j], origen, base[i]))

        vertices = bytearray()
        for a, b, c in caras:
            n = np.cross(b - a, c - a)
            norma = np.linalg.norm(n)
            n = n / norma if norma else np.array((0.0, 1.0, 0.0))
            for v in (a, b, c):
                vertices += struct.pack("<6f", *v, *n)

        self.setStride(24)  # 3 floats de posición + 3 de normal
        self.setVertexData(bytes(vertices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_NORMAL, 12, _F32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.setBounds(QVector3D(-radio, 0, -radio), QVector3D(radio, 1, radio))
        self.update()  # type: ignore[attr-defined]


class MallaPuntaFlecha(QQuick3DGeometry):
    """La punta de la flecha: el marco de la base más la pirámide.

    Es de tamaño fijo —la vista no la escala— y la base queda en el origen, en
    el plano donde empalma con el vastago, con el ápice sobre +Y. El marco son
    los trapecios entre el cuadrado del vastago y el de la pirámide, que
    comparten orientación y quedan al hilo.

    Cada vértice lleva la normal de su cara, que es la que ilumina: la punta se
    ve facetada.
    """

    def __init__(
        self,
        radio_vastago: float = RADIO_VASTAGO_FLECHA,
        radio_punta: float = RADIO_PUNTA_FLECHA,
        largo: float = LARGO_PUNTA_FLECHA,
    ) -> None:
        super().__init__()
        interior = _seccion_flecha(radio_vastago)
        exterior = _seccion_flecha(radio_punta)
        apice = np.array((0.0, largo, 0.0))

        caras: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for i in range(4):
            j = (i + 1) % 4
            # El marco mira hacia abajo, como el pie del vastago.
            caras.append((exterior[i], exterior[j], interior[j]))
            caras.append((exterior[i], interior[j], interior[i]))
            caras.append((exterior[i], apice, exterior[j]))

        vertices = bytearray()
        for a, b, c in caras:
            n = np.cross(b - a, c - a)
            norma = np.linalg.norm(n)
            n = n / norma if norma else np.array((0.0, 1.0, 0.0))
            for v in (a, b, c):
                vertices += struct.pack("<6f", *v, *n)

        self.setStride(24)  # 3 floats de posición + 3 de normal
        self.setVertexData(bytes(vertices))
        self.addAttribute(_POSICION, 0, _F32)
        self.addAttribute(_NORMAL, 12, _F32)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.setBounds(
            QVector3D(-radio_punta, 0, -radio_punta),
            QVector3D(radio_punta, largo, radio_punta),
        )
        self.update()  # type: ignore[attr-defined]


class MallaAristasVastagoFlecha(_LineaGruesa):
    """Las aristas del vastago, listas para el shader de líneas gruesas.

    La vista la escala igual que el vastago: los cuatro cantos verticales y
    los cuadrados del pie y del tope, sobre un prisma de largo 1. El cuadrado
    del tope es también el borde interior del marco de la punta.
    """

    def __init__(self, radio: float = RADIO_VASTAGO_FLECHA) -> None:
        super().__init__()
        base = _seccion_flecha(radio, 0.0)
        tope = _seccion_flecha(radio, 1.0)
        aristas: list[tuple[np.ndarray, np.ndarray]] = []
        for i in range(4):
            j = (i + 1) % 4
            aristas.append((base[i], tope[i]))
            aristas.append((base[i], base[j]))
            aristas.append((tope[i], tope[j]))
        self._armar(np.array(aristas))


class MallaAristasPuntaFlecha(_LineaGruesa):
    """Las aristas de la punta, listas para el shader de líneas gruesas.

    Es de tamaño fijo, igual que la punta: los cuatro cantos de la pirámide y
    el perímetro de su base. El borde interior del marco lo dibuja el cuadrado
    del tope del vastago.
    """

    def __init__(
        self,
        radio: float = RADIO_PUNTA_FLECHA,
        largo: float = LARGO_PUNTA_FLECHA,
    ) -> None:
        super().__init__()
        base = _seccion_flecha(radio)
        apice = np.array((0.0, largo, 0.0))
        aristas: list[tuple[np.ndarray, np.ndarray]] = []
        for i in range(4):
            j = (i + 1) % 4
            aristas.append((base[i], apice))
            aristas.append((base[i], base[j]))
        self._armar(np.array(aristas))


class MallaTrazoVastagoFlecha(MallaTrazo):
    """La silueta del vastago para el glow: sólo los cuatro cantos.

    Los cuadrados de la base y del tope quedan afuera a propósito: la base
    apoya contra la cara y el tope empalma con el marco de la punta, así que
    son uniones interiores del conjunto cara + flecha y el glow no tiene que
    dibujarlas.
    """

    def __init__(self, radio: float = RADIO_VASTAGO_FLECHA) -> None:
        super().__init__([])
        base = _seccion_flecha(radio, 0.0)
        tope = _seccion_flecha(radio, 1.0)
        self._armar([((base[i], tope[i]), False) for i in range(4)])


class MallaTrazoPuntaFlecha(MallaTrazo):
    """La silueta de la punta para el glow: el perímetro de la base y los
    cuatro cantos que suben al ápice. El borde interior del marco lo aporta
    el vastago y queda sin glow, como toda unión interior del conjunto."""

    def __init__(
        self,
        radio: float = RADIO_PUNTA_FLECHA,
        largo: float = LARGO_PUNTA_FLECHA,
    ) -> None:
        super().__init__([])
        seccion = _seccion_flecha(radio)
        apice = np.array((0.0, largo, 0.0))
        polilineas: list[tuple[Any, bool]] = [
            ((seccion[i], apice), False) for i in range(4)
        ]
        polilineas.append((seccion, True))
        self._armar(polilineas)


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
