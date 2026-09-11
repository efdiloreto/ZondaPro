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

"""El servidor MCP de Zonda.

Expone el cálculo del CIRSOC 102-2025 como herramientas MCP por stdio, para
que un cliente con LLM calcule presiones y lea las coordenadas de las zonas
sin abrir la interfaz. Se corre con ``uv run zonda-mcp`` (o
``python -m zonda.mcp``) y se registra en el cliente con el diálogo
``DialogoInstalarMCP`` o a mano; ver el README del proyecto.
"""

from __future__ import annotations

from fastmcp import FastMCP

from zonda.mcp import herramientas

mcp = FastMCP(
    "Zonda",
    instructions=(
        "Zonda calcula cargas de viento según el Reglamento CIRSOC 102-2025 "
        "(Argentina). Use las herramientas para calcular presiones y fuerzas "
        "de una tipología y leer las coordenadas de cada zona de presión: "
        "cada fila de resultado comparte claves con la zona que la produce, "
        "así que puede cruzar presión, área y geometría sin ambigüedad. Las "
        "unidades están en la respuesta, junto con la descripción del "
        "sistema de coordenadas. Los componentes y revestimientos de una "
        "tipología pueden no aparecer cuando el Reglamento no da "
        "lineamientos para la geometría: la respuesta lo indica en "
        "``error_componentes``."
    ),
)

mcp.tool(herramientas.calcular_edificio)
mcp.tool(herramientas.calcular_cartel)
mcp.tool(herramientas.calcular_cubierta_aislada)


def principal() -> None:
    """Corre el servidor MCP por stdio."""
    mcp.run()


if __name__ == "__main__":
    principal()
