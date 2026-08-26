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

from __future__ import annotations

from typing import TYPE_CHECKING

import pypandoc
from jinja2 import Environment, FileSystemLoader

from zonda import enums, recursos
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel, CubiertaAislada, Edificio
    from zonda.enums import Unidad


# Antes las plantillas se leían del sistema de recursos de Qt mediante un loader
# propio; ahora viven en el sistema de archivos y alcanza con el loader estándar
# de Jinja.
env = Environment(loader=FileSystemLoader(recursos.directorio("plantillas")))
env.globals.update(zip=zip, all=all, enums=enums)
env.filters["convertir_unidad"] = convertir_unidad


def render_plantilla(plantilla: str, **kwargs) -> str:
    """Renderiza una plantilla a string.

    Args:
        plantilla: La plantilla a renderizar.
        **kwargs: Los argumentos que se le pasa a la plantilla.

    Returns: La plantilla renderizada en string.

    """
    plantilla_ = env.get_template(plantilla)
    return plantilla_.render(**kwargs)


class Reporte:
    """Reporte

    Renderiza una plantilla a Markdown y se utiliza para diferentes conversiones de formatos.
    """

    def __init__(
        self,
        plantilla: str,
        estructura: Edificio | Cartel | CubiertaAislada,
        unidades: dict[str, Unidad],
    ) -> None:
        """

        Args:
            plantilla: La plantilla a utilizar.
            estructura: La estructura de donde se renderizan los resultados.
            unidades: Las unidades en la que se muestran los resultados
        """
        self._texto_md = render_plantilla(
            plantilla, estructura=estructura, unidades=unidades
        )

    def exportar(
        self,
        formato: str,
        nombre_archivo: str | None = None,
        css: str = "",
        referencia_doc: str = "",
        papel: dict[str, str | float] | None = None,
    ) -> str:
        """

        Args:
            formato: El formato a exportar.
            nombre_archivo: El nombre del archivo a exportar
            css: El archivo de estilo para el html.
            referencia_doc: El archivo de referencia para .docx o .odt
            papel: Parámetros de configuración del papel.

        Returns:

        """
        extra_args = ["-s"]
        if formato in ("docx", "odt") and referencia_doc:
            extra_args.append(f"--reference-doc={referencia_doc}")
        elif formato == "html":
            ruta_css = css or recursos.ruta("css/github-pandoc.css")
            extra_args.append(f"--include-in-header={ruta_css}")
        elif formato == "pdf" and papel is not None:
            for propiedad, valor in papel.items():
                extra_args.append(f"--variable=geometry:{propiedad}={valor}mm")
        return pypandoc.convert_text(
            self._texto_md,
            formato,
            "md",
            outputfile=nombre_archivo,
            extra_args=extra_args,
        )
