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

"""Contiene clases que selecionan los actores para cada tipo de representación de un edificio (Geometria, Zonas de presiones, etc).
Además proveé métodos para la configuración de la cámara en diferentes posiciones.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    ParedEdificioSprfv,
    PosicionCamara,
    PosicionCubiertaAleroSprfv,
    TipoCubierta,
    ZonaComponenteCubiertaEdificio,
    ZonaComponenteParedEdificio,
)
from zonda.excepciones import ErrorLineamientos
from zonda.graficos.actores import (
    ActorPresion,
    actores_poligonos,
    crear_poligono,
    recortar_poligono,
)
from zonda.graficos.directores.utils_geometria import (
    coords_pared_rectangular,
    coords_zona_cubierta,
    coords_zona_cubierta_desde_proyeccion,
    proyeccion_punto_horizontal_sobre_cubierta,
    punto_sobre_vector,
)
from zonda.graficos.directores.utils_iter import aplicar_func_recursivamente

if TYPE_CHECKING:
    from zonda.cirsoc import Edificio
    from zonda.graficos.colores import TablaColores
    from zonda.graficos.escena import Camara, Escena3D

# Ancho mínimo de un rectángulo de zona, para descartar los degenerados.
TOLERANCIA = 1e-9


def _rango(
    opuesto: bool, inicio: float, fin: float, total: float
) -> tuple[float, float]:
    """Un rango de distancias al borde, espejado si se mide desde el opuesto.

    Args:
        opuesto: Indica si las distancias se miden desde el borde opuesto.
        inicio: La distancia al borde donde empieza el rango.
        fin: La distancia al borde donde termina el rango.
        total: La dimensión total sobre la que se espeja.

    Returns:
        El rango, en coordenadas que crecen desde el origen.
    """
    return (total - fin, total - inicio) if opuesto else (inicio, fin)


class Geometria:
    """Geometria.

    Representa la geometria de un edificio. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        escena: Escena3D,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        alero: float = 0,
        elevacion: float = 0,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            ancho: El ancho del edificio.
            longitud: La longitud del edificio.
            altura_alero: La altura de alero del edificio.
            altura_cumbrera: La altura de cumbrera del edificio.
            tipo_cubierta: El tipo de cubierta.
            alero: La dimensión del alero.
            elevacion: La elevación sobre el suelo.
        """
        self.actores_paredes = None
        self.actores_cubierta = None
        self.actores_alero = None

        self.escena = escena
        self.ancho = ancho
        # Se pasa a negativo para que la estructura crezca hacia atras.
        self.longitud = -longitud
        self.altura_alero = altura_alero
        self.altura_cumbrera = altura_cumbrera
        self.tipo_cubierta = tipo_cubierta
        self.alero_ = alero
        self.elevacion = elevacion

    @actores_poligonos(crear_atributo=True, color="BlanchedAlmond", mostrar=True)
    def paredes(self):
        """Genera los actores de las paredes.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada pared.
        """
        barlovento = self._pared_frente(0, invertir_sentido=True)
        sotavento = self._pared_frente(self.longitud)
        lateral_izq = self._pared_lateral(0, self.altura_alero)
        if self.tipo_cubierta != TipoCubierta.UN_AGUA:
            altura_der = self.altura_alero
        else:
            altura_der = self.altura_cumbrera
        lateral_der = self._pared_lateral(self.ancho, altura_der, invertir_sentido=True)
        return {
            ParedEdificioSprfv.BARLOVENTO: barlovento,
            ParedEdificioSprfv.SOTAVENTO: sotavento,
            ParedEdificioSprfv.LATERAL: (lateral_izq, lateral_der),
        }

    @actores_poligonos(color="LightCoral", mostrar=True)
    def cubierta(self, z_inicio: float, z_fin: float):
        """Genera los actores para la cubierta.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Args:
            z_inicio: El inicio de la cubierta sobre el eje Z.
            z_fin: El fin de la cubierta sobre el eje Z.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.PLANA:
            return self._cubierta_plana(z_inicio, z_fin)
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            return self._cubierta_dos_aguas(z_inicio, z_fin)
        return self._cubierta_un_agua(z_inicio, z_fin)

    @actores_poligonos(color="LightCoral", mostrar=True)
    def alero(self, z_inicio: float, z_fin: float):
        """Genera los actores para el o los aleros.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Args:
            z_inicio: El inicio del alero sobre el eje Z.
            z_fin: El fin del alero sobre el eje Z.

        Returns:
            Las coordenadas el o los aleros.
        """
        dist_alero = -self.alero_
        altura_cumbrera = self.altura_cumbrera
        ancho_cumbrera = self.ancho / 2
        if self.tipo_cubierta == TipoCubierta.PLANA:
            altura_cumbrera = self.altura_alero
        elif self.tipo_cubierta == TipoCubierta.UN_AGUA:
            ancho_cumbrera = self.ancho
        alero_izq = coords_zona_cubierta(
            (0, self.altura_alero),
            (ancho_cumbrera, altura_cumbrera),
            z_inicio,
            z_fin,
            dist_inicio=dist_alero,
            dist_fin=0,
            dist_eucl=False,
        )
        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            return alero_izq
        else:
            alero_der = coords_zona_cubierta(
                (self.ancho, self.altura_alero),
                (self.ancho / 2, altura_cumbrera),
                z_inicio,
                z_fin,
                dist_inicio=dist_alero,
                dist_fin=0,
                dist_eucl=False,
                invertir_sentido=True,
            )
        return {
            PosicionCubiertaAleroSprfv.BARLOVENTO: alero_der,
            PosicionCubiertaAleroSprfv.SOTAVENTO: alero_izq,
        }

    @actores_poligonos(mostrar=True)
    def base(self):
        """Genera el actor para la base del edificio. (Es un poligono que sirve de tapa inferior)

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas de la base.
        """
        return (
            (0, self.elevacion, 0),
            (self.ancho, self.elevacion, 0),
            (self.ancho, self.elevacion, self.longitud),
            (0, self.elevacion, self.longitud),
        )

    def volumen(self) -> float:
        """Calcula el volumen del edificio en m3.

        Returns:
            El volumen del edificio.
        """
        pared = self.actores_paredes[ParedEdificioSprfv.BARLOVENTO]
        return pared.poligono.area() * abs(self.longitud)

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.escena.limpiar()
        self.paredes()
        self.cubierta(0, self.longitud)
        self.base()
        if self.alero_:
            self.alero(0, self.longitud)

    def setear_posicion_camara(self, camara: Camara, posicion: PosicionCamara) -> None:
        """Setea la posición de la camara.

        Args:
            camara: La camara a la que se le setea la vista.
            posicion: La posición a setear.
        """
        camara.setear_punto_focal(self.ancho / 2, 0, self.longitud / 2)
        posiciones = {
            PosicionCamara.SUPERIOR: (
                self.ancho / 2,
                self.altura_alero,
                self.longitud / 2,
            ),
            PosicionCamara.PERSPECTIVA: (self.ancho, self.altura_alero, 0),
            PosicionCamara.IZQUIERDA: (0, 0, self.longitud / 2),
            PosicionCamara.DERECHA: (self.ancho, 0, self.longitud / 2),
            PosicionCamara.FRENTE: (self.ancho / 2, 0, 0),
            PosicionCamara.CONTRAFRENTE: (self.ancho / 2, 0, self.longitud),
        }
        camara.setear_posicion(*posiciones[posicion])

        vector_altura = (1, 0, 0) if posicion == PosicionCamara.SUPERIOR else (0, 1, 0)
        camara.setear_vector_altura(*vector_altura)
        self.escena.encuadrar()

    def _pared_lateral(self, x0: float, altura: float, invertir_sentido: bool = False):
        """Determina las coordenadas de una pared lateral.

        Args:
            x0: La profundidad sobre el eje X en la que se encuentra.
            altura: La altura de la pared
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono apareza de un lado o del otro.

        Returns:
            Las coordenadas de una pared lateral.
        """
        return coords_pared_rectangular(
            self.longitud,
            altura,
            altura,
            z0=x0,
            elevacion=self.elevacion,
            sobre_eje_z=True,
            invertir_sentido=invertir_sentido,
        )

    def _pared_frente(self, z0: float, invertir_sentido: bool = False):
        """Determina las coordenadas de una pared de frente (o contrafrente).

        Args:
            z0: La profundidad sobre el eje Z en la que se encuentra.
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono apareza de un lado o del otro.

        Returns:
            Las coordenadas de una pared de frente.
        """
        if self.tipo_cubierta != TipoCubierta.DOS_AGUAS:
            if self.tipo_cubierta == TipoCubierta.PLANA:
                altura_der = self.altura_alero
            else:
                altura_der = self.altura_cumbrera
            coords = coords_pared_rectangular(
                self.ancho,
                self.altura_alero,
                altura_der,
                z0=z0,
                elevacion=self.elevacion,
                invertir_sentido=invertir_sentido,
            )
        else:
            coord_cumbrera = (self.ancho / 2, self.altura_cumbrera, z0)
            coords = coords_pared_rectangular(
                self.ancho,
                self.altura_alero,
                self.altura_alero,
                0,
                z0=z0,
                elevacion=self.elevacion,
                invertir_sentido=invertir_sentido,
            )
            coords.insert(2, coord_cumbrera)
        return coords

    def _cubierta_dos_aguas(self, z_inicio: float, z_fin: float):
        """Determina las coordenadas para una cubierta a dos aguas.

        Args:
            z_inicio: El inicio de la cubierta sobre el eje Z.
            z_fin: El fin de la cubierta sobre el eje Z.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        faldon_izq = coords_zona_cubierta(
            (0, self.altura_alero),
            (self.ancho / 2, self.altura_cumbrera),
            z_inicio,
            z_fin,
            dist_eucl=True,
        )
        faldon_der = coords_zona_cubierta(
            (self.ancho, self.altura_alero),
            (self.ancho / 2, self.altura_cumbrera),
            z_inicio,
            z_fin,
            dist_eucl=True,
            invertir_sentido=True,
        )
        return {
            PosicionCubiertaAleroSprfv.BARLOVENTO: faldon_der,
            PosicionCubiertaAleroSprfv.SOTAVENTO: faldon_izq,
        }

    def _cubierta_un_agua(self, z_inicio: float, z_fin: float):
        """Determina las coordenadas para una cubierta a un agua.

        Args:
            z_inicio: El inicio de la cubierta sobre el eje Z.
            z_fin: El fin de la cubierta sobre el eje Z.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_zona_cubierta(
            (0, self.altura_alero),
            (self.ancho, self.altura_cumbrera),
            z_inicio,
            z_fin,
            dist_eucl=True,
        )

    def _cubierta_plana(self, z_inicio: float, z_fin: float):
        """Determina las coordenadas para una cubierta plana.

        Args:
            z_inicio: El inicio de la cubierta sobre el eje Z.
            z_fin: El fin de la cubierta sobre el eje Z.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_zona_cubierta(
            (0, self.altura_alero),
            (self.ancho, self.altura_alero),
            z_inicio,
            z_fin,
            dist_eucl=True,
        )


class PresionesSprfvMetodoDireccional(Geometria):
    """PresionesSprfvMetodoDireccional.

    Representa las zonas de presiones para el SPRFV de un edificio. Inicializa los actores, setea las diferentes posiciones
    de la camara y provee los actores correspondientes dependiendo el estado actual de la dirección del viento y otros
    factores.
    """

    def __init__(
        self,
        escena: Escena3D,
        tabla_colores: TablaColores,
        edificio: Edificio,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            tabla_colores: La tabla de escalas de colores de la escena general.
            edificio: Una instancia de edificio.
        """
        self.actores_paredes = None
        self.actores_cubierta = None
        self.actores_alero = None

        altura_alero = edificio.altura_alero
        altura_cumbrera = edificio.altura_cumbrera
        alero = getattr(edificio.geometria.cubierta, "alero", 0)
        super().__init__(
            escena,
            edificio.ancho,
            edificio.longitud,
            altura_alero,
            altura_cumbrera,
            edificio.tipo_cubierta,
            alero=alero,
            elevacion=edificio.elevacion,
        )

        self.tabla_colores = tabla_colores  # Es usada por el decorador.
        self._zonas_cubierta = edificio.cp.cubierta.sprfv.zonas
        self._zonas_cubierta_normal = self._zonas_cubierta[
            DireccionVientoMetodoDireccionalSprfv.NORMAL
        ]
        if self._zonas_cubierta_normal is not None:
            self._zonas_cubierta_invertida_normal = tuple(
                (self.ancho - inicio, self.ancho - fin)
                for inicio, fin in self._zonas_cubierta_normal
            )

        self.direccion = DireccionVientoMetodoDireccionalSprfv.PARALELO

        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            self.posicion_cubierta_un_agua = PosicionCubiertaAleroSprfv.SOTAVENTO

        self.normal_como_paralelo = edificio.cp.cubierta.sprfv.normal_como_paralelo

        self.inicializar_actores()

    def obtener_paredes(
        self,
    ) -> dict[ParedEdificioSprfv, ActorPresion | tuple[ActorPresion, ActorPresion]]:
        """Selecciona los actores de paredes en base al tipo de cubierta y la posición de la misma respecto al viento.

        Returns:
            Los actores seleccionados.
        """
        paredes = self.actores_paredes[self.direccion].copy()
        posicion_cubierta_un_agua = getattr(self, "posicion_cubierta_un_agua", None)
        if (
            posicion_cubierta_un_agua == PosicionCubiertaAleroSprfv.BARLOVENTO
            and self.direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
        ):
            (
                paredes[ParedEdificioSprfv.BARLOVENTO],
                paredes[ParedEdificioSprfv.SOTAVENTO],
            ) = (
                paredes[ParedEdificioSprfv.SOTAVENTO],
                paredes[ParedEdificioSprfv.BARLOVENTO],
            )
        return paredes

    def obtener_cubierta(
        self,
    ) -> (
        tuple[ActorPresion, ...]
        | dict[PosicionCubiertaAleroSprfv, tuple[ActorPresion, ...] | ActorPresion]
        | ActorPresion
    ):
        """Selecciona los actores de cubierta en base al tipo de cubierta y la posición de la misma respecto al viento.

        Returns:
            Los actores seleccionados.
        """
        if (
            self.direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL
            and self.normal_como_paralelo
        ):
            posicion_cubierta = getattr(self, "posicion_cubierta_un_agua", None)
            if posicion_cubierta is not None:
                return self.actores_cubierta[self.direccion][posicion_cubierta]
        return self.actores_cubierta[self.direccion]

    def obtener_alero(
        self,
    ) -> (
        dict[PosicionCubiertaAleroSprfv, tuple[ActorPresion, ...] | ActorPresion]
        | ActorPresion
        | None
    ):
        """Selecciona los actores de alero en base a la posición del viento respecto a la cubierta.

        Returns:
            Los actores seleccionados.
        """
        actores_alero = getattr(self, "actores_alero", None)
        if actores_alero is None:
            return None
        return actores_alero[self.direccion]

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def paredes(self):
        """Genera los actores de las paredes.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada pared.
        """
        paredes_paralelo = super().paredes.__wrapped__(self)

        paredes_normal = {
            ParedEdificioSprfv.LATERAL: (
                paredes_paralelo[ParedEdificioSprfv.BARLOVENTO],
                paredes_paralelo[ParedEdificioSprfv.SOTAVENTO],
            ),
            ParedEdificioSprfv.SOTAVENTO: paredes_paralelo[ParedEdificioSprfv.LATERAL][
                0
            ],
            ParedEdificioSprfv.BARLOVENTO: paredes_paralelo[ParedEdificioSprfv.LATERAL][
                1
            ],
        }

        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: paredes_paralelo,
            DireccionVientoMetodoDireccionalSprfv.NORMAL: paredes_normal,
        }

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def cubierta(self):
        """Genera los actores para la cubierta.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta para cada direccion del viento.
        """
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: self._cubierta_paralelo_cumbrera(),
            DireccionVientoMetodoDireccionalSprfv.NORMAL: self._cubierta_normal_cumbrera(),
        }

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def alero(self):
        """Genera los actores para el o los aleros.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas el o los aleros.
        """
        alero_func = super().alero.__wrapped__
        alero_normal = alero_func(self, 0, self.longitud)
        bool_cubierta_un_agua = self.tipo_cubierta == TipoCubierta.UN_AGUA
        alero_paralelo = {PosicionCubiertaAleroSprfv.SOTAVENTO: []}
        if not bool_cubierta_un_agua:
            alero_paralelo[PosicionCubiertaAleroSprfv.BARLOVENTO] = []
        for inicio, fin in self._zonas_cubierta[
            DireccionVientoMetodoDireccionalSprfv.PARALELO
        ]:
            alero = alero_func(self, -inicio, -fin)
            try:
                for posicion, coords in alero.items():
                    alero_paralelo[posicion].append(coords)
            except AttributeError:
                alero_paralelo[PosicionCubiertaAleroSprfv.SOTAVENTO].append(alero)
        return {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: alero_paralelo,
            DireccionVientoMetodoDireccionalSprfv.NORMAL: alero_normal,
        }

    def inicializar_actores(self) -> None:
        """Inicializa todos los actores."""
        self.paredes()
        self.cubierta()
        self.base()
        if self.alero:
            self.alero()

    def volumen(self):
        raise NotImplementedError()

    def _cubierta_paralelo_cumbrera(self):
        """Determina las coordenadas para las zonas de la cubierta con viendo actuando paralelo a la cumbrera.

        Returns:
            Las coordenadas para las zonas de la cubierta con viendo actuando paralelo a la cumbrera.
        """
        coords = []
        cubierta_func = super().cubierta.__wrapped__
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            dos_aguas_coords = {
                PosicionCubiertaAleroSprfv.BARLOVENTO: [],
                PosicionCubiertaAleroSprfv.SOTAVENTO: [],
            }
            for inicio, fin in self._zonas_cubierta[
                DireccionVientoMetodoDireccionalSprfv.PARALELO
            ]:
                for zona in cubierta_func(self, -inicio, -fin).values():
                    coords.append(zona)
            for barlovento, sotavento in zip(coords[::2], coords[1::2]):
                dos_aguas_coords[PosicionCubiertaAleroSprfv.BARLOVENTO].append(
                    barlovento
                )
                dos_aguas_coords[PosicionCubiertaAleroSprfv.SOTAVENTO].append(sotavento)
            return dos_aguas_coords
        else:
            for inicio, fin in self._zonas_cubierta[
                DireccionVientoMetodoDireccionalSprfv.PARALELO
            ]:
                coords.append(cubierta_func(self, -inicio, -fin))
            return coords

    def _cubierta_normal_cumbrera(self):
        """Determina las coordenadas para las zonas de la cubierta con viendo actuando normal a la cumbrera.

        Returns:
            Las coordenadas para las zonas de la cubierta con viendo actuando normal a la cumbrera.
        """
        if self._zonas_cubierta_normal is None:
            # La longitud de mantiene sin cambiar el signo porque cuando se instancia se pasa el valor como negativo.
            cubierta_func = super().cubierta.__wrapped__
            cubierta = cubierta_func(self, 0, self.longitud)
            return cubierta
        elif self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            return self._cubierta_dos_aguas_normal_como_paralelo()
        else:
            return self._cubierta_un_agua_plana_normal_como_paralelo()

    def _cubierta_un_agua_plana_normal_como_paralelo(self):
        """Determina las coordenadas para las zonas de la cubierta con viendo actuando normal a la cumbrera para
        cubierta a un agua cuando el viento sobre esta se comporta de la misma forma que si actua paralelo a la cumbrera.

        Returns:
            Las coordenadas para las zonas de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.PLANA:
            return (
                coords_zona_cubierta_desde_proyeccion(
                    zona,
                    (self.ancho, self.altura_alero),
                    (0, self.altura_alero),
                    0,
                    self.longitud,
                    invertir_sentido=True,
                )
                for zona in self._zonas_cubierta_invertida_normal
            )
        else:
            coords_cubierta_sotavento = (
                coords_zona_cubierta_desde_proyeccion(
                    zona,
                    (self.ancho, self.altura_cumbrera),
                    (0, self.altura_alero),
                    0,
                    self.longitud,
                    invertir_sentido=True,
                )
                for zona in self._zonas_cubierta_invertida_normal
            )
            coords_cubierta_barlovento = (
                coords_zona_cubierta_desde_proyeccion(
                    zona,
                    (0, self.altura_alero),
                    (self.ancho, self.altura_cumbrera),
                    0,
                    self.longitud,
                )
                for zona in self._zonas_cubierta_normal
            )
            return {
                PosicionCubiertaAleroSprfv.SOTAVENTO: coords_cubierta_sotavento,
                PosicionCubiertaAleroSprfv.BARLOVENTO: coords_cubierta_barlovento,
            }

    def _cubierta_dos_aguas_normal_como_paralelo(self):
        """Determina las coordenadas para las zonas de la cubierta con viendo actuando normal a la cumbrera para
        cubierta a dos aguas cuando el viento sobre esta se comporta de la misma forma que si actua paralelo a la
        cumbrera.

        Returns:
            Las coordenadas para las zonas de la cubierta.
        """
        mitad_ancho = self.ancho / 2
        zonas_faldon_der = (
            (inicio, fin)
            for (inicio, fin) in self._zonas_cubierta_invertida_normal
            if fin >= mitad_ancho
        )
        zonas_faldon_izq = (
            (inicio, fin)
            for (inicio, fin) in self._zonas_cubierta_invertida_normal
            if inicio <= mitad_ancho
        )
        coords_faldon_der = tuple(
            coords_zona_cubierta_desde_proyeccion(
                zona,
                (self.ancho, self.altura_alero),
                (mitad_ancho, self.altura_cumbrera),
                0,
                self.longitud,
                invertir_sentido=True,
            )
            for zona in zonas_faldon_der
        )
        coords_faldon_izq = tuple(
            coords_zona_cubierta_desde_proyeccion(
                zona,
                (0, self.altura_alero),
                (mitad_ancho, self.altura_cumbrera),
                0,
                self.longitud,
                invertir_sentido=True,
            )
            for zona in zonas_faldon_izq
        )
        return coords_faldon_der + coords_faldon_izq


class PresionesComponentes(Geometria):
    """PresionesComponentes.

    Representa las zonas de presiones para el los componentes de un edificio. Inicializa los actores, setea las diferentes
    posiciones de la camara.
    """

    def __init__(
        self,
        escena: Escena3D,
        tabla_colores: TablaColores,
        edificio: Edificio,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            tabla_colores: La tabla de escalas de colores de la escena general.
            edificio: Una instancia de Edificio.
        """
        altura_alero = edificio.altura_alero
        altura_cumbrera = edificio.altura_cumbrera
        alero = getattr(edificio.geometria.cubierta, "alero", 0)
        super().__init__(
            escena,
            edificio.ancho,
            edificio.longitud,
            altura_alero,
            altura_cumbrera,
            edificio.tipo_cubierta,
            alero=alero,
            elevacion=edificio.elevacion,
        )
        self.tabla_colores = tabla_colores
        self._distancia_a = edificio.cp.paredes.componentes.distancia_a
        self._referencia_cubierta = None
        self._distancias_zonas_cubierta = None
        try:
            if edificio.componentes_cubierta:
                self._referencia_cubierta = edificio.cp.cubierta.componentes.referencia
                self._distancias_zonas_cubierta = (
                    edificio.cp.cubierta.componentes.distancias_zonas
                )
        except ErrorLineamientos:
            self._referencia_cubierta = None
        self.inicializar_actores()

    def alero(self):
        if self._referencia_cubierta is None:
            self.actores_alero = defaultdict(list)
            return
        coords = self._seleccionar_cubierta_por_faldon()
        dict_poligonos = aplicar_func_recursivamente(coords, crear_poligono)
        normal_origen = {
            "faldon izq": ((-1, 0, 0), (0, 0, 0)),
            "faldon der": ((1, 0, 0), (self.ancho, 0, 0)),
        }
        self.actores_alero = defaultdict(list)
        for faldon, zonas in dict_poligonos.items():
            normal, origen = normal_origen[faldon]
            for zona, poligonos in zonas.items():
                for poligono in poligonos:
                    clip = recortar_poligono(poligono, origen, normal)
                    if clip is not None:
                        self.actores_alero[zona].append(
                            ActorPresion(
                                self.escena,
                                poligono=clip,
                                tabla_colores=self.tabla_colores,
                                presion=True,
                                mostrar=True,
                            )
                        )

    # TODO - CORREGIR (No me gusta como quedó este método.)
    def cubierta(self):
        coords = self._seleccionar_cubierta()
        dict_poligonos = aplicar_func_recursivamente(coords, crear_poligono)
        if self._referencia_cubierta is None:
            self.actores_cubierta = aplicar_func_recursivamente(
                dict_poligonos,
                lambda x: ActorPresion(
                    self.escena,
                    poligono=x,
                    tabla_colores=self.tabla_colores,
                    presion=True,
                    mostrar=True,
                ),
            )
        else:
            normal_origen = {
                "faldon izq": ((1, 0, 0), (0, 0, 0)),
                "faldon der": ((-1, 0, 0), (self.ancho, 0, 0)),
            }
            self.actores_cubierta = defaultdict(list)
            for faldon, zonas in dict_poligonos.items():
                normal, origen = normal_origen[faldon]
                for zona, poligonos in zonas.items():
                    for poligono in poligonos:
                        clip = recortar_poligono(poligono, origen, normal)
                        if clip is not None:
                            self.actores_cubierta[zona].append(
                                ActorPresion(
                                    self.escena,
                                    poligono=clip,
                                    tabla_colores=self.tabla_colores,
                                    presion=True,
                                    mostrar=True,
                                )
                            )

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=True)
    def paredes(self):
        dict_paredes = super().paredes.__wrapped__(self)
        dict_paredes["lateral_izq"], dict_paredes["lateral_der"] = dict_paredes.pop(
            ParedEdificioSprfv.LATERAL
        )
        coords = defaultdict(list)
        for pared in dict_paredes.values():
            for zona, coords_pared in pared.items():
                coords[zona].append(coords_pared)
        return dict_paredes

    def obtener_cubierta(self):
        return self.actores_cubierta

    def obtener_paredes(self):
        return self.actores_paredes

    def obtener_alero(self):
        return self.actores_alero

    def inicializar_actores(self) -> None:
        """Inicializa los actores."""
        # if self._referencia_cubierta is not None:
        self.cubierta()
        # else:
        #     super().cubierta(0, self.longitud)
        self.paredes()
        self.base()
        if self.alero_:
            self.alero()

    def _pared_frente(self, z0, invertir_sentido=False):
        """Determina las coordenadas de una pared de frente (o contrafrente).

        Args:
            z0: La profundidad sobre el eje Z en la que se encuentra.
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono apareza de un lado o del otro.

        Returns:
            Las coordenadas de una pared de frente.
        """
        altura_final = self.altura_alero
        if self.tipo_cubierta == TipoCubierta.PLANA:
            punto_interseccion_distancia_a_con_cubierta_inicial = (
                punto_interseccion_distancia_a_con_cubierta_final
            ) = self.altura_alero
        elif self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            origen, fin = (0, self.altura_alero), (self.ancho / 2, self.altura_cumbrera)
            punto_interseccion_distancia_a_con_cubierta_inicial = (
                punto_interseccion_distancia_a_con_cubierta_final
            ) = proyeccion_punto_horizontal_sobre_cubierta(
                self._distancia_a, origen, fin
            )[1]
        else:
            altura_final = self.altura_cumbrera
            origen, fin = (0, self.altura_alero), (self.ancho, self.altura_cumbrera)
            punto_interseccion_distancia_a_con_cubierta_inicial = (
                proyeccion_punto_horizontal_sobre_cubierta(
                    self._distancia_a, origen, fin
                )[1]
            )
            punto_interseccion_distancia_a_con_cubierta_final = (
                proyeccion_punto_horizontal_sobre_cubierta(
                    self.ancho - self._distancia_a, origen, fin
                )[1]
            )
        zonas_5 = (
            coords_pared_rectangular(
                self._distancia_a,
                self.altura_alero,
                punto_interseccion_distancia_a_con_cubierta_inicial,
                z0=z0,
                elevacion=self.elevacion,
                invertir_sentido=invertir_sentido,
            ),
            coords_pared_rectangular(
                self._distancia_a,
                punto_interseccion_distancia_a_con_cubierta_final,
                altura_final,
                x0=self.ancho - self._distancia_a,
                z0=z0,
                elevacion=self.elevacion,
                invertir_sentido=invertir_sentido,
            ),
        )
        zona_4 = coords_pared_rectangular(
            self.ancho - 2 * self._distancia_a,
            punto_interseccion_distancia_a_con_cubierta_inicial,
            punto_interseccion_distancia_a_con_cubierta_final,
            x0=self._distancia_a,
            z0=z0,
            elevacion=self.elevacion,
            invertir_sentido=invertir_sentido,
        )
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            zona_4.insert(2, (self.ancho / 2, self.altura_cumbrera, z0))
        return {
            ZonaComponenteParedEdificio.CUATRO: zona_4,
            ZonaComponenteParedEdificio.CINCO: zonas_5,
        }

    def _pared_lateral(self, x0, altura, invertir_sentido=False):
        """Determina las coordenadas de una pared lateral.

        Args:
            x0: La profundidad sobre el eje X en la que se encuentra.
            altura: La altura de la pared
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono apareza de un lado o del otro.

        Returns:
            Las coordenadas de una pared lateral.
        """
        zona_4 = coords_pared_rectangular(
            self.longitud + 2 * self._distancia_a,  # La longitud es negativa
            altura,
            altura,
            x0=-self._distancia_a,
            z0=x0,
            elevacion=self.elevacion,
            sobre_eje_z=True,
            invertir_sentido=invertir_sentido,
        )
        zonas_5 = (
            coords_pared_rectangular(
                -self._distancia_a,
                altura,
                altura,
                x0=0,
                z0=x0,
                elevacion=self.elevacion,
                sobre_eje_z=True,
                invertir_sentido=invertir_sentido,
            ),
            coords_pared_rectangular(
                -self._distancia_a,
                altura,
                altura,
                x0=self.longitud + self._distancia_a,  # La longitud es negativa
                z0=x0,
                elevacion=self.elevacion,
                sobre_eje_z=True,
                invertir_sentido=invertir_sentido,
            ),
        )
        return {
            ZonaComponenteParedEdificio.CUATRO: zona_4,
            ZonaComponenteParedEdificio.CINCO: zonas_5,
        }

    def _seleccionar_cubierta_por_faldon(self):
        """Las zonas de cubierta separadas por faldón, para recortar el alero.

        Returns:
            Las coordenadas de las zonas de la tabla que corresponda.
        """
        if self._referencia_cubierta == "Tabla C 5.3-2":
            return self._cubierta_tabla_c_5_3_2()
        if self._referencia_cubierta == "Tabla C 5.3-3":
            return self._cubierta_tabla_c_5_3_3()
        return {}

    def _seleccionar_cubierta(self):
        if self._referencia_cubierta is None:
            return super().cubierta.__wrapped__(self, 0, self.longitud)
        if self._referencia_cubierta == "Tabla C 5.3-2":
            return self._cubierta_tabla_c_5_3_2()
        if self._referencia_cubierta == "Tabla C 5.3-3":
            return self._cubierta_tabla_c_5_3_3()
        return {}

    def _cubierta_tabla_c_5_3_3(self):
        """Determina las coordenadas de las zonas de la Figura 5.3-2B.

        Cada faldón se divide en un listón de ancho "a" junto a la cumbrera y
        un campo que llega hasta el borde exterior del voladizo si existe
        (Nota 7). Las Zonas 3 son los cuadrados a×a de la cumbrera en las
        cabeceras; las Zonas 2 son el listón de cumbrera del tramo central -que
        conecta las dos Zonas 3- y los cuadrados a×a de la cabecera junto al
        borde; la Zona 1 es el resto. Los rectángulos se arman en planta y se
        parten en la cumbrera para proyectarlos sobre cada faldón.

        Returns:
            Las coordenadas de las zonas de cada faldón.
        """
        mitad_ancho = self.ancho / 2
        punto_mitad = (mitad_ancho, self.altura_cumbrera)

        if self.alero_:
            punto_alero_inicio = tuple(
                punto_sobre_vector(-self.alero_, (0, self.altura_alero), punto_mitad)
            )
            punto_alero_fin = (
                self.ancho + abs(punto_alero_inicio[0]),
                punto_alero_inicio[1],
            )
        else:
            punto_alero_inicio = (0, self.altura_alero)
            punto_alero_fin = (self.ancho, self.altura_alero)

        inicio = punto_alero_inicio[0]
        ancho_total = punto_alero_fin[0] - inicio
        profundidad = -self.longitud  # La longitud es negativa.

        x_cumbrera = mitad_ancho - inicio

        # Si el edificio es chico los listones solapan, así que la distancia
        # "a" se recorta a la mitad de la menor dimensión en planta.
        mitad_menor_dimension = min(ancho_total, profundidad) / 2
        a = min(self._distancia_a, mitad_menor_dimension)

        # Franjas de cabecera (a de profundidad) y tramo central.
        gable = (0, a)
        centro = (a, profundidad - a)
        gable_trasero = (profundidad - a, profundidad)
        # Listón de cumbrera y campos de borde.
        cumbrera = (x_cumbrera - a, x_cumbrera + a)
        borde_izq = (0, x_cumbrera - a)
        borde_der = (x_cumbrera + a, ancho_total)

        rectangulos_zonas = {
            ZonaComponenteCubiertaEdificio.TRES: [
                (cumbrera, gable),
                (cumbrera, gable_trasero),
            ],
            ZonaComponenteCubiertaEdificio.DOS: [
                (cumbrera, centro),
                (borde_izq, gable),
                (borde_izq, gable_trasero),
                (borde_der, gable),
                (borde_der, gable_trasero),
            ],
            ZonaComponenteCubiertaEdificio.UNO: [
                (borde_izq, centro),
                (borde_der, centro),
            ],
        }

        coords_faldon_izq = defaultdict(list)
        coords_faldon_der = defaultdict(list)
        for zona, rectangulos in rectangulos_zonas.items():
            for (x_inicio, x_fin), (z_inicio, z_fin) in rectangulos:
                if x_fin - x_inicio < TOLERANCIA or z_fin - z_inicio < TOLERANCIA:
                    continue
                faldones = (
                    (
                        coords_faldon_izq,
                        (x_inicio, min(x_fin, x_cumbrera)),
                        punto_alero_inicio,
                        punto_mitad,
                    ),
                    (
                        coords_faldon_der,
                        (max(x_inicio, x_cumbrera), x_fin),
                        punto_mitad,
                        punto_alero_fin,
                    ),
                )
                for coords, (x_faldon_inicio, x_faldon_fin), origen, fin in faldones:
                    if x_faldon_fin - x_faldon_inicio < TOLERANCIA:
                        continue
                    coords[zona].append(
                        coords_zona_cubierta_desde_proyeccion(
                            (inicio + x_faldon_inicio, inicio + x_faldon_fin),
                            origen,
                            fin,
                            -z_inicio,
                            -z_fin,
                        )
                    )
        return {
            "faldon izq": dict(coords_faldon_izq),
            "faldon der": dict(coords_faldon_der),
        }

    def _cubierta_tabla_c_5_3_2(self):
        """Determina las coordenadas de las zonas de la Figura 5.3-2A.

        Las distancias se miden desde el borde de la cubierta -desde el borde
        exterior del voladizo si existe, Nota 7-: la Zona 3 es una "L" de 0,2h
        de espesor que corre 0,6h sobre cada borde desde la esquina, la Zona 2
        el resto de la franja perimetral de 0,6h, la Zona 1 la franja que le
        sigue (hasta 1,2h) y la Zona 1' el interior. Los rectángulos se arman
        en planta y después se parten en la cumbrera para proyectarlos sobre
        cada faldón.

        Returns:
            Las coordenadas de las zonas de cada faldón.
        """
        mitad_ancho = self.ancho / 2
        punto_mitad = (mitad_ancho, self.altura_cumbrera)

        if self.alero_:
            punto_alero_inicio = tuple(
                punto_sobre_vector(-self.alero_, (0, self.altura_alero), punto_mitad)
            )
            punto_alero_fin = (
                self.ancho + abs(punto_alero_inicio[0]),
                punto_alero_inicio[1],
            )
        else:
            punto_alero_inicio = (0, self.altura_alero)
            punto_alero_fin = (self.ancho, self.altura_alero)

        inicio = punto_alero_inicio[0]
        ancho_total = punto_alero_fin[0] - inicio
        profundidad = -self.longitud  # La longitud es negativa.

        # Si el edificio es chico las franjas se solapan, así que se recortan a
        # la mitad de la menor dimensión en planta.
        mitad_menor_dimension = min(ancho_total, profundidad) / 2
        zona_3, zona_2, zona_1 = (
            min(distancia, mitad_menor_dimension)
            for distancia in self._distancias_zonas_cubierta
        )

        # La Zona 3 es una "L" en cada esquina: un brazo de 0.2h de espesor y
        # 0.6h de largo sobre cada borde. Lo que queda de la esquina, hasta
        # completar la franja de 0.6h, sigue siendo Zona 2.
        zona_3_rectangulos = []
        zona_2_esquinas = []
        for x_opuesto in (False, True):
            for z_opuesto in (False, True):
                zona_3_rectangulos += [
                    (
                        _rango(x_opuesto, 0, zona_2, ancho_total),
                        _rango(z_opuesto, 0, zona_3, profundidad),
                    ),
                    (
                        _rango(x_opuesto, 0, zona_3, ancho_total),
                        _rango(z_opuesto, zona_3, zona_2, profundidad),
                    ),
                ]
                zona_2_esquinas.append(
                    (
                        _rango(x_opuesto, zona_3, zona_2, ancho_total),
                        _rango(z_opuesto, zona_3, zona_2, profundidad),
                    )
                )

        rectangulos_zonas = {
            ZonaComponenteCubiertaEdificio.TRES: zona_3_rectangulos,
            ZonaComponenteCubiertaEdificio.DOS: [
                # La franja perimetral de 0.6h, sin las "L" de las esquinas.
                ((zona_2, ancho_total - zona_2), (0, zona_2)),
                ((zona_2, ancho_total - zona_2), (profundidad - zona_2, profundidad)),
                ((0, zona_2), (zona_2, profundidad - zona_2)),
                ((ancho_total - zona_2, ancho_total), (zona_2, profundidad - zona_2)),
                *zona_2_esquinas,
            ],
            ZonaComponenteCubiertaEdificio.UNO: [
                ((zona_2, zona_1), (zona_2, profundidad - zona_2)),
                (
                    (ancho_total - zona_1, ancho_total - zona_2),
                    (zona_2, profundidad - zona_2),
                ),
                ((zona_1, ancho_total - zona_1), (zona_2, zona_1)),
                (
                    (zona_1, ancho_total - zona_1),
                    (profundidad - zona_1, profundidad - zona_2),
                ),
            ],
            ZonaComponenteCubiertaEdificio.UNO_PRIMA: [
                ((zona_1, ancho_total - zona_1), (zona_1, profundidad - zona_1)),
            ],
        }

        x_cumbrera = mitad_ancho - inicio
        coords_faldon_izq = defaultdict(list)
        coords_faldon_der = defaultdict(list)
        for zona, rectangulos in rectangulos_zonas.items():
            for (x_inicio, x_fin), (z_inicio, z_fin) in rectangulos:
                if x_fin - x_inicio < TOLERANCIA or z_fin - z_inicio < TOLERANCIA:
                    continue
                faldones = (
                    (
                        coords_faldon_izq,
                        (x_inicio, min(x_fin, x_cumbrera)),
                        punto_alero_inicio,
                        punto_mitad,
                    ),
                    (
                        coords_faldon_der,
                        (max(x_inicio, x_cumbrera), x_fin),
                        punto_mitad,
                        punto_alero_fin,
                    ),
                )
                for coords, (x_faldon_inicio, x_faldon_fin), origen, fin in faldones:
                    if x_faldon_fin - x_faldon_inicio < TOLERANCIA:
                        continue
                    coords[zona].append(
                        coords_zona_cubierta_desde_proyeccion(
                            (inicio + x_faldon_inicio, inicio + x_faldon_fin),
                            origen,
                            fin,
                            -z_inicio,
                            -z_fin,
                        )
                    )
        return {
            "faldon izq": dict(coords_faldon_izq),
            "faldon der": dict(coords_faldon_der),
        }
