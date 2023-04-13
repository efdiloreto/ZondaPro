from __future__ import annotations

from typing import TYPE_CHECKING

from vtkmodules import all as vtk

from zonda.enums import (
    TipoCubierta,
    PosicionBloqueoCubierta,
    PosicionCamara,
    ZonaPresionCubiertaAislada,
    TipoPresionCubiertaAislada,
)
from zonda.graficos.actores import actores_poligonos, color_3d
from zonda.graficos.directores.utils_geometria import (
    coords_zona_cubierta,
    coords_zona_cubierta_desde_proyeccion,
)

if TYPE_CHECKING:
    from zonda.cirsoc import CubiertaAislada


class Geometria:
    """Geometria.
    Representa la geometria de una cubierta aislada. Inicializa los actores y setea las diferentes posiciones de la camara.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        posicion_bloqueo: PosicionBloqueoCubierta = PosicionBloqueoCubierta.ALERO_BAJO,
    ) -> None:
        """
        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
            ancho: El ancho de la cubierta.
            longitud: La longitud de la cubierta.
            altura_alero: La altura de alero de la cubierta.
            altura_cumbrera: La altura de cumbrera de la cubierta.
            tipo_cubierta: El tipo de cubierta.
            posicion_bloqueo: La posicion del bloqueo en la cubierta. Solo es requerida si el tipo de cubierta es a un agua.
        """
        self.actores_cubierta = None

        self.renderer = renderer
        self.ancho = ancho
        # Se pasa a Negativo para que en VTK crezca hacia atras.
        self.longitud = -longitud
        self.altura_alero = altura_alero
        self.altura_cumbrera = altura_cumbrera
        self.tipo_cubierta = tipo_cubierta
        self.posicion_bloqueo = posicion_bloqueo

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
        self.renderer.RemoveAllViewProps()
        self.cubierta()
        self._crear_soportes()

    def setear_posicion_camara(
        self, camara: vtk.vtkCamera, posicion: PosicionCamara
    ) -> None:
        """Setea la posición de la camara.
        Args:
            camara: La camara a la que se le setea la vista.
            posicion: La posición a setear.
        """
        camara.SetFocalPoint(self.ancho / 2, 0, self.longitud / 2)
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
        camara.SetPosition(*posiciones[posicion])

        if posicion == PosicionCamara.SUPERIOR:
            vector_altura = (1, 0, 0)
        else:
            vector_altura = (0, 1, 0)
        camara.SetViewUp(*vector_altura)
        self.renderer.ResetCamera()

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
        for x, y, z in (
            (0, 0, 0),
            (self.ancho, 0, 0),
            (0, 0, self.longitud),
            (self.ancho, 0, self.longitud),
        ):
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(x, y, z)
            if x == self.ancho and self.tipo_cubierta == TipoCubierta.UN_AGUA:
                altura = self.altura_cumbrera
            else:
                altura = self.altura_alero
            line_source.SetPoint2(x, altura, z)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_source.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetLineWidth(2)
            actor.GetProperty().SetColor(color_3d("black"))
            self.renderer.AddActor(actor)


class Presiones(Geometria):
    """Presiones.

    Representa las zonas de presiones para los casos globales y locales de una cubierta aislada. Inicializa los actores,
    setea las diferentes posiciones de la camara y provee los actores correspondientes dependiendo del tipo de presión.
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        tabla_colores: vtk.vtkLookupTable,
        cubierta_aislada: CubiertaAislada,
    ) -> None:
        """

        Args:
            renderer: El renderer utilizado para limpiar la escena y resetear la cámara.
            tabla_colores: La tabla de escalas de colores de la escena general.
            cubierta_aislada: Una instancia de CubiertaAislada.
        """
        super().__init__(
            renderer,
            cubierta_aislada.ancho,
            cubierta_aislada.longitud,
            cubierta_aislada.altura_alero,
            cubierta_aislada.altura_cumbrera,
            cubierta_aislada.tipo_cubierta,
            cubierta_aislada.posicion_bloqueo,
        )
        self.tabla_colores = tabla_colores
        self.tipo_presion = None

        self.inicializar_actores()

    def obtener_actores(self):
        return self.actores_cubierta[self.tipo_presion]

    @actores_poligonos(crear_atributo=True, presion=True, mostrar=False)
    def cubierta(self):
        if self.tipo_cubierta == TipoCubierta.DOS_AGUAS:
            actores_presion_local = self._cubierta_dos_aguas()
            actores_presion_global = super()._cubierta_dos_aguas()
        else:
            actores_presion_local = self._cubierta_un_agua()
            actores_presion_global = super()._cubierta_un_agua()
        return {
            TipoPresionCubiertaAislada.GLOBAL: actores_presion_global,
            TipoPresionCubiertaAislada.LOCAL: actores_presion_local,
        }

    def inicializar_actores(self) -> None:
        """Elimina los actores existentes y genera y añade los actores generados por cada función."""
        self.cubierta()
        self._crear_soportes()

    def _cubierta_un_agua(self):
        punto_inicio = (0, self.altura_alero)
        punto_fin = (self.ancho, self.altura_cumbrera)

        long_dividida = self.longitud / 10
        ancho_dividido = self.ancho / 10

        zonas_z = (
            (0, long_dividida),
            (long_dividida, self.longitud - long_dividida),
            (self.longitud - long_dividida, self.longitud),
        )

        fin_ancho_div_resta = self.ancho - ancho_dividido

        zonas_x = (
            (0, ancho_dividido),
            (ancho_dividido, fin_ancho_div_resta),
            (fin_ancho_div_resta, self.ancho),
        )

        zonas_c = zonas_x[:1] + zonas_x[-1:]

        coords_zonas_b = []
        coords_zonas_bc = []
        for z_inicio, z_fin in zonas_z[:1] + zonas_z[-1:]:
            coords_zonas_b.append(
                coords_zona_cubierta_desde_proyeccion(
                    zonas_x[1], punto_inicio, punto_fin, z_inicio, z_fin
                )
            )
            for zona_x in zonas_c:
                coords_zonas_bc.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_fin, z_inicio, z_fin
                    )
                )

        coords_zonas_a = coords_zona_cubierta_desde_proyeccion(
            zonas_x[1], punto_inicio, punto_fin, *zonas_z[1]
        )

        coords_zonas_c = []
        for zona_x in zonas_c:
            coords_zonas_c.append(
                coords_zona_cubierta_desde_proyeccion(
                    zona_x, punto_inicio, punto_fin, *zonas_z[1]
                )
            )

        return {
            ZonaPresionCubiertaAislada.A: coords_zonas_a,
            ZonaPresionCubiertaAislada.B: coords_zonas_b,
            ZonaPresionCubiertaAislada.C: coords_zonas_c,
            ZonaPresionCubiertaAislada.BC: coords_zonas_bc,
        }

    def _cubierta_dos_aguas(self):
        punto_inicio = (0, self.altura_alero)
        punto_fin = (self.ancho, self.altura_alero)
        mitad_ancho = self.ancho / 2
        punto_mitad = (mitad_ancho, self.altura_cumbrera)

        long_dividida = self.longitud / 10
        ancho_dividido = self.ancho / 10

        zonas_z = (
            (0, long_dividida),
            (long_dividida, self.longitud - long_dividida),
            (self.longitud - long_dividida, self.longitud),
        )

        mitad_ancho_div_resta = mitad_ancho - ancho_dividido
        mitad_ancho_div_suma = mitad_ancho + ancho_dividido
        fin_ancho_div_resta = self.ancho - ancho_dividido

        zonas_x = (
            (0, ancho_dividido),
            (ancho_dividido, mitad_ancho_div_resta),
            (mitad_ancho_div_resta, mitad_ancho),
            (mitad_ancho, mitad_ancho_div_suma),
            (mitad_ancho_div_suma, fin_ancho_div_resta),
            (fin_ancho_div_resta, self.ancho),
        )
        zonas_b_izq = zonas_x[1:2]
        zonas_b_der = zonas_x[4:5]
        zonas_a_izq = zonas_b_izq
        zonas_a_der = zonas_b_der
        zonas_c_izq = zonas_x[:1]
        zonas_c_der = zonas_x[-1:]
        zonas_d_izq = zonas_x[2:3]
        zonas_d_der = zonas_x[3:4]
        zonas_esq_bc_izq = zonas_c_izq
        zonas_esq_bc_der = zonas_c_der
        zonas_esq_bd_izq = zonas_d_izq
        zonas_esq_bd_der = zonas_d_der

        coords_zonas_b = []
        coords_zonas_bc = []
        coords_zonas_bd = []
        for z_inicio, z_fin in zonas_z[:1] + zonas_z[-1:]:
            for zona_x in zonas_b_izq:
                coords_zonas_b.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_b_der:
                coords_zonas_b.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_esq_bc_izq:
                coords_zonas_bc.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_esq_bc_der:
                coords_zonas_bc.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_esq_bd_izq:
                coords_zonas_bd.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_esq_bd_der:
                coords_zonas_bd.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )

        coords_zonas_a = []
        coords_zonas_c = []
        coords_zonas_d = []
        for z_inicio, z_fin in zonas_z[1:2]:
            for zona_x in zonas_a_izq:
                coords_zonas_a.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_a_der:
                coords_zonas_a.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_c_izq:
                coords_zonas_c.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_c_der:
                coords_zonas_c.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_d_izq:
                coords_zonas_d.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_inicio, punto_mitad, z_inicio, z_fin
                    )
                )
            for zona_x in zonas_d_der:
                coords_zonas_d.append(
                    coords_zona_cubierta_desde_proyeccion(
                        zona_x, punto_mitad, punto_fin, z_inicio, z_fin
                    )
                )

        return {
            ZonaPresionCubiertaAislada.A: coords_zonas_a,
            ZonaPresionCubiertaAislada.B: coords_zonas_b,
            ZonaPresionCubiertaAislada.C: coords_zonas_c,
            ZonaPresionCubiertaAislada.D: coords_zonas_d,
            ZonaPresionCubiertaAislada.BC: coords_zonas_bc,
            ZonaPresionCubiertaAislada.BD: coords_zonas_bd,
        }
