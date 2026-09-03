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

"""Smoke tests del renderizado de reportes (Jinja2 + pandoc)."""

import shutil

import pytest

from zonda import enums
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


def test_reporte_edificio_angulo_menor_diez_muestra_el_caso_positivo(
    edificio_angulo_pequeno,
):
    """El reporte lista el caso de presión positiva de la cubierta < 10°."""
    texto = Reporte("edificio.md", edificio_angulo_pequeno, UNIDADES)._texto_md
    assert "PRESIÓN POSITIVA" in texto


def test_reporte_edificio_con_parapeto_distingue_el_positivo_por_zona(
    edificio_con_parapeto,
):
    """Con parapeto, las Zonas 2 y 3 llevan dos filas y hay que diferenciarlas.

    La Nota 5 de la Figura 5.3-2A les da un positivo propio, así que la tabla
    de la zona deja de tener una sola fila.
    """
    texto = Reporte("edificio.md", edificio_con_parapeto, UNIDADES)._texto_md
    assert "2 (positiva)" in texto
    assert "3 (positiva)" in texto


def test_reporte_edificio_gran_altura_resuelve_las_paredes_por_altura():
    """Con h > 20 m la Figura 5.4-1 evalúa las paredes con qz a cada altura
    (Nota 4), tanto las positivas como las negativas.

    Las Zonas 4, 5 y "todas" de pared viajan con varias alturas y entran al
    bloque por altura del reporte; la cubierta queda con un valor único qh.
    """
    from zonda.cirsoc import Edificio

    edificio = Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=22,
        altura_cumbrera=23,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        componentes_paredes={"Viga": 10.0},
        componentes_cubierta={"Correa": 5.0},
    )
    texto = Reporte("edificio.md", edificio, UNIDADES)._texto_md
    assert "Figura 5.4-1" in texto
    assert "q~z~" in texto
    assert "Viga" in texto


def test_reporte_cartel(cartel):
    reporte = Reporte("cartel.md", cartel, UNIDADES)
    assert reporte._texto_md.strip()


def test_reporte_cartel_con_topografia(cartel_con_topografia):
    """El reporte tiene que poder mostrar los datos de topografía del cartel.

    Las tres fixtures originales usaban ``considerar_topografia=False``, así que
    esta rama de la plantilla nunca se renderizaba y el reporte fallaba con
    ``UndefinedError``: ``Cartel.__init__`` anotaba ``distancia_cresta``,
    ``distancia_barlovento_sotavento`` y ``direccion`` en lugar de asignarlas.
    """
    texto = Reporte("cartel.md", cartel_con_topografia, UNIDADES)._texto_md
    assert "Topografía no considerada" not in texto
    assert "Distancia a la cresta: 50.00 m" in texto
    assert "Distancia a Barlovento: 20.00 m" in texto


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
