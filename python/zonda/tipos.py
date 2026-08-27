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

"""Tipos básicos que utiliza ZONDA para type hints.

Los resultados del cálculo se describen en `zonda.cirsoc.resultados`; acá sólo
quedan los alias geométricos y numéricos que se usan en todo el programa.
"""

ParNumerico = tuple[float, float]

Punto = tuple[float, float, float]

Punto2D = ParNumerico
