import math
from functools import cached_property

from zonda.enums import TipoCubierta, PosicionBloqueoCubierta


class Cubierta:
    """Cubierta.

    Genera la geometria de una cubierta.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        parapeto: float = 0,
        alero: float = 0,
        altura_bloqueo: float = 0,
        posicion_bloqueo: PosicionBloqueoCubierta = PosicionBloqueoCubierta.ALERO_BAJO,
    ) -> None:
        """
        Args:
            ancho: El ancho de la cubierta.
            longitud: La longitud de la cubierta.
            altura_alero: La altura de alero de la cubierta, medida desde el nivel de suelo.
            altura_cumbrera: La altura de cumbrera de la cubierta, medida desde el nivel de suelo.
            tipo_cubierta: El tipo de cubierta.
            parapeto: La dimensión del parapeto.
            alero: La dimensión del alero.
            altura_bloqueo: La altura de bloqueo. Se utiliza en el caso de cubiertas aisladas. Se necesita cuando se usa
                la cubierta para calcular los coeficientes de presión de cubiertas aisladas.
            posicion_bloqueo: La posicion de bloqueo. Se utiliza en el caso de cubiertas aisladas a un agua.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_alero = altura_alero
        self.tipo_cubierta = tipo_cubierta
        if self.tipo_cubierta == TipoCubierta.PLANA:
            self.altura_cumbrera = altura_alero
        else:
            self.altura_cumbrera = altura_cumbrera
        self.parapeto = parapeto
        self.alero = alero
        self.altura_bloqueo = altura_bloqueo
        self.posicion_bloqueo = posicion_bloqueo

    @cached_property
    def relacion_bloqueo(self) -> float:
        """Calcula la relación de bloqueo de la cubierta.

        Returns:
            La relación de bloqueo. (Valor entre 0 y 1)
        """
        if (
            self.tipo_cubierta == TipoCubierta.PLANA
            or self.posicion_bloqueo == PosicionBloqueoCubierta.ALERO_BAJO
        ):
            altura = self.altura_alero
        else:
            altura = self.altura_cumbrera
        return min(self.altura_bloqueo / altura, 1)

    @cached_property
    def angulo(self) -> float:
        """Calcula el ángulo de la cubierta.

        Returns:
            El ángulo de cubierta.
        """
        pendiente = (self.altura_cumbrera - self.altura_alero) / self.ancho
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            pendiente *= 2
        angulo = math.atan(pendiente)
        return math.degrees(angulo)

    @cached_property
    def area(self) -> float:
        """Calcula el área de la cubierta.

        Returns:
            El area de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.PLANA:
            return self.ancho * self.longitud

        altura = self.altura_cumbrera - self.altura_alero
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            perimetro_frontal = 2 * math.hypot(altura, self.ancho / 2)
        else:
            perimetro_frontal = math.hypot(altura, self.ancho)
        return perimetro_frontal * self.longitud

    @cached_property
    def altura_media(self) -> float:
        """Calcula la altura media de cubierta.

        Returns:
            La altura media de cubierta.
        """
        if self.angulo <= 10:
            return self.altura_alero
        return (self.altura_alero + self.altura_cumbrera) / 2

    @cached_property
    def area_mojinete(self) -> float:
        """Calcula el area de la zona de mojinete de la pared.

        Returns:
            El area de mojinete.
        """
        return self.ancho * (self.altura_cumbrera - self.altura_alero) / 2
