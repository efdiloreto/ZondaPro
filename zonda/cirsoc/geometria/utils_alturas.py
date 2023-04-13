import math
from typing import Optional, Sequence

import numpy as np


def array_alturas(
    altura_inferior: float,
    altura_superior: float,
    alturas_personalizadas: Optional[Sequence[float]] = None,
    *otras_alturas: float
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
