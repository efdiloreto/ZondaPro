from __future__ import annotations

import os
from collections import abc
from typing import Union, TYPE_CHECKING, Dict, Optional

import pypandoc
from PyQt5.QtCore import QDir, QDirIterator, QFile, QFileInfo, QIODevice
from jinja2 import Environment
from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import BaseLoader, split_template_path

from zondapro import enums
from zondapro.sistema import guardar_archivo_temporal
from zondapro.unidades import convertir_unidad

if TYPE_CHECKING:
    from zondapro.cirsoc import Edificio, Cartel, CubiertaAislada
    from zondapro.enums import Unidad


class QFileSystemLoader(BaseLoader):
    def __init__(self, searchpath, encoding="utf-8", followlinks=False):
        if not isinstance(searchpath, abc.Iterable) or isinstance(searchpath, str):
            searchpath = [searchpath]

        self.searchpath = list(searchpath)
        self.encoding = encoding
        self.followlinks = followlinks

    def get_source(self, environment, template):
        pieces = split_template_path(template)
        for searchpath in self.searchpath:
            filename = os.path.join(searchpath, *pieces)

            f = QFile(filename)
            if not f.exists():
                continue
            if not f.open(QIODevice.ReadOnly):
                continue
            contents = f.readAll().data().decode(self.encoding)
            f.close()

            dt = QFileInfo(f).fileTime(QFile.FileModificationTime)

            def uptodate():
                return QFileInfo(filename).fileTime(QFile.FileModificationTime) == dt

            return contents, filename, uptodate
        raise TemplateNotFound(template)

    def list_templates(self):
        found = set()
        for searchpath in self.searchpath:
            d = QDir(searchpath)
            it_flag = QDirIterator.Subdirectories
            if self.followlinks:
                it_flag |= QDirIterator.FollowSymlinks
            it_filter = QDir.Files | QDir.NoDotAndDotDot | QDir.Hidden | QDir.Readable
            if not self.followlinks:
                it_filter |= QDir.NoSymLinks
            it = QDirIterator(searchpath, it_filter, it_flag)
            while it.hasNext():
                it.next()
                found.add(d.relativeFilePath(it.filePath()))
        return sorted(found)


qloader = QFileSystemLoader(":/plantillas/")
env = Environment(loader=qloader)
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
        self, plantilla: str, estructura: Union[Edificio, Cartel, CubiertaAislada], unidades: Dict[str, Unidad]
    ) -> None:
        """

        Args:
            plantilla: La plantilla a utilizar.
            estructura: La estructura de donde se renderizan los resultados.
            unidades: Las unidades en la que se muestran los resultados
        """
        self._texto_md = render_plantilla(plantilla, estructura=estructura, unidades=unidades)

    def exportar(
        self,
        formato: str,
        nombre_archivo: Optional[str] = None,
        css: str = "",
        referencia_doc: str = "",
        papel: Optional[Dict[str, Union[str, float]]] = None,
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
        css = css or QFile(":/css/github-pandoc.css")
        extra_args = ["-s"]
        if formato in ("docx", "odt") and referencia_doc:
            extra_args.append(f"--reference-doc={referencia_doc}")
        elif formato == "html":
            if isinstance(css, QFile):
                if css.open(QIODevice.ReadOnly):
                    ruta_css = guardar_archivo_temporal(css.readAll().data().decode("utf-8"), ".css")
            else:
                ruta_css = css
            extra_args.append(f"--include-in-header={ruta_css}")
        elif formato == "pdf" and papel is not None:
            for propiedad, valor in papel.items():
                extra_args.append(f"--variable=geometry:{propiedad}={valor}mm")
        return pypandoc.convert_text(self._texto_md, formato, "md", outputfile=nombre_archivo, extra_args=extra_args)
