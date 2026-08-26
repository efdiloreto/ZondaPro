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

import math
from collections.abc import Sequence

import numpy as np


def array_alturas(
    altura_inferior: float,
    altura_superior: float,
    alturas_personalizadas: Sequence[float] | None = None,
    *otras_alturas: float,
) -> np.ndarray:
    """Crea un array de alturas desde altura inferior a altura superior.

    Args:
        altura_inferior: La altura inferior desde donde comenzará el array.
        altura_superior: La altura inferior desde donde comenzará el array.
        alturas_personalizadas: Una secuencia de alturas personalizadas desde las que se creará el array. Si no se especifica
        este parámetro, se calculan las alturas con un paso de 1 metro.
        *otras_alturas: Alturas extras que se agregarán al array.

    Returns:
        Un array de alturas.
    """

    if alturas_personalizadas is not None:
        alturas = [
            altura
            for altura in alturas_personalizadas
            if altura_inferior <= altura <= altura_superior
        ]
    else:
        alturas = list(range(math.ceil(altura_inferior), math.ceil(altura_superior), 1))
    # Se añaden valores representativos en el array si no se encuentran.
    alturas_caracteristicas = (altura_inferior, altura_superior, *otras_alturas)
    for altura in alturas_caracteristicas:
        if altura not in alturas:
            alturas.append(altura)
    alturas.sort()
    return np.array(alturas)
