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

"""Lectura y escritura de los archivos de proyecto.

Un archivo de proyecto guarda **los datos de entrada** de un módulo —geometría,
viento, topografía y componentes—, no los resultados: al abrirlo se recalcula
todo. Así el archivo no queda atado a la versión del motor de cálculo, que es lo
que se mueve entre versiones del programa.

Lo que se guarda es el *estado de los widgets de entrada*, no el diccionario que
sale de ``parametros()``. Ese diccionario es lo que necesita el motor de
cálculo y por eso deja cosas afuera —los spinboxes deshabilitados, la altura de
cumbrera de una cubierta plana, el volumen interno cuando no se reduce el
GCpi—. El estado, en cambio, vuelve a dejar la pantalla exactamente como
estaba.

El formato es JSON. Los enums del dominio se guardan por su **nombre**
(``TipoCubierta.DOS_AGUAS`` -> ``"DOS_AGUAS"``), que es estable aunque cambie el
texto que se le muestra al usuario.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from zonda import enums
from zonda.excepciones import ErrorArchivo

EXTENSION = ".zda"
FILTRO = f"Proyecto Zonda (*{EXTENSION})"

VERSION_FORMATO = 1

_CLAVE_ENUM = "__enum__"


class _Codificador(json.JSONEncoder):
    """Escribe los enums del dominio como ``{"__enum__": clase, "nombre": ...}``."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return {_CLAVE_ENUM: type(o).__name__, "nombre": o.name}
        return super().default(o)


def _decodificar(diccionario: dict[str, Any]) -> Any:
    """Reconstruye los enums que escribió ``_Codificador``."""
    nombre_clase = diccionario.get(_CLAVE_ENUM)
    if nombre_clase is None:
        return diccionario
    clase = getattr(enums, nombre_clase, None)
    if not isinstance(clase, type) or not issubclass(clase, Enum):
        raise ErrorArchivo(
            f'El archivo usa un tipo de dato desconocido: "{nombre_clase}".'
        )
    try:
        return clase[diccionario["nombre"]]
    except KeyError as error:
        raise ErrorArchivo(
            f'El archivo usa un valor desconocido de {nombre_clase}: "{diccionario.get("nombre")}".'
        ) from error


def guardar(
    ruta: str | Path, estructura: enums.Estructura, estado: dict[str, Any]
) -> None:
    """Escribe un archivo de proyecto.

    Args:
        ruta: El archivo a escribir.
        estructura: El tipo de estructura del módulo que se está guardando.
        estado: El estado de los widgets de entrada.

    Raises:
        ErrorArchivo: Si el archivo no se puede escribir.
    """
    contenido = {
        "programa": "zonda",
        "version_formato": VERSION_FORMATO,
        "estructura": estructura,
        "estado": estado,
    }
    try:
        Path(ruta).write_text(
            json.dumps(contenido, cls=_Codificador, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as error:
        raise ErrorArchivo(f"No se pudo escribir el archivo:\n{error}") from error


def abrir(ruta: str | Path) -> tuple[enums.Estructura, dict[str, Any]]:
    """Lee un archivo de proyecto.

    Args:
        ruta: El archivo a leer.

    Returns:
        El tipo de estructura al que pertenece el archivo y el estado de los
        widgets de entrada.

    Raises:
        ErrorArchivo: Si el archivo no se puede leer o no es un proyecto de Zonda.
    """
    try:
        texto = Path(ruta).read_text(encoding="utf-8")
    except OSError as error:
        raise ErrorArchivo(f"No se pudo leer el archivo:\n{error}") from error

    try:
        contenido = json.loads(texto, object_hook=_decodificar)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ErrorArchivo(
            "El archivo no es un proyecto de Zonda o está dañado."
        ) from error

    if not isinstance(contenido, dict) or contenido.get("programa") != "zonda":
        raise ErrorArchivo("El archivo no es un proyecto de Zonda.")

    version = contenido.get("version_formato")
    if version != VERSION_FORMATO:
        raise ErrorArchivo(
            f"El archivo es de un formato distinto (versión {version}). Esta versión"
            f" del programa lee el formato {VERSION_FORMATO}."
        )

    estructura = contenido.get("estructura")
    estado = contenido.get("estado")
    if not isinstance(estructura, enums.Estructura) or not isinstance(estado, dict):
        raise ErrorArchivo("El archivo está incompleto o dañado.")

    return estructura, estado
