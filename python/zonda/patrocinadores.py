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

"""Quiénes apoyan el proyecto, para mostrarlos en la pantalla de bienvenida.

La lista viaja empaquetada con cada versión: es un JSON al lado de los logos,
en ``recursos/patrocinadores/``. Sumar a alguien es copiar su logo y agregarle
una entrada al JSON, y publicar una release. No se descarga nada, así que la
bienvenida no depende de la red ni tarda más en abrir.

**Nada de esto puede impedir que Zonda arranque.** Un JSON con un error de
tipeo, un logo que se olvidaron de copiar o un nivel mal escrito hacen que esa
entrada se ignore, no que el programa falle: es información de cortesía, y el
usuario vino a calcular cargas de viento.

Los precios y las condiciones de cada nivel no están acá a propósito: viven en
la web del proyecto, porque cambiarlos no puede obligar a publicar una versión
nueva del programa.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from zonda.enums import NivelPatrocinio

NOMBRE_ARCHIVO = "patrocinadores.json"
"""El JSON con la lista, dentro del directorio de recursos."""

DIRECTORIO_RECURSOS = "patrocinadores"
"""El subdirectorio de recursos donde viven el JSON y los logos."""


@dataclass(frozen=True)
class Patrocinador:
    """Alguien que apoya el proyecto, tal como se lo muestra en pantalla."""

    nombre: str
    """El nombre del estudio o de la persona. Es lo único obligatorio."""

    nivel: NivelPatrocinio
    """Con qué nivel apoya. Decide dónde y con qué tamaño aparece."""

    web: str = ""
    """El sitio al que lleva el logo. Vacío si no tiene, y el logo no linkea."""

    logo: Path | None = None
    """La ruta al archivo del logo, ya resuelta y verificada.

    Es ``None`` cuando el nivel no lleva logo -bronce- o cuando el archivo
    declarado no está: en ese caso se lo muestra por nombre, que es preferible a
    dejar el hueco de una imagen rota.
    """

    fundador: bool = False
    """Si estuvo desde el principio. Es un distintivo, no un nivel aparte."""


def _directorio_por_defecto() -> Path:
    """El directorio de recursos donde vive la lista.

    Se importa acá adentro y no arriba porque ``recursos`` levanta Qt, y este
    módulo se puede leer -y testear- sin necesidad de una aplicación gráfica.

    Returns: La ruta al directorio de patrocinadores.
    """
    from zonda import recursos

    return recursos.directorio(DIRECTORIO_RECURSOS)


def cargar(directorio: Path | None = None) -> tuple[Patrocinador, ...]:
    """Lee la lista de patrocinadores.

    Devuelve las entradas en el orden de los niveles -oro, plata, bronce- y,
    dentro de cada nivel, en el orden del archivo. Para mostrarlos en pantalla
    conviene ``mezclados_por_nivel()``, que no le da a nadie el primer lugar
    para siempre.

    Args:
        directorio: Dónde buscar el JSON y los logos. Por omisión, el
            directorio de recursos del paquete.

    Returns: Los patrocinadores legibles. Vacío si no hay archivo, si no se
        puede leer o si ninguna entrada es válida.
    """
    raiz = directorio if directorio is not None else _directorio_por_defecto()
    archivo = raiz / NOMBRE_ARCHIVO

    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()

    if not isinstance(datos, dict):
        return ()

    entradas = datos.get("patrocinadores")
    if not isinstance(entradas, list):
        return ()

    patrocinadores = [
        patrocinador
        for entrada in entradas
        if (patrocinador := _leer_entrada(entrada, raiz)) is not None
    ]

    orden = list(NivelPatrocinio)
    patrocinadores.sort(key=lambda p: orden.index(p.nivel))
    return tuple(patrocinadores)


def _leer_entrada(entrada: object, raiz: Path) -> Patrocinador | None:
    """Interpreta una entrada del JSON.

    Args:
        entrada: Un elemento de la lista ``patrocinadores``.
        raiz: El directorio contra el que se resuelve la ruta del logo.

    Returns: El patrocinador, o ``None`` si la entrada no sirve.
    """
    if not isinstance(entrada, dict):
        return None

    nombre = str(entrada.get("nombre", "")).strip()
    if not nombre:
        return None

    try:
        nivel = NivelPatrocinio(str(entrada.get("nivel", "")).strip().lower())
    except ValueError:
        return None

    logo = None
    archivo_logo = str(entrada.get("logo", "")).strip()
    if archivo_logo:
        # ``name`` corta cualquier ruta que traiga la entrada: los logos se
        # buscan siempre dentro del directorio de recursos, y un "../" en el
        # JSON no tiene por qué poder señalar a otro lado del disco.
        candidato = raiz / Path(archivo_logo).name
        if candidato.is_file():
            logo = candidato

    return Patrocinador(
        nombre=nombre,
        nivel=nivel,
        web=str(entrada.get("web", "")).strip(),
        logo=logo,
        fundador=bool(entrada.get("fundador", False)),
    )


def por_nivel(
    patrocinadores: tuple[Patrocinador, ...],
) -> dict[NivelPatrocinio, tuple[Patrocinador, ...]]:
    """Agrupa a los patrocinadores por nivel.

    Args:
        patrocinadores: La lista a agrupar.

    Returns: Los niveles que tienen al menos un patrocinador, en orden de
        importancia. Los niveles vacíos no aparecen.
    """
    agrupados: defaultdict[NivelPatrocinio, list[Patrocinador]] = defaultdict(list)
    for patrocinador in patrocinadores:
        agrupados[patrocinador.nivel].append(patrocinador)

    return {
        nivel: tuple(agrupados[nivel]) for nivel in NivelPatrocinio if agrupados[nivel]
    }


def mezclados_por_nivel(
    patrocinadores: tuple[Patrocinador, ...],
) -> dict[NivelPatrocinio, tuple[Patrocinador, ...]]:
    """Como ``por_nivel()``, pero barajando dentro de cada nivel.

    Quien paga lo mismo que otro no tiene por qué quedarse con el peor lugar
    para siempre porque su nombre empieza con W. El orden cambia en cada
    arranque; entre niveles no se mezcla nada.

    Args:
        patrocinadores: La lista a agrupar.

    Returns: Los niveles con al menos un patrocinador, cada uno barajado.
    """
    agrupados = por_nivel(patrocinadores)
    return {
        nivel: tuple(random.sample(lista, len(lista)))
        for nivel, lista in agrupados.items()
    }
