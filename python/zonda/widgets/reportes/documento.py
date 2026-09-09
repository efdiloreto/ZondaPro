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

"""El modelo del documento de reporte.

Es la fuente única de la que salen las dos caras del reporte: la vista en
pantalla (:mod:`zonda.widgets.reportes.secciones`) y el PDF exportado
(:mod:`zonda.pdf`). Los módulos por tipología lo arman desde
``estructura.resultados*`` filtrando y agrupando la tabla plana, con los
valores ya formateados y las unidades resueltas: es un documento
presentacional, no un modelo de cálculo.

Los bloques describen contenido, no widgets: la vista los convierte en
``Seccion``, ``Subseccion``, ``TablaResultados``, etc., y el PDF en
formatos de ``QTextDocument``. Ninguno de los dos consume el otro.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Celda:
    """Una celda de tabla, con su texto y el resaltado si corresponde.

    La clase marca un extremo de la columna: ``maximo`` para la máxima
    presión (rojo) y ``minimo`` para la máxima succión (azul), la misma
    semántica que usa la vista en pantalla y la escala de la vista 3D.
    """

    texto: str
    clase: str | None = None


@dataclass(frozen=True, slots=True)
class Tabla:
    """Una tabla de resultados, lista para mostrarse.

    Args:
        columnas: Los títulos de las columnas, con sus unidades.
        filas: Las filas; cada una trae una celda por columna, como texto
            plano o como `Celda` resaltada.
    """

    columnas: list[str]
    filas: Sequence[Sequence[Celda | str]]


@dataclass(frozen=True, slots=True)
class Datos:
    """Pares etiqueta-valor, la forma de los datos de entrada."""

    filas: Sequence[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class Tarjeta:
    """Un valor destacado: etiqueta, valor y detalle opcional."""

    titulo: str
    valor: str
    detalle: str | None = None
    destacada: bool = False


@dataclass(frozen=True, slots=True)
class Tarjetas:
    """Una fila de tarjetas, repartidas en el ancho disponible."""

    tarjetas: list[Tarjeta]


@dataclass(frozen=True, slots=True)
class Nota:
    """Una consideración del Reglamento que hay que leer aunque no se
    revisen los números."""

    texto: str
    titulo: str = "Nota"


@dataclass(frozen=True, slots=True)
class Texto:
    """Un párrafo con formato enriquecido.

    El texto viaja en el subset de HTML que entiende Qt (etiquetas
    ``<b>``, ``<li>``...): la vista lo muestra en un ``QLabel`` de texto
    enriquecido y el PDF lo inserta con el mismo motor. Es el formato que
    ya usaban las consideraciones del cartel en pantalla.
    """

    texto: str


@dataclass(frozen=True, slots=True)
class Titulo:
    """Un rótulo intermedio entre contenidos, dentro de un grupo.

    Es el nivel que nombra, por ejemplo, cada dirección de viento dentro
    del factor de ráfaga, sin abrir un grupo propio.
    """

    texto: str


@dataclass(frozen=True, slots=True)
class Grupo:
    """Un título de segundo nivel con el contenido que encabeza.

    Es la forma de la subsección: una tabla con su referencia al
    Reglamento, unos datos con su rótulo, o un grupo de ellos.

    Args:
        titulo: El título del grupo.
        bloques: El contenido del grupo, en orden de lectura.
        referencia: La referencia al Reglamento (figura, tabla o artículo).
    """

    titulo: str
    bloques: list[Bloque]
    referencia: str | None = None


@dataclass(frozen=True, slots=True)
class Pestanas:
    """Contenido conmutado por pestañas.

    En pantalla cada item es una pestaña de un ``QTabWidget``; en el PDF,
    donde no hay interactividad, los items se muestran uno después del
    otro con su título.
    """

    items: list[tuple[str, list[Bloque]]]


@dataclass(frozen=True, slots=True)
class Superficie:
    """Una superficie del selector de componentes, con sus componentes."""

    etiqueta: str
    componentes: list[tuple[str, list[Bloque]]]


@dataclass(frozen=True, slots=True)
class SelectorComponentes:
    """El selector de componentes y revestimientos.

    En pantalla muestra de a un componente por vez (cápsula de
    superficies y desplegable de componentes); en el PDF se muestran
    todos, agrupados por superficie.
    """

    superficies: list[Superficie]


@dataclass(frozen=True, slots=True)
class Pagina:
    """Una página del reporte, como las del índice de la vista.

    Args:
        titulo: El nombre de la página, que encabeza el contenido.
        bloques: El contenido, en orden de lectura.
        descripcion: Un texto introductorio opcional, debajo del título.
        exportable: Si la página viaja al PDF. La de resumen, pensada
            para leer en pantalla, no viaja.
    """

    titulo: str
    bloques: list[Bloque] = field(default_factory=list)
    descripcion: str | None = None
    exportable: bool = True


@dataclass(frozen=True, slots=True)
class Documento:
    """El documento completo: título y páginas en el orden del índice."""

    titulo: str
    paginas: list[Pagina]


Bloque = (
    Grupo
    | Datos
    | Tabla
    | Tarjetas
    | Nota
    | Texto
    | Titulo
    | Pestanas
    | SelectorComponentes
)
