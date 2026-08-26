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

"""Verifica el sistema de recursos que reemplazó al módulo generado por pyrcc5."""

import pytest

from zonda import recursos


def test_todos_los_alias_del_manifiesto_existen():
    """Cada alias declarado en recursos.qrc debe apuntar a un archivo real."""
    faltantes = [
        clave for clave in recursos._alias() if not recursos.ruta(clave).is_file()
    ]
    assert faltantes == []


def test_el_manifiesto_no_esta_vacio():
    assert len(recursos._alias()) > 0


@pytest.mark.parametrize(
    "clave",
    [
        "iconos/zonda.ico",
        "qss/zonda.qss",
        "css/github-pandoc.css",
        "fuentes/Oswald-VariableFont_wght.ttf",
        "plantillas/base.md",
    ],
)
def test_recursos_clave_disponibles(clave):
    """Los recursos que carga el arranque de la aplicación."""
    assert recursos.ruta(clave).is_file()


def test_se_acepta_el_prefijo_qt_historico():
    """Las claves con el prefijo ':/' de Qt siguen resolviendo igual."""
    assert recursos.ruta(":/iconos/zonda.ico") == recursos.ruta("iconos/zonda.ico")


def test_recurso_inexistente_falla_con_mensaje_claro():
    with pytest.raises(FileNotFoundError, match="no está declarado"):
        recursos.ruta("iconos/no-existe.png")


def test_leer_texto():
    assert "QPushButton" in recursos.texto("qss/zonda.qss")


def test_directorio_de_plantillas():
    assert recursos.directorio("plantillas").is_dir()


def test_directorio_inexistente_falla():
    with pytest.raises(FileNotFoundError):
        recursos.directorio("no-existe")
