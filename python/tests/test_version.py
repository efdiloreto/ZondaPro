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

"""Que la version no quede escrita distinta en dos lugares.

``__version__`` en ``zonda/__acercade__.py`` es la fuente de verdad. El
empaquetado la lee de ahi (``empaquetado/version.py``), ``pyproject.toml`` la
declara dinamica, y el ``.rc`` de Windows y el ``Info.plist`` de macOS se
generan al compilar.

El metainfo del Flatpak es el unico que sigue a mano, porque cada entrada lleva
un changelog escrito por una persona. Este test es lo que hace que no se olvide.
"""

import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from zonda import __acercade__

RAIZ = Path(__file__).resolve().parent.parent.parent
METAINFO = RAIZ / "empaquetado" / "linux" / "io.github.efdiloreto.ZondaPro.metainfo.xml"
PYPROJECT = RAIZ / "python" / "pyproject.toml"


# No se compara contra importlib.metadata.version("zonda"): un install editable
# congela la version en su metadata al instalarse y uv sync no la regenera, asi
# que despues de subir __version__ ese test fallaria hasta correr
# "uv sync --reinstall-package zonda". Seria rojo por el entorno y no por el
# codigo, que es la clase de test que enseña a ignorar el rojo. La garantia real
# la da el test de abajo: si la version es dinamica, no puede divergir.


def test_pyproject_no_fija_la_version_a_mano():
    datos = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "version" not in datos["project"]
    assert "version" in datos["project"]["dynamic"]


def test_el_metainfo_declara_la_version_actual():
    """El changelog del Flatpak tiene que mencionar la version que se publica."""
    componente = ET.parse(METAINFO).getroot()
    versiones = [
        release.get("version")
        for release in componente.iterfind("releases/release")
        if release.get("version")
    ]

    assert __acercade__.__version__ in versiones, (
        f'Falta la entrada <release version="{__acercade__.__version__}"> en '
        f"{METAINFO.name}. Agregala con el changelog de la version."
    )
