"""Contiene clases que selecionan los actores para cada tipo de representación de un edificio (Geometria, Zonas de presiones, etc).
Además proveé métodos para la configuración de la cámara en diferentes posiciones.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple, TYPE_CHECKING, Union

from vtkmodules import all as vtk

from sse102.enums import (
    ParedEdificioSprfv,
    TipoCubierta,
    PosicionCubiertaAleroSprfv,
    PosicionCamara,
    DireccionVientoMetodoDireccionalSprfv,
    ZonaComponenteParedEdificio,
    ZonaComponenteCubiertaEdificio,
)
from sse102.excepciones import ErrorLineamientos
from sse102.graficos.actores import (
    actores_poligonos,
    crear_poly_data,
    clip_poly_data,
    ActorPresion,
)
from sse102.graficos.directores.utils_geometria import (
    coords_zona_cubierta,
    coords_pared_rectangular,
    coords_zona_cubierta_desde_proyeccion,
    proyeccion_punto_horizontal_sobre_cubierta,
    punto_sobre_vector,
)
from sse102.graficos.directores.utils_iter import aplicar_func_recursivamente

if TYPE_CHECKING:
    from sse102.cirsoc import Edificio
    from sse102.tipos import Punto2D


class Geometria:
    """Geometria.

    Representa la geometria de un edificio. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
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
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
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

        self.renderer = renderer
        self.ancho = ancho
        # Se pasa a Negativo para que en VTK crezca hacia atras.
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
        return {PosicionCubiertaAleroSprfv.BARLOVENTO: alero_der, PosicionCubiertaAleroSprfv.SOTAVENTO: alero_izq}

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
        filtro = vtk.vtkTriangleFilter()
        mapper = vtk.vtkPolyDataMapper()
        filtro.SetInputData(self.actores_paredes[ParedEdificioSprfv.BARLOVENTO].poly_data)
        mapper.SetInputData(filtro.GetOutput())
        propiedades = vtk.vtkMassProperties()
        propiedades.SetInputConnection(filtro.GetOutputPort())
        propiedades.Update()
        return propiedades.GetSurfaceArea() * abs(self.longitud)

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.renderer.RemoveAllViewProps()
        self.paredes()
        self.cubierta(0, self.longitud)
        self.base()
        if self.alero_:
            self.alero(0, self.longitud)

    def setear_posicion_camara(self, camara: vtk.vtkCamera, posicion: PosicionCamara) -> None:
        """Setea la posición de la camara.

        Args:
            camara: La camara a la que se le setea la vista.
            posicion: La posición a setear.
        """
        camara.SetFocalPoint(self.ancho / 2, 0, self.longitud / 2)
        posiciones = {
            PosicionCamara.SUPERIOR: (self.ancho / 2, self.altura_alero, self.longitud / 2),
            PosicionCamara.PERSPECTIVA: (self.ancho, self.altura_alero, 0),
            PosicionCamara.IZQUIERDA: (0, 0, self.longitud / 2),
            PosicionCamara.DERECHA: (self.ancho, 0, self.longitud / 2),
            PosicionCamara.FRENTE: (self.ancho / 2, 0, 0),
            PosicionCamara.CONTRAFRENTE: (self.ancho / 2, 0, self.longitud),
        }
        camara.SetPosition(*posiciones[posicion])

        if posicion == PosicionCamara.SUPERIOR:
            vector_altura = (1, 0, 0)
        else:
            vector_altura = (0, 1, 0)
        camara.SetViewUp(*vector_altura)
        self.renderer.ResetCamera()

    def _pared_lateral(self, x0: float, altura: float, invertir_sentido: bool = False):
        """Determina las coordenadas de una pared lateral.

        Args:
            x0: La profundidad sobre el eje X en la que se encuentra.
            altura: La altura de la pared
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono en VTK apareza de un lado o del otro.

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
            quiere que la normal al poligono en VTK apareza de un lado o del otro.

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
        return {PosicionCubiertaAleroSprfv.BARLOVENTO: faldon_der, PosicionCubiertaAleroSprfv.SOTAVENTO: faldon_izq}

    def _cubierta_un_agua(self, z_inicio: float, z_fin: float):
        """Determina las coordenadas para una cubierta a un agua.

        Args:
            z_inicio: El inicio de la cubierta sobre el eje Z.
            z_fin: El fin de la cubierta sobre el eje Z.

        Returns:
            Las coordenadas para cada zona de la cubierta.
        """
        return coords_zona_cubierta(
            (0, self.altura_alero), (self.ancho, self.altura_cumbrera), z_inicio, z_fin, dist_eucl=True
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

    def __init__(self, renderer: vtk.vtkRenderer, tabla_colores: vtk.vtkLookupTable, edificio: Edificio) -> None:
        """

        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
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
            renderer,
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
        self._zonas_cubierta_normal = self._zonas_cubierta[DireccionVientoMetodoDireccionalSprfv.NORMAL]
        if self._zonas_cubierta_normal is not None:
            self._zonas_cubierta_invertida_normal = tuple(
                (self.ancho - inicio, self.ancho - fin) for inicio, fin in self._zonas_cubierta_normal
            )

        self.direccion = DireccionVientoMetodoDireccionalSprfv.PARALELO

        if self.tipo_cubierta == TipoCubierta.UN_AGUA:
            self.posicion_cubierta_un_agua = PosicionCubiertaAleroSprfv.SOTAVENTO

        self.normal_como_paralelo = edificio.cp.cubierta.sprfv.normal_como_paralelo

        self.inicializar_actores()

    def obtener_paredes(self) -> Dict[ParedEdificioSprfv : Union[ActorPresion, Tuple[ActorPresion, ActorPresion]]]:
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
            paredes[ParedEdificioSprfv.BARLOVENTO], paredes[ParedEdificioSprfv.SOTAVENTO] = (
                paredes[ParedEdificioSprfv.SOTAVENTO],
                paredes[ParedEdificioSprfv.BARLOVENTO],
            )
        return paredes

    def obtener_cubierta(
        self,
    ) -> Union[
        Tuple[ActorPresion, ...],
        Dict[PosicionCubiertaAleroSprfv, Union[Tuple[ActorPresion, ...], ActorPresion]],
        ActorPresion,
    ]:
        """Selecciona los actores de cubierta en base al tipo de cubierta y la posición de la misma respecto al viento.

        Returns:
            Los actores seleccionados.
        """
        if self.direccion == DireccionVientoMetodoDireccionalSprfv.NORMAL and self.normal_como_paralelo:
            posicion_cubierta = getattr(self, "posicion_cubierta_un_agua", None)
            if posicion_cubierta is not None:
                return self.actores_cubierta[self.direccion][posicion_cubierta]
        return self.actores_cubierta[self.direccion]

    def obtener_alero(
        self,
    ) -> Union[Dict[PosicionCubiertaAleroSprfv, Union[Tuple[ActorPresion, ...], ActorPresion]], ActorPresion]:
        """Selecciona los actores de alero en base a la posición del viento respecto a la cubierta.

        Returns:
            Los actores seleccionados.
        """
        actores_alero = getattr(self, "actores_alero", None)
        if actores_alero is not None:
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
            ParedEdificioSprfv.SOTAVENTO: paredes_paralelo[ParedEdificioSprfv.LATERAL][0],
            ParedEdificioSprfv.BARLOVENTO: paredes_paralelo[ParedEdificioSprfv.LATERAL][1],
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
        for inicio, fin in self._zonas_cubierta[DireccionVientoMetodoDireccionalSprfv.PARALELO]:
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
            dos_aguas_coords = {PosicionCubiertaAleroSprfv.BARLOVENTO: [], PosicionCubiertaAleroSprfv.SOTAVENTO: []}
            for inicio, fin in self._zonas_cubierta[DireccionVientoMetodoDireccionalSprfv.PARALELO]:
                for zona in cubierta_func(self, -inicio, -fin).values():
                    coords.append(zona)
            for barlovento, sotavento in zip(coords[::2], coords[1::2]):
                dos_aguas_coords[PosicionCubiertaAleroSprfv.BARLOVENTO].append(barlovento)
                dos_aguas_coords[PosicionCubiertaAleroSprfv.SOTAVENTO].append(sotavento)
            return dos_aguas_coords
        else:
            for inicio, fin in self._zonas_cubierta[DireccionVientoMetodoDireccionalSprfv.PARALELO]:
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
            (inicio, fin) for (inicio, fin) in self._zonas_cubierta_invertida_normal if fin >= mitad_ancho
        )
        zonas_faldon_izq = (
            (inicio, fin) for (inicio, fin) in self._zonas_cubierta_invertida_normal if inicio <= mitad_ancho
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
        renderer: vtk.vtkRenderer,
        tabla_colores: vtk.vtkLookupTable,
        edificio: Edificio,
    ) -> None:
        """

        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
            tabla_colores: La tabla de escalas de colores de la escena general.
            edificio: Una instancia de Edificio.
        """
        altura_alero = edificio.altura_alero
        altura_cumbrera = edificio.altura_cumbrera
        alero = getattr(edificio.geometria.cubierta, "alero", 0)
        super().__init__(
            renderer,
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
        try:
            if edificio.componentes_cubierta:
                self._referencia_cubierta = edificio.cp.cubierta.componentes.referencia
        except ErrorLineamientos:
            self._referencia_cubierta = None
        self.inicializar_actores()

    def alero(self):
        coords = self._cubierta_figura_5b()
        dict_poly_datas = aplicar_func_recursivamente(coords, crear_poly_data)
        normal_origen = {"faldon izq": ((-1, 0, 0), (0, 0, 0)), "faldon der": ((1, 0, 0), (self.ancho, 0, 0))}
        self.actores_alero = defaultdict(list)
        for faldon, zonas in dict_poly_datas.items():
            normal, origen = normal_origen[faldon]
            for zona, poly_datas in zonas.items():
                for poly_data in poly_datas:
                    clip = clip_poly_data(poly_data, origen, normal)
                    if clip is not None:
                        self.actores_alero[zona].append(
                            ActorPresion(
                                self.renderer,
                                poly_data=clip,
                                tabla_colores=self.tabla_colores,
                                presion=True,
                                mostrar=True,
                            )
                        )

    # TODO - CORREGIR (No me gusta como quedó este método.)
    def cubierta(self):
        coords = self._seleccionar_cubierta()
        dict_poly_datas = aplicar_func_recursivamente(coords, crear_poly_data)
        if self._referencia_cubierta is None:
            self.actores_cubierta = aplicar_func_recursivamente(
                dict_poly_datas,
                lambda x: ActorPresion(
                    self.renderer, poly_data=x, tabla_colores=self.tabla_colores, presion=True, mostrar=True
                ),
            )
        else:
            normal_origen = {"faldon izq": ((1, 0, 0), (0, 0, 0)), "faldon der": ((-1, 0, 0), (self.ancho, 0, 0))}
            self.actores_cubierta = defaultdict(list)
            if "Figura 7A" in self._referencia_cubierta:
                normal, origen = normal_origen["faldon izq"]
                for zona, poly_datas in dict_poly_datas.items():
                    for poly_data in poly_datas:
                        clip = clip_poly_data(poly_data, origen, normal)
                        if clip is not None:
                            self.actores_cubierta[zona].append(
                                ActorPresion(
                                    self.renderer,
                                    poly_data=clip,
                                    tabla_colores=self.tabla_colores,
                                    presion=True,
                                    mostrar=True,
                                )
                            )
            else:
                for faldon, zonas in dict_poly_datas.items():
                    normal, origen = normal_origen[faldon]
                    for zona, poly_datas in zonas.items():
                        for poly_data in poly_datas:
                            clip = clip_poly_data(poly_data, origen, normal)
                            if clip is not None:
                                self.actores_cubierta[zona].append(
                                    ActorPresion(
                                        self.renderer,
                                        poly_data=clip,
                                        tabla_colores=self.tabla_colores,
                                        presion=True,
                                        mostrar=True,
                                    )
                                )

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=True)
    def paredes(self):
        dict_paredes = super().paredes.__wrapped__(self)
        dict_paredes["lateral_izq"], dict_paredes["lateral_der"] = dict_paredes.pop(ParedEdificioSprfv.LATERAL)
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
            quiere que la normal al poligono en VTK apareza de un lado o del otro.

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
            ) = proyeccion_punto_horizontal_sobre_cubierta(self._distancia_a, origen, fin)[1]
        else:
            altura_final = self.altura_cumbrera
            origen, fin = (0, self.altura_alero), (self.ancho, self.altura_cumbrera)
            punto_interseccion_distancia_a_con_cubierta_inicial = proyeccion_punto_horizontal_sobre_cubierta(
                self._distancia_a, origen, fin
            )[1]
            punto_interseccion_distancia_a_con_cubierta_final = proyeccion_punto_horizontal_sobre_cubierta(
                self.ancho - self._distancia_a, origen, fin
            )[1]
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
        return {ZonaComponenteParedEdificio.CUATRO: zona_4, ZonaComponenteParedEdificio.CINCO: zonas_5}

    def _pared_lateral(self, x0, altura, invertir_sentido=False):
        """Determina las coordenadas de una pared lateral.

        Args:
            x0: La profundidad sobre el eje X en la que se encuentra.
            altura: La altura de la pared
            invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se
            quiere que la normal al poligono en VTK apareza de un lado o del otro.

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
        return {ZonaComponenteParedEdificio.CUATRO: zona_4, ZonaComponenteParedEdificio.CINCO: zonas_5}

    def _seleccionar_cubierta(self):
        if self._referencia_cubierta is None:
            return super().cubierta.__wrapped__(self, 0, self.longitud)
        if "5B" in self._referencia_cubierta:
            return self._cubierta_figura_5b()
        elif self._referencia_cubierta == "Figura 7A":
            return self._cubierta_figura_7a()
        elif self._referencia_cubierta == "Figura 7A (cont.)":
            return self._cubierta_figura_7a_cont()
        elif self._referencia_cubierta == "Figura 8":
            return self._cubierta_figura_8()

    def _cubierta_figura_5b(self):
        es_cubierta_plana = self.tipo_cubierta == TipoCubierta.UN_AGUA

        mitad_ancho = self.ancho / 2
        punto_mitad = (mitad_ancho, self.altura_cumbrera)

        if es_cubierta_plana:
            punto_mitad = (mitad_ancho, (self.altura_cumbrera + self.altura_alero) / 2)

        if self.alero_:
            punto_alero_inicio = tuple(punto_sobre_vector(-self.alero_, (0, self.altura_alero), punto_mitad))
            punto_alero_fin = (self.ancho + abs(punto_alero_inicio[0]), punto_alero_inicio[1])
        else:
            punto_alero_inicio = (0, self.altura_alero)
            punto_alero_fin = (self.ancho, self.altura_alero)

        if es_cubierta_plana:
            punto_alero_fin = (self.ancho, self.altura_cumbrera)

        zonas_z = (
            (0, -self._distancia_a),
            (-self._distancia_a, self.longitud + self._distancia_a),
            (self.longitud + self._distancia_a, self.longitud),
        )

        inicio = punto_alero_inicio[0]
        fin = punto_alero_fin[0]
        a_inicial = inicio + self._distancia_a
        a_final = fin - self._distancia_a

        if self._referencia_cubierta == "Figura 5B" or self.tipo_cubierta == TipoCubierta.UN_AGUA:
            zonas_x = ((inicio, a_inicial), (a_inicial, mitad_ancho), (mitad_ancho, a_final), (a_final, fin))
            zonas_3_izq = zonas_x[:1]
            zonas_3_der = zonas_x[-1:]
            zonas_2_centro_izq = zonas_3_izq
            zonas_2_centro_der = zonas_3_der
            zonas_2_extremo_izq = zonas_x[1:2]
            zonas_2_extremo_der = zonas_x[2:3]
            indice_zona_1_izq = 1
            indice_zona_1_der = 2
        else:
            a_mitad_izq = mitad_ancho - self._distancia_a
            a_mitad_der = mitad_ancho + self._distancia_a
            zonas_x = (
                (inicio, a_inicial),
                (a_inicial, a_mitad_izq),
                (a_mitad_izq, mitad_ancho),
                (mitad_ancho, a_mitad_der),
                (a_mitad_der, a_final),
                (a_final, fin),
            )
            zonas_3_izq = zonas_x[:1] + zonas_x[2:3]
            zonas_3_der = zonas_x[3:4] + zonas_x[-1:]
            zonas_2_centro_izq = zonas_3_izq
            zonas_2_centro_der = zonas_3_der
            zonas_2_extremo_izq = zonas_x[1:2]
            zonas_2_extremo_der = zonas_x[4:5]
            indice_zona_1_izq = 1
            indice_zona_1_der = 4

        coords_zonas_3_faldon_izq = []
        coords_zonas_3_faldon_der = []
        for z_inicio, z_fin in zonas_z[:1] + zonas_z[-1:]:
            for zona_x in zonas_3_izq:
                coords_zonas_3_faldon_izq.append(
                    coords_zona_cubierta_desde_proyeccion(zona_x, punto_alero_inicio, punto_mitad, z_inicio, z_fin)
                )
            for zona_x in zonas_3_der:
                coords_zonas_3_faldon_der.append(
                    coords_zona_cubierta_desde_proyeccion(zona_x, punto_mitad, punto_alero_fin, z_inicio, z_fin)
                )
        coords_zonas_2_faldon_izq = []
        coords_zonas_2_faldon_der = []
        for i, (z_inicio, z_fin) in enumerate(zonas_z):
            if i == 1:
                zonas_x_izq = zonas_2_centro_izq
                zonas_x_der = zonas_2_centro_der
            else:
                zonas_x_izq = zonas_2_extremo_izq
                zonas_x_der = zonas_2_extremo_der
            for zona in zonas_x_izq:
                coords_zonas_2_faldon_izq.append(
                    coords_zona_cubierta_desde_proyeccion(zona, punto_alero_inicio, punto_mitad, z_inicio, z_fin)
                )
            for zona in zonas_x_der:
                coords_zonas_2_faldon_der.append(
                    coords_zona_cubierta_desde_proyeccion(zona, punto_mitad, punto_alero_fin, z_inicio, z_fin)
                )
        coords_zona_1_faldon_izq = coords_zona_cubierta_desde_proyeccion(
            zonas_x[indice_zona_1_izq], punto_alero_inicio, punto_mitad, *zonas_z[1]
        )
        coords_zona_1_faldon_der = coords_zona_cubierta_desde_proyeccion(
            zonas_x[indice_zona_1_der], punto_mitad, punto_alero_fin, *zonas_z[1]
        )

        coords_faldon_izq = {
            ZonaComponenteCubiertaEdificio.TRES: coords_zonas_3_faldon_izq,
            ZonaComponenteCubiertaEdificio.DOS: coords_zonas_2_faldon_izq,
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1_faldon_izq,),
        }
        coords_faldon_der = {
            ZonaComponenteCubiertaEdificio.TRES: coords_zonas_3_faldon_der,
            ZonaComponenteCubiertaEdificio.DOS: coords_zonas_2_faldon_der,
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1_faldon_der,),
        }
        coords = {"faldon izq": coords_faldon_izq, "faldon der": coords_faldon_der}

        return coords

    def _cubierta_figura_7a(self):
        punto_alero_inicio = self._inicio_alero_cubierta_un_agua()
        inicio = punto_alero_inicio[0]

        dos_distancia_a = 2 * self._distancia_a
        cuatro_distancia_a = 4 * self._distancia_a

        coords_zona_3 = (
            coords_zona_cubierta_desde_proyeccion(
                (inicio, inicio + dos_distancia_a),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                z_inicio,
                z_fin,
            )
            for z_inicio, z_fin in ((0, -dos_distancia_a), (self.longitud + dos_distancia_a, self.longitud))
        )
        coords_zona_3_prima = (
            coords_zona_cubierta_desde_proyeccion(
                (self.ancho - dos_distancia_a, self.ancho),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                z_inicio,
                z_fin,
            )
            for z_inicio, z_fin in ((0, -cuatro_distancia_a), (self.longitud + cuatro_distancia_a, self.longitud))
        )
        coords_zona_2_prima = tuple(
            coords_zona_cubierta_desde_proyeccion(
                (inicio + dos_distancia_a, self.ancho - dos_distancia_a),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                z_inicio,
                z_fin,
            )
            for z_inicio, z_fin in ((0, -dos_distancia_a), (self.longitud + dos_distancia_a, self.longitud))
        )

        coords_zona_2_prima += (
            coords_zona_cubierta_desde_proyeccion(
                (self.ancho - dos_distancia_a, self.ancho),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                -cuatro_distancia_a,
                self.longitud + cuatro_distancia_a,
            ),
        )

        coords_zona_2 = coords_zona_cubierta_desde_proyeccion(
            (inicio, inicio + self._distancia_a),
            punto_alero_inicio,
            (self.ancho, self.altura_cumbrera),
            -dos_distancia_a,
            self.longitud + dos_distancia_a,
        )

        coords_zona_1 = coords_zona_cubierta_desde_proyeccion(
            (inicio + self._distancia_a, self.ancho - dos_distancia_a),
            punto_alero_inicio,
            (self.ancho, self.altura_cumbrera),
            -dos_distancia_a,
            self.longitud + dos_distancia_a,
        )

        return {
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1,),
            ZonaComponenteCubiertaEdificio.DOS: (coords_zona_2,),
            ZonaComponenteCubiertaEdificio.TRES: coords_zona_3,
            ZonaComponenteCubiertaEdificio.DOS_PRIMA: coords_zona_2_prima,
            ZonaComponenteCubiertaEdificio.TRES_PRIMA: coords_zona_3_prima,
        }

    def _cubierta_figura_7a_cont(self):
        punto_alero_inicio = self._inicio_alero_cubierta_un_agua()
        inicio = punto_alero_inicio[0]

        dos_distancia_a = 2 * self._distancia_a
        cuatro_distancia_a = 4 * self._distancia_a

        coords_zona_3 = (
            coords_zona_cubierta_desde_proyeccion(
                (self.ancho - dos_distancia_a, self.ancho),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                z_inicio,
                z_fin,
            )
            for z_inicio, z_fin in ((0, -cuatro_distancia_a), (self.longitud + cuatro_distancia_a, self.longitud))
        )

        coords_zona_2 = [
            coords_zona_cubierta_desde_proyeccion(
                (inicio + self._distancia_a, self.ancho - dos_distancia_a),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                z_inicio,
                z_fin,
            )
            for z_inicio, z_fin in ((0, -self._distancia_a), (self.longitud + self._distancia_a, self.longitud))
        ]

        coords_zona_2.append(
            coords_zona_cubierta_desde_proyeccion(
                (self.ancho - dos_distancia_a, self.ancho),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                -cuatro_distancia_a,
                self.longitud + cuatro_distancia_a,
            )
        )

        coords_zona_2.append(
            coords_zona_cubierta_desde_proyeccion(
                (inicio, inicio + self._distancia_a),
                punto_alero_inicio,
                (self.ancho, self.altura_cumbrera),
                0,
                self.longitud,
            )
        )

        coords_zona_1 = coords_zona_cubierta_desde_proyeccion(
            (inicio + self._distancia_a, self.ancho - dos_distancia_a),
            punto_alero_inicio,
            (self.ancho, self.altura_cumbrera),
            -self._distancia_a,
            self.longitud + self._distancia_a,
        )

        return {
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1,),
            ZonaComponenteCubiertaEdificio.DOS: coords_zona_2,
            ZonaComponenteCubiertaEdificio.TRES: coords_zona_3,
        }

    def _cubierta_figura_8(self):
        es_cubierta_un_agua = self.tipo_cubierta == TipoCubierta.UN_AGUA

        mitad_ancho = self.ancho / 2
        punto_mitad = (mitad_ancho, self.altura_cumbrera)

        if es_cubierta_un_agua:
            punto_mitad = (mitad_ancho, (self.altura_cumbrera + self.altura_alero) / 2)

        if self.alero_:
            punto_alero_inicio = tuple(punto_sobre_vector(-self.alero_, (0, self.altura_alero), punto_mitad))
            punto_alero_fin = (self.ancho + abs(punto_alero_inicio[0]), punto_alero_inicio[1])
        else:
            punto_alero_inicio = (0, self.altura_alero)
            punto_alero_fin = (self.ancho, self.altura_alero)

        if es_cubierta_un_agua:
            punto_alero_fin = (self.ancho, self.altura_cumbrera)

        dos_distancia_a = 2 * self._distancia_a

        zonas_z = (
            (0, -self._distancia_a),
            (-self._distancia_a, -dos_distancia_a),
            (-dos_distancia_a, self.longitud + dos_distancia_a),
            (self.longitud + dos_distancia_a, self.longitud + self._distancia_a),
            (self.longitud + self._distancia_a, self.longitud),
        )

        inicio = punto_alero_inicio[0]
        fin = punto_alero_fin[0]

        a_inicial_1 = inicio + self._distancia_a
        a_inicial_2 = inicio + dos_distancia_a
        a_final_1 = fin - self._distancia_a
        a_final_2 = fin - dos_distancia_a

        zonas_x = (
            (inicio, a_inicial_1),
            (inicio, a_inicial_2),
            (a_inicial_1, a_inicial_2),
            (a_inicial_2, mitad_ancho),
            (mitad_ancho, a_final_2),
            (a_final_2, a_final_1),
            (a_final_2, fin),
            (a_final_1, fin),
        )

        zonas_3_extremo_izq = zonas_x[1:2]
        zonas_3_extremo_der = zonas_x[6:7]
        zonas_3_centro_izq = zonas_x[:1]
        zonas_3_centro_der = zonas_x[-1:]
        zonas_2_centro_izq = zonas_3_centro_izq
        zonas_2_centro_der = zonas_3_centro_der
        zonas_2_extremo_izq = zonas_x[3:4]
        zonas_2_extremo_der = zonas_x[4:5]
        zona_1_izq = (a_inicial_1, mitad_ancho)
        zona_1_der = (mitad_ancho, a_final_1)

        coords_zonas_3_faldon_izq = []
        coords_zonas_3_faldon_der = []
        for i, (z_inicio, z_fin) in enumerate(zonas_z[:2] + zonas_z[3:]):
            if i in (0, 3):
                zonas_x_izq = zonas_3_extremo_izq
                zonas_x_der = zonas_3_extremo_der
            else:
                zonas_x_izq = zonas_3_centro_izq
                zonas_x_der = zonas_3_centro_der
            for zona_x in zonas_x_izq:
                coords_zonas_3_faldon_izq.append(
                    coords_zona_cubierta_desde_proyeccion(zona_x, punto_alero_inicio, punto_mitad, z_inicio, z_fin)
                )
            for zona_x in zonas_x_der:
                coords_zonas_3_faldon_der.append(
                    coords_zona_cubierta_desde_proyeccion(zona_x, punto_mitad, punto_alero_fin, z_inicio, z_fin)
                )

        coords_zonas_2_faldon_izq = []
        coords_zonas_2_faldon_der = []
        for i, (z_inicio, z_fin) in enumerate(zonas_z[:1] + zonas_z[2:3] + zonas_z[-1:]):
            if i == 1:
                zonas_x_izq = zonas_2_centro_izq
                zonas_x_der = zonas_2_centro_der
            else:
                zonas_x_izq = zonas_2_extremo_izq
                zonas_x_der = zonas_2_extremo_der
            for zona in zonas_x_izq:
                coords_zonas_2_faldon_izq.append(
                    coords_zona_cubierta_desde_proyeccion(zona, punto_alero_inicio, punto_mitad, z_inicio, z_fin)
                )
            for zona in zonas_x_der:
                coords_zonas_2_faldon_der.append(
                    coords_zona_cubierta_desde_proyeccion(zona, punto_mitad, punto_alero_fin, z_inicio, z_fin)
                )
        coords_zona_1_faldon_izq = coords_zona_cubierta_desde_proyeccion(
            zona_1_izq, punto_alero_inicio, punto_mitad, -self._distancia_a, self.longitud + self._distancia_a
        )
        coords_zona_1_faldon_der = coords_zona_cubierta_desde_proyeccion(
            zona_1_der, punto_mitad, punto_alero_fin, -self._distancia_a, self.longitud + self._distancia_a
        )

        coords_faldon_izq = {
            ZonaComponenteCubiertaEdificio.TRES: coords_zonas_3_faldon_izq,
            ZonaComponenteCubiertaEdificio.DOS: coords_zonas_2_faldon_izq,
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1_faldon_izq,),
        }
        coords_faldon_der = {
            ZonaComponenteCubiertaEdificio.TRES: coords_zonas_3_faldon_der,
            ZonaComponenteCubiertaEdificio.DOS: coords_zonas_2_faldon_der,
            ZonaComponenteCubiertaEdificio.UNO: (coords_zona_1_faldon_der,),
        }
        coords = {"faldon izq": coords_faldon_izq, "faldon der": coords_faldon_der}

        return coords

    def _inicio_alero_cubierta_un_agua(self) -> Punto2D:
        """Calcula el punto de inicio del alero para la cubierta a un agua.

        Returns:
            El punto de inicio.
        """
        if self.alero_:
            punto_alero_inicio = tuple(
                punto_sobre_vector(-self.alero_, (0, self.altura_alero), (self.ancho, self.altura_cumbrera))
            )
        else:
            punto_alero_inicio = (0, self.altura_alero)
        return punto_alero_inicio
