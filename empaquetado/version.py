# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
#
# This file is part of Zonda.
#
# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

"""Módulo para obtener la versión oficial de Zonda desde una única fuente de verdad."""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ACERCADE_PY = RAIZ / "python" / "zonda" / "__acercade__.py"


def obtener_version() -> str:
    """Extrae la versión actual de __acercade__.py."""
    if not ACERCADE_PY.exists():
        return "1.0.0"

    contenido = ACERCADE_PY.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', contenido)
    if match:
        return match.group(1)
    return "1.0.0"


if __name__ == "__main__":
    print(obtener_version())
