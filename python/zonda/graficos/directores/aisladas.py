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

from itertools import pairwise
from typing import TYPE_CHECKING

from zonda.enums import (
    DireccionVientoCubiertaAislada,
    PosicionCamara,
    TipoCubierta,
    ZonaPresionCubiertaAislada,
)
from zonda.graficos.actores import ActorLineas, actores_poligonos
from zonda.graficos.directores.utils_geometria import (
    coords_zona_cubierta,
    coords_zona_cubierta_desde_proyeccion,
)

if TYPE_CHECKING:
    from zonda.cirsoc import CubiertaAislada
    from zonda.graficos.colores import TablaColores
    from zonda.graficos.escena import Camara, Escena3D


class Geometria:
    """Geometria.
    Representa la geometria de una cubierta aislada. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        escena: Escena3D,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
    ) -> None:
        """
        Args:
            escena: La escena que junta los actores.
            ancho: El ancho de la cubierta.
            longitud: La longitud de la cubierta.
            altura_alero: La altura de alero de la cubierta.
            altura_cumbrera: La altura de cumbrera de la cubierta.
            tipo_cubierta: El tipo de cubierta.
        """
        self.actores_cubierta = None

        self.escena = escena
        self.ancho = ancho
        # Se pasa a negativo para que la estructura crezca hacia atras.
        self.longitud = -longitud
        self.altura_alero = altura_alero
        self.altura_cumbrera = altura_cumbrera
        self.tipo_cubierta = tipo_cubierta

    @actores_poligonos(color="LightCoral", mostrar=True)
    def cubierta(self):
        """Genera los actores para la cubierta.

        La función en sí genera las coordenadas para la creación de los actores, que luego son generados por el decorador.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            return self._cubierta_dos_aguas()
        return self._cubierta_un_agua()

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.escena.limpiar()
        self.cubierta()
        self._crear_soportes()

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

    def _cubierta_dos_aguas(self):
        """Determina las coordenadas para una cubierta a dos aguas.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        faldon_izq = coords_zona_cubierta(
            (0, self.altura_alero),
            (self.ancho / 2, self.altura_cumbrera),
            0,
            self.longitud,
            dist_eucl=True,
        )
        faldon_der = coords_zona_cubierta(
            (self.ancho, self.altura_alero),
            (self.ancho / 2, self.altura_cumbrera),
            0,
            self.longitud,
            dist_eucl=True,
            invertir_sentido=True,
        )
        return faldon_izq, faldon_der

    def _cubierta_un_agua(self):
        """Determina las coordenadas para una cubierta a un agua.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_zona_cubierta(
            (0, self.altura_alero),
            (self.ancho, self.altura_cumbrera),
            0,
            self.longitud,
            dist_eucl=True,
        )

    def _crear_soportes(self):
        puntos = []
        for x, y, z in (
            (0, 0, 0),
            (self.ancho, 0, 0),
            (0, 0, self.longitud),
            (self.ancho, 0, self.longitud),
        ):
            if x == self.ancho and self.tipo_cubierta == TipoCubierta.UN_AGUA:
                altura = self.altura_cumbrera
            else:
                altura = self.altura_alero
            puntos += [(x, y, z), (x, altura, z)]
        ActorLineas(self.escena, puntos, "black")


