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

"""Instalación del servidor MCP en clientes locales.

Cada cliente LLM guarda sus servidores MCP en un archivo de configuración
propio. Este módulo agrega, actualiza o quita la entrada de Zonda en ese
archivo, sin tocar las demás entradas, con una copia de respaldo antes de
escribir. La entrada apunta al intérprete del entorno virtual que corre la
aplicación, así que el servidor arranca igual en el entorno aislado de cada
cliente, sin depender de que ``uv`` esté en el PATH. Para los clientes que no
están en la lista, ``prompt_instalacion()`` genera el texto que un agente
necesita para instalarse el servidor y verificarlo por su cuenta.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from zonda.excepciones import ErrorConfiguracionMCP

CLIENTE_ZONDA = "zonda"
"""El nombre de la entrada de Zonda en la configuración del cliente."""


class EstadoCliente(StrEnum):
    """El estado de la instalación del MCP en un cliente."""

    INSTALADO = "instalado"
    DESACTUALIZADO = "desactualizado"
    NO_INSTALADO = "no instalado"
    NO_DETECTADO = "no detectado"
    NO_DISPONIBLE = "no disponible"
    ILEGIBLE = "ilegible"


@dataclass(frozen=True)
class Cliente:
    """Un cliente LLM local con configuración MCP conocida.

    Args:
        nombre: El nombre del cliente, para la interfaz.
        archivo_config: El archivo de configuración en esta plataforma, o
            None si el cliente no está disponible para ella.
        marcadores: Las rutas cuya existencia indica que el cliente está
            instalado, aunque todavía no tenga configuración.
        raiz: La clave raíz de los servidores en el archivo de configuración.
            Casi todos usan ``mcpServers``; OpenCode usa ``mcp``.
    """

    nombre: str
    archivo_config: Path | None
    marcadores: tuple[Path, ...] = ()
    raiz: str = "mcpServers"


def _archivos_claude_desktop() -> tuple[Path, ...]:
    """Los archivos de configuración posibles de Claude Desktop.

    Returns:
        La ruta estándar de la plataforma y, en Windows, la del paquete de la
        Microsoft Store. En Linux, la que usan los builds no oficiales.
    """
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",
        )
    if sys.platform == "win32":
        candidatos = []
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidatos.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            paquetes = Path(local) / "Packages"
            if paquetes.is_dir():
                candidatos.extend(
                    paquete
                    / "LocalCache"
                    / "Roaming"
                    / "Claude"
                    / "claude_desktop_config.json"
                    for paquete in paquetes.glob("Claude_*")
                )
        return tuple(candidatos)
    return (Path.home() / ".config" / "Claude" / "claude_desktop_config.json",)


def _clientes() -> tuple[Cliente, ...]:
    """Los clientes soportados con sus rutas en esta plataforma.

    Returns:
        Los clientes, con el primero cuyo archivo exista (o el estándar si
        ninguno existe todavía).
    """
    archivos_desktop = _archivos_claude_desktop()
    existentes = [archivo for archivo in archivos_desktop if archivo.exists()]
    archivo_desktop = (existentes or archivos_desktop)[0] if archivos_desktop else None
    marcadores_desktop = tuple(dict.fromkeys(a.parent for a in archivos_desktop))
    hogar = Path.home()
    return (
        Cliente(
            nombre="Claude Desktop",
            archivo_config=archivo_desktop,
            marcadores=marcadores_desktop,
        ),
        Cliente(
            nombre="Claude Code",
            archivo_config=hogar / ".claude.json",
            marcadores=(hogar / ".claude",),
        ),
        Cliente(
            nombre="Antigravity",
            archivo_config=hogar / ".gemini" / "config" / "mcp_config.json",
            marcadores=(
                hogar / ".gemini" / "config",
                hogar / ".gemini" / "antigravity",
            ),
        ),
        Cliente(
            nombre="OpenCode",
            archivo_config=hogar / ".config" / "opencode" / "opencode.json",
            marcadores=(hogar / ".config" / "opencode",),
            raiz="mcp",
        ),
    )


CLIENTES = _clientes()
"""Los clientes LLM locales en los que se puede instalar el servidor."""

CHATGPT_NO_LOCAL = (
    "ChatGPT solo acepta servidores MCP remotos por HTTP con URL pública "
    "(modo Developer, planes Pro, Team, Enterprise y Edu). Un servidor local "
    "por stdio, como el de Zonda, no se puede conectar."
)


def entrada_servidor(raiz: str = "mcpServers") -> dict:
    """La entrada que lanza el servidor de Zonda.

    Args:
        raiz: La clave raíz de la configuración, que determina el formato de
            la entrada: ``mcpServers`` usa ``command`` como texto, y ``mcp``
            (OpenCode) usa ``type local`` con ``command`` como lista.

    Returns:
        El diccionario de la entrada con el intérprete del entorno virtual en
        curso y ``-m zonda.mcp`` como argumento.
    """
    if raiz == "mcp":
        return {
            "type": "local",
            "command": [sys.executable, "-m", "zonda.mcp"],
            "enabled": True,
        }
    return {"command": sys.executable, "args": ["-m", "zonda.mcp"], "env": {}}


def prompt_instalacion() -> str:
    """El texto para que un agente instale el servidor en su propio cliente.

    Returns:
        El prompt con el comando real, el nombre de la entrada y los pasos de
        verificación (listar las herramientas y hacer una llamada de prueba).
    """
    return (
        "Instalá el servidor MCP de Zonda en tu configuración de servidores"
        " MCP.\n\n"
        f'La entrada se llama "{CLIENTE_ZONDA}" y lanza un servidor por'
        f" stdio con el comando:\n{sys.executable} -m zonda.mcp\n\n"
        "Pasos:\n"
        f'1. Agregá la entrada "{CLIENTE_ZONDA}" a tu configuración de'
        " servidores MCP, con el formato que use tu cliente (por ejemplo"
        " command y args bajo mcpServers, o type local con command como"
        " lista).\n"
        "2. Recargá la configuración de servidores MCP.\n"
        "3. Verificá que aparezcan las herramientas calcular_edificio,"
        " calcular_cartel y calcular_cubierta_aislada.\n"
        "4. Hacé una llamada de prueba a calcular_cartel con un cartel de 10"
        " m de ancho, 1 m de profundidad, alturas de 5 a 10 m, velocidad 45"
        " m/s y categoría de exposición B. Si devuelve resultados con presión"
        " y fuerza, la instalación quedó lista.\n\n"
        "El comando apunta al intérprete del entorno virtual de Zonda; si"
        " movés el proyecto, volvé a instalar."
    )


def _leer(archivo: Path) -> dict:
    """Lee la configuración de un cliente.

    Args:
        archivo: El archivo de configuración.

    Returns:
        El diccionario del archivo, o vacío si no existe o está vacío.
        Antigravity, entre otros, crea el archivo sin contenido la primera
        vez que abre su administrador de MCP.

    Raises:
        ErrorConfiguracionMCP: Cuando el archivo existe pero no es JSON
            válido.
    """
    if not archivo.exists():
        return {}
    texto = archivo.read_text(encoding="utf-8")
    if not texto.strip():
        return {}
    try:
        contenido = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorConfiguracionMCP(
            f"La configuración de {archivo} no es un JSON válido: {error}. Si"
            " tiene comentarios o no se puede corregir a mano, no la toques y"
            " usá el prompt de instalación para que un agente la edite."
        ) from None
    if not isinstance(contenido, dict):
        raise ErrorConfiguracionMCP(
            f"La configuración de {archivo} no es un objeto JSON."
        )
    return contenido


def _escribir(archivo: Path, datos: dict) -> None:
    """Escribe la configuración de un cliente con respaldo y escritura atómica.

    Args:
        archivo: El archivo de configuración.
        datos: El contenido a escribir.
    """
    archivo.parent.mkdir(parents=True, exist_ok=True)
    if archivo.exists():
        shutil.copy2(archivo, archivo.with_name(archivo.name + ".bak"))
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporal, archivo)


def estado(cliente: Cliente) -> EstadoCliente:
    """El estado de la instalación en un cliente.

    Args:
        cliente: El cliente a inspeccionar.

    Returns:
        El estado: NO_DISPONIBLE si el cliente no existe para la plataforma;
        NO_DETECTADO si no hay rastros del cliente; NO_INSTALADO si el
        cliente está pero no tiene la entrada de Zonda; DESACTUALIZADO si la
        entrada difiere de la actual; INSTALADO si coincide; ILEGIBLE si el
        archivo existe pero no se puede leer como JSON (por ejemplo con
        comentarios).
    """
    if cliente.archivo_config is None:
        return EstadoCliente.NO_DISPONIBLE
    instalado = cliente.archivo_config.exists() or any(
        marcador.exists() for marcador in cliente.marcadores
    )
    if not instalado:
        return EstadoCliente.NO_DETECTADO
    try:
        entrada = _leer(cliente.archivo_config).get(cliente.raiz, {}).get(CLIENTE_ZONDA)
    except ErrorConfiguracionMCP:
        return EstadoCliente.ILEGIBLE
    if entrada is None:
        return EstadoCliente.NO_INSTALADO
    return (
        EstadoCliente.INSTALADO
        if entrada == entrada_servidor(cliente.raiz)
        else EstadoCliente.DESACTUALIZADO
    )


def instalar(cliente: Cliente) -> None:
    """Agrega o actualiza la entrada de Zonda en la configuración de un cliente.

    Args:
        cliente: El cliente en el que instalar.

    Raises:
        ErrorConfiguracionMCP: Cuando el cliente no está disponible en la
            plataforma o su configuración no se puede leer.
    """
    archivo = cliente.archivo_config
    if archivo is None:
        raise ErrorConfiguracionMCP(
            f"{cliente.nombre} no está disponible en esta plataforma."
        )
    datos = _leer(archivo)
    datos.setdefault(cliente.raiz, {})[CLIENTE_ZONDA] = entrada_servidor(cliente.raiz)
    _escribir(archivo, datos)


def desinstalar(cliente: Cliente) -> None:
    """Quita la entrada de Zonda de la configuración de un cliente.

    Args:
        cliente: El cliente del que desinstalar.

    Raises:
        ErrorConfiguracionMCP: Cuando el cliente no está disponible en la
            plataforma.
    """
    archivo = cliente.archivo_config
    if archivo is None:
        raise ErrorConfiguracionMCP(
            f"{cliente.nombre} no está disponible en esta plataforma."
        )
    datos = _leer(archivo)
    servidores = datos.get(cliente.raiz, {})
    if CLIENTE_ZONDA not in servidores:
        return
    del servidores[CLIENTE_ZONDA]
    _escribir(archivo, datos)
