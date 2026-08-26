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

"""Smoke tests del renderizado de reportes (Jinja2 + pandoc)."""

import shutil

import pytest

from zonda.enums import Unidad
from zonda.reportes import Reporte, env, render_plantilla

UNIDADES = {"fuerza": Unidad.KN, "presion": Unidad.N}

necesita_pandoc = pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc no está instalado"
)


def test_las_plantillas_se_encuentran():
    """El loader de Jinja debe resolver las plantillas del paquete."""
    plantillas = set(env.list_templates())
    assert {
        "base.md",
        "macros.md",
        "edificio.md",
        "cartel.md",
        "cubierta-aislada.md",
    } <= plantillas


def test_reporte_edificio(edificio):
    reporte = Reporte("edificio.md", edificio, UNIDADES)
    assert reporte._texto_md.strip()


def test_reporte_cartel(cartel):
    reporte = Reporte("cartel.md", cartel, UNIDADES)
    assert reporte._texto_md.strip()


def test_reporte_cubierta_aislada(cubierta_aislada):
    reporte = Reporte("cubierta-aislada.md", cubierta_aislada, UNIDADES)
    assert reporte._texto_md.strip()


def test_el_reporte_no_deja_marcas_de_jinja_sin_renderizar(cartel):
    reporte = Reporte("cartel.md", cartel, UNIDADES)
    assert "{{" not in reporte._texto_md
    assert "{%" not in reporte._texto_md


def test_render_plantilla_de_plantilla_inexistente():
    from jinja2.exceptions import TemplateNotFound

    with pytest.raises(TemplateNotFound):
        render_plantilla("no-existe.md")


@necesita_pandoc
def test_exportar_html_incluye_el_css_del_paquete(cartel):
    html = Reporte("cartel.md", cartel, UNIDADES).exportar("html")
    assert "<html" in html.lower()
