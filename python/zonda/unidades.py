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

from zonda.enums import Unidad


def convertir_unidad(valor: float, unidad: Unidad) -> float:
    """Convierte un valor de N a la unidad especificada.

    Args:
        valor: El valor a convertir en Newtons.
        unidad: La unidad a la que se convierte.

    Returns:

    """
    if unidad == Unidad.N:
        return valor
    if unidad == Unidad.KN:
        return valor * 0.001
    if unidad == Unidad.KG:
        return valor * 0.1019716213
