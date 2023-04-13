from __future__ import annotations

from functools import cached_property
from typing import Optional, Sequence, TYPE_CHECKING, Tuple

from zonda.cirsoc.geometria.utils_alturas import array_alturas

if TYPE_CHECKING:
    import numpy as np


class Cartel:
    """Cartel

    Genera la geometria de un cartel un cartel.
    """

    def __init__(
        self,
        profundidad: float,
        ancho: float,
        altura_inferior: float,
        altura_superior: float,
        alturas_personalizadas: Optional[Sequence[float]] = None,
    ) -> None:
        """
        Args:
            profundidad: La profundidad del cartel.
            ancho: El ancho del cartel.
            altura_inferior: La altura desde el suelo desde donde se consideran las presiones del viento sobre el cartel.
            altura_superior: La altura superior del cartel.
            alturas_personalizadas: Las alturas sobre las que se calcularán las presiones de viento.
        """
        self.profundidad = profundidad
        self.ancho = ancho
        self.altura_inferior = altura_inferior
        self.altura_superior = altura_superior
        self.alturas_personalizadas = alturas_personalizadas

    @cached_property
    def altura_neta(self) -> float:
        """Calcula la altura de la superficie del cartel donde pega el viento.

        Returns:
            La altura neta.
        """
        return self.altura_superior - self.altura_inferior

    @cached_property
    def area(self) -> float:
        """Calcula el area del cartel.

        Returns:
            El area del cartel.
        """
        return self.ancho * self.altura_neta

    @cached_property
    def altura_media(self) -> float:
        """Calcula la altura media del cartel.

        Returns:
            La altura media.
        """
        return (self.altura_inferior + self.altura_superior) / 2

    @cached_property
    def alturas(self) -> np.ndarray:
        """Crea un array de alturas desde elevacion a altura_superior.

        Returns:
            Un array de alturas.
        """
        return array_alturas(
            self.altura_inferior, self.altura_superior, self.alturas_personalizadas
        )

    @cached_property
    def areas_parciales(self) -> Tuple[float, ...]:
        """Calcula para cada altura, el area que existe entre la altura y la altura superior consecutiva.

        Returns:
            Las areas parciales del cartel.
        """
        return tuple(
            self.ancho * (area_sup - area_inf)
            for area_inf, area_sup in zip(self.alturas, self.alturas[1:])
        )