class Presiones(Geometria):
    """Presiones.

    Representa las zonas de presiones de las Figuras 2.4-4 a 2.4-7 para una
    cubierta aislada. Crea de una sola vez los actores de las cuatro
    direcciones del viento, ocultos e indexados por dirección, y los devuelve
    según la dirección vigente.

    Convenciones de dirección: para γ = 0º el viento sopla desde el borde del
    ancho de mayor altura (el de cumbrera en cubiertas a un agua); para
    γ = 90º sopla desde el borde de la longitud que queda en el plano de
    pantalla (Z = 0).
    """

    def __init__(
        self,
        escena: Escena3D,
        tabla_colores: TablaColores,
        cubierta_aislada: CubiertaAislada,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            tabla_colores: La tabla de escalas de colores de la escena general.
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__(
            escena,
            cubierta_aislada.ancho,
            cubierta_aislada.longitud,
            cubierta_aislada.altura_alero,
            cubierta_aislada.altura_cumbrera,
            cubierta_aislada.tipo_cubierta,
        )
        self.tabla_colores = tabla_colores
        # La altura media h del Reglamento: define las bandas del viento
        # paralelo a la cumbrera (Figura 2.4-7).
        self.altura_media = cubierta_aislada.geometria.altura_media
        self.direccion: DireccionVientoCubiertaAislada | None = None

        self.inicializar_actores()

    def obtener_actores(self):
        return self.actores_cubierta[self.direccion]

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def cubierta(self):
        return {
            DireccionVientoCubiertaAislada.GAMMA_0: self._cubierta_perpendicular(
                DireccionVientoCubiertaAislada.GAMMA_0
            ),
            DireccionVientoCubiertaAislada.GAMMA_180: self._cubierta_perpendicular(
                DireccionVientoCubiertaAislada.GAMMA_180
            ),
            DireccionVientoCubiertaAislada.GAMMA_90: self._cubierta_paralela(),
            DireccionVientoCubiertaAislada.GAMMA_270: self._cubierta_paralela(
                desde_contrafrente=True
            ),
        }

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.cubierta()
        self._crear_soportes()

    def _cubierta_perpendicular(self, direccion: DireccionVientoCubiertaAislada):
        """Las mitades de barlovento y sotavento del viento perpendicular.

        La Figura 2.4-4 divide la vertiente única en dos mitades de 0,5L
        medidas desde el borde de barlovento, y las Figuras 2.4-5 y 2.4-6
        asignan un coeficiente a cada faldón de la cubierta a dos aguas.

        Args:
            direccion: La dirección del viento, perpendicular a la cumbrera.

        Returns:
            Las coordenadas de cada zona.
        """
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            faldon_izq, faldon_der = super()._cubierta_dos_aguas()
            # γ = 0º: viento desde el lado del ancho alto (el faldón derecho).
            if direccion is DireccionVientoCubiertaAislada.GAMMA_0:
                barlovento, sotavento = faldon_der, faldon_izq
            else:
                barlovento, sotavento = faldon_izq, faldon_der
        else:
            punto_inicio = (0, self.altura_alero)
            punto_fin = (self.ancho, self.altura_cumbrera)
            mitad_ancho = self.ancho / 2
            mitad_alta = coords_zona_cubierta_desde_proyeccion(
                (mitad_ancho, self.ancho), punto_inicio, punto_fin, 0, self.longitud
            )
            mitad_baja = coords_zona_cubierta_desde_proyeccion(
                (0, mitad_ancho), punto_inicio, punto_fin, 0, self.longitud
            )
            # γ = 0º: viento desde el lado alto; el barlovento es la mitad
            # que va de la cumbrera al medio.
            if direccion is DireccionVientoCubiertaAislada.GAMMA_0:
                barlovento, sotavento = mitad_alta, mitad_baja
            else:
                barlovento, sotavento = mitad_baja, mitad_alta
        return {
            ZonaPresionCubiertaAislada.BARLOVENTO: barlovento,
            ZonaPresionCubiertaAislada.SOTAVENTO: sotavento,
        }

    def _cubierta_paralela(self, desde_contrafrente: bool = False):
        """Las bandas del viento paralelo a la cumbrera (Figura 2.4-7).

        Las bandas son franjas de ancho h y 2h medidas en horizontal desde el
        borde de barlovento. Sólo se dibujan las que caben en la longitud de
        la cubierta, igual que las zonas que produce el cálculo.

        Args:
            desde_contrafrente: Indica si el viento sopla desde el borde
                opuesto (γ = 270º en vez de γ = 90º).

        Returns:
            Las coordenadas de cada banda, proyectadas sobre el o los faldones.
        """
        # Las distancias crecen hacia el interior de la escena, contra el
        # sentido del eje Z: desde Z = 0 para γ = 90º, y desde el borde del
        # contrafrente para γ = 270º.
        if desde_contrafrente:
            inicio_barlovento = self.longitud
            sentido = 1.0
        else:
            inicio_barlovento = 0.0
            sentido = -1.0

        def z_de(distancia: float) -> float:
            return inicio_barlovento + sentido * distancia

        mitad_ancho = self.ancho / 2
        faldon_izq = (
            ((0, self.altura_alero), (mitad_ancho, self.altura_cumbrera)),
            (
                0,
                mitad_ancho,
            ),
        )
        faldon_der = (
            (
                (mitad_ancho, self.altura_cumbrera),
                (self.ancho, self.altura_alero),
            ),
            (mitad_ancho, self.ancho),
        )
        faldon_unico = (
            ((0, self.altura_alero), (self.ancho, self.altura_cumbrera)),
            (
                0,
                self.ancho,
            ),
        )
        faldones = (
            (faldon_izq, faldon_der)
            if self.tipo_cubierta == TipoCubierta.DOS_AGUAS
            else (faldon_unico,)
        )

        limites = (0.0, self.altura_media, 2 * self.altura_media, abs(self.longitud))
        zonas = {}
        for zona, (d1, d2) in zip(
            (
                ZonaPresionCubiertaAislada.HASTA_H,
                ZonaPresionCubiertaAislada.ENTRE_H_Y_2H,
                ZonaPresionCubiertaAislada.MAYOR_2H,
            ),
            pairwise(limites),
            strict=True,
        ):
            if d1 >= abs(self.longitud):
                continue
            d2 = min(d2, abs(self.longitud))
            # Con el viento desde el contrafrente el polígono se recorre en
            # el sentido inverso para que la normal siga apuntando hacia
            # arriba y la flecha no atraviese la cubierta.
            zonas[zona] = tuple(
                coords_zona_cubierta_desde_proyeccion(
                    rango_x,
                    origen,
                    fin,
                    z_de(d1),
                    z_de(d2),
                    invertir_sentido=desde_contrafrente,
                )
                for (origen, fin), rango_x in faldones
            )
        return zonas


class Componentes(Geometria):
    """Componentes.

    Representa las zonas de componentes y revestimientos de las Figuras
    5.5-1 a 5.5-3 para una cubierta aislada. Crea de una sola vez todos los
    actores, visibles e indexados por zona: las figuras consideran una sola
    disposición de zonas y no hay direcciones que conmutar.
    """

    def __init__(
        self,
        escena: Escena3D,
        tabla_colores: TablaColores,
        cubierta_aislada: CubiertaAislada,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores.
            tabla_colores: La tabla de escalas de colores de la escena general.
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__(
            escena,
            cubierta_aislada.ancho,
            cubierta_aislada.longitud,
            cubierta_aislada.altura_alero,
            cubierta_aislada.altura_cumbrera,
            cubierta_aislada.tipo_cubierta,
        )
        self.tabla_colores = tabla_colores
        # Los rectángulos de cada zona en planta los define el cálculo: la
        # vista no recalcula nada del Reglamento.
        self._rectangulos_zonas = cubierta_aislada.cpn_componentes.distancias_zonas
        self.inicializar_actores()

    def obtener_actores(self):
        """Los actores de las zonas, indexados por zona.

        Returns:
            El diccionario de zona a actores.
        """
        return self.actores_zonas

    def inicializar_actores(self) -> None:
        """Genera y añade los actores de cada función."""
        self.zonas()
        self._crear_soportes()

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=True)
    def zonas(self):
        """Genera los actores de cada zona de componentes.

        Returns:
            Las coordenadas de los polígonos de cada zona.
        """
        return {
            zona: self._proyectar_rectangulos(rectangulos)
            for zona, rectangulos in self._rectangulos_zonas.items()
        }

    def _proyectar_rectangulos(self, rectangulos):
        """Proyecta los rectángulos de una zona sobre la cubierta.

        Args:
            rectangulos: Los rectángulos (x0, x1, z0, z1) de la zona, en
                coordenadas de planta.

        Returns:
            Una tupla con los polígonos de la zona, uno por rectángulo y
            faldón.
        """
        poligonos = []
        for x0, x1, z0, z1 in rectangulos:
            poligonos.extend(self._proyectar_rectangulo(x0, x1, z0, z1))
        return tuple(poligonos)

    def _proyectar_rectangulo(
        self, x0: float, x1: float, z0: float, z1: float
    ) -> tuple:
        """Proyecta un rectángulo en planta sobre la cubierta.

        Args:
            x0: La coordenada X inicial del rectángulo.
            x1: La coordenada X final del rectángulo.
            z0: La coordenada Z inicial del rectángulo.
            z1: La coordenada Z final del rectángulo.

        Returns:
            Los polígonos que cubren el rectángulo: uno para la vertiente
            única, hasta dos para la cubierta a dos aguas.
        """
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            return self._proyectar_rectangulo_dos_aguas(x0, x1, z0, z1)
        return (
            coords_zona_cubierta_desde_proyeccion(
                (x0, x1),
                (0, self.altura_alero),
                (self.ancho, self.altura_cumbrera),
                z0,
                z1,
            ),
        )

    def _proyectar_rectangulo_dos_aguas(
        self, x0: float, x1: float, z0: float, z1: float
    ) -> tuple:
        """Proyecta un rectángulo sobre los faldones de una cubierta a dos aguas.

        El rectángulo se parte en la cumbrera y cada mitad se proyecta sobre
        su faldón. Ambos faldones se describen con X creciente -el izquierdo
        desde el alero a la cumbrera, el derecho desde la cumbrera al
        alero- para que las proyecciones y las normales salgan derechas.

        Args:
            x0: La coordenada X inicial del rectángulo.
            x1: La coordenada X final del rectángulo.
            z0: La coordenada Z inicial del rectángulo.
            z1: La coordenada Z final del rectángulo.

        Returns:
            Los polígonos de las mitades del rectángulo que caen sobre cada
            faldón.
        """
        mitad = self.ancho / 2
        poligonos = []
        if x0 < mitad:
            poligonos.append(
                coords_zona_cubierta_desde_proyeccion(
                    (x0, min(x1, mitad)),
                    (0, self.altura_alero),
                    (mitad, self.altura_cumbrera),
                    z0,
                    z1,
                )
            )
        if x1 > mitad:
            poligonos.append(
                coords_zona_cubierta_desde_proyeccion(
                    (max(x0, mitad), x1),
                    (mitad, self.altura_cumbrera),
                    (self.ancho, self.altura_alero),
                    z0,
                    z1,
                )
            )
        return tuple(poligonos)
