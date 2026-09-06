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

from __future__ import annotations

from typing import TYPE_CHECKING

from zonda.enums import PosicionCamara
from zonda.graficos.actores import actores_poligonos, cilindro
from zonda.graficos.directores.utils_geometria import (
    coords_pared_rectangular,
    coords_zona_cubierta,
)

if TYPE_CHECKING:
    from zonda.cirsoc import Cartel
    from zonda.graficos.colores import TablaColores
    from zonda.graficos.escena import Camara, Escena3D


class Geometria:
    """Geometria.
    Representa la geometria de un cartel. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        escena: Escena3D,
        ancho: float,
        profundidad: float,
        altura_inferior: float,
        altura_superior: float,
    ) -> None:
        """
        Args:
            escena: La escena que junta los actores.
            profundidad: La profundidad del cartel.
            ancho: El ancho del cartel.
            altura_inferior: La altura desde el suelo desde donde se consideran las presiones del viento sobre el cartel.
            altura_superior: La altura superior del cartel.
        """
        self.actores_cubierta = None

        self.escena = escena
        self.ancho = ancho
        # Se pasa a negativo para que la estructura crezca hacia atras.
        self.profundidad = -profundidad
        self.altura_inferior = altura_inferior
        self.altura_superior = altura_superior

    @actores_poligonos(color="LightCoral", mostrar=True)
    def caras(self):
        """Genera los actores para todas las caras del cartel, excepto la cara que recibe la presión del viento.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        superior = coords_zona_cubierta(
            (0, self.altura_superior),
            (self.ancho, self.altura_superior),
            0,
            self.profundidad,
            dist_eucl=True,
        )
        inferior = coords_zona_cubierta(
            (0, self.altura_inferior),
            (self.ancho, self.altura_inferior),
            0,
            self.profundidad,
            dist_eucl=True,
        )
        lateral_izq = coords_pared_rectangular(
            self.profundidad,
            self.altura_superior,
            self.altura_superior,
            z0=0,
            elevacion=self.altura_inferior,
            sobre_eje_z=True,
        )
        lateral_der = coords_pared_rectangular(
            self.profundidad,
            self.altura_superior,
            self.altura_superior,
            z0=self.ancho,
            elevacion=self.altura_inferior,
            sobre_eje_z=True,
        )
        sotavento = coords_pared_rectangular(
            self.ancho,
            self.altura_superior,
            self.altura_superior,
            z0=self.profundidad,
            elevacion=self.altura_inferior,
            invertir_sentido=False,
        )

        return lateral_der, lateral_izq, superior, inferior, sotavento

    @actores_poligonos(color="LightCoral", mostrar=True)
    def cara_barlovento(self):
        """Genera el actor para la cara que recibe presion de viento.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_pared_rectangular(
            self.ancho,
            self.altura_superior,
            self.altura_superior,
            z0=0,
            elevacion=self.altura_inferior,
            invertir_sentido=True,
        )

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.escena.limpiar()
        self.caras()
        self.cara_barlovento()
        self._crear_soportes()

    def setear_posicion_camara(self, camara: Camara, posicion: PosicionCamara) -> None:
        """Setea la posición de la camara.
        Args:
            camara: La camara a la que se le setea la vista.
            posicion: La posición a setear.
        """
        camara.setear_punto_focal(self.ancho / 2, 0, self.profundidad / 2)
        posiciones = {
            PosicionCamara.SUPERIOR: (
                self.ancho / 2,
                self.altura_superior,
                self.profundidad / 2,
            ),
            PosicionCamara.PERSPECTIVA: (self.ancho, self.altura_superior, 0),
            PosicionCamara.IZQUIERDA: (0, 0, self.profundidad / 2),
            PosicionCamara.DERECHA: (self.ancho, 0, self.profundidad / 2),
            PosicionCamara.FRENTE: (self.ancho / 2, 0, 0),
            PosicionCamara.CONTRAFRENTE: (self.ancho / 2, 0, self.profundidad),
        }
        camara.setear_posicion(*posiciones[posicion])

        vector_altura = (1, 0, 0) if posicion == PosicionCamara.SUPERIOR else (0, 1, 0)
        camara.setear_vector_altura(*vector_altura)
        self.escena.encuadrar()

    def _crear_soportes(self):
        if self.altura_inferior > 0:
            radio = min(self.ancho, abs(self.profundidad)) / 4
            cilindro(
                self.escena,
                radio,
                self.altura_inferior,
                (self.ancho / 2, self.profundidad / 2),
            )


class Presiones(Geometria):
    """Presiones.

    Representa las presiones para un cartel. Inicializa los actores, setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        escena: Escena3D,
        tabla_colores: TablaColores,
        cartel: Cartel,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            tabla_colores: La tabla de escalas de colores de la escena general.
            cartel: Una instancia de Cartel.
        """
        super().__init__(
            escena,
            cartel.ancho,
            cartel.profundidad,
            cartel.altura_inferior,
            cartel.altura_superior,
        )
        self.cartel = cartel
        self.tabla_colores = tabla_colores

        self.inicializar_actores()

    def obtener_actores(self):
        # Se genera al inicializar la función cara_barlovento
        return self.actores_cara_barlovento

    def obtener_regiones(self):
        # Se genera al inicializar la función regiones_caso_c
        return self.actores_regiones_caso_c

    @actores_poligonos(crear_atributo=False, presion=False, mostrar=True)
    def caras(self):
        return super().caras.__wrapped__(self)

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=True)
    def cara_barlovento(self):
        return super().cara_barlovento.__wrapped__(self)

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def regiones_caso_c(self):
        """Genera un actor por cada región del Caso C de la Figura 4.4-1.

        Son franjas verticales de la cara a barlovento, medidas desde el borde
        de barlovento según los límites que expone el cálculo. Se crean ocultos:
        los muestra la escena cuando se selecciona el Caso C.

        Returns:
            Las coordenadas de cada región, indexadas por región.
        """
        return {
            region: coords_pared_rectangular(
                fin - inicio,
                self.altura_superior,
                self.altura_superior,
                x0=inicio,
                elevacion=self.altura_inferior,
                invertir_sentido=True,
            )
            for region, (inicio, fin) in self.cartel.cf.limites_regiones.items()
        }

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.caras()
        self.cara_barlovento()
        self.regiones_caso_c()
        self._crear_soportes()
