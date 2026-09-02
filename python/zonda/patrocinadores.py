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
from urllib.parse import urlsplit

from zonda.enums import NivelPatrocinio

ESQUEMAS_PERMITIDOS = frozenset({"http", "https", "mailto"})
"""Los esquemas de enlace que se aceptan de los datos.

Estos enlaces terminan en ``QDesktopServices.openUrl()``, que le pide al sistema
operativo que abra lo que sea. Un ``file://`` acá abriría archivos de la máquina
de quien usa el programa, así que todo lo que no sea una web o un correo se
descarta al leer.
"""

NOMBRE_ARCHIVO = "patrocinadores.json"
"""El JSON con la lista, dentro del directorio de recursos."""

NOMBRE_ARCHIVO_COLABORADORES = "colaboradores.json"
"""El JSON con quienes aportan tiempo al proyecto.

Se mantiene a mano y no se saca del historial de git a propósito: los aportes
que más importan —revisar un cálculo contra el Reglamento, reportar un
resultado dudoso, probar un instalador— no dejan ningún commit.
"""

DIRECTORIO_RECURSOS = "patrocinadores"
"""El subdirectorio de recursos donde viven el JSON y los logos."""


@dataclass(frozen=True)
class Colaborador:
    """Alguien que le pone tiempo al proyecto sin patrocinarlo."""

    nombre: str
    """Cómo quiere que se lo nombre."""

    aporte: str = ""
    """En qué ayuda, en pocas palabras."""


@dataclass(frozen=True)
class Patrocinador:
    """Alguien que apoya el proyecto, tal como se lo muestra en pantalla."""

    nombre: str
    """El nombre del estudio o de la persona. Es lo único obligatorio."""

    nivel: NivelPatrocinio
    """Con qué nivel apoya. Decide dónde y con qué tamaño aparece."""

    web: str = ""
    """Adónde lleva el logo: su sitio, o un ``mailto:`` si prefieren eso.

    Vacío cuando no tienen, o cuando lo declarado no pasó la validación de
    esquemas, y entonces el logo no linkea a ningún lado.
    """

    contacto: str = ""
    """Un segundo enlace para el perfil de oro, normalmente un ``mailto:``."""

    ciudad: str = ""
    """Dónde están. Sólo se muestra en el perfil de oro."""

    rubro: str = ""
    """A qué se dedican, en una línea. Sólo en el perfil de oro."""

    descripcion: str = ""
    """El párrafo que escriben ellos. Sólo en el perfil de oro."""

    desde: str = ""
    """Desde qué año patrocinan el proyecto."""

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


def _enlace(valor: object) -> str:
    """Deja pasar un enlace sólo si es de un esquema aceptado.

    Args:
        valor: Lo que trae el JSON.

    Returns: El enlace, o una cadena vacía si no sirve.
    """
    enlace = str(valor or "").strip()
    if not enlace:
        return ""
    return enlace if urlsplit(enlace).scheme.lower() in ESQUEMAS_PERMITIDOS else ""


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
        web=_enlace(entrada.get("web")),
        contacto=_enlace(entrada.get("contacto")),
        ciudad=str(entrada.get("ciudad", "")).strip(),
        rubro=str(entrada.get("rubro", "")).strip(),
        descripcion=str(entrada.get("descripcion", "")).strip(),
        desde=str(entrada.get("desde", "")).strip(),
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


def colaboradores(directorio: Path | None = None) -> tuple[Colaborador, ...]:
    """Lee la lista de quienes aportan tiempo al proyecto.

    Args:
        directorio: Dónde buscar el JSON. Por omisión, el de recursos.

    Returns: Los colaboradores, en el orden del archivo. Vacío si el archivo no
        está o no se puede leer, igual que con los patrocinadores: es
        información de cortesía y no puede impedir que el programa arranque.
    """
    raiz = directorio if directorio is not None else _directorio_por_defecto()

    try:
        datos = json.loads(
            (raiz / NOMBRE_ARCHIVO_COLABORADORES).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return ()

    if not isinstance(datos, dict):
        return ()

    entradas = datos.get("colaboradores")
    if not isinstance(entradas, list):
        return ()

    leidos = []
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue
        nombre = str(entrada.get("nombre", "")).strip()
        if nombre:
            leidos.append(
                Colaborador(
                    nombre=nombre, aporte=str(entrada.get("aporte", "")).strip()
                )
            )
    return tuple(leidos)
