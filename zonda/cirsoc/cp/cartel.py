from functools import cached_property

import numpy as np

from zonda.cirsoc import geometria


class Cartel:
    """Cartel.

    Determina los coeficientes de de fuerza para un cartel.
    """

    def __init__(
        self,
        altura_inferior: float,
        altura_neta: float,
        ancho: float,
        es_parapeto: bool = False,
    ) -> None:
        """

        Args:
            altura_inferior: La altura inferior desde la cual se calculan las presiones.
            altura_neta: La altura de la superficie del cartel donde pega el viento. La altura superior del cartel va a
                estar dada por la suma de la altura inferior y la altura neta.
            ancho: El ancho del cartel.
            es_parapeto: Si es True, se considera que el cartel actua como parapeto de edificio.
        """
        self.altura_inferior = altura_inferior
        self.altura_neta = altura_neta
        self.ancho = ancho
        self.es_parapeto = es_parapeto

    def sobre_nivel_terreno(self) -> bool:
        """Determina si el cartel esta sobre o a nivel del terreno.

        Returns:
            False si es parapeto o si la altura inferior es menor que 25% de la altura neta.
        """
        if self.altura_inferior < 0.25 * self.altura_neta or self.es_parapeto:
            return False
        return True

    @cached_property
    def cf(self) -> float:
        """Calcula el factor coeficiente de fuerza para un cartel.

        Returns:
            El coeficiente de fuerza.
        """
        if self.sobre_nivel_terreno():
            return self._sobre_nivel_terreno()
        return self._a_nivel_terreno()

    def _sobre_nivel_terreno(self) -> float:
        """Calcula el factor coeficiente de fuerza para un cartel sobre nivel de terreno.

        Returns:
            El coeficiente de fuerza.
        """
        m_n = (6, 10, 16, 20, 40, 60, 80)
        cfs = (1.2, 1.3, 1.4, 1.5, 1.75, 1.85, 2)
        m = max(self.altura_neta, self.ancho)
        n = min(self.altura_neta, self.ancho)
        return np.interp(m / n, m_n, cfs)

    def _a_nivel_terreno(self) -> float:
        """Calcula el factor coeficiente de fuerza para un cartel a nivel de terreno.

        Returns:
            El coeficiente de fuerza.
        """
        m_n = (3, 5, 8, 10, 20, 30, 40)
        cfs = (1.2, 1.3, 1.4, 1.5, 1.75, 1.85, 2)
        return np.interp(self.altura_neta / self.ancho, m_n, cfs)

    @classmethod
    def desde_cartel(cls, cartel: geometria.Cartel, es_parapeto: bool = False):
        """Crea una instancia desde la geometria de un cratel

        Args:
            cartel: La geometria de un cartel.
            es_parapeto: Si es True, se considera que el cartel actua como parapeto de edificio.
        """
        return cls(
            cartel.altura_inferior, cartel.altura_neta, cartel.ancho, es_parapeto
        )

    def __call__(self) -> float:
        return self.cf
