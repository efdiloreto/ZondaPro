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

"""Cómo se decide si hay que avisar de una versión nueva.

Nada de acá sale a internet: se prueba la lectura de la respuesta de GitHub, no
la consulta. Lo que importa es que Zonda avise cuando corresponde y, sobre todo,
que se quede callado cuando no.
"""

import pytest

from zonda import __acercade__, actualizaciones


@pytest.fixture(autouse=True)
def settings_limpios(monkeypatch):
    """Aísla los tests de la versión que el usuario real haya elegido ignorar."""
    monkeypatch.setattr(actualizaciones, "version_ignorada", lambda: "")


def respuesta(tag: str) -> dict:
    """Una respuesta de la API como la que devuelve GitHub."""
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/efdiloreto/ZondaPro/releases/tag/{tag}",
    }


@pytest.mark.parametrize(
    ("tag", "esperado"),
    [
        ("v1.0.1", "1.0.1"),
        ("1.0.1", "1.0.1"),
        ("v2.0", "2.0"),
        ("", None),
        ("v", None),
        ("ultima", None),
        ("vNext", None),
    ],
)
def test_version_de_tag(tag, esperado):
    """El tag que publica el empaquetado lleva una ``v`` que no es del número."""
    version = actualizaciones.version_de_tag(tag)
    assert (None if version is None else str(version)) == esperado


def test_avisa_cuando_la_publicada_es_mas_nueva(monkeypatch):
    monkeypatch.setattr(__acercade__, "__version__", "1.0.0")

    actualizacion = actualizaciones.leer_respuesta(respuesta("v1.0.1"))

    assert actualizacion is not None
    assert actualizacion.version == "1.0.1"
    assert actualizacion.url.endswith("v1.0.1")


def test_no_avisa_cuando_es_la_misma_version(monkeypatch):
    monkeypatch.setattr(__acercade__, "__version__", "1.0.0")

    assert actualizaciones.leer_respuesta(respuesta("v1.0.0")) is None


def test_no_avisa_cuando_la_instalada_es_mas_nueva(monkeypatch):
    """Pasa al correr desde el código fuente con una versión sin publicar."""
    monkeypatch.setattr(__acercade__, "__version__", "1.1.0")

    assert actualizaciones.leer_respuesta(respuesta("v1.0.0")) is None


def test_compara_por_numero_y_no_como_texto(monkeypatch):
    """Como texto, "1.10.0" es menor que "1.9.0"; como versión, no."""
    monkeypatch.setattr(__acercade__, "__version__", "1.9.0")

    actualizacion = actualizaciones.leer_respuesta(respuesta("v1.10.0"))

    assert actualizacion is not None
    assert actualizacion.version == "1.10.0"


def test_no_avisa_de_la_version_que_el_usuario_silencio(monkeypatch):
    monkeypatch.setattr(__acercade__, "__version__", "1.0.0")
    monkeypatch.setattr(actualizaciones, "version_ignorada", lambda: "1.0.1")

    assert actualizaciones.leer_respuesta(respuesta("v1.0.1")) is None
    # Silenciar una versión no silencia las que vengan después.
    assert actualizaciones.leer_respuesta(respuesta("v1.0.2")) is not None


@pytest.mark.parametrize(
    "datos",
    [
        None,
        [],
        "",
        {},
        {"tag_name": None},
        # Lo que contesta GitHub mientras no haya ninguna release publicada.
        {"message": "Not Found", "status": "404"},
    ],
)
def test_una_respuesta_inesperada_no_avisa_nada(datos):
    """Ante cualquier cosa rara, callarse: el aviso es opcional, romper no."""
    assert actualizaciones.leer_respuesta(datos) is None


def test_la_url_de_la_api_sale_del_repositorio_del_proyecto():
    assert (
        actualizaciones.url_api()
        == "https://api.github.com/repos/efdiloreto/ZondaPro/releases/latest"
    )
